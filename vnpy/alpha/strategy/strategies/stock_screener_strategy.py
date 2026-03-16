"""
选股策略模板

支持截面选股策略，包括：
- 定期调仓（日频/周频/月频）
- 股票池动态管理
- 仓位控制
- 交易成本优化
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Literal

import polars as pl

from vnpy.trader.object import BarData, TradeData
from vnpy.trader.constant import Direction
from vnpy.trader.utility import round_to

from ..template import AlphaStrategy


class StockScreenerStrategy(AlphaStrategy):
    """选股策略基类"""

    # ========== 策略参数 ==========
    # 调仓周期
    rebalance_freq: Literal["daily", "weekly", "monthly"] = "weekly"  # 调仓频率
    rebalance_day: int = 1          # 调仓日（周频：1-5 代表周一到周五，月频：1-31）

    # 持仓控制
    max_holdings: int = 50          # 最大持仓数量
    min_holdings: int = 10          # 最小持仓数量
    cash_ratio: float = 0.95        # 目标仓位（0-1）
    min_cash_ratio: float = 0.05    # 最小现金比例

    # 个股限制
    max_weight: float = 0.10        # 个股权重上限（10%）
    min_weight: float = 0.01        # 个股权重下限（1%）

    # 交易限制
    min_holding_days: int = 1       # 最小持有天数
    max_turnover_rate: float = 0.5  # 最大换手率（单次调仓）

    # 交易成本
    open_rate: float = 0.0003       # 买入费率
    close_rate: float = 0.0013      # 卖出费率
    min_commission: float = 5       # 最低佣金
    price_add: float = 0.001        # 价格滑点

    # 股票池
    stock_pool_name: str = ""       # 股票池名称（可选）

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)

        # 持仓跟踪
        self.holding_days: defaultdict = defaultdict(int)  # 持仓天数
        self.holding_cost: defaultdict = defaultdict(float)  # 持仓成本

        # 调仓跟踪
        self.last_rebalance_date: Optional[datetime] = None
        self.should_rebalance: bool = True  # 首次运行需要调仓

        # 交易统计
        self.turnover_today: float = 0  # 今日成交额

    def on_init(self) -> None:
        """策略初始化"""
        self.write_log(f"策略初始化 - {self.strategy_name}")
        self.write_log(f"调仓频率：{self.rebalance_frequency}")
        self.write_log(f"最大持仓：{self.max_holdings} 只")

    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        # 更新持仓天数和成本
        if trade.direction == Direction.SHORT:
            # 卖出时清除记录
            self.holding_days.pop(trade.vt_symbol, None)
            self.holding_cost.pop(trade.vt_symbol, None)
            self.write_log(f"卖出成交：{trade.vt_symbol} {trade.volume}股 @ {trade.price}")
        else:
            # 买入时记录成本
            self.holding_cost[trade.vt_symbol] = trade.price
            self.write_log(f"买入成交：{trade.vt_symbol} {trade.volume}股 @ {trade.price}")

    def on_bars(self, bars: dict[str, BarData]) -> None:
        """K 线回调 - 由子类实现具体选股逻辑"""
        # 检查是否需要调仓
        if self._should_rebalance_now():
            self._execute_rebalance(bars)
        else:
            # 非调仓日，更新持仓天数
            self._update_holding_days()

    def _should_rebalance_now(self) -> bool:
        """判断是否应该调仓"""
        if not self.datetime:
            return False

        # 首次运行
        if self.last_rebalance_date is None:
            return True

        # 根据频率判断
        if self.rebalance_frequency == "daily":
            return True

        elif self.rebalance_frequency == "weekly":
            # 判断是否是调仓日（weekday: 0=周一，4=周五）
            days_since_rebalance = (self.datetime - self.last_rebalance_date).days
            if days_since_rebalance >= 7:
                return True
            # 或者判断是否是指定的周几
            if self.datetime.weekday() == (self.rebalance_day - 1):
                return True

        elif self.rebalance_frequency == "monthly":
            # 判断是否是调仓日
            if self.datetime.day == self.rebalance_day:
                return True
            # 或者距离上次调仓超过 30 天
            days_since_rebalance = (self.datetime - self.last_rebalance_date).days
            if days_since_rebalance >= 30:
                return True

        return False

    def _update_holding_days(self) -> None:
        """更新持仓天数"""
        for vt_symbol in list(self.pos_data.keys()):
            if self.pos_data[vt_symbol] > 0:
                self.holding_days[vt_symbol] += 1

    def _execute_rebalance(self, bars: dict[str, BarData]) -> None:
        """执行调仓"""
        self.write_log(f"\n{'='*60}")
        self.write_log(f"开始调仓 - {self.datetime.strftime('%Y-%m-%d')}")
        self.write_log(f"{'='*60}")

        # 重置今日成交统计
        self.turnover_today = 0

        # 1. 获取选股信号
        stock_pool = self._get_stock_pool(bars)

        if stock_pool.is_empty():
            self.write_log("警告：股票池为空，跳过调仓")
            return

        # 2. 计算目标持仓
        target_positions = self._calculate_target_positions(stock_pool, bars)

        # 3. 生成交易列表
        sell_list, buy_list = self._generate_trades(target_positions, bars)

        # 4. 执行卖出
        cash = self.get_cash_available()
        cash = self._execute_sells(sell_list, bars, cash)

        # 5. 执行买入
        self._execute_buys(buy_list, bars, cash)

        # 更新调仓日期
        self.last_rebalance_date = self.datetime
        self.should_rebalance = False

        self.write_log(f"调仓完成 - 买入{len(buy_list)}只，卖出{len(sell_list)}只")
        self.write_log(f"{'='*60}\n")

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """
        获取候选股票池

        子类需要实现此方法来定义选股逻辑

        Returns:
            DataFrame 包含股票信号，至少需要以下列：
            - vt_symbol: 股票代码
            - signal: 选股信号值（用于排序）
        """
        # 默认实现：返回当前有信号的股票
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 确保有 signal 列
        if "signal" not in signal_df.columns:
            signal_df = signal_df.with_columns(pl.lit(1.0).alias("signal"))

        return signal_df

    def _calculate_target_positions(
        self,
        stock_pool: pl.DataFrame,
        bars: dict[str, BarData]
    ) -> dict[str, float]:
        """
        计算目标持仓

        Args:
            stock_pool: 候选股票池
            bars: 当前 K 线数据

        Returns:
            {vt_symbol: target_volume}
        """
        # 按信号排序
        stock_pool = stock_pool.sort("signal", descending=True)

        # 限制持仓数量
        stock_pool = stock_pool.limit(self.max_holdings)

        # 获取可用资金
        portfolio_value = self.get_portfolio_value()
        target_equity_value = portfolio_value * self.cash_ratio

        # 等权重分配
        n_stocks = min(len(stock_pool), self.max_holdings)
        if n_stocks == 0:
            return {}

        value_per_stock = target_equity_value / n_stocks

        # 计算目标持仓
        target_positions = {}
        for row in stock_pool.iter_rows(named=True):
            vt_symbol = row["vt_symbol"]

            # 获取当前价格
            bar = bars.get(vt_symbol)
            if not bar or bar.close_price <= 0:
                continue

            price = bar.close_price

            # 计算目标股数
            target_volume = round_to(value_per_stock / price, 100)

            # 应用权重限制
            weight = target_volume * price / portfolio_value
            if weight > self.max_weight:
                target_volume = round_to((self.max_weight * portfolio_value) / price, 100)
            elif weight < self.min_weight and target_volume > 0:
                target_volume = 0  # 低于最小权重则不买

            if target_volume > 0:
                target_positions[vt_symbol] = target_volume

        return target_positions

    def _generate_trades(
        self,
        target_positions: dict[str, float],
        bars: dict[str, BarData]
    ) -> tuple[list, list]:
        """
        生成交易列表

        Returns:
            (sell_list, buy_list)
        """
        sell_list = []
        buy_list = []

        current_positions = {
            k: v for k, v in self.pos_data.items() if v > 0
        }

        # 找出需要卖出的股票
        for vt_symbol, current_volume in current_positions.items():
            target_volume = target_positions.get(vt_symbol, 0)

            if target_volume < current_volume:
                # 需要卖出
                sell_volume = current_volume - target_volume

                # 检查最小持有天数
                if self.holding_days.get(vt_symbol, 0) < self.min_holding_days:
                    self.write_log(f"跳过 {vt_symbol} - 持有天数不足")
                    continue

                bar = bars.get(vt_symbol)
                if bar:
                    sell_list.append({
                        "vt_symbol": vt_symbol,
                        "volume": sell_volume,
                        "price": bar.close_price
                    })

        # 找出需要买入的股票
        for vt_symbol, target_volume in target_positions.items():
            current_volume = current_positions.get(vt_symbol, 0)

            if target_volume > current_volume:
                # 需要买入
                buy_volume = target_volume - current_volume

                bar = bars.get(vt_symbol)
                if bar:
                    buy_list.append({
                        "vt_symbol": vt_symbol,
                        "volume": buy_volume,
                        "price": bar.close_price
                    })

        # 检查换手率限制
        portfolio_value = self.get_portfolio_value()
        sell_value = sum(item["volume"] * item["price"] for item in sell_list)
        buy_value = sum(item["volume"] * item["price"] for item in buy_list)
        turnover_rate = (sell_value + buy_value) / portfolio_value

        if turnover_rate > self.max_turnover_rate:
            self.write_log(f"换手率超限 ({turnover_rate:.2%} > {self.max_turnover_rate:.2%})，降低交易规模")
            scale = self.max_turnover_rate / turnover_rate
            for item in sell_list:
                item["volume"] = round_to(item["volume"] * scale, 100)
            for item in buy_list:
                item["volume"] = round_to(item["volume"] * scale, 100)

        return sell_list, buy_list

    def _execute_sells(
        self,
        sell_list: list,
        bars: dict[str, BarData],
        cash: float
    ) -> float:
        """执行卖出"""
        for item in sell_list:
            vt_symbol = item["vt_symbol"]
            volume = item["volume"]
            price = item["price"]

            if volume <= 0:
                continue

            # 设置目标仓位为 0 或减少
            current_target = self.get_target(vt_symbol)
            new_target = max(0, current_target - volume)
            self.set_target(vt_symbol, new_target)

            # 计算成交金额和费用
            turnover = volume * price
            cost = max(turnover * self.close_rate, self.min_commission)
            cash += turnover - cost
            self.turnover_today += turnover

            self.write_log(f"卖出：{vt_symbol} {volume}股 @ {price:.2f} (目标：{new_target})")

        return cash

    def _execute_buys(
        self,
        buy_list: list,
        bars: dict[str, BarData],
        cash: float
    ) -> None:
        """执行买入"""
        if not buy_list:
            return

        # 计算可用资金
        target_cash = self.get_portfolio_value() * (1 - self.cash_ratio)
        available_cash = cash - target_cash

        if available_cash <= 0:
            self.write_log("可用资金不足，跳过买入")
            return

        # 等权重分配买入资金
        buy_value_per_stock = available_cash / len(buy_list)

        for item in buy_list:
            vt_symbol = item["vt_symbol"]
            volume = item["volume"]
            price = item["price"]

            if volume <= 0 or price <= 0:
                continue

            # 计算实际可买数量（考虑资金限制）
            buy_value = volume * price
            if buy_value > buy_value_per_stock * 1.2:  # 允许 20% 浮动
                volume = round_to((buy_value_per_stock / price), 100)
                buy_value = volume * price

            # 设置目标仓位
            current_target = self.get_target(vt_symbol)
            new_target = current_target + volume
            self.set_target(vt_symbol, new_target)

            # 计算费用
            cost = max(buy_value * self.open_rate, self.min_commission)

            self.write_log(f"买入：{vt_symbol} {volume}股 @ {price:.2f} (目标：{new_target}, 金额：{buy_value:.2f})")

    def get_turnover_rate(self) -> float:
        """获取当前换手率"""
        portfolio_value = self.get_portfolio_value()
        if portfolio_value <= 0:
            return 0
        return self.turnover_today / portfolio_value

    def get_holding_info(self) -> dict:
        """获取持仓信息"""
        info = {}
        for vt_symbol, volume in self.pos_data.items():
            if volume > 0:
                info[vt_symbol] = {
                    "volume": volume,
                    "holding_days": self.holding_days.get(vt_symbol, 0),
                    "cost": self.holding_cost.get(vt_symbol, 0)
                }
        return info

    def write_log(self, msg: str) -> None:
        """写日志"""
        super().write_log(msg)


# ========== 简单选股策略示例 ==========

class SimpleScreenerStrategy(StockScreenerStrategy):
    """简单选股策略示例 - 基于信号排序"""

    top_k: int = 30  # 持有前 K 只股票

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

    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """获取股票池 - 直接使用信号"""
        signal_df = self.get_signal()

        if signal_df.is_empty():
            return pl.DataFrame()

        # 确保有 signal 列
        if "signal" not in signal_df.columns:
            signal_df = signal_df.with_columns(pl.lit(1.0).alias("signal"))

        # 过滤掉没有行情的股票
        valid_symbols = [s for s in signal_df["vt_symbol"].to_list() if s in bars]
        signal_df = signal_df.filter(pl.col("vt_symbol").is_in(valid_symbols))

        return signal_df
