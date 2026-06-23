#!/usr/bin/env python3
"""
AKShare 多数据源支持

实现 P0-2: 新增 DataSource 抽象基类 + AKShareDataSource / TushareDataSource +
MultiSourceManager（可配置优先级、自动降级、健康检查、熔断）。

标准输出列: [datetime, open, high, low, close, volume]

用法::

    from akshare_source import AKShareDataSource, MultiSourceManager

    manager = MultiSourceManager()
    manager.register_source(AKShareDataSource())
    df, source_name = manager.fetch('000001.SZSE', '20240101', '20241231')
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ==================== 标准数据格式 ====================

STANDARD_COLUMNS: List[str] = [
    'datetime', 'open', 'high', 'low', 'close', 'volume',
]

# AKShare 中文列名 → 标准列名
_AKSHARE_COLUMN_MAP: Dict[str, str] = {
    '日期': 'datetime',
    '开盘': 'open',
    '最高': 'high',
    '最低': 'low',
    '收盘': 'close',
    '成交量': 'volume',
    '成交额': 'amount',
}

# Tushare 列名 → 标准列名
_TUSHARE_COLUMN_MAP: Dict[str, str] = {
    'trade_date': 'datetime',
    'vol': 'volume',
}


# ==================== 默认配置 ====================

DEFAULT_CONFIG: Dict = {
    'sources': {
        'tushare': {
            'priority': 1,
            'enabled': True,
            'token_env': 'TUSHARE_TOKEN',
        },
        'akshare': {
            'priority': 2,
            'enabled': True,
        },
    },
    'health_check': {
        'interval_seconds': 300,
        'failure_threshold': 3,
        'recovery_timeout': 300,
    },
    'failover': {
        'auto_switch': True,
        'log_switch_event': True,
    },
}


# ==================== DataSource 抽象基类 ====================

class DataSource(ABC):
    """
    数据源抽象基类。

    子类必须实现:
    - fetch_daily_bars(): 获取日线数据
    - health_check(): 轻量级可用性检测
    """

    def __init__(self, name: str, priority: int = 10, enabled: bool = True):
        self.name = name
        self.priority = priority
        self.enabled = enabled

        # 健康度指标（EMA 平滑）
        self._success_rate: float = 1.0
        self._avg_response_ms: float = 0.0
        self._consecutive_failures: int = 0
        self._last_check_time: Optional[str] = None
        self._last_success_time: Optional[str] = None
        self._last_failure_time: Optional[str] = None
        self._last_error: Optional[str] = None
        self._healthy: bool = True

    # ---------- 抽象方法 ----------

    @abstractmethod
    def fetch_daily_bars(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[pd.DataFrame]:
        """
        获取日线 K 线数据。

        Returns:
            DataFrame with columns [datetime, open, high, low, close, volume]，
            或 None 表示无数据 / 获取失败。
        """

    @abstractmethod
    def health_check(self) -> bool:
        """
        轻量级可用性检测（ping）。

        Returns:
            True 表示数据源可用。
        """

    # ---------- 指标记录 ----------

    def record_success(self, response_ms: float) -> None:
        """记录一次成功请求（EMA α=0.1）"""
        self._success_rate = 0.9 * self._success_rate + 0.1 * 1.0
        self._avg_response_ms = 0.9 * self._avg_response_ms + 0.1 * response_ms
        self._consecutive_failures = 0
        self._last_success_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self._healthy = True

    def record_failure(self, error: str = '') -> None:
        """记录一次失败请求"""
        self._success_rate = 0.9 * self._success_rate + 0.1 * 0.0
        self._consecutive_failures += 1
        self._last_failure_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self._last_error = error
        if self._consecutive_failures >= 3:
            self._healthy = False

    # ---------- 状态 ----------

    def get_status(self) -> Dict:
        """返回当前数据源状态"""
        return {
            'name': self.name,
            'priority': self.priority,
            'enabled': self.enabled,
            'healthy': self._healthy,
            'success_rate': round(self._success_rate, 3),
            'avg_response_ms': round(self._avg_response_ms, 1),
            'consecutive_failures': self._consecutive_failures,
            'last_check_time': self._last_check_time,
            'last_success_time': self._last_success_time,
            'last_failure_time': self._last_failure_time,
            'last_error': self._last_error,
        }

    def reset(self) -> None:
        """重置健康度指标"""
        self._success_rate = 1.0
        self._avg_response_ms = 0.0
        self._consecutive_failures = 0
        self._last_error = None
        self._healthy = True


# ==================== AKShareDataSource ====================

class AKShareDataSource(DataSource):
    """
    AKShare 数据源。

    使用 ak.stock_zh_a_hist() 获取日线数据，输出标准格式。
    """

    def __init__(
        self,
        priority: int = 2,
        enabled: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        super().__init__(name='akshare', priority=priority, enabled=enabled)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._ak = None  # 延迟导入

    def _ensure_ak(self):
        """延迟导入 akshare"""
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                raise ImportError(
                    "akshare 未安装。请运行: pip install akshare"
                )
        return self._ak

    @staticmethod
    def _standardize(df: pd.DataFrame) -> pd.DataFrame:
        """将 AKShare 中文列名转换为标准格式"""
        df = df.rename(columns=_AKSHARE_COLUMN_MAP)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        # 只保留标准列
        cols = [c for c in STANDARD_COLUMNS if c in df.columns]
        df = df[cols].sort_values('datetime').reset_index(drop=True)
        return df

    def fetch_daily_bars(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[pd.DataFrame]:
        ak = self._ensure_ak()
        code = symbol.split('.')[0]

        last_error = None
        for attempt in range(self.max_retries):
            try:
                t0 = time.time()
                kwargs = {
                    'symbol': code,
                    'period': 'daily',
                    'adjust': 'qfq',
                }
                if start_date:
                    kwargs['start_date'] = start_date
                if end_date:
                    kwargs['end_date'] = end_date

                df = ak.stock_zh_a_hist(**kwargs)
                response_ms = (time.time() - t0) * 1000

                if df is None or df.empty:
                    return None

                df = self._standardize(df)
                self.record_success(response_ms)
                return df

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (attempt + 1)
                    time.sleep(wait)

        self.record_failure(last_error or 'unknown')
        return None

    def health_check(self) -> bool:
        """通过获取 000001 最近 1 天数据检测可用性"""
        self._last_check_time = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            ak = self._ensure_ak()
            today = datetime.now().strftime('%Y%m%d')
            df = ak.stock_zh_a_hist(
                symbol='000001',
                period='daily',
                start_date=today,
                end_date=today,
                adjust='qfq',
            )
            ok = df is not None and not df.empty
            if ok:
                self._healthy = True
                self._consecutive_failures = 0
            else:
                # 非交易日返回空 DataFrame 也算正常（API 可达）
                self._healthy = True
            return True
        except Exception as e:
            self._last_error = str(e)
            self._healthy = False
            return False


# ==================== TushareDataSource ====================

class TushareDataSource(DataSource):
    """
    Tushare Pro 数据源。

    无 token 时自动 enabled=False。
    """

    def __init__(
        self,
        priority: int = 1,
        enabled: bool = True,
        token: Optional[str] = None,
        max_retries: int = 2,
    ):
        super().__init__(name='tushare', priority=priority, enabled=enabled)
        self.max_retries = max_retries
        self._pro = None
        self._token = token or os.environ.get('TUSHARE_TOKEN', '')

        # 无 token → 自动禁用
        if not self._token or not self._token.strip():
            self.enabled = False
            logger.info("TushareDataSource: 无 TUSHARE_TOKEN，自动禁用")
        else:
            self._init_tushare()

    def _init_tushare(self) -> None:
        try:
            import tushare as ts
            ts.set_token(self._token)
            self._pro = ts.pro_api()
        except ImportError:
            self.enabled = False
            logger.warning("TushareDataSource: tushare 未安装，自动禁用")
        except Exception as e:
            self.enabled = False
            logger.warning(f"TushareDataSource: 初始化失败 ({e})，自动禁用")

    @staticmethod
    def _standardize(df: pd.DataFrame) -> pd.DataFrame:
        """将 Tushare 列名转换为标准格式"""
        df = df.rename(columns=_TUSHARE_COLUMN_MAP)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        cols = [c for c in STANDARD_COLUMNS if c in df.columns]
        df = df[cols].sort_values('datetime').reset_index(drop=True)
        return df

    def fetch_daily_bars(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[pd.DataFrame]:
        if not self._pro:
            return None

        code = symbol.split('.')[0]
        exchange = symbol.split('.')[1] if '.' in symbol else 'SZ'
        ts_exchange = 'SZ' if exchange in ('SZ', 'SZSE') else 'SH'
        ts_symbol = f"{code}.{ts_exchange}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                t0 = time.time()
                kwargs = {'ts_code': ts_symbol}
                if start_date:
                    kwargs['start_date'] = start_date
                if end_date:
                    kwargs['end_date'] = end_date

                df = self._pro.daily(**kwargs)
                response_ms = (time.time() - t0) * 1000

                if df is None or df.empty:
                    return None

                df = self._standardize(df)
                self.record_success(response_ms)
                return df

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    time.sleep(self.max_retries)

        self.record_failure(last_error or 'unknown')
        return None

    def health_check(self) -> bool:
        """通过查询指数日线检测可用性"""
        self._last_check_time = time.strftime('%Y-%m-%d %H:%M:%S')
        if not self._pro:
            self._healthy = False
            return False
        try:
            today = datetime.now().strftime('%Y%m%d')
            df = self._pro.index_daily(
                ts_code='000001.SH',
                start_date=today,
                end_date=today,
            )
            # 非交易日返回空也算正常
            self._healthy = True
            self._consecutive_failures = 0
            return True
        except Exception as e:
            self._last_error = str(e)
            self._healthy = False
            return False


# ==================== MultiSourceManager ====================

class MultiSourceManager:
    """
    多数据源管理器。

    - 按 priority 升序尝试各数据源
    - 跳过 enabled=False 或连续失败超过 failure_threshold 的数据源（熔断）
    - 自动降级 + 日志记录
    """

    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        hc = self._config.get('health_check', DEFAULT_CONFIG['health_check'])
        self._failure_threshold: int = hc.get('failure_threshold', 3)
        self._recovery_timeout: int = hc.get('recovery_timeout', 300)
        fo = self._config.get('failover', DEFAULT_CONFIG['failover'])
        self._auto_switch: bool = fo.get('auto_switch', True)
        self._log_switch: bool = fo.get('log_switch_event', True)
        self._sources: Dict[str, DataSource] = {}

    # ---------- 注册 ----------

    def register_source(self, source: DataSource) -> None:
        """注册一个数据源"""
        self._sources[source.name] = source

    @property
    def sources(self) -> Dict[str, DataSource]:
        return dict(self._sources)

    # ---------- 核心 fetch ----------

    def fetch(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], str]:
        """
        按优先级获取数据，自动降级。

        Returns:
            (DataFrame or None, source_name or 'none')
        """
        ordered = sorted(
            self._sources.values(), key=lambda s: s.priority
        )

        prev_source_name: Optional[str] = None
        for source in ordered:
            if not source.enabled:
                continue
            if source._consecutive_failures >= self._failure_threshold:
                logger.debug(
                    "跳过熔断数据源 %s（连续失败 %d 次）",
                    source.name, source._consecutive_failures,
                )
                continue

            if self._log_switch and prev_source_name is not None:
                logger.warning(
                    "数据源降级: %s → %s (symbol=%s)",
                    prev_source_name, source.name, symbol,
                )

            t0 = time.time()
            try:
                df = source.fetch_daily_bars(symbol, start_date, end_date)
            except Exception as e:
                source.record_failure(str(e))
                prev_source_name = source.name
                continue

            if df is not None and not df.empty:
                return df, source.name

            # fetch 返回空 → 记录为失败
            source.record_failure('empty result')
            prev_source_name = source.name

        return None, 'none'

    # ---------- 健康检查 ----------

    def health_check_all(self) -> Dict[str, bool]:
        """对所有启用的数据源执行健康检查"""
        results: Dict[str, bool] = {}
        for name, source in self._sources.items():
            if not source.enabled:
                results[name] = False
                continue
            try:
                results[name] = source.health_check()
            except Exception as e:
                logger.warning("健康检查异常 %s: %s", name, e)
                results[name] = False
        return results

    def get_status(self) -> Dict[str, Dict]:
        """返回所有数据源状态"""
        return {name: src.get_status() for name, src in self._sources.items()}


# ==================== 配置加载 ====================

def load_source_config(config_path: Optional[str] = None) -> Dict:
    """
    加载数据源配置。

    优先级: config_path 参数 > 默认 config.yaml > DEFAULT_CONFIG
    """
    if config_path:
        p = Path(config_path)
        if p.exists():
            import yaml
            with open(p, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return data.get('data_sources', data)

    # 尝试默认路径
    for candidate in [
        Path('./config.yaml'),
        Path('./examples/alpha_research/config.yaml'),
    ]:
        if candidate.exists():
            import yaml
            with open(candidate, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            ds = data.get('data_sources', {})
            if ds:
                return ds

    return DEFAULT_CONFIG


def create_default_manager(
    config: Optional[Dict] = None,
) -> MultiSourceManager:
    """
    工厂函数：根据配置创建 MultiSourceManager 并注册默认数据源。
    """
    cfg = config or load_source_config()
    manager = MultiSourceManager(cfg)

    src_cfg = cfg.get('sources', DEFAULT_CONFIG['sources'])

    # Tushare
    ts_cfg = src_cfg.get('tushare', {})
    if ts_cfg.get('enabled', True):
        manager.register_source(TushareDataSource(
            priority=ts_cfg.get('priority', 1),
        ))

    # AKShare
    ak_cfg = src_cfg.get('akshare', {})
    if ak_cfg.get('enabled', True):
        manager.register_source(AKShareDataSource(
            priority=ak_cfg.get('priority', 2),
        ))

    return manager
