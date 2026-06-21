"""
统一数据下载器

提供 DataDownloader 类，直接 import download_data_akshare 中的函数，
避免 subprocess 开销。支持：
- 并发下载（ThreadPoolExecutor）
- 增量检测（跳过已有最新数据的股票）
- 失败队列（持久化 + 自动重试）
- 双数据源（Tushare 主 + AKShare 备）

用法:
    from data_downloader import DataDownloader
    downloader = DataDownloader()
    results = downloader.download(['000001', '000002'])
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import pandas as pd

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
        downloader = DataDownloader(max_workers=4)
        results = downloader.download(['000001', '000002'])
    """

    def __init__(
        self,
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
            max_workers: 并发线程数（默认 4）
            max_retries: 单只股票最大重试次数
            base_delay: 重试基础延迟（秒）
            max_delay: 重试最大延迟（秒）
            timeout: 单次下载超时（秒）
            stock_delay: 股票间延迟（秒，串行模式下使用）
            data_dir: 数据目录（用于增量检测，默认 examples/alpha_research/data/akshare/bars）
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.stock_delay = stock_delay
        self.data_dir = data_dir or (Path(__file__).parent / 'data' / 'akshare' / 'bars')
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

    def is_up_to_date(self, symbol: str) -> bool:
        """
        检查股票数据是否已是最新（本地 CSV 最后日期 >= 今天）
        """
        csv_path = self.data_dir / f"{symbol}.csv"
        if not csv_path.exists():
            return False
        try:
            df = pd.read_csv(csv_path)
            if df.empty or 'date' not in df.columns:
                return False
            last_date = pd.to_datetime(df['date'].iloc[-1]).date()
            return last_date >= datetime.now().date()
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

    def _download_one(self, symbol: str) -> dict:
        """
        下载单只股票（Tushare -> AKShare -> Baostock，带重试）

        Returns:
            {'symbol': str, 'status': 'success'|'failed', 'source': str, 'error': str|None}
        """
        last_error = None
        delay = self.base_delay

        for attempt in range(1, self.max_retries + 1):
            # 1. Tushare
            if USE_TUSHARE:
                try:
                    bars = get_stock_bars_tushare(symbol, None, None)
                    if bars is not None and not bars.empty:
                        self._save_bars(symbol, bars)
                        remove_from_failed_queue(symbol)
                        return {'symbol': symbol, 'status': 'success', 'source': 'tushare', 'error': None}
                except Exception as e:
                    last_error = f"Tushare attempt {attempt}: {e}"
                    logger.debug(last_error)

            # 2. AKShare
            try:
                bars = get_stock_bars_akshare(symbol, None, None)
                if bars is not None and not bars.empty:
                    self._save_bars(symbol, bars)
                    remove_from_failed_queue(symbol)
                    return {'symbol': symbol, 'status': 'success', 'source': 'akshare', 'error': None}
            except Exception as e:
                last_error = f"AKShare attempt {attempt}: {e}"
                logger.debug(last_error)

            # 3. Baostock
            try:
                bars = get_stock_bars_baostock(symbol, None, None)
                if bars is not None and not bars.empty:
                    self._save_bars(symbol, bars)
                    remove_from_failed_queue(symbol)
                    return {'symbol': symbol, 'status': 'success', 'source': 'baostock', 'error': None}
            except Exception as e:
                last_error = f"Baostock attempt {attempt}: {e}"
                logger.debug(last_error)

            # 重试前等待（指数退避）
            if attempt < self.max_retries:
                time.sleep(min(delay, self.max_delay))
                delay *= 2

        # 全部失败
        add_to_failed_queue(symbol, last_error or "未知错误")
        return {'symbol': symbol, 'status': 'failed', 'source': 'none', 'error': last_error}

    def _save_bars(self, symbol: str, bars: pd.DataFrame):
        """保存 K 线数据到 CSV"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.data_dir / f"{symbol}.csv"
        bars.to_csv(csv_path, index=False)

    def _update_stats(self, result: dict):
        """更新统计信息（线程安全）"""
        with self._stats_lock:
            self._stats['total'] += 1
            if result['status'] == 'success':
                self._stats['success'] += 1
                source = result.get('source', 'unknown')
                if source in self._stats:
                    self._stats[source] += 1
            else:
                self._stats['failed'] += 1

    # ---------- 批量下载 ----------

    def download(
        self,
        symbols: List[str],
        incremental: bool = True,
        concurrent: bool = True,
    ) -> List[dict]:
        """
        批量下载股票数据

        Args:
            symbols: 股票代码列表
            incremental: 是否启用增量检测（跳过已有最新数据）
            concurrent: 是否并发下载（False 则串行，带 stock_delay）

        Returns:
            每只股票的下载结果列表
        """
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
                        result = {'symbol': symbol, 'status': 'failed', 'source': 'none', 'error': str(e)}
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
        logger.info(
            f"✅ 下载完成: 成功 {self._stats['success']}/{self._stats['total']} "
            f"(Tushare={self._stats['tushare']}, AKShare={self._stats['akshare']}, "
            f"Baostock={self._stats['baostock']}, 失败={self._stats['failed']}, "
            f"跳过={self._stats['skipped']})"
        )
        return results

    def get_stats(self) -> dict:
        """返回下载统计"""
        with self._stats_lock:
            return dict(self._stats)
