"""
股票池管理模块

用于管理选股策略的股票池，包括：
- 预定义指数成分股（沪深 300、中证 500、中证 1000 等）
- 自定义股票池
- 成分股历史变化跟踪
- 股票池过滤（ST、停牌、新股等）
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import polars as pl

from ..logger import logger


class StockPool:
    """股票池管理类"""

    # 预定义指数代码映射
    INDEX_MAP = {
        "csi300": {"name": "沪深 300", "code": "000300.SSE", "rq_code": "000300.XSHG"},
        "csi500": {"name": "中证 500", "code": "000905.SSE", "rq_code": "000905.XSHG"},
        "csi1000": {"name": "中证 1000", "code": "000852.SSE", "rq_code": "000852.XSHG"},
        "csi2000": {"name": "中证 2000", "code": "932000.SSE", "rq_code": "932000.XSHG"},
        "a50": {"name": "富时 A50", "code": "XIN9.SGF", "rq_code": "XIN9.SGF"},
        "zx300": {"name": "中小 300", "code": "399008.SZSE", "rq_code": "399008.XSHE"},
        "cyb": {"name": "创业板指", "code": "399006.SZSE", "rq_code": "399006.XSHE"},
        "kcb": {"name": "科创 50", "code": "000688.SSE", "rq_code": "000688.XSHG"},
    }

    def __init__(self, pool_path: Optional[str] = None) -> None:
        """
        初始化股票池
        
        Args:
            pool_path: 股票池数据存储路径，默认为 ./data/pool
        """
        self.pool_path = Path(pool_path) if pool_path else Path("./data/pool")
        self.pool_path.mkdir(parents=True, exist_ok=True)
        
        # 成分股缓存：{date_str: [vt_symbol, ...]}
        self._components_cache: dict[str, list[str]] = {}
        
        # 自定义股票池
        self._custom_pools: dict[str, set[str]] = {}
        
        # 加载已保存的股票池
        self._load_pools()

    def _load_pools(self) -> None:
        """加载已保存的自定义股票池"""
        pool_file = self.pool_path / "custom_pools.json"
        if pool_file.exists():
            with open(pool_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._custom_pools = {
                    name: set(symbols) for name, symbols in data.items()
                }
            logger.info(f"已加载 {len(self._custom_pools)} 个自定义股票池")

    def _save_pools(self) -> None:
        """保存自定义股票池"""
        pool_file = self.pool_path / "custom_pools.json"
        data = {
            name: list(symbols) for name, symbols in self._custom_pools.items()
        }
        with open(pool_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(self._custom_pools)} 个自定义股票池")

    def get_index_components(
        self,
        index_name: str,
        date: Optional[datetime] = None
    ) -> list[str]:
        """
        获取指定指数的成分股
        
        Args:
            index_name: 指数名称（如 "csi300", "csi500" 等）
            date: 查询日期，默认为今天
            
        Returns:
            成分股代码列表（vt_symbol 格式，如 "000001.SZSE"）
        """
        if index_name not in self.INDEX_MAP:
            raise ValueError(
                f"未知的指数：{index_name}，可选：{list(self.INDEX_MAP.keys())}"
            )
        
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        cache_key = f"{index_name}_{date_str}"
        
        # 检查缓存
        if cache_key in self._components_cache:
            return self._components_cache[cache_key]
        
        # 从文件加载（如果有）
        components_file = self.pool_path / f"{index_name}_components.json"
        if components_file.exists():
            with open(components_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if date_str in data:
                    components = data[date_str]
                    self._components_cache[cache_key] = components
                    return components
        
        logger.warning(f"未找到 {index_name} 在 {date_str} 的成分股数据")
        return []

    def save_index_components(
        self,
        index_name: str,
        components: dict[str, list[str]]
    ) -> None:
        """
        保存指数成分股历史数据
        
        Args:
            index_name: 指数名称
            components: 成分股字典 {date_str: [vt_symbol, ...]}
        """
        if index_name not in self.INDEX_MAP:
            raise ValueError(f"未知的指数：{index_name}")
        
        components_file = self.pool_path / f"{index_name}_components.json"
        
        # 加载现有数据（如果有）
        data = {}
        if components_file.exists():
            with open(components_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # 更新数据
        data.update(components)
        
        # 保存
        with open(components_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        
        logger.info(f"已保存 {index_name} 的 {len(components)} 条成分股记录")
        
        # 更新缓存
        for date_str, symbols in components.items():
            self._components_cache[f"{index_name}_{date_str}"] = symbols

    def create_custom_pool(
        self,
        pool_name: str,
        symbols: list[str],
        overwrite: bool = False
    ) -> None:
        """
        创建自定义股票池
        
        Args:
            pool_name: 股票池名称
            symbols: 股票代码列表
            overwrite: 是否覆盖已存在的同名股票池
        """
        if pool_name in self._custom_pools and not overwrite:
            raise ValueError(f"股票池 '{pool_name}' 已存在，设置 overwrite=True 覆盖")
        
        self._custom_pools[pool_name] = set(symbols)
        self._save_pools()
        logger.info(f"已创建自定义股票池 '{pool_name}'，包含 {len(symbols)} 只股票")

    def add_to_pool(self, pool_name: str, symbols: list[str]) -> None:
        """
        向自定义股票池添加股票
        
        Args:
            pool_name: 股票池名称
            symbols: 要添加的股票代码列表
        """
        if pool_name not in self._custom_pools:
            raise ValueError(f"股票池 '{pool_name}' 不存在")
        
        self._custom_pools[pool_name].update(symbols)
        self._save_pools()
        logger.info(f"已向 '{pool_name}' 添加 {len(symbols)} 只股票")

    def remove_from_pool(self, pool_name: str, symbols: list[str]) -> None:
        """
        从自定义股票池移除股票
        
        Args:
            pool_name: 股票池名称
            symbols: 要移除的股票代码列表
        """
        if pool_name not in self._custom_pools:
            raise ValueError(f"股票池 '{pool_name}' 不存在")
        
        self._custom_pools[pool_name].difference_update(symbols)
        self._save_pools()
        logger.info(f"已从 '{pool_name}' 移除 {len(symbols)} 只股票")

    def get_custom_pool(self, pool_name: str) -> list[str]:
        """
        获取自定义股票池
        
        Args:
            pool_name: 股票池名称
            
        Returns:
            股票代码列表
        """
        if pool_name not in self._custom_pools:
            raise ValueError(f"股票池 '{pool_name}' 不存在")
        
        return list(self._custom_pools[pool_name])

    def list_pools(self) -> list[str]:
        """
        列出所有自定义股票池名称
        
        Returns:
            股票池名称列表
        """
        return list(self._custom_pools.keys())

    def filter_stocks(
        self,
        symbols: list[str],
        df: pl.DataFrame,
        exclude_st: bool = True,
        exclude_suspended: bool = True,
        exclude_new: bool = False,
        new_days: int = 60,
        min_turnover: float = 0,
        date: Optional[datetime] = None
    ) -> list[str]:
        """
        过滤股票池
        
        Args:
            symbols: 待过滤的股票代码列表
            df: 包含股票数据的 DataFrame（需要有 symbol, date, close, volume, turnover 等列）
            exclude_st: 是否排除 ST 股票
            exclude_suspended: 是否排除停牌股票
            exclude_new: 是否排除新股
            new_days: 新股天数阈值（默认 60 天）
            min_turnover: 最小成交额（元），用于排除流动性差的股票
            date: 过滤基准日期，默认为今天
            
        Returns:
            过滤后的股票代码列表
        """
        if date is None:
            date = datetime.now()
        
        filtered = symbols.copy()
        
        # 排除 ST 股票
        if exclude_st:
            st_symbols = {s for s in filtered if "ST" in s.upper()}
            filtered = [s for s in filtered if s not in st_symbols]
            logger.debug(f"排除 {len(st_symbols)} 只 ST 股票")
        
        # 排除停牌股票（成交量为 0）
        if exclude_suspended and not df.is_empty():
            date_str = date.strftime("%Y-%m-%d")
            suspended = df.filter(
                (pl.col("date") == date_str) & 
                (pl.col("volume") == 0)
            )["symbol"].unique().to_list()
            
            filtered = [s for s in filtered if s not in suspended]
            logger.debug(f"排除 {len(suspended)} 只停牌股票")
        
        # 排除新股
        if exclude_new and not df.is_empty():
            # 计算每只股票的首个交易日期
            first_dates = df.groupby("symbol").agg(
                pl.col("date").min().alias("first_date")
            )
            
            cutoff_date = (date - timedelta(days=new_days)).strftime("%Y-%m-%d")
            new_stocks = first_dates.filter(
                pl.col("first_date") > cutoff_date
            )["symbol"].to_list()
            
            filtered = [s for s in filtered if s not in new_stocks]
            logger.debug(f"排除 {len(new_stocks)} 只新股（<{new_days}天）")
        
        # 排除低流动性股票
        if min_turnover > 0 and not df.is_empty():
            date_str = date.strftime("%Y-%m-%d")
            low_liquidity = df.filter(
                (pl.col("date") == date_str) & 
                (pl.col("turnover") < min_turnover)
            )["symbol"].unique().to_list()
            
            filtered = [s for s in filtered if s not in low_liquidity]
            logger.debug(f"排除 {len(low_liquidity)} 只低流动性股票（成交额<{min_turnover:,.0f}）")
        
        logger.info(f"股票池过滤：{len(symbols)} -> {len(filtered)} 只")
        return filtered

    def get_universe(
        self,
        pool_names: list[str],
        date: Optional[datetime] = None
    ) -> list[str]:
        """
        获取多个股票池的并集
        
        Args:
            pool_names: 股票池名称列表（可以是指数名称或自定义股票池）
            date: 查询日期（仅对指数成分股有效）
            
        Returns:
            合并后的股票代码列表（去重）
        """
        all_symbols = set()
        
        for pool_name in pool_names:
            # 尝试作为指数成分股
            if pool_name in self.INDEX_MAP:
                symbols = self.get_index_components(pool_name, date)
                all_symbols.update(symbols)
            # 尝试作为自定义股票池
            elif pool_name in self._custom_pools:
                symbols = self.get_custom_pool(pool_name)
                all_symbols.update(symbols)
            else:
                logger.warning(f"未知的股票池：{pool_name}")
        
        return list(all_symbols)

    def get_intersection(
        self,
        pool_names: list[str],
        date: Optional[datetime] = None
    ) -> list[str]:
        """
        获取多个股票池的交集
        
        Args:
            pool_names: 股票池名称列表
            date: 查询日期（仅对指数成分股有效）
            
        Returns:
            交集股票代码列表
        """
        if not pool_names:
            return []
        
        # 获取第一个股票池
        first_pool = pool_names[0]
        if first_pool in self.INDEX_MAP:
            result = set(self.get_index_components(first_pool, date))
        elif first_pool in self._custom_pools:
            result = set(self.get_custom_pool(first_pool))
        else:
            logger.warning(f"未知的股票池：{first_pool}")
            return []
        
        # 依次求交集
        for pool_name in pool_names[1:]:
            if pool_name in self.INDEX_MAP:
                symbols = set(self.get_index_components(pool_name, date))
            elif pool_name in self._custom_pools:
                symbols = set(self.get_custom_pool(pool_name))
            else:
                logger.warning(f"未知的股票池：{pool_name}")
                continue
            
            result &= symbols
        
        return list(result)


# 便捷函数
def create_pool(pool_path: Optional[str] = None) -> StockPool:
    """创建股票池实例"""
    return StockPool(pool_path)
