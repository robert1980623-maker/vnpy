"""
统一数据下载器

提供 DataDownloader 类，直接 import download_data_akshare 中的函数，
避免 subprocess 开销。支持：
- 并发下载（ThreadPoolExecutor）
- 增量检测（跳过已有最新数据的股票）
- 失败队列（持久化 + 自动重试）
- 双数据源（Tushare 主 + AKShare/Baostock 备）

用法:
    from data_downloader import DataDownloader, DownloaderConfig
    config = DownloaderConfig(max_workers=4)
    downloader = DataDownloader(config)
    results = downloader.download_batch(['000001.SZSE', '000002.SZSE'])
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Literal, Callable, Tuple

import pandas as pd


# ==================== 限频控制 ====================

class RateLimiter:
    """
    简单的令牌桶限流器（线程安全）

    用于控制 API 调用频率，避免触发数据源限频。
    Tushare 限频 200次/分钟，默认设置 180次/分钟（留 10% 余量）。
    """

    def __init__(self, max_per_minute: int = 180):
        self.interval = 60.0 / max_per_minute
        self._lock = Lock()
        self._last_call = 0.0

    def wait(self):
        """等待直到可以发起下一次调用"""
        with self._lock:
            now = time.time()
            wait = self.interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()

# 导入底层下载函数（直接调用，不开子进程）
from download_data_akshare import (
    get_stock_bars_akshare,
    get_stock_bars_baostock,
    get_stock_bars_tushare,
    USE_TUSHARE,
)

# 失败队列文件路径
_FAILED_DOWNLOADS_FILE = Path(__file__).parent / 'failed_downloads.json'
_FAILED_LOCK = Lock()

logger = logging.getLogger(__name__)


# ==================== 配置与结果数据结构 ====================

@dataclass
class DownloaderConfig:
    """
    下载器配置

    Attributes:
        max_workers: 并发线程数
        stock_delay: 股票间延迟（秒，串行模式使用）
        batch_delay: 批次间延迟（秒）
        batch_size: 批次大小
        max_retries: 单只股票最大重试次数
        base_delay: 重试基础延迟（秒）
        max_delay: 重试最大延迟（秒）
        timeout: 单次下载超时（秒）
        data_dir: 数据目录
        failed_queue_file: 失败队列文件路径
    """
    max_workers: int = 4
    stock_delay: float = 1.0
    batch_delay: float = 5.0
    batch_size: int = 50
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    timeout: float = 120.0
    data_dir: str = './data/akshare/bars'
    failed_queue_file: str = './failed_downloads.json'


@dataclass
class DownloadResult:
    """
    单只股票下载结果

    Attributes:
        symbol: 股票代码
        status: 下载状态 ('success' | 'failed' | 'skipped')
        source: 数据来源 ('tushare' | 'akshare' | 'baostock' | 'cache' | 'none')
        rows: 数据行数
        duration: 下载耗时（秒）
        error: 错误信息（失败时）
    """
    symbol: str
    status: Literal['success', 'failed', 'skipped']
    source: Literal['tushare', 'akshare', 'baostock', 'cache', 'none'] = 'none'
    rows: int = 0
    duration: float = 0.0
    error: str = ''

    def to_dict(self) -> dict:
        """转换为字典（兼容旧接口）"""
        return asdict(self)

    @property
    def ok(self) -> bool:
        """是否成功"""
        return self.status == 'success'


# ==================== 失败队列 ====================

def load_failed_downloads() -> dict:
    """加载失败队列（线程安全）"""
    with _FAILED_LOCK:
        if _FAILED_DOWNLOADS_FILE.exists():
            try:
                with open(_FAILED_DOWNLOADS_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}


def save_failed_downloads(failed: dict):
    """保存失败队列（线程安全）"""
    with _FAILED_LOCK:
        with open(_FAILED_DOWNLOADS_FILE, 'w') as f:
            json.dump(failed, f, indent=2)


def add_to_failed_queue(symbol: str, error: str):
    """添加失败股票到队列"""
    with _FAILED_LOCK:
        failed = {}
        if _FAILED_DOWNLOADS_FILE.exists():
            try:
                with open(_FAILED_DOWNLOADS_FILE, 'r') as f:
                    failed = json.load(f)
            except Exception:
                failed = {}
        if symbol not in failed:
            failed[symbol] = {'error': error, 'count': 1, 'last_try': datetime.now().isoformat()}
        else:
            failed[symbol]['count'] += 1
            failed[symbol]['last_try'] = datetime.now().isoformat()
        with open(_FAILED_DOWNLOADS_FILE, 'w') as f:
            json.dump(failed, f, indent=2)


def remove_from_failed_queue(symbol: str):
    """从失败队列移除（成功后调用）"""
    with _FAILED_LOCK:
        if not _FAILED_DOWNLOADS_FILE.exists():
            return
        try:
            with open(_FAILED_DOWNLOADS_FILE, 'r') as f:
                failed = json.load(f)
            if symbol in failed:
                del failed[symbol]
                with open(_FAILED_DOWNLOADS_FILE, 'w') as f:
                    json.dump(failed, f, indent=2)
        except Exception:
            pass


def get_retry_candidates(max_retry_count: int = 3) -> list:
    """获取可重试的股票（未超过最大重试次数）"""
    failed = load_failed_downloads()
    return [s for s, info in failed.items() if info['count'] < max_retry_count]


# ==================== DataDownloader ====================

class DataDownloader:
    """
    统一数据下载器

    特性:
    - 直接调用 download_data_akshare 中的函数（无 subprocess 开销）
    - Tushare 优先 + AKShare/Baostock 备份
    - 并发下载（ThreadPoolExecutor，默认 4 线程）
    - 增量检测（基于本地 CSV 最后日期）
    - 失败队列（持久化到 failed_downloads.json）

    示例:
        # 使用配置对象
        config = DownloaderConfig(max_workers=4)
        downloader = DataDownloader(config)

        # 使用关键字参数（向后兼容）
        downloader = DataDownloader(max_workers=4)

        results = downloader.download_batch(['000001.SZSE', '000002.SZSE'])
    """

    def __init__(
        self,
        config: Optional[DownloaderConfig] = None,
        # 向后兼容：支持关键字参数
        max_workers: int = 4,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        timeout: float = 120.0,
        stock_delay: float = 1.0,
        data_dir: Optional[Path] = None,
    ):
        """
        Args:
            config: DownloaderConfig 对象（优先使用）
            max_workers: 并发线程数（默认 4）
            max_retries: 单只股票最大重试次数
            base_delay: 重试基础延迟（秒）
            max_delay: 重试最大延迟（秒）
            timeout: 单次下载超时（秒）
            stock_delay: 股票间延迟（秒，串行模式下使用）
            data_dir: 数据目录（用于增量检测）
        """
        if config is not None:
            self.config = config
            self.max_workers = config.max_workers
            self.max_retries = config.max_retries
            self.base_delay = config.base_delay
            self.max_delay = config.max_delay
            self.timeout = config.timeout
            self.stock_delay = config.stock_delay
            self.data_dir = Path(config.data_dir)
            self._failed_file = Path(config.failed_queue_file)
        else:
            self.config = DownloaderConfig(
                max_workers=max_workers,
                stock_delay=stock_delay,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                timeout=timeout,
            )
            self.max_workers = max_workers
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay
            self.timeout = timeout
            self.stock_delay = stock_delay
            self.data_dir = data_dir or (Path(__file__).parent / 'data' / 'akshare' / 'bars')
            self._failed_file = _FAILED_DOWNLOADS_FILE

        self._stats_lock = Lock()
        self._stats = {
            'total': 0,
            'success': 0,
            'tushare': 0,
            'akshare': 0,
            'baostock': 0,
            'failed': 0,
            'skipped': 0,
        }

    # ---------- 增量检测 ----------

    def is_up_to_date(self, symbol: str, max_age_days: int = 1) -> bool:
        """
        检查股票数据是否已是最新（优化：用 tail 读最后一行，不读全量）

        Args:
            symbol: 股票代码
            max_age_days: 允许的最大数据年龄（天），默认 1 天

        Returns:
            bool: 如果本地数据最后日期 >= (今天 - max_age_days) 则返回 True
        """
        csv_path = self.data_dir / f"{symbol}.csv"
        if not csv_path.exists():
            return False
        try:
            # Phase 3 Fix 1: 用 tail 只读最后 2 行（header + last row）
            import subprocess
            result = subprocess.run(
                ['tail', '-2', str(csv_path)],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return False
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return False
            # 解析 header 和 last row
            header = lines[0].split(',')
            last_row = dict(zip(header, lines[1].split(',')))
            # 找日期列
            for col in ['date', 'datetime', 'trade_date']:
                if col in last_row:
                    last_date = pd.to_datetime(last_row[col]).date()
                    threshold = datetime.now().date() - timedelta(days=max_age_days)
                    return last_date >= threshold
            return False
        except Exception as e:
            logger.debug(f"增量检测失败 {symbol}: {e}")
            return False

    def filter_fresh(self, symbols: List[str]) -> List[str]:
        """过滤掉已有最新数据的股票，返回需要下载的列表"""
        fresh = []
        skipped = 0
        for s in symbols:
            if self.is_up_to_date(s):
                skipped += 1
            else:
                fresh.append(s)
        if skipped:
            logger.info(f"⏭️  跳过 {skipped} 只已有最新数据的股票")
            with self._stats_lock:
                self._stats['skipped'] += skipped
        return fresh

    # ---------- 单只股票下载 ----------

    def download_single(self, symbol: str) -> DownloadResult:
        """
        下载单只股票（公开 API）

        Args:
            symbol: 股票代码

        Returns:
            DownloadResult: 下载结果
        """
        return self._download_one(symbol)

    # Phase 3 Fix 3: 限频控制（类级别共享，所有实例共用同一个限流器）
    _rate_limiter = RateLimiter(max_per_minute=180)

    def _download_one(self, symbol: str) -> DownloadResult:
        """
        下载单只股票（Phase 3 Fix 2: 每次 retry 只尝试一个数据源，轮换使用）

        重试策略：
        - attempt 1: Tushare（主数据源）
        - attempt 2: AKShare（备用）
        - attempt 3: Baostock（备选）
        每次 retry 只调用 1 个数据源，避免浪费 API 配额。

        Returns:
            DownloadResult
        """
        start_time = time.time()
        last_error = None
        delay = self.base_delay

        # Phase 3 Fix 2: 构建数据源列表，每个 retry 轮换一个
        sources: List[Tuple[str, Callable]] = []
        if USE_TUSHARE:
            sources.append(('tushare', get_stock_bars_tushare))
        sources.append(('akshare', get_stock_bars_akshare))
        sources.append(('baostock', get_stock_bars_baostock))

        for attempt in range(self.max_retries):
            # Phase 3 Fix 3: 限频控制
            self._rate_limiter.wait()

            source_name, source_fn = sources[attempt % len(sources)]
            try:
                bars = source_fn(symbol, None, None)
                if bars is not None and not bars.empty:
                    self._save_bars(symbol, bars)
                    remove_from_failed_queue(symbol)
                    return DownloadResult(
                        symbol=symbol,
                        status='success',
                        source=source_name,
                        rows=len(bars),
                        duration=time.time() - start_time,
                    )
            except Exception as e:
                last_error = f"{source_name} attempt {attempt + 1}: {e}"
                logger.debug(last_error)

            # 重试前等待（指数退避）
            if attempt < self.max_retries - 1:
                time.sleep(min(delay, self.max_delay))
                delay *= 2

        # 全部失败
        add_to_failed_queue(symbol, last_error or "未知错误")
        return DownloadResult(
            symbol=symbol,
            status='failed',
            source='none',
            duration=time.time() - start_time,
            error=last_error or "未知错误",
        )

    def _save_bars(self, symbol: str, bars: pd.DataFrame):
        """保存 K 线数据到 CSV"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.data_dir / f"{symbol}.csv"
        bars.to_csv(csv_path, index=False)

    def _update_stats(self, result: DownloadResult):
        """更新统计信息（线程安全）"""
        with self._stats_lock:
            self._stats['total'] += 1
            if result.status == 'success':
                self._stats['success'] += 1
                if result.source in self._stats:
                    self._stats[result.source] += 1
            elif result.status == 'failed':
                self._stats['failed'] += 1
            elif result.status == 'skipped':
                self._stats['skipped'] += 1

    # ---------- 批量下载 ----------

    def download_batch(
        self,
        symbols: List[str],
        incremental: bool = True,
        concurrent: bool = True,
    ) -> List[DownloadResult]:
        """
        批量下载股票数据（主 API）

        Args:
            symbols: 股票代码列表
            incremental: 是否启用增量检测（跳过已有最新数据）
            concurrent: 是否并发下载（False 则串行，带 stock_delay）

        Returns:
            List[DownloadResult]: 每只股票的下载结果列表
        """
        return self._do_download(symbols, incremental, concurrent)

    def download(
        self,
        symbols: List[str],
        incremental: bool = True,
        concurrent: bool = True,
    ) -> List[dict]:
        """
        批量下载股票数据（向后兼容接口，返回 dict 列表）

        新代码请使用 download_batch()，返回 DownloadResult 对象列表。
        """
        results = self._do_download(symbols, incremental, concurrent)
        # 向后兼容：返回 dict 列表
        return [r.to_dict() for r in results]

    def _do_download(
        self,
        symbols: List[str],
        incremental: bool = True,
        concurrent: bool = True,
    ) -> List[DownloadResult]:
        """批量下载的内部实现"""
        # 增量过滤
        if incremental:
            symbols = self.filter_fresh(symbols)

        if not symbols:
            logger.info("✅ 所有股票数据已是最新，无需下载")
            return []

        logger.info(f"📥 准备下载 {len(symbols)} 只股票 (并发={concurrent}, workers={self.max_workers})")

        results = []
        if concurrent and self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_symbol = {executor.submit(self._download_one, s): s for s in symbols}
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = DownloadResult(
                            symbol=symbol,
                            status='failed',
                            source='none',
                            error=str(e),
                        )
                        add_to_failed_queue(symbol, str(e))
                    self._update_stats(result)
                    results.append(result)
        else:
            for i, symbol in enumerate(symbols):
                result = self._download_one(symbol)
                self._update_stats(result)
                results.append(result)
                if i < len(symbols) - 1:
                    time.sleep(self.stock_delay)

        # 汇总
        stats = self.get_stats()
        logger.info(
            f"✅ 下载完成: 成功 {stats['success']}/{stats['total']} "
            f"(Tushare={stats['tushare']}, AKShare={stats['akshare']}, "
            f"Baostock={stats['baostock']}, 失败={stats['failed']}, "
            f"跳过={stats['skipped']})"
        )
        return results

    def get_stats(self) -> dict:
        """返回下载统计"""
        with self._stats_lock:
            return dict(self._stats)
