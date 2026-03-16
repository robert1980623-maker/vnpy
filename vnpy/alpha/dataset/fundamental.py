"""
财务数据模块

提供基本面数据的管理和计算，包括：
- 财务指标获取（PE、PB、ROE、净利润等）
- 财务数据存储和查询
- 估值指标计算
- 成长性指标计算
- 盈利能力指标
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal

import polars as pl
import numpy as np

from ..logger import logger


class FundamentalData:
    """财务数据管理类"""

    # 财务指标分类
    VALUATION_METRICS = [
        "pe_ratio",      # 市盈率（TTM）
        "pb_ratio",      # 市净率
        "ps_ratio",      # 市销率
        "pcf_ratio",     # 市现率
        "ev_ebitda",     # 企业价值倍数
        "dividend_yield", # 股息率
    ]

    PROFITABILITY_METRICS = [
        "roe",           # 净资产收益率
        "roa",           # 总资产收益率
        "roic",          # 投入资本回报率
        "gross_margin",  # 毛利率
        "net_margin",    # 净利率
        "operating_margin", # 营业利润率
    ]

    GROWTH_METRICS = [
        "revenue_growth",    # 营收增长率
        "net_profit_growth", # 净利润增长率
        "roe_growth",        # ROE 增长率
        "eps_growth",        # EPS 增长率
    ]

    LEVERAGE_METRICS = [
        "debt_to_asset",     # 资产负债率
        "debt_to_equity",    # 产权比率
        "current_ratio",     # 流动比率
        "quick_ratio",       # 速动比率
    ]

    EFFICIENCY_METRICS = [
        "asset_turnover",    # 总资产周转率
        "inventory_turnover", # 存货周转率
        "receivables_turnover", # 应收账款周转率
    ]

    def __init__(self, data_path: Optional[str] = None) -> None:
        """
        初始化财务数据
        
        Args:
            data_path: 数据存储路径，默认为 ./data/fundamental
        """
        self.data_path = Path(data_path) if data_path else Path("./data/fundamental")
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 缓存
        self._cache: dict[str, pl.DataFrame] = {}

    def save_data(
        self,
        df: pl.DataFrame,
        data_type: str = "daily",
        symbol: Optional[str] = None
    ) -> None:
        """
        保存财务数据
        
        Args:
            df: 数据 DataFrame
            data_type: 数据类型（"daily" 日线指标，"quarterly" 季度财报，"yearly" 年度财报）
            symbol: 股票代码（可选，如果不传则保存全市场数据）
        """
        if df.is_empty():
            logger.warning("空数据，跳过保存")
            return
        
        # 确定文件路径
        if symbol:
            file_path = self.data_path / data_type / f"{symbol}.parquet"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.data_path / data_type / f"all_{timestamp}.parquet"
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存
        df.write_parquet(file_path)
        logger.info(f"已保存 {data_type} 数据到 {file_path}，共 {len(df)} 条记录")

    def load_data(
        self,
        symbol: str,
        data_type: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pl.DataFrame:
        """
        加载单只股票的财务数据
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            财务数据 DataFrame
        """
        file_path = self.data_path / data_type / f"{symbol}.parquet"
        
        if not file_path.exists():
            logger.warning(f"数据文件不存在：{file_path}")
            return pl.DataFrame()
        
        df = pl.read_parquet(file_path)
        
        # 时间过滤
        if start_date or end_date:
            if start_date:
                df = df.filter(pl.col("date") >= start_date)
            if end_date:
                df = df.filter(pl.col("date") <= end_date)
        
        return df

    def load_market_data(
        self,
        date: str,
        data_type: str = "daily"
    ) -> pl.DataFrame:
        """
        加载指定日期的全市场财务数据
        
        Args:
            date: 日期（YYYY-MM-DD）
            data_type: 数据类型
            
        Returns:
            全市场财务数据 DataFrame
        """
        # 查找包含该日期的文件
        folder_path = self.data_path / data_type
        
        if not folder_path.exists():
            logger.warning(f"数据文件夹不存在：{folder_path}")
            return pl.DataFrame()
        
        # 合并所有文件
        all_dfs = []
        for file_path in folder_path.glob("*.parquet"):
            if file_path.name.startswith("all_"):
                df = pl.read_parquet(file_path)
                if "date" in df.columns and date in df["date"].to_list():
                    all_dfs.append(df.filter(pl.col("date") == date))
        
        if not all_dfs:
            return pl.DataFrame()
        
        return pl.concat(all_dfs)

    def calculate_pe_ratio(
        self,
        price: float,
        eps_ttm: float
    ) -> Optional[float]:
        """
        计算市盈率
        
        Args:
            price: 当前股价
            eps_ttm: 每股收益（TTM）
            
        Returns:
            市盈率，计算失败返回 None
        """
        if eps_ttm <= 0:
            return None
        return round(price / eps_ttm, 2)

    def calculate_pb_ratio(
        self,
        price: float,
        bvps: float
    ) -> Optional[float]:
        """
        计算市净率
        
        Args:
            price: 当前股价
            bvps: 每股净资产
            
        Returns:
            市净率，计算失败返回 None
        """
        if bvps <= 0:
            return None
        return round(price / bvps, 2)

    def calculate_roe(
        self,
        net_profit: float,
        equity: float
    ) -> Optional[float]:
        """
        计算净资产收益率
        
        Args:
            net_profit: 净利润
            equity: 净资产
            
        Returns:
            ROE（百分比），计算失败返回 None
        """
        if equity <= 0:
            return None
        return round((net_profit / equity) * 100, 2)

    def calculate_growth_rate(
        self,
        current_value: float,
        previous_value: float,
        periods: int = 1
    ) -> Optional[float]:
        """
        计算增长率
        
        Args:
            current_value: 当前值
            previous_value: 前期值
            periods: 期间数
            
        Returns:
            增长率（年化百分比），计算失败返回 None
        """
        if previous_value <= 0:
            return None
        
        if periods == 1:
            return round(((current_value - previous_value) / previous_value) * 100, 2)
        else:
            # 年化增长率
            cagr = ((current_value / previous_value) ** (1 / periods) - 1) * 100
            return round(cagr, 2)

    def get_financial_statements(
        self,
        symbol: str,
        report_type: Literal["quarterly", "yearly"] = "quarterly",
        limit: int = 20
    ) -> pl.DataFrame:
        """
        获取财务报表数据
        
        Args:
            symbol: 股票代码
            report_type: 报表类型
            limit: 返回最近 N 期报表
            
        Returns:
            财务报表数据 DataFrame
        """
        df = self.load_data(symbol, report_type)
        
        if df.is_empty():
            return df
        
        # 按日期排序并限制数量
        return df.sort("date", descending=True).limit(limit)

    def filter_by_metrics(
        self,
        df: pl.DataFrame,
        min_pe: Optional[float] = None,
        max_pe: Optional[float] = None,
        min_pb: Optional[float] = None,
        max_pb: Optional[float] = None,
        min_roe: Optional[float] = None,
        min_revenue_growth: Optional[float] = None,
        min_net_profit_growth: Optional[float] = None,
        max_debt_to_asset: Optional[float] = None,
        min_dividend_yield: Optional[float] = None,
        date: Optional[str] = None
    ) -> pl.DataFrame:
        """
        根据财务指标过滤股票
        
        Args:
            df: 包含财务数据的 DataFrame
            min_pe: 最小市盈率
            max_pe: 最大市盈率
            min_pb: 最小市净率
            max_pb: 最大市净率
            min_roe: 最小 ROE
            min_revenue_growth: 最小营收增长率
            min_net_profit_growth: 最小净利润增长率
            max_debt_to_asset: 最大资产负债率
            min_dividend_yield: 最小股息率
            date: 过滤日期
            
        Returns:
            过滤后的 DataFrame
        """
        if df.is_empty():
            return df
        
        # 日期过滤
        if date:
            df = df.filter(pl.col("date") == date)
        
        # 指标过滤
        conditions = []
        
        if min_pe is not None:
            conditions.append(pl.col("pe_ratio") >= min_pe)
        if max_pe is not None:
            conditions.append(pl.col("pe_ratio") <= max_pe)
        if min_pb is not None:
            conditions.append(pl.col("pb_ratio") >= min_pb)
        if max_pb is not None:
            conditions.append(pl.col("pb_ratio") <= max_pb)
        if min_roe is not None:
            conditions.append(pl.col("roe") >= min_roe)
        if min_revenue_growth is not None:
            conditions.append(pl.col("revenue_growth") >= min_revenue_growth)
        if min_net_profit_growth is not None:
            conditions.append(pl.col("net_profit_growth") >= min_net_profit_growth)
        if max_debt_to_asset is not None:
            conditions.append(pl.col("debt_to_asset") <= max_debt_to_asset)
        if min_dividend_yield is not None:
            conditions.append(pl.col("dividend_yield") >= min_dividend_yield)
        
        if conditions:
            df = df.filter(pl.all_horizontal(conditions))
        
        logger.info(f"财务指标过滤：{len(df)} 只股票")
        return df

    def calculate_composite_score(
        self,
        df: pl.DataFrame,
        factors: dict[str, float],
        direction: dict[str, int]
    ) -> pl.DataFrame:
        """
        计算综合得分
        
        Args:
            df: 包含财务指标的 DataFrame
            factors: 因子权重 {factor_name: weight}
            direction: 因子方向 {factor_name: 1(正向) 或 -1(负向)}
            
        Returns:
            添加综合得分列的 DataFrame
        """
        if df.is_empty():
            return df
        
        # 标准化各因子
        normalized = {}
        for factor in factors.keys():
            if factor in df.columns:
                # Z-Score 标准化
                mean_val = df[factor].mean()
                std_val = df[factor].std()
                
                if std_val > 0:
                    normalized[factor] = (df[factor] - mean_val) / std_val
                else:
                    normalized[factor] = pl.lit(0)
        
        # 计算加权得分
        score_expr = None
        for factor, weight in factors.items():
            if factor in normalized:
                dir_mult = direction.get(factor, 1)
                if score_expr is None:
                    score_expr = dir_mult * weight * normalized[factor]
                else:
                    score_expr = score_expr + dir_mult * weight * normalized[factor]
        
        if score_expr is not None:
            df = df.with_columns(score_expr.alias("composite_score"))
        
        return df

    def get_quality_stocks(
        self,
        df: pl.DataFrame,
        min_roe: float = 15,
        min_revenue_growth: float = 10,
        max_debt_to_asset: float = 60,
        min_net_margin: float = 10
    ) -> pl.DataFrame:
        """
        筛选优质股票（高 ROE、稳定增长、低负债、高利润率）
        
        Args:
            df: 财务数据 DataFrame
            min_roe: 最小 ROE（%）
            min_revenue_growth: 最小营收增长率（%）
            max_debt_to_asset: 最大资产负债率（%）
            min_net_margin: 最小净利率（%）
            
        Returns:
            优质股票列表
        """
        return self.filter_by_metrics(
            df=df,
            min_roe=min_roe,
            min_revenue_growth=min_revenue_growth,
            max_debt_to_asset=max_debt_to_asset,
            min_net_profit_growth=0  # 至少正增长
        ).filter(pl.col("net_margin") >= min_net_margin)

    def get_value_stocks(
        self,
        df: pl.DataFrame,
        max_pe: float = 20,
        max_pb: float = 3,
        min_dividend_yield: float = 2
    ) -> pl.DataFrame:
        """
        筛选价值股（低估值、高股息）
        
        Args:
            df: 财务数据 DataFrame
            max_pe: 最大市盈率
            max_pb: 最大市净率
            min_dividend_yield: 最小股息率（%）
            
        Returns:
            价值股列表
        """
        return self.filter_by_metrics(
            df=df,
            max_pe=max_pe,
            max_pb=max_pb,
            min_dividend_yield=min_dividend_yield
        )

    def get_growth_stocks(
        self,
        df: pl.DataFrame,
        min_revenue_growth: float = 20,
        min_net_profit_growth: float = 25,
        min_roe: float = 10
    ) -> pl.DataFrame:
        """
        筛选成长股（高增长）
        
        Args:
            df: 财务数据 DataFrame
            min_revenue_growth: 最小营收增长率（%）
            min_net_profit_growth: 最小净利润增长率（%）
            min_roe: 最小 ROE（%）
            
        Returns:
            成长股列表
        """
        return self.filter_by_metrics(
            df=df,
            min_revenue_growth=min_revenue_growth,
            min_net_profit_growth=min_net_profit_growth,
            min_roe=min_roe
        )


# 便捷函数
def create_fundamental_data(data_path: Optional[str] = None) -> FundamentalData:
    """创建财务数据实例"""
    return FundamentalData(data_path)
