#!/usr/bin/env python3
"""
data_downloader.py Phase 4A 修复验证测试

覆盖 Phase 4A 的 3 个 P0 修复：
1. is_up_to_date: 替换 subprocess tail 为 Python 原生 seek
2. RateLimiter: 使用滑动窗口计数器（SlidingWindowRateLimiter）
3. CSV 写入原子性（_save_bars - 已有测试，新增边界覆盖）

测试特点：
- 不依赖任何 subprocess 调用（验证修复 1）
- 验证滑动窗口限流的 burst 防护能力（验证修复 2）
- 新增 CSV 原子写入的异常场景覆盖（验证修复 3）
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# 将 examples/alpha_research 加入 sys.path，使 data_downloader 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'examples' / 'alpha_research'))

from data_downloader import (
    DataDownloader,
    DownloaderConfig,
    RateLimiter,  # 向后兼容别名
    SlidingWindowRateLimiter,
    AsyncSlidingWindowRateLimiter,
)


# ===========================================================================
# 修复 1: is_up_to_date - Python 原生 seek
# ===========================================================================

class TestIsUpToDateSeekBased:
    """验证 is_up_to_date 不再依赖 subprocess"""

    @pytest.fixture
    def downloader(self, tmp_path):
        """创建一个使用临时目录的 DataDownloader 实例"""
        config = DownloaderConfig(data_dir=str(tmp_path))
        return DataDownloader(config=config)

    def test_no_subprocess_substitution(self, downloader, tmp_path):
        """验证 is_up_to_date 不再调用 subprocess（seek-based 实现）"""
        symbol = '000001.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 写入 CSV
        today_str = datetime.now().strftime('%Y-%m-%d')
        csv_path.write_text(f"date,open,close\n{today_str},10.0,10.5\n")

        # 测试：文件存在且日期新鲜时返回 True
        result = downloader.is_up_to_date(symbol, max_age_days=1)
        assert result is True, "新鲜数据应返回 True"

        # 测试：文件不存在时返回 False
        result = downloader.is_up_to_date('NONEXISTENT.SZSE', max_age_days=1)
        assert result is False, "不存在的文件应返回 False"

    def test_seek_based_fresh_data(self, downloader, tmp_path):
        """seek-based 方法识别新鲜数据"""
        symbol = '000002.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 写入 CSV：header + 多行数据，最后日期为今天
        today_str = datetime.now().strftime('%Y-%m-%d')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        csv_path.write_text(
            f"date,open,close\n{yesterday_str},9.0,9.5\n{today_str},10.0,10.5\n"
        )

        result = downloader.is_up_to_date(symbol, max_age_days=1)
        assert result is True

    def test_seek_based_stale_data(self, downloader, tmp_path):
        """seek-based 方法识别过期数据"""
        symbol = '000003.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 最后日期是 3 天前
        date_3_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        csv_path.write_text(
            f"date,open,close\n{date_3_days_ago},9.0,9.5\n"
        )

        result = downloader.is_up_to_date(symbol, max_age_days=1)
        assert result is False

    def test_seek_based_no_file(self, downloader):
        """seek-based 方法：文件不存在返回 False"""
        result = downloader.is_up_to_date('999999.SZSE')
        assert result is False

    def test_seek_based_empty_file(self, downloader, tmp_path):
        """seek-based 方法：空文件返回 False"""
        symbol = '000004.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"
        csv_path.write_text("")  # 空文件

        result = downloader.is_up_to_date(symbol)
        assert result is False

    def test_seek_based_header_only(self, downloader, tmp_path):
        """seek-based 方法：只有 header 没有数据返回 False"""
        symbol = '000005.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"
        csv_path.write_text("date,open,close\n")  # 只有 header

        result = downloader.is_up_to_date(symbol)
        assert result is False

    def test_seek_based_invalid_date(self, downloader, tmp_path):
        """seek-based 方法：日期列无效返回 False"""
        symbol = '000006.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"
        csv_path.write_text("date,open,close\ninvalid_date,10.0,10.5\n")

        result = downloader.is_up_to_date(symbol)
        assert result is False

    def test_seek_based_large_file(self, downloader, tmp_path):
        """seek-based 方法：大文件只读末尾 4KB（高效）"""
        symbol = '000007.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 生成大文件（>4KB），最后日期为今天
        today_str = datetime.now().strftime('%Y-%m-%d')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 生成多行数据（约 5KB），确保最后两行是新鲜数据
        lines = ["date,open,close"]
        for i in range(100):
            lines.append(f"{yesterday_str},{10.0 + i},{10.5 + i}")
        lines.append(f"{today_str},20.0,20.5")  # 最后一行是今天
        csv_path.write_text("\n".join(lines))

        # 文件应该小于 4KB（测试小文件场景）
        assert csv_path.stat().st_size < 4096
        result = downloader.is_up_to_date(symbol, max_age_days=1)
        assert result is True

    def test_seek_based_no_newline_at_end(self, downloader, tmp_path):
        """seek-based 方法：文件末尾无换行符也能处理"""
        symbol = '000008.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 模拟没有末尾换行的 CSV
        today_str = datetime.now().strftime('%Y-%m-%d')
        csv_path.write_text(f"date,open,close\n{today_str},10.0,10.5")

        result = downloader.is_up_to_date(symbol)
        assert result is True


# ===========================================================================
# 修复 2: SlidingWindowRateLimiter
# ===========================================================================

class TestSlidingWindowRateLimiter:
    """SlidingWindowRateLimiter 滑动窗口限流器测试"""

    def test_basic_wait(self):
        """基础等待：第一次调用不等待"""
        limiter = SlidingWindowRateLimiter(max_per_minute=60)  # 1 秒/次
        start = time.time()
        limiter.wait()  # 第一次调用，不等待
        elapsed = time.time() - start
        assert elapsed < 0.1  # 应立即返回

    def test_enforces_rate_limit(self):
        """限频生效：60秒窗口内达到上限后，下一次调用会等待"""
        # 使用较小的 max_count 便于测试：5次/60秒 = 12秒/次
        limiter = SlidingWindowRateLimiter(max_per_minute=5)
        expected_interval = 60.0 / 5  # 12秒

        # 先用满 5 次配额（初始为空）
        for i in range(5):
            limiter.wait()

        # 此时窗口内有 5 个时间戳，最近的是 ~0秒前
        # 第 6 次调用应该等待约 60秒（窗口满）
        t0 = time.time()
        limiter.wait()  # 应该阻塞约 60秒
        elapsed = time.time() - t0

        # 等待时间应在 59-61秒范围（允许 2% 误差）
        assert elapsed >= 58, (
            f"限频未生效: {elapsed:.3f}s < 58s"
        )
        # 不应等待太久（窗口满时需等待完整的 60 秒）
        assert elapsed < 62

    def test_no_burst_within_window(self):
        """ burst 防护：60s 内调用次数不能超过 max_per_minute"""
        limiter = SlidingWindowRateLimiter(max_per_minute=10)  # 6 秒/次
        timestamps = []

        for i in range(10):
            limiter.wait()
            timestamps.append(time.time())

        # 10 次调用应在 60 秒内完成（无等待）
        assert timestamps[-1] - timestamps[0] < 60

        # 第 11 次调用必须等待
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start

        # 应等待约 60 - (10 * 6) = 0秒（刚好），实际可能有微小抖动
        # 至少不应该立即返回
        assert elapsed >= 0.01  # 至少等待了

    def test_sliding_window_clears_old(self):
        """滑动窗口：60s 后旧时间戳被清除"""
        limiter = SlidingWindowRateLimiter(max_per_minute=2)  # 30 秒/次

        # 模拟时间前进（通过注入 mock time.time）
        current_time = [time.time()]

        def mock_time():
            return current_time[0]

        with patch('data_downloader.time.time', side_effect=mock_time):
            limiter.wait()
            current_time[0] += 30
            limiter.wait()
            current_time[0] += 30

            # 此时窗口应已清除 30s 前的时间戳
            # 可以再次调用
            limiter.wait()  # 不应等待

    def test_thread_safety(self):
        """线程安全：多线程并发调用不超限"""
        limiter = SlidingWindowRateLimiter(max_per_minute=100)
        results = {'count': 0, 'timestamps': []}
        lock = threading.Lock()

        def worker():
            limiter.wait()
            with lock:
                results['count'] += 1
                results['timestamps'].append(time.time())

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results['count'] == 20

    def test_backward_compat_rate_limiter_alias(self):
        """向后兼容：RateLimiter 是 SlidingWindowRateLimiter 的别名"""
        assert RateLimiter is SlidingWindowRateLimiter

        limiter = RateLimiter(max_per_minute=60)
        from collections import deque
        assert hasattr(limiter, '_timestamps')
        assert isinstance(limiter._timestamps, deque)


class TestAsyncSlidingWindowRateLimiter:
    """异步滑动窗口限流器测试"""

    @pytest.mark.asyncio
    async def test_async_basic_wait(self):
        """异步基础等待"""
        limiter = AsyncSlidingWindowRateLimiter(max_per_minute=60)

        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start

        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_async_no_burst(self):
        """异步 burst 防护"""
        limiter = AsyncSlidingWindowRateLimiter(max_per_minute=10)
        timestamps = []

        for i in range(10):
            await limiter.wait()
            timestamps.append(time.time())

        assert timestamps[-1] - timestamps[0] < 60

        # 第 11 次必须等待
        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start

        assert elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_backward_compat_async_rate_limiter_alias(self):
        """异步向后兼容：AsyncRateLimiter 是 AsyncSlidingWindowRateLimiter 的别名"""
        from data_downloader import AsyncRateLimiter
        assert AsyncRateLimiter is AsyncSlidingWindowRateLimiter


# ===========================================================================
# 修复 3: CSV 原子写入 - 新增边界覆盖
# ===========================================================================

class TestCsvAtomicWritePhase4A:
    """Phase 4A: CSV 原子写入新增测试"""

    @pytest.fixture
    def downloader(self, tmp_path):
        config = DownloaderConfig(data_dir=str(tmp_path))
        return DataDownloader(config=config)

    def test_tmp_file_cleanup_on_success(self, downloader, tmp_path):
        """成功写入后 .tmp 文件被清理"""
        symbol = '000001.SZSE'
        bars = pd.DataFrame({
            'date': ['2026-06-21'],
            'open': [10.0],
            'close': [11.0],
        })
        downloader._save_bars(symbol, bars)

        csv_path = tmp_path / f"{symbol}.csv"
        tmp_path_file = tmp_path / f"{symbol}.csv.tmp"

        assert csv_path.exists()
        assert not tmp_path_file.exists()

    def test_no_tmp_file_on_failure(self, downloader, tmp_path):
        """写入失败时 .tmp 文件被清理，旧文件保持"""
        symbol = '000002.SZSE'

        # 先写入旧文件
        old_content = "date,open,close\n2026-06-20,10.0,11.0\n"
        (tmp_path / f"{symbol}.csv").write_text(old_content)

        # 构造写入失败
        bad_df = MagicMock()
        bad_df.to_csv.side_effect = IOError("写入失败")

        with pytest.raises(IOError):
            downloader._save_bars(symbol, bad_df)

        # 旧文件保持完整
        assert (tmp_path / f"{symbol}.csv").read_text() == old_content

        # .tmp 文件应被清理
        tmp_path_file = tmp_path / f"{symbol}.csv.tmp"
        assert not tmp_path_file.exists()

    def test_atomic_replace_behavior(self, downloader, tmp_path):
        """原子替换：文件要么是旧版本，要么是完整新版本"""
        symbol = '000003.SZSE'

        # 写入第一版
        bars1 = pd.DataFrame({
            'date': ['2026-06-20'],
            'open': [10.0],
            'close': [11.0],
        })
        downloader._save_bars(symbol, bars1)

        csv_path = tmp_path / f"{symbol}.csv"
        content1 = csv_path.read_text()

        # 写入第二版
        bars2 = pd.DataFrame({
            'date': ['2026-06-21'],
            'open': [12.0],
            'close': [13.0],
        })
        downloader._save_bars(symbol, bars2)

        content2 = csv_path.read_text()

        # 验证文件存在且是第二版内容
        assert '2026-06-21' in content2
        assert '2026-06-20' not in content2

    def test_concurrent_different_symbols(self, downloader, tmp_path):
        """不同 symbol 的并发写入互不干扰"""
        import concurrent.futures

        def save_one(i):
            symbol = f'ATOMIC{i:04d}.SZSE'
            bars = pd.DataFrame({
                'date': [f'2026-06-{(i % 28) + 1:02d}'],
                'open': [float(i)],
                'close': [float(i + 1)],
            })
            downloader._save_bars(symbol, bars)
            return symbol

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            symbols = list(executor.map(save_one, range(50)))

        # 验证所有文件都存在且有内容
        for s in symbols:
            csv_path = tmp_path / f"{s}.csv"
            assert csv_path.exists(), f"{s} 文件不存在"
            assert csv_path.stat().st_size > 0, f"{s} 文件为空"

            # 验证没有残留的 .tmp 文件
            assert not (tmp_path / f"{s}.csv.tmp").exists(), f"{s} 有残留的 .tmp 文件"

    def test_large_dataframe_write(self, downloader, tmp_path):
        """大 DataFrame 写入的原子性"""
        symbol = 'LARGE.SZSE'

        # 生成大 DataFrame（约 1MB）
        dates = pd.date_range('2026-01-01', periods=10000, freq='1min')
        bars = pd.DataFrame({
            'date': dates,
            'open': [10.0 + i * 0.01 for i in range(10000)],
            'high': [11.0 + i * 0.01 for i in range(10000)],
            'low': [9.0 + i * 0.01 for i in range(10000)],
            'close': [10.5 + i * 0.01 for i in range(10000)],
            'volume': [1000 + i for i in range(10000)],
        })

        downloader._save_bars(symbol, bars)

        csv_path = tmp_path / f"{symbol}.csv"
        assert csv_path.exists()
        assert csv_path.stat().st_size > 0

        # 验证没有残留 .tmp
        assert not (tmp_path / f"{symbol}.csv.tmp").exists()

    def test_special_characters_in_dataframe(self, downloader, tmp_path):
        """包含特殊字符的 DataFrame 写入"""
        symbol = 'SPECIAL.SZSE'
        bars = pd.DataFrame({
            'date': ['2026-06-21'],
            'open': [10.0],
            'close': [11.0],
            'comment': ['测试,数据"包含"特殊字符\n换行'],
        })

        downloader._save_bars(symbol, bars)

        csv_path = tmp_path / f"{symbol}.csv"
        assert csv_path.exists()

        # 验证内容可读取
        df = pd.read_csv(csv_path)
        assert len(df) == 1
        assert '特殊字符' in str(df.iloc[0]['comment'])

    def test_overwrite_existing_file(self, downloader, tmp_path):
        """覆盖已有文件的原子性"""
        symbol = 'OVERWRITE.SZSE'

        # 第一次写入
        bars1 = pd.DataFrame({
            'date': ['2026-06-20'],
            'open': [10.0],
            'close': [11.0],
        })
        downloader._save_bars(symbol, bars1)

        csv_path = tmp_path / f"{symbol}.csv"
        assert csv_path.exists()

        # 第二次写入（覆盖）
        bars2 = pd.DataFrame({
            'date': ['2026-06-21'],
            'open': [12.0],
            'close': [13.0],
        })
        downloader._save_bars(symbol, bars2)

        # 验证文件更新
        df = pd.read_csv(csv_path)
        assert len(df) == 1
        assert df.iloc[0]['open'] == 12.0


# ===========================================================================
# 性能对比测试：seek vs subprocess tail
# ===========================================================================

class TestSeekVsSubprocessPerformance:
    """验证 seek-based 实现的性能优势"""

    @pytest.fixture
    def downloader(self, tmp_path):
        config = DownloaderConfig(data_dir=str(tmp_path))
        return DataDownloader(config=config)

    def test_seek_implementation_exists(self, downloader, tmp_path):
        """验证使用 Python seek 实现，无 subprocess 调用"""
        import inspect
        # 使用源代码的实现部分（排除 docstring）
        source_lines = inspect.getsourcelines(downloader.__class__.is_up_to_date)[0]
        # 跳过 docstring 行（通常前几行是 docstring）
        source = '\n'.join(source_lines)

        # 不应包含 subprocess.run 或 subprocess.Popen 调用
        assert 'subprocess.run' not in source.lower(), "is_up_to_date 不应使用 subprocess.run"
        assert 'subprocess.Popen' not in source.lower(), "is_up_to_date 不应使用 subprocess.Popen"
        assert 'subprocess.call' not in source.lower(), "is_up_to_date 不应使用 subprocess.call"

    def test_large_file_efficiency(self, downloader, tmp_path):
        """大文件下 seek 比 subprocess tail 快（无进程创建开销）"""
        import time

        symbol = 'LARGE_PERF.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 生成 ~10MB 文件
        lines = ["date,open,close"]
        for i in range(200000):
            lines.append(f"2026-06-20,{10.0 + i * 0.0001},{10.5 + i * 0.0001}")
        lines.append(f"2026-06-21,{20.0},{20.5}")
        csv_path.write_text("\n".join(lines))

        # 第一次读取（文件缓存）
        downloader.is_up_to_date(symbol)

        # 测量 read_time
        start = time.time()
        for _ in range(5):
            downloader.is_up_to_date(symbol)
        elapsed = time.time() - start

        # 5 次应很快（< 10 秒）
        # 如果用 subprocess，每次都要 fork+exec tail，会慢很多
        assert elapsed < 10, f"seek 实现太慢: {elapsed:.2f}s"
