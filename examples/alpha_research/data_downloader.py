"""
统一数据下载器

提供 DataDownloader 类，直接 import download_data_akshare 中的函数，
避免 subprocess 开销。支持：
- 并发下载（ThreadPoolExecutor）
- 增量检测（跳过已有最新数据的股票）
- 失败队列（持久化 + 自动重试）
- 多数据源（MultiSourceManager 可配置优先级 + 自动降级）
- 双数据源（Tushare 主 + AKShare/Baostock 备，无 Manager 时的回退）

用法:
    from data_downloader import DataDownloader, DownloaderConfig
    config = DownloaderConfig(max_workers=4)
    downloader = DataDownloader(config)
    results = downloader.download_batch(['000001.SZSE', '000002.SZSE'])

    # 使用 MultiSourceManager（P0-2 多数据源支持）
    from akshare_source import create_default_manager
    manager = create_default_manager()
    config = DownloaderConfig(max_workers=4, source_manager=manager)
    downloader = DataDownloader(config)
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Event
from typing import Dict, List, Optional, Literal, Callable, Tuple

import pandas as pd

# tqdm 可选依赖：缺失时回退到简单的内置进度显示
try:
    from tqdm import tqdm as _tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    class _SimpleProgressBar:
        """极简内置进度条（无 tqdm 时的回退方案）"""

        def __init__(self, total: int, desc: str = '', disable: bool = False):
            self.total = total
            self.desc = desc
            self.disable = disable
            self.n = 0
            self._lock = Lock()

        def update(self, n: int = 1):
            with self._lock:
                self.n += n
                if not self.disable and self.total > 0:
                    pct = self.n * 100 // self.total
                    bar_len = 30
                    filled = bar_len * self.n // self.total
                    bar = '=' * filled + '-' * (bar_len - filled)
                    print(
                        f'\r{self.desc}[{bar}] {self.n}/{self.total} ({pct}%)',
                        end='', flush=True,
                    )

        def set_description(self, desc: str):
            self.desc = desc

        def close(self):
            if not self.disable and self.total > 0:
                print()  # 换行

    def _tqdm(*args, **kwargs):  # type: ignore[misc]
        return _SimpleProgressBar(*args, **kwargs)


# ==================== 限频控制 ====================

class SlidingWindowRateLimiter:
    """
    60s 滑动窗口计数器（线程安全）

    用于控制 API 调用频率，避免 burst。
    Tushare 限频 200次/分钟，默认设置 180次/分钟（留 10% 余量）。

    相比简单间隔检查：
    - 不允许任何 60s 窗口内超过 max_count 次调用
    - 避免并发场景下的 burst 问题
    """

    def __init__(self, max_per_minute: int = 180):
        self.max_count = max_per_minute
        self._lock = Lock()
        self._timestamps: deque = deque(maxlen=max_per_minute)

    def wait(self):
        """等待直到可以发起下一次调用"""
        with self._lock:
            now = time.time()
            # 移除 60s 之前的旧时间戳
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()

            # 如果已达上限，等待到最早的_timeStamp 超过 60s
            if len(self._timestamps) >= self.max_count:
                sleep_for = 60 - (now - self._timestamps[0]) + 0.01
                time.sleep(sleep_for)

            self._timestamps.append(time.time())


# 向后兼容：保留 RateLimiter 类名作为滑动窗口的别名
RateLimiter = SlidingWindowRateLimiter


class AsyncSlidingWindowRateLimiter:
    """
    异步 60s 滑动窗口计数器（asyncio 协程安全）

    用于控制异步 API 调用频率，避免 burst。
    """

    def __init__(self, max_per_minute: int = 180):
        self.max_count = max_per_minute
        self._lock = asyncio.Lock()
        self._timestamps: deque = deque(maxlen=max_per_minute)

    async def wait(self):
        """异步等待直到可以发起下一次调用"""
        async with self._lock:
            now = time.time()
            # 移除 60s 之前的旧时间戳
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()

            # 如果已达上限，计算等待时间
            if len(self._timestamps) >= self.max_count:
                sleep_for = 60 - (now - self._timestamps[0]) + 0.01
                await asyncio.sleep(sleep_for)

            self._timestamps.append(time.time())


# 向后兼容：保留 AsyncRateLimiter 类名作为异步滑动窗口的别名
AsyncRateLimiter = AsyncSlidingWindowRateLimiter

# 导入底层下载函数（直接调用，不开子进程）
from download_data_akshare import (
    get_stock_bars_akshare,
    get_stock_bars_baostock,
    get_stock_bars_tushare,
    USE_TUSHARE,
)

# P0-2: MultiSourceManager 可选导入（多数据源管理）
try:
    from akshare_source import MultiSourceManager, create_default_manager
    HAS_MULTI_SOURCE = True
except ImportError:
    HAS_MULTI_SOURCE = False
    MultiSourceManager = None  # type: ignore

# 失败队列文件路径
_FAILED_DOWNLOADS_FILE = Path(__file__).parent / 'failed_downloads.json'
_FAILED_LOCK = Lock()

# Phase 4B: 原子写入的失败队列（模块级单例，跨进程安全）
from atomic_failed_queue import AtomicFailedQueue
_failed_queue: Optional[AtomicFailedQueue] = None


def _get_failed_queue() -> AtomicFailedQueue:
    """获取模块级失败队列实例（懒初始化）"""
    global _failed_queue
    if _failed_queue is None:
        _failed_queue = AtomicFailedQueue(_FAILED_DOWNLOADS_FILE)
    return _failed_queue


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
        validate: 下载后是否自动校验数据质量
        notify_on_failure: 校验失败时是否发送飞书通知
        source_manager: P0-2 多数据源管理器（MultiSourceManager 实例）
        source_config_path: P0-2 数据源配置文件路径（YAML）
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
    validate: bool = False
    notify_on_failure: bool = False
    progress: bool = True
    graceful_shutdown: bool = True
    source_manager: object = None  # Optional[MultiSourceManager]
    source_config_path: Optional[str] = None


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
        validation: 校验结果 (validate=True 时填充)
    """
    symbol: str
    status: Literal['success', 'failed', 'skipped']
    source: Literal['tushare', 'akshare', 'baostock', 'cache', 'none'] = 'none'
    rows: int = 0
    duration: float = 0.0
    error: str = ''
    validation: Optional[dict] = None

    def to_dict(self) -> dict:
        """转换为字典（兼容旧接口）"""
        return asdict(self)

    @property
    def ok(self) -> bool:
        """是否成功"""
        return self.status == 'success'

    @property
    def validation_passed(self) -> Optional[bool]:
        """校验是否通过（None 表示未校验）"""
        if self.validation is None:
            return None
        return self.validation.get('passed', False)


# ==================== 失败队列（Phase 4B: 原子写入） ====================

def load_failed_downloads() -> dict:
    """加载失败队列（线程安全 + 跨进程安全）

    Phase 4B: 委托给 AtomicFailedQueue，使用 fsync + rename 原子读取。
    """
    return _get_failed_queue().get_all()


def save_failed_downloads(failed: dict):
    """保存失败队列（线程安全 + 原子写入）

    Phase 4B: 委托给 AtomicFailedQueue._save_atomic()。
    """
    _get_failed_queue()._save_atomic(failed)


def add_to_failed_queue(symbol: str, error: str):
    """添加失败股票到队列（原子写入）

    Phase 4B: 使用 AtomicFailedQueue.add()，保证崩溃安全。
    """
    _get_failed_queue().add(symbol, error)


def remove_from_failed_queue(symbol: str):
    """从失败队列移除（成功后调用，原子写入）

    Phase 4B: 使用 AtomicFailedQueue.remove()。
    """
    _get_failed_queue().remove(symbol)


def get_retry_candidates(max_retry_count: int = 3) -> list:
    """获取可重试的股票（未超过最大重试次数）

    Phase 4B: 使用 AtomicFailedQueue.get_retry_candidates()。
    """
    return _get_failed_queue().get_retry_candidates(max_retry_count)


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
        validate: bool = False,
        notify_on_failure: bool = False,
        progress: bool = True,
        graceful_shutdown: bool = True,
        source_manager: object = None,
        source_config_path: Optional[str] = None,
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
            validate: 下载后是否自动校验数据质量
            notify_on_failure: 校验失败时是否发送飞书通知
            progress: 是否显示进度条（默认 True，需 tqdm；无 tqdm 时回退到内置进度条）
            graceful_shutdown: 是否注册 SIGINT/SIGTERM 处理器以支持优雅关闭（默认 True）
            source_manager: P0-2 多数据源管理器（MultiSourceManager 实例）
            source_config_path: P0-2 数据源配置文件路径（YAML），无 source_manager 时自动创建
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
            self.validate = config.validate
            self.notify_on_failure = config.notify_on_failure
            self.progress = config.progress
            self.graceful_shutdown = config.graceful_shutdown
            self._source_manager = config.source_manager
            self._source_config_path = config.source_config_path
        else:
            self.config = DownloaderConfig(
                max_workers=max_workers,
                stock_delay=stock_delay,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                timeout=timeout,
                validate=validate,
                notify_on_failure=notify_on_failure,
                progress=progress,
                graceful_shutdown=graceful_shutdown,
                source_manager=source_manager,
                source_config_path=source_config_path,
            )
            self.max_workers = max_workers
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay
            self.timeout = timeout
            self.stock_delay = stock_delay
            self.data_dir = data_dir or (Path(__file__).parent / 'data' / 'akshare' / 'bars')
            self._failed_file = _FAILED_DOWNLOADS_FILE
            self.validate = validate
            self.notify_on_failure = notify_on_failure
            self.progress = progress
            self.graceful_shutdown = graceful_shutdown
            self._source_manager = source_manager
            self._source_config_path = source_config_path

        # P0-2: 初始化 MultiSourceManager（如已配置）
        if self._source_manager is None and self._source_config_path and HAS_MULTI_SOURCE:
            try:
                from akshare_source import load_source_config
                cfg = load_source_config(self._source_config_path)
                self._source_manager = create_default_manager(cfg)
                logger.info("✅ MultiSourceManager 已从配置加载: %s", self._source_config_path)
            except Exception as e:
                logger.warning("MultiSourceManager 初始化失败 (%s)，将使用传统数据源轮转", e)
                self._source_manager = None

        self._stats_lock = Lock()
        self._stats = {
            'total': 0,
            'success': 0,
            'tushare': 0,
            'akshare': 0,
            'baostock': 0,
            'failed': 0,
            'skipped': 0,
            'multi_source': 0,  # P0-2: 通过 MultiSourceManager 成功获取的次数
        }
        # Graceful shutdown 支持
        self._shutdown_event = Event()
        # 上一次 batch 的部分结果（Ctrl+C 时保存已下载数据）
        self._last_partial_results: List[DownloadResult] = []
        # Phase 4B: 原子写入的失败队列实例
        self.failed_queue = AtomicFailedQueue(self._failed_file)

        # 下载进度状态文件路径
        self._progress_file = Path('./state/download_progress.json')
        self._progress_file.parent.mkdir(parents=True, exist_ok=True)
        self._progress_lock = Lock()

    # ---------- 增量检测 ----------

    def is_up_to_date(self, symbol: str, max_age_days: int = 1) -> bool:
        """
        检查股票数据是否已是最新（使用 pandas 读取最后几行，更健壮）

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
            # 为了检测是否有header，我们需要读取第一行并检查是否包含常见字段名
            with open(csv_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            # 分析第一行判断是否是header
            first_cols = first_line.split(',')
            is_header_line = any(col.lower() in ['date', 'datetime', 'dt', 'time', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount', 'symbol']
                               for col in first_cols[:5])  # 检查前5列，通常日期和价格字段在前

            # 根据是否有header读取数据
            if is_header_line:
                # 有header，常规读取
                df = pd.read_csv(csv_path)
            else:
                # 没有header，指定header=None
                df = pd.read_csv(csv_path, header=None)

            if df.empty:
                return False

            # 确定日期列
            date_column = None
            for col in df.columns:
                if str(col).lower() in ['date', 'datetime', 'dt', 'time', 'timestamp']:
                    date_column = col
                    break

            # 如果没有找到日期列，尝试第一列
            if date_column is None:
                date_column = df.columns[0]

            # 确保有数据行
            if len(df) == 0:
                return False

            # 获取最后一行的日期值
            last_row = df.iloc[-1]

            # 获取日期列的值，如果没有该列则使用第一列
            if date_column in last_row:
                last_date_str = last_row[date_column]
            else:
                # 使用第一列
                last_date_str = last_row.iloc[0] if hasattr(last_row, 'iloc') else last_row[df.columns[0]]

            # 解析日期
            last_date = pd.to_datetime(str(last_date_str), errors='coerce')
            if pd.isna(last_date):
                return False

            # 检查是否在允许的最大天数范围内
            threshold = datetime.now().date() - timedelta(days=max_age_days)
            return last_date.date() >= threshold

        except pd.errors.EmptyDataError:
            return False
        except Exception as e:
            logger.debug(f"增量检测失败 {symbol}: {e}")
            # 在出错的情况下，回退到原始的seek方法
            try:
                # Phase 4A Fix 1: 用 Python 原生 seek 读文件末尾 4KB（跨平台，无 subprocess 开销）
                file_size = csv_path.stat().st_size
                read_size = min(4096, file_size)
                with open(csv_path, 'rb') as f:
                    f.seek(file_size - read_size)
                    tail = f.read(read_size).decode('utf-8', errors='ignore')

                # 处理文件末尾有换行符的情况
                tail_lines = tail.split('\n')
                # 移除尾部空行
                while tail_lines and not tail_lines[-1].strip():
                    tail_lines.pop()

                if not tail_lines:
                    return False
                if len(tail_lines) == 1:
                    # 只有一行：可能是只有 header，或者没有换行符结尾的单行数据
                    first_line = tail_lines[0].strip()
                    if not first_line:
                        return False
                    if first_line.startswith('date,'):
                        return False
                    last_line = first_line
                elif len(tail_lines) == 2:
                    # 两行可能是：[header, data] 或 [data, data]
                    # 检查第一行是否为 header
                    if tail_lines[0].strip().startswith('date,'):
                        # 正常情况：header + data（无尾部换行符）
                        last_line = tail_lines[1].strip()
                    else:
                        # 两行都是数据，用最后一行
                        last_line = tail_lines[-1].strip()
                else:
                    last_line = tail_lines[-2].strip()  # 倒数第二行是最后一条数据

                if not last_line:
                    return False

                # 解析最后一行，找日期列
                first_col = last_line.split(',', 1)[0]
                last_date = pd.to_datetime(first_col, errors='coerce')
                if pd.isna(last_date):
                    return False

                threshold = datetime.now().date() - timedelta(days=max_age_days)
                return last_date.date() >= threshold
            except Exception:
                logger.debug(f"回退方法也失败 {symbol}: {e}")
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

    def _save_progress(self, symbol: str, attempt: int, source: str, error_message: str = ""):
        """保存下载进度状态到文件"""
        with self._progress_lock:
            try:
                # 读取现有状态
                if self._progress_file.exists():
                    with open(self._progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                else:
                    progress_data = {}

                # 更新状态
                progress_data[symbol] = {
                    'symbol': symbol,
                    'attempt': attempt,
                    'source': source,
                    'timestamp': datetime.now().isoformat(),
                    'error_message': error_message
                }

                # 原子写入新数据
                temp_file = self._progress_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, self._progress_file)

            except Exception as e:
                logger.warning(f"保存下载进度状态失败: {e}")

    def _remove_progress(self, symbol: str):
        """移除指定股票的下载进度状态"""
        with self._progress_lock:
            try:
                if self._progress_file.exists():
                    with open(self._progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)

                    # 删除指定股票的状态
                    if symbol in progress_data:
                        del progress_data[symbol]

                        # 原子写入新数据
                        temp_file = self._progress_file.with_suffix('.tmp')
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(progress_data, f, ensure_ascii=False, indent=2)
                        os.replace(temp_file, self._progress_file)

            except Exception as e:
                logger.warning(f"移除下载进度状态失败: {e}")

    def get_download_progress(self) -> Dict:
        """获取当前下载进度状态"""
        try:
            if self._progress_file.exists():
                with open(self._progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logger.warning(f"读取下载进度状态失败: {e}")
            return {}

    def _download_one(self, symbol: str) -> DownloadResult:
        """
        下载单只股票。

        P0-2: 如果配置了 MultiSourceManager，优先使用多数据源管理器（自动降级）。
        回退: 传统数据源轮转（Tushare → AKShare → Baostock）。

        Returns:
            DownloadResult
        """
        start_time = time.time()
        last_error = None

        # P0-2: 优先使用 MultiSourceManager
        if self._source_manager is not None:
            try:
                df, source_name = self._source_manager.fetch(symbol, None, None)
                if df is not None and not df.empty:
                    self._save_bars(symbol, df)
                    self.failed_queue.remove(symbol)  # Phase 4B: 原子写入
                    validation = self._run_validation(symbol, df)
                    with self._stats_lock:
                        self._stats['multi_source'] += 1
                    # 成功后移除进度状态
                    self._remove_progress(symbol)
                    return DownloadResult(
                        symbol=symbol,
                        status='success',
                        source=source_name,
                        rows=len(df),
                        duration=time.time() - start_time,
                        validation=validation,
                    )
                else:
                    last_error = f"multi_source: all sources returned empty for {symbol}"
                    logger.debug(last_error)
                    # 继续尝试传统数据源作为回退
            except Exception as e:
                last_error = f"multi_source: {e}"
                logger.debug(last_error)
                # 继续尝试传统数据源作为回退
                # 记录初始状态
                self._save_progress(symbol, 0, "multi_source", str(e))

        # 传统数据源轮转（回退路径）
        delay = self.base_delay
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
                    self.failed_queue.remove(symbol)  # Phase 4B: 原子写入
                    validation = self._run_validation(symbol, bars)
                    # 成功后移除进度状态
                    self._remove_progress(symbol)
                    return DownloadResult(
                        symbol=symbol,
                        status='success',
                        source=source_name,
                        rows=len(bars),
                        duration=time.time() - start_time,
                        validation=validation,
                    )
            except Exception as e:
                last_error = f"{source_name} attempt {attempt + 1}: {e}"
                logger.debug(last_error)

                # 记录每次重试的状态
                self._save_progress(symbol, attempt + 1, source_name, str(e))

            # 重试前等待（指数退避）
            if attempt < self.max_retries - 1:
                time.sleep(min(delay, self.max_delay))
                delay *= 2

        # 全部失败
        self.failed_queue.add(symbol, last_error or "未知错误")  # Phase 4B: 原子写入
        # 重试失败后仍然保留进度状态以便调试
        return DownloadResult(
            symbol=symbol,
            status='failed',
            source='none',
            duration=time.time() - start_time,
            error=last_error or "未知错误",
        )

    def _save_bars(self, symbol: str, bars: pd.DataFrame):
        """保存 K 线数据到 CSV（原子写入，crash-safe）

        先写临时文件，再 os.replace() 覆盖目标文件。
        os.replace() 在 POSIX 上是原子操作，Windows 上也是原子的（Python 3.3+）。
        这样即使写入中途崩溃，目标文件要么保持旧版本，要么是完整的新版本，
        不会出现截断或半写状态。
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.data_dir / f"{symbol}.csv"
        tmp_path = csv_path.with_suffix('.csv.tmp')
        try:
            bars.to_csv(tmp_path, index=False)
            os.replace(tmp_path, csv_path)
        except Exception:
            # 清理临时文件
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise

    def _run_validation(self, symbol: str, bars: pd.DataFrame) -> Optional[dict]:
        """下载后运行数据质量校验（如已启用）

        Returns:
            校验结果的 dict 形式，未启用时返回 None
        """
        if not self.validate:
            return None
        try:
            from data_validator import DataValidator
            validator = DataValidator()
            result = validator.validate(bars, symbol)
            if not result.passed and self.notify_on_failure:
                validator.notify_validation_failure(result)
            logger.info(result.summary())
            return result.to_dict()
        except Exception as e:
            logger.warning(f"Validation failed for {symbol}: {e}")
            return {'symbol': symbol, 'passed': False, 'error': str(e), 'checks': []}

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

    # ---------- Graceful Shutdown ----------

    def shutdown_requested(self) -> bool:
        """是否已收到关闭信号"""
        return self._shutdown_event.is_set()

    def request_shutdown(self):
        """主动请求优雅关闭（也可由 SIGINT/SIGTERM 触发）"""
        self._shutdown_event.set()
        logger.info("🛑 收到关闭请求，将在完成进行中的下载后停止")

    def reset_shutdown(self):
        """重置 shutdown 标志（用于测试或复用时）"""
        self._shutdown_event.clear()

    def get_partial_results(self) -> List[DownloadResult]:
        """返回上一次 batch 中被中断时已完成的结果（Ctrl+C 时保存已下载数据）"""
        return list(self._last_partial_results)

    # ---------- 批量下载（内部实现） ----------

    def _do_download(
        self,
        symbols: List[str],
        incremental: bool = True,
        concurrent: bool = True,
    ) -> List[DownloadResult]:
        """批量下载的内部实现

        支持:
        - tqdm 进度条（缺失时回退到内置进度条）
        - graceful shutdown（Ctrl+C 时保存已下载数据并退出）

        Shutdown 语义:
        - batch 开始前调用 request_shutdown() → 不提交任何任务，全部 skipped
        - batch 进行中触发 SIGINT/request_shutdown() → 停止提交新任务，进行中的任务完成
        - batch 结束后自动清除 shutdown 标志，下一次 batch 可正常启动
        """
        # 注意：不在这里 clear() shutdown 标志，尊重 batch 开始前外部设置的 shutdown 请求
        self._last_partial_results = []

        # 增量过滤
        if incremental:
            symbols = self.filter_fresh(symbols)

        if not symbols:
            logger.info("✅ 所有股票数据已是最新，无需下载")
            return []

        logger.info(f"📥 准备下载 {len(symbols)} 只股票 (并发={concurrent}, workers={self.max_workers})")

        # 注册 SIGINT/SIGTERM 处理器（graceful shutdown）
        prev_sigint = None
        prev_sigterm = None
        if self.graceful_shutdown:
            try:
                prev_sigint = signal.getsignal(signal.SIGINT)
                prev_sigterm = signal.getsignal(signal.SIGTERM)

                def _signal_handler(signum, frame):
                    sig_name = signal.Signals(signum).name
                    logger.warning(
                        f"⚠️  收到 {sig_name}，正在优雅关闭 "
                        f"(已完成 {len(self._last_partial_results)}/{len(symbols)})..."
                    )
                    self._shutdown_event.set()

                signal.signal(signal.SIGINT, _signal_handler)
                signal.signal(signal.SIGTERM, _signal_handler)
            except (ValueError, OSError):
                # 在非主线程注册 signal 会抛 ValueError，忽略
                prev_sigint = None
                prev_sigterm = None

        results: List[DownloadResult] = []
        try:
            if concurrent and self.max_workers > 1:
                results = self._download_concurrent(symbols)
            else:
                results = self._download_serial(symbols)
        finally:
            # 恢复原有 signal handler
            if prev_sigint is not None:
                try:
                    signal.signal(signal.SIGINT, prev_sigint)
                    signal.signal(signal.SIGTERM, prev_sigterm)
                except (ValueError, OSError):
                    pass
            # 清除 shutdown 标志，让下一次 batch 可以从干净状态开始
            # （本次 batch 的 shutdown 效果已通过 results 中的 skipped 体现）
            self._shutdown_event.clear()

        # 保存部分结果（用于 Ctrl+C 后查询已下载数据）
        self._last_partial_results = list(results)

        # 汇总
        stats = self.get_stats()
        shutdown_note = " (被中断)" if self._shutdown_event.is_set() else ""
        multi_note = f", MultiSource={stats.get('multi_source', 0)}" if self._source_manager else ""
        logger.info(
            f"✅ 下载完成{shutdown_note}: 成功 {stats['success']}/{stats['total']} "
            f"(Tushare={stats['tushare']}, AKShare={stats['akshare']}, "
            f"Baostock={stats['baostock']}{multi_note}, "
            f"失败={stats['failed']}, 跳过={stats['skipped']})"
        )
        return results

    def _download_concurrent(self, symbols: List[str]) -> List[DownloadResult]:
        """并发下载（ThreadPoolExecutor）+ 进度条 + graceful shutdown"""
        results: List[DownloadResult] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 仅在未 shutdown 时提交任务
            future_to_symbol: Dict[Future, str] = {}
            for s in symbols:
                if self._shutdown_event.is_set():
                    break
                future_to_symbol[executor.submit(self._download_one, s)] = s

            # 进度条
            total = len(future_to_symbol)
            skipped = len(symbols) - total
            if skipped > 0:
                # 为跳过的（未提交的）股票填充 skipped 结果
                submitted_symbols = set(future_to_symbol.values())
                for s in symbols:
                    if s not in submitted_symbols:
                        r = DownloadResult(
                            symbol=s, status='skipped', source='none',
                            error='shutdown requested before submission',
                        )
                        self._update_stats(r)
                        results.append(r)

            pbar = _tqdm(
                total=total,
                desc='Downloading',
                disable=not self.progress,
            )
            try:
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
                        self.failed_queue.add(symbol, str(e))  # Phase 4B
                    self._update_stats(result)
                    results.append(result)
                    pbar.update(1)

                    # 进度条描述
                    stats = self.get_stats()
                    pbar.set_description(
                        f"OK={stats['success']} FAIL={stats['failed']}"
                    )
            except KeyboardInterrupt:
                # 理论上被 signal handler 捕获，这里做兜底
                logger.warning("⚠️  KeyboardInterrupt 捕获，正在等待进行中的任务...")
                self._shutdown_event.set()
            finally:
                pbar.close()

        return results

    def _download_serial(self, symbols: List[str]) -> List[DownloadResult]:
        """串行下载 + 进度条 + graceful shutdown"""
        results: List[DownloadResult] = []
        pbar = _tqdm(
            total=len(symbols),
            desc='Downloading',
            disable=not self.progress,
        )
        try:
            for i, symbol in enumerate(symbols):
                if self._shutdown_event.is_set():
                    # 为剩余股票填充 skipped 结果
                    for remaining in symbols[i:]:
                        r = DownloadResult(
                            symbol=remaining, status='skipped', source='none',
                            error='shutdown requested',
                        )
                        self._update_stats(r)
                        results.append(r)
                    break

                result = self._download_one(symbol)
                self._update_stats(result)
                results.append(result)
                pbar.update(1)

                stats = self.get_stats()
                pbar.set_description(
                    f"OK={stats['success']} FAIL={stats['failed']}"
                )

                if i < len(symbols) - 1 and not self._shutdown_event.is_set():
                    time.sleep(self.stock_delay)
        finally:
            pbar.close()

        return results

    def get_stats(self) -> dict:
        """返回下载统计"""
        with self._stats_lock:
            return dict(self._stats)

    def get_source_status(self) -> dict:
        """
        P0-2: 返回 MultiSourceManager 中各数据源的状态。

        Returns:
            dict: 数据源状态字典，未配置 MultiSourceManager 时返回空字典。
        """
        if self._source_manager is not None:
            return self._source_manager.get_status()
        return {}

    def health_check_sources(self) -> dict:
        """
        P0-2: 对所有数据源执行健康检查。

        Returns:
            dict: {source_name: bool}，未配置时返回空字典。
        """
        if self._source_manager is not None:
            return self._source_manager.health_check_all()
        return {}

    # ---------- 异步下载（asyncio） ----------

    # 类级别共享的异步限流器（与同步限流器独立，各自限频）
    _async_rate_limiter = AsyncRateLimiter(max_per_minute=180)

    async def _download_one_async(self, symbol: str) -> DownloadResult:
        """
        异步下载单只股票。

        P0-2: 如果配置了 MultiSourceManager，优先使用多数据源管理器。
        回退: 传统数据源轮转（Tushare → AKShare → Baostock）。

        Returns:
            DownloadResult
        """
        start_time = time.time()
        last_error = None

        # P0-2: 优先使用 MultiSourceManager
        if self._source_manager is not None:
            try:
                df, source_name = await asyncio.to_thread(
                    self._source_manager.fetch, symbol, None, None
                )
                if df is not None and not df.empty:
                    await asyncio.to_thread(self._save_bars, symbol, df)
                    await asyncio.to_thread(self.failed_queue.remove, symbol)  # Phase 4B
                    validation = await asyncio.to_thread(self._run_validation, symbol, df)
                    with self._stats_lock:
                        self._stats['multi_source'] += 1
                    return DownloadResult(
                        symbol=symbol,
                        status='success',
                        source=source_name,
                        rows=len(df),
                        duration=time.time() - start_time,
                        validation=validation,
                    )
                else:
                    last_error = f"multi_source: all sources returned empty for {symbol}"
                    logger.debug(last_error)
            except Exception as e:
                last_error = f"multi_source: {e}"
                logger.debug(last_error)

        # 传统数据源轮转（回退路径）
        delay = self.base_delay
        sources: List[Tuple[str, Callable]] = []
        if USE_TUSHARE:
            sources.append(('tushare', get_stock_bars_tushare))
        sources.append(('akshare', get_stock_bars_akshare))
        sources.append(('baostock', get_stock_bars_baostock))

        for attempt in range(self.max_retries):
            # 异步限频控制
            await self._async_rate_limiter.wait()

            source_name, source_fn = sources[attempt % len(sources)]
            try:
                # 使用 asyncio.to_thread 将同步调用放入线程池
                bars = await asyncio.to_thread(source_fn, symbol, None, None)
                if bars is not None and not bars.empty:
                    await asyncio.to_thread(self._save_bars, symbol, bars)
                    await asyncio.to_thread(self.failed_queue.remove, symbol)  # Phase 4B
                    validation = await asyncio.to_thread(self._run_validation, symbol, bars)
                    return DownloadResult(
                        symbol=symbol,
                        status='success',
                        source=source_name,
                        rows=len(bars),
                        duration=time.time() - start_time,
                        validation=validation,
                    )
            except Exception as e:
                last_error = f"{source_name} attempt {attempt + 1}: {e}"
                logger.debug(last_error)

            # 重试前等待（指数退避）— 异步版本不阻塞事件循环
            if attempt < self.max_retries - 1:
                await asyncio.sleep(min(delay, self.max_delay))
                delay *= 2

        # 全部失败
        await asyncio.to_thread(self.failed_queue.add, symbol, last_error or "未知错误")  # Phase 4B
        return DownloadResult(
            symbol=symbol,
            status='failed',
            source='none',
            duration=time.time() - start_time,
            error=last_error or "未知错误",
        )

    async def download_batch_async(
        self,
        symbols: List[str],
        incremental: bool = True,
    ) -> List[DownloadResult]:
        """
        异步批量下载股票数据

        使用 asyncio.gather 并发执行所有下载任务，
        配合 AsyncRateLimiter 控制总调用频率。

        Args:
            symbols: 股票代码列表
            incremental: 是否启用增量检测（跳过已有最新数据）

        Returns:
            List[DownloadResult]: 每只股票的下载结果列表

        示例:
            import asyncio
            from data_downloader import DataDownloader, DownloaderConfig

            async def main():
                config = DownloaderConfig()
                downloader = DataDownloader(config)
                results = await downloader.download_batch_async(
                    ['000001.SZSE', '000002.SZSE']
                )

            asyncio.run(main())
        """
        # 增量过滤（同步操作，不需要异步）
        if incremental:
            symbols = self.filter_fresh(symbols)

        if not symbols:
            logger.info("✅ 所有股票数据已是最新，无需下载")
            return []

        logger.info(f"📥 准备异步下载 {len(symbols)} 只股票")

        # 使用 asyncio.as_completed 模式实现进度条
        pending_tasks = {asyncio.create_task(self._download_one_async(s)): s for s in symbols}
        processed: List[DownloadResult] = []

        pbar = _tqdm(
            total=len(pending_tasks),
            desc='Async downloading',
            disable=not self.progress,
        )

        try:
            while pending_tasks:
                done, _ = await asyncio.wait(
                    pending_tasks.keys(),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    symbol = pending_tasks.pop(task)
                    try:
                        result = task.result()
                    except Exception as e:
                        result = DownloadResult(
                            symbol=symbol,
                            status='failed',
                            source='none',
                            error=str(e),
                        )
                        await asyncio.to_thread(self.failed_queue.add, symbol, str(e))  # Phase 4B
                    await asyncio.to_thread(self._update_stats, result)
                    processed.append(result)
                    pbar.update(1)

                    stats = self.get_stats()
                    pbar.set_description(
                        f"OK={stats['success']} FAIL={stats['failed']}"
                    )
        finally:
            pbar.close()

        # 汇总
        stats = self.get_stats()
        multi_note = f", MultiSource={stats.get('multi_source', 0)}" if self._source_manager else ""
        logger.info(
            f"✅ 异步下载完成: 成功 {stats['success']}/{stats['total']} "
            f"(Tushare={stats['tushare']}, AKShare={stats['akshare']}, "
            f"Baostock={stats['baostock']}{multi_note}, "
            f"失败={stats['failed']}, 跳过={stats['skipped']})"
        )
        return processed
