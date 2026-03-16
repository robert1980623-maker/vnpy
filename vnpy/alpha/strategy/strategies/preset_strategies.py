"""
预设选股策略

包含常用的选股策略：
1. 价值选股策略 - 低估值、高股息
2. 成长选股策略 - 高增长、高 ROE
3. 动量选股策略 - 价格动量、趋势
4. 多因子选股策略 - 综合评分
"""

import polars as pl
from datetime import datetime, timedelta

from vnpy.trader.object import BarData

from .stock_screener_strategy import StockScreenerStrategy


# ========== 价值选股策略 ==========

class ValueStockStrategy(StockScreenerStrategy):
    """价值选股策略 - 低估值、高股息"""

    # 价值股筛选条件
    max_pe: float = 20.0          # 最大市盈率
    max_pb: float = 3.0           # 最大市净率
    min_dividend_yield: float = 2.0  # 最小股息率
    min_roe: float = 10.0         # 最小 ROE

    top_k: int = 30               # 持有股票数量

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        self.max_holdings = self.top_k
        self.rebalance_frequency = "monthly"  # 月度调仓
        self.rebalance_day = 1  # 每月 1 号

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """获取价值股股票池"""
        # 获取信号（包含财务数据）
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 确保有所需的列
        required_cols = ["vt_symbol", "pe_ratio", "pb_ratio", "dividend_yield", "roe"]
        for col in required_cols:
            if col not in signal_df.columns:
                self.write_log(f"警告：缺少列 {col}")
                return pl.DataFrame()

        # 价值股筛选条件
        filtered = signal_df.filter(
            (pl.col("pe_ratio") > 0) &
            (pl.col("pe_ratio") <= self.max_pe) &
            (pl.col("pb_ratio") <= self.max_pb) &
            (pl.col("dividend_yield") >= self.min_dividend_yield) &
            (pl.col("roe") >= self.min_roe)
        )

        # 计算综合得分（估值越低越好，股息越高越好）
        # 使用排名来标准化
        filtered = filtered.with_columns([
            # PE 倒数作为估值得分（PE 越低得分越高）
            (1.0 / pl.col("pe_ratio")).alias("value_score"),
            # 股息率作为收益得分
            pl.col("dividend_yield").alias("yield_score"),
        ])

        # 综合得分 = 估值得分 * 0.6 + 股息得分 * 0.4
        # 需要先标准化
        value_mean = filtered["value_score"].mean()
        value_std = filtered["value_score"].std()
        yield_mean = filtered["yield_score"].mean()
        yield_std = filtered["yield_score"].std()

        if value_std > 0 and yield_std > 0:
            filtered = filtered.with_columns([
                ((pl.col("value_score") - value_mean) / value_std * 0.6 +
                 (pl.col("yield_score") - yield_mean) / yield_std * 0.4).alias("signal")
            ])
        else:
            # 如果标准差为 0，直接相加
            filtered = filtered.with_columns([
                (pl.col("value_score") * 0.6 + pl.col("yield_score") * 0.4).alias("signal")
            ])

        # 过滤有行情的股票
        valid_symbols = [s for s in filtered["vt_symbol"].to_list() if s in bars]
        filtered = filtered.filter(pl.col("vt_symbol").is_in(valid_symbols))

        self.write_log(f"价值股筛选：原始{len(signal_df)}只 -> 过滤后{len(filtered)}只")

        return filtered


# ========== 成长选股策略 ==========

class GrowthStockStrategy(StockScreenerStrategy):
    """成长选股策略 - 高增长、高 ROE"""

    # 成长股筛选条件
    min_revenue_growth: float = 20.0   # 最小营收增长率
    min_net_profit_growth: float = 25.0  # 最小净利润增长率
    min_roe: float = 15.0              # 最小 ROE
    max_pe: float = 50.0               # 最大市盈率（成长股可以容忍高 PE）

    top_k: int = 30                    # 持有股票数量

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        self.max_holdings = self.top_k
        self.rebalance_frequency = "monthly"
        self.rebalance_day = 15  # 每月 15 号

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """获取成长股股票池"""
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 确保有所需的列
        required_cols = ["vt_symbol", "revenue_growth", "net_profit_growth", "roe"]
        for col in required_cols:
            if col not in signal_df.columns:
                self.write_log(f"警告：缺少列 {col}")
                return pl.DataFrame()

        # 成长股筛选条件
        filtered = signal_df.filter(
            (pl.col("revenue_growth") >= self.min_revenue_growth) &
            (pl.col("net_profit_growth") >= self.min_net_profit_growth) &
            (pl.col("roe") >= self.min_roe)
        )

        # 计算综合得分
        # 增长得分 = 营收增长 * 0.4 + 净利润增长 * 0.4
        # 质量得分 = ROE * 0.2
        filtered = filtered.with_columns([
            (
                pl.col("revenue_growth") * 0.4 +
                pl.col("net_profit_growth") * 0.4 +
                pl.col("roe") * 0.2
            ).alias("signal")
        ])

        # 过滤有行情的股票
        valid_symbols = [s for s in filtered["vt_symbol"].to_list() if s in bars]
        filtered = filtered.filter(pl.col("vt_symbol").is_in(valid_symbols))

        self.write_log(f"成长股筛选：原始{len(signal_df)}只 -> 过滤后{len(filtered)}只")

        return filtered


# ========== 动量选股策略 ==========

class MomentumStockStrategy(StockScreenerStrategy):
    """动量选股策略 - 价格动量、趋势"""

    # 动量参数
    lookback_period: int = 20       # 回看天数
    min_momentum: float = 0.0       # 最小动量（收益率）
    top_k: int = 30                 # 持有股票数量

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        self.max_holdings = self.top_k
        self.rebalance_frequency = "weekly"
        self.rebalance_day = 1  # 每周一

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """获取动量股股票池"""
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 计算动量（收益率）
        # 假设有 close_price 和 close_price_N 天前 的列
        if "momentum" not in signal_df.columns:
            # 如果没有预计算的动量，尝试计算
            if "close_price" in signal_df.columns and f"close_price_{self.lookback_period}" in signal_df.columns:
                signal_df = signal_df.with_columns([
                    ((pl.col("close_price") - pl.col(f"close_price_{self.lookback_period}")) /
                     pl.col(f"close_price_{self.lookback_period}")).alias("momentum")
                ])
            else:
                self.write_log("无法计算动量，使用默认信号")
                signal_df = signal_df.with_columns(pl.lit(1.0).alias("momentum"))

        # 过滤动量为正的股票
        filtered = signal_df.filter(pl.col("momentum") >= self.min_momentum)

        # 使用动量作为信号
        filtered = filtered.with_columns(pl.col("momentum").alias("signal"))

        # 过滤有行情的股票
        valid_symbols = [s for s in filtered["vt_symbol"].to_list() if s in bars]
        filtered = filtered.filter(pl.col("vt_symbol").is_in(valid_symbols))

        self.write_log(f"动量股筛选：原始{len(signal_df)}只 -> 过滤后{len(filtered)}只")

        return filtered


# ========== 多因子选股策略 ==========

class MultiFactorStrategy(StockScreenerStrategy):
    """多因子选股策略 - 综合评分"""

    # 因子权重
    value_weight: float = 0.25      # 估值因子权重
    quality_weight: float = 0.25    # 质量因子权重
    growth_weight: float = 0.25     # 成长因子权重
    momentum_weight: float = 0.25   # 动量因子权重

    top_k: int = 50                 # 持有股票数量

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        self.max_holdings = self.top_k
        self.rebalance_frequency = "monthly"
        self.rebalance_day = 1

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """获取多因子股票池"""
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 定义所需因子
        value_factors = ["pe_ratio", "pb_ratio"]
        quality_factors = ["roe", "net_margin"]
        growth_factors = ["revenue_growth", "net_profit_growth"]
        momentum_factors = ["momentum_20d"]

        # 检查是否有足够的因子
        all_factors = value_factors + quality_factors + growth_factors + momentum_factors
        available_factors = [f for f in all_factors if f in signal_df.columns]

        if len(available_factors) < 4:
            self.write_log(f"因子不足，只有 {len(available_factors)} 个因子")
            # 使用简单排序
            if "signal" in signal_df.columns:
                return signal_df
            else:
                return signal_df.with_columns(pl.lit(1.0).alias("signal"))

        # 计算各因子得分（Z-Score 标准化）
        factor_scores = {}

        # 估值因子（逆向：越低越好）
        for factor in value_factors:
            if factor in signal_df.columns:
                mean_val = signal_df[factor].mean()
                std_val = signal_df[factor].std()
                if std_val > 0:
                    factor_scores[factor] = -(signal_df[factor] - mean_val) / std_val  # 负号表示逆向
                else:
                    factor_scores[factor] = pl.lit(0)

        # 质量因子（正向：越高越好）
        for factor in quality_factors:
            if factor in signal_df.columns:
                mean_val = signal_df[factor].mean()
                std_val = signal_df[factor].std()
                if std_val > 0:
                    factor_scores[factor] = (signal_df[factor] - mean_val) / std_val
                else:
                    factor_scores[factor] = pl.lit(0)

        # 成长因子（正向）
        for factor in growth_factors:
            if factor in signal_df.columns:
                mean_val = signal_df[factor].mean()
                std_val = signal_df[factor].std()
                if std_val > 0:
                    factor_scores[factor] = (signal_df[factor] - mean_val) / std_val
                else:
                    factor_scores[factor] = pl.lit(0)

        # 动量因子（正向）
        for factor in momentum_factors:
            if factor in signal_df.columns:
                mean_val = signal_df[factor].mean()
                std_val = signal_df[factor].std()
                if std_val > 0:
                    factor_scores[factor] = (signal_df[factor] - mean_val) / std_val
                else:
                    factor_scores[factor] = pl.lit(0)

        # 计算综合得分
        # 需要动态构建表达式
        n_value = len([f for f in value_factors if f in factor_scores])
        n_quality = len([f for f in quality_factors if f in quality_factors])
        n_growth = len([f for f in growth_factors if f in factor_scores])
        n_momentum = len([f for f in momentum_factors if f in factor_scores])

        # 如果某个类别没有因子，重新分配权重
        total_weight = 0
        if n_value > 0:
            total_weight += self.value_weight
        if n_quality > 0:
            total_weight += self.quality_weight
        if n_growth > 0:
            total_weight += self.growth_weight
        if n_momentum > 0:
            total_weight += self.momentum_weight

        if total_weight == 0:
            return signal_df.with_columns(pl.lit(1.0).alias("signal"))

        # 归一化权重
        if n_value > 0:
            value_w = self.value_weight / total_weight / n_value
        else:
            value_w = 0

        if n_quality > 0:
            quality_w = self.quality_weight / total_weight / n_quality
        else:
            quality_w = 0

        if n_growth > 0:
            growth_w = self.growth_weight / total_weight / n_growth
        else:
            growth_w = 0

        if n_momentum > 0:
            momentum_w = self.momentum_weight / total_weight / n_momentum
        else:
            momentum_w = 0

        # 构建综合得分表达式
        score_expr = None

        for factor, score in factor_scores.items():
            if factor in value_factors:
                weight = value_w
            elif factor in quality_factors:
                weight = quality_w
            elif factor in growth_factors:
                weight = growth_w
            else:
                weight = momentum_w

            if score_expr is None:
                score_expr = weight * score
            else:
                score_expr = score_expr + weight * score

        if score_expr is not None:
            signal_df = signal_df.with_columns(score_expr.alias("signal"))

        # 过滤有行情的股票
        valid_symbols = [s for s in signal_df["vt_symbol"].to_list() if s in bars]
        signal_df = signal_df.filter(pl.col("vt_symbol").is_in(valid_symbols))

        self.write_log(f"多因子选股：原始{len(signal_df)}只 -> 有效{len(signal_df)}只")

        return signal_df
