#!/usr/bin/env python3
"""
data_downloader.py 单元测试

覆盖:
- RateLimiter.wait(): 180/min 限频验证
- is_up_to_date(): 增量检测（数据新鲜 / 数据过期）
- download_single(): 单只股票下载成功
- download_single(): 重试逻辑（轮换数据源）

注意: 所有外部依赖 (Tushare/AKShare/Baostock API, subprocess) 均通过 mock 模拟，
      测试不依赖外部服务。
"""

import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# 将 examples/alpha_research 加入 sys.path，使 data_downloader 可导入
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'examples' / 'alpha_research'))

from data_downloader import RateLimiter, DataDownloader, DownloaderConfig, DownloadResult


# ---------------------------------------------------------------------------
# RateLimiter 测试
# ---------------------------------------------------------------------------
class TestRateLimiter:
    """RateLimiter 限频控制测试"""

    def test_rate_limiter_wait(self):
        """验证 180/min 限频：两次调用间隔应 >= 60/180 ≈ 0.333 秒"""
        limiter = RateLimiter(max_per_minute=180)
        expected_interval = 60.0 / 180  # ≈ 0.3333 秒

        # 第一次 wait()：_last_call=0，无需等待，仅设置 _last_call
        limiter.wait()
        t0 = time.time()

        # 第二次 wait()：应等待约 expected_interval 秒
        limiter.wait()
        elapsed = time.time() - t0

        # 允许 20% 误差（系统调度抖动）
        assert elapsed >= expected_interval * 0.8, (
            f"限频间隔过短: {elapsed:.3f}s < {expected_interval * 0.8:.3f}s"
        )
        # 不应等待太久（不超过 2 倍间隔 + 0.1s 容差）
        assert elapsed < expected_interval * 2 + 0.1, (
            f"限频间隔过长: {elapsed:.3f}s"
        )


# ---------------------------------------------------------------------------
# is_up_to_date 增量检测测试
# ---------------------------------------------------------------------------
class TestIsUpToDate:
    """is_up_to_date() 增量检测测试"""

    @pytest.fixture
    def downloader(self, tmp_path):
        """创建一个使用临时目录的 DataDownloader 实例"""
        config = DownloaderConfig(data_dir=str(tmp_path))
        return DataDownloader(config=config)

    def test_is_up_to_date_fresh(self, downloader, tmp_path):
        """增量检测：数据新鲜时返回 True（最后日期 >= 今天 - max_age_days）"""
        symbol = '000001.SZSE'
        csv_path = tmp_path / f"{symbol}.csv"

        # 写入 CSV：header + 1 行，日期为今天
        today_str = datetime.now().strftime('%Y-%m-%d')
        csv_path.write_text(f"symbol,date,open,close\n{symbol},{today_str},10.0,10.5\n")

        # mock subprocess.run 返回 tail 输出
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"symbol,date,open,close\n{symbol},{today_str},10.0,10.5\n"

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            result = downloader.is_up_to_date(symbol, max_age_days=1)

        assert result is True, "新鲜数据应返回 True"
        mock_run.assert_called_once()

    def test_is_up_to_date_stale(self, downloader, tmp_path):
        """增量检测：数据过期时返回 False（最后日期 < 今天 - max_age_days）"""
        symbol = '000002.SZSE'

        # 数据日期为 3 天前（超过 max_age_days=1）
        stale_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"symbol,date,open,close\n{symbol},{stale_date},10.0,10.5\n"

        with patch('subprocess.run', return_value=mock_result):
            result = downloader.is_up_to_date(symbol, max_age_days=1)

        assert result is False, "过期数据应返回 False"

    def test_is_up_to_date_no_file(self, downloader):
        """增量检测：文件不存在时返回 False"""
        result = downloader.is_up_to_date('999999.SZSE', max_age_days=1)
        assert result is False


# ---------------------------------------------------------------------------
# download_single 测试
# ---------------------------------------------------------------------------
class TestDownloadSingle:
    """download_single() 下载逻辑测试"""

    @pytest.fixture
    def downloader(self, tmp_path):
        """创建一个使用临时目录的 DataDownloader 实例"""
        config = DownloaderConfig(
            data_dir=str(tmp_path),
            max_retries=3,
            base_delay=0.01,  # 测试用极短延迟
            max_delay=0.05,
        )
        return DataDownloader(config=config)

    @patch('data_downloader.get_stock_bars_akshare')
    @patch('data_downloader.USE_TUSHARE', True)
    def test_download_single_success(self, mock_akshare, downloader, tmp_path):
        """单只股票下载成功：Tushare 首次调用成功"""
        symbol = '000001.SZSE'
        fake_df = pd.DataFrame({
            'date': ['2026-06-20', '2026-06-21'],
            'open': [10.0, 10.5],
            'close': [10.5, 11.0],
            'volume': [1000, 1200],
        })

        # mock Tushare 成功返回
        with patch('data_downloader.get_stock_bars_tushare', return_value=fake_df) as mock_tushare:
            # mock 限频器避免真实等待
            with patch.object(downloader._rate_limiter, 'wait'):
                result = downloader.download_single(symbol)

        assert result.status == 'success'
        assert result.source == 'tushare'
        assert result.rows == 2
        assert result.symbol == symbol
        # 验证 CSV 已写入
        csv_path = tmp_path / f"{symbol}.csv"
        assert csv_path.exists()

    @patch('data_downloader.get_stock_bars_baostock')
    @patch('data_downloader.get_stock_bars_akshare')
    @patch('data_downloader.get_stock_bars_tushare')
    @patch('data_downloader.USE_TUSHARE', True)
    def test_download_single_retry(self, mock_tushare, mock_akshare, mock_baostock, downloader):
        """重试逻辑：Tushare 失败 → AKShare 失败 → Baostock 成功（轮换数据源）"""
        symbol = '000002.SZSE'
        fake_df = pd.DataFrame({
            'date': ['2026-06-21'],
            'open': [20.0],
            'close': [21.0],
            'volume': [500],
        })

        # Tushare 抛异常
        mock_tushare.side_effect = Exception("Tushare API timeout")
        # AKShare 返回空 DataFrame
        mock_akshare.return_value = pd.DataFrame()
        # Baostock 成功
        mock_baostock.return_value = fake_df

        # mock 限频器和 sleep 避免真实等待
        with patch.object(downloader._rate_limiter, 'wait'):
            with patch('data_downloader.time.sleep'):
                result = downloader.download_single(symbol)

        assert result.status == 'success', f"预期成功，实际: {result.status}, error={result.error}"
        assert result.source == 'baostock', f"预期 baostock 数据源，实际: {result.source}"
        assert result.rows == 1

        # 验证三个数据源各被调用一次（轮换）
        mock_tushare.assert_called_once()
        mock_akshare.assert_called_once()
        mock_baostock.assert_called_once()

    @patch('data_downloader.get_stock_bars_baostock')
    @patch('data_downloader.get_stock_bars_akshare')
    @patch('data_downloader.get_stock_bars_tushare')
    @patch('data_downloader.USE_TUSHARE', True)
    def test_download_single_all_fail(self, mock_tushare, mock_akshare, mock_baostock, downloader):
        """全部数据源失败时返回 failed 状态"""
        symbol = '000003.SZSE'

        mock_tushare.side_effect = Exception("Tushare error")
        mock_akshare.side_effect = Exception("AKShare error")
        mock_baostock.side_effect = Exception("Baostock error")

        with patch.object(downloader._rate_limiter, 'wait'):
            with patch('data_downloader.time.sleep'):
                with patch('data_downloader.add_to_failed_queue'):
                    result = downloader.download_single(symbol)

        assert result.status == 'failed'
        assert result.source == 'none'
        assert 'error' in result.error.lower() or 'attempt' in result.error.lower()
