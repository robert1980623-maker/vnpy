"""
截面回测引擎

支持选股策略的截面回测，包括：
- 多股票同时回测
- 截面调仓
- 股票池动态变化
- 截面绩效分析
"""

from collections import defaultdict
from datetime import date, datetime
from copy import copy
from typing import cast, Optional
import traceback

import numpy as np
import polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from tqdm import tqdm

from vnpy.trader.constant import Direction, Offset, Interval, Status
from vnpy.trader.object import OrderData, TradeData, BarData
from vnpy.trader.utility import round_to, extract_vt_symbol

from ..logger import logger
from ..lab import AlphaLab
from .template import AlphaStrategy
from .strategies.stock_screener_strategy import StockScreenerStrategy


class CrossSectionalBacktestingEngine:
    """截面回测引擎 - 支持选股策略"""

    gateway_name: str = "CROSS_SECTIONAL"

    def __init__(self, lab: AlphaLab) -> None:
        """构造函数"""
        self.lab: AlphaLab = lab

        # 基础参数
        self.vt_symbols: list[str] = []  # 全市场股票池
        self.start: datetime
        self.end: datetime
        self.capital: float = 0
        self.risk_free: float = 0
        self.annual_days: int = 240

        # 策略
        self.strategy_class: type[AlphaStrategy]
        self.strategy: Optional[AlphaStrategy] = None
        self.strategy_setting: dict = {}

        # 数据
        self.interval: Interval = Interval.DAILY
        self.history_data: dict[tuple[datetime, str], BarData] = {}  # (datetime, vt_symbol) -> BarData
        self.dts: set[datetime] = set()
        self.signal_data: dict[datetime, pl.DataFrame] = {}  # 每日信号

        # 交易
        self.trade_count: int = 0
        self.trades: dict[str, TradeData] = {}

        # 持仓
        self.positions: dict[str, float] = defaultdict(float)  # vt_symbol -> volume
        self.target_positions: dict[str, float] = defaultdict(float)  # vt_symbol -> target_volume

        # T+1 交易规则：记录每只股票的买入日期
        self._buy_dates: dict[str, date] = {}  # vt_symbol -> buy date

        # 流动性限制：记录每只股票的成交量（用于部分成交）
        self._daily_volumes: dict[str, float] = {}  # vt_symbol -> volume

        # 涨跌停限制：记录每只股票的涨停价/跌停价
        self._limit_prices: dict[str, tuple[float, float]] = {}  # vt_symbol -> (upper_limit, lower_limit)

        # 滑点参数（默认万分之5）
        self.slippage_rate: float = 0.0005

        # 资金
        self.cash: float = 0
        self.frozen_cash: float = 0

        # 每日结果
        self.daily_results: dict[date, CrossSectionalDailyResult] = {}
        self.daily_df: Optional[pl.DataFrame] = None

        # 日志
        self.logs: list[str] = []

    def set_parameters(
        self,
        vt_symbols: list[str],
        interval: Interval,
        start: datetime,
        end: datetime,
        capital: int = 1_000_000,
        risk_free: float = 0,
        annual_days: int = 240
    ) -> None:
        """设置回测参数"""
        self.vt_symbols = vt_symbols
        self.interval = interval
        self.start = start
        self.end = end
        self.capital = capital
        self.risk_free = risk_free
        self.annual_days = annual_days
        self.cash = capital

        logger.info(f"回测参数设置完成")
        logger.info(f"  股票数量：{len(vt_symbols)}")
        logger.info(f"  时间范围：{start.date()} - {end.date()}")
        logger.info(f"  初始资金：{capital:,.0f}")

    def add_strategy(self, strategy_class: type, setting: dict) -> None:
        """添加策略"""
        self.strategy_class = strategy_class
        self.strategy_setting = setting
        logger.info(f"策略添加完成：{strategy_class.__name__}")

    def load_data(self) -> None:
        """加载历史数据"""
        logger.info("开始加载历史数据")

        if not self.end:
            self.end = datetime.now()

        if self.start >= self.end:
            logger.error("起始日期必须小于结束日期")
            return

        # 清空历史数据
        self.history_data.clear()
        self.dts.clear()
        self.signal_data.clear()

        # 加载每只股票的历史数据
        empty_symbols: list[str] = []
        for vt_symbol in tqdm(self.vt_symbols, desc="加载股票数据"):
            data: list[BarData] = self.lab.load_bar_data(
                vt_symbol,
                self.interval,
                self.start,
                self.end
            )

            for bar in data:
                self.dts.add(bar.datetime)
                self.history_data[(bar.datetime, vt_symbol)] = bar

            if not data:
                empty_symbols.append(vt_symbol)

        if empty_symbols:
            logger.warning(f"{len(empty_symbols)} 只股票无数据")

        # 按日期组织信号数据
        self._organize_signals()

        logger.info(f"数据加载完成：{len(self.dts)} 个交易日，{len(self.history_data)} 条记录")

    def _organize_signals(self) -> None:
        """组织信号数据"""
        # 从实验室加载信号数据
        if not hasattr(self.lab, 'load_signals'):
            logger.debug("AlphaLab 无 load_signals 方法，跳过信号数据加载")
            return

        all_signals = self.lab.load_signals()

        if all_signals.is_empty():
            logger.warning("信号数据为空")
            return

        # 按日期分组
        for dt in self.dts:
            date_str = dt.strftime("%Y-%m-%d")
            daily_signals = all_signals.filter(pl.col("datetime") == date_str)

            if not daily_signals.is_empty():
                self.signal_data[dt] = daily_signals

        logger.info(f"信号数据组织完成：{len(self.signal_data)} 个交易日")

    def run_backtesting(self) -> None:
        """运行回测"""
        logger.info("开始截面回测")

        # 初始化策略
        self._init_strategy()

        # 排序日期
        dts: list[datetime] = sorted(list(self.dts))

        logger.info(f"开始回放历史数据：{len(dts)} 个交易日")

        # 回测主循环
        for dt in tqdm(dts, desc="回测中"):
            try:
                self._run_daily(dt)
            except Exception as e:
                logger.error(f"回测出错：{dt} - {str(e)}")
                logger.error(traceback.format_exc())
                break

        logger.info("回测完成")

    def _init_strategy(self) -> None:
        """初始化策略"""
        if not self.strategy_class:
            logger.error("策略类未设置")
            return

        # 创建策略实例
        self.strategy = self.strategy_class(
            strategy_engine=self,
            strategy_name=self.strategy_class.__name__,
            vt_symbols=copy(self.vt_symbols),
            setting=self.strategy_setting
        )

        # 调用策略初始化
        self.strategy.on_init()

        logger.info("策略初始化完成")

    def _run_daily(self, dt: datetime) -> None:
        """运行单个交易日"""
        self.datetime = dt
        d = dt.date()

        # 创建每日结果记录
        if d not in self.daily_results:
            self.daily_results[d] = CrossSectionalDailyResult(dt)

        daily_result = self.daily_results[d]

        # 获取当日的 K 线数据
        bars: dict[str, BarData] = {}
        for vt_symbol in self.vt_symbols:
            key = (dt, vt_symbol)
            if key in self.history_data:
                bars[vt_symbol] = self.history_data[key]

        # 更新策略的 bars
        if self.strategy:
            self.strategy.bars = bars
            self.strategy.datetime = dt

        # 获取信号
        if dt in self.signal_data:
            if self.strategy:
                self.strategy.signal_df = self.signal_data[dt]

        # 调用策略的 on_bars
        if self.strategy and bars:
            self.strategy.on_bars(bars)

        # 计算每日结果
        daily_result.calculate_daily_result(
            positions=self.positions,
            cash=self.cash,
            bars=bars,
            pre_closes=self._get_pre_closes(dt)
        )

    def _get_pre_closes(self, dt: datetime) -> dict[str, float]:
        """获取前收盘价"""
        pre_closes: dict[str, float] = {}

        # 获取前一交易日
        prev_dt = self._get_prev_trading_day(dt)
        if not prev_dt:
            return pre_closes

        for vt_symbol in self.vt_symbols:
            key = (prev_dt, vt_symbol)
            if key in self.history_data:
                bar = self.history_data[key]
                pre_closes[vt_symbol] = bar.close_price

        return pre_closes

    def _get_prev_trading_day(self, dt: datetime) -> Optional[datetime]:
        """获取前一交易日"""
        sorted_dts = sorted(self.dts)
        for i, d in enumerate(sorted_dts):
            if d == dt and i > 0:
                return sorted_dts[i - 1]
        return None

    def _is_chi_next(self, vt_symbol: str) -> bool:
        """判断是否为创业板股票（300开头）"""
        symbol = extract_vt_symbol(vt_symbol)[0]
        return symbol.startswith("300")

    def _is_st_stock(self, vt_symbol: str, bar: Optional[BarData] = None) -> bool:
        """判断是否为 ST 股票"""
        # 实际项目中应从数据源获取 ST 状态，这里简化处理
        # 如果 bar 数据包含 ST 标记则使用，否则返回 False
        if bar and hasattr(bar, "symbol"):
            symbol = bar.symbol.upper()
            return "ST" in symbol or "*ST" in symbol or "S*" in symbol
        return False

    def _get_limit_prices(self, vt_symbol: str, preclose: float, bar: Optional[BarData] = None) -> tuple[float, float]:
        """计算涨跌停价格
        
        Args:
            vt_symbol: 股票代码
            preclose: 前收盘价
            bar: 当日 K 线数据（用于判断是否为 ST）
            
        Returns:
            (upper_limit, lower_limit) 涨停价和跌停价
        """
        if preclose <= 0:
            return (float('inf'), 0.0)
        
        # 判断股票类型
        is_st = self._is_st_stock(vt_symbol, bar)
        is_chi_next = self._is_chi_next(vt_symbol)
        
        if is_st:
            limit_rate = 0.05  # ST 股 ±5%
        elif is_chi_next:
            limit_rate = 0.20  # 创业板 ±20%
        else:
            limit_rate = 0.10  # A 股主板 ±10%
        
        upper_limit = preclose * (1 + limit_rate)
        lower_limit = preclose * (1 - limit_rate)
        
        return (upper_limit, lower_limit)

    def _round_to_trading_unit(self, volume: float) -> float:
        """调整为最小交易单位（100股）"""
        if volume <= 0:
            return 0.0
        return int(volume // 100) * 100

    def _can_sell(self, vt_symbol: str, current_date: date) -> bool:
        """T+1 交易规则检查：当日买入的股票不能当日卖出
        
        Args:
            vt_symbol: 股票代码
            current_date: 当前日期
            
        Returns:
            True 可以卖出，False 不能卖出
        """
        if vt_symbol not in self._buy_dates:
            # 从未买入过，可以卖出（持仓来自其他来源）
            return True
        buy_date = self._buy_dates[vt_symbol]
        return buy_date < current_date

    def _apply_liquidity_constraint(
        self, 
        vt_symbol: str, 
        target_volume: float, 
        direction: Direction,
        dt: datetime
    ) -> float:
        """流动性约束：当成交量不足时部分成交
        
        Args:
            vt_symbol: 股票代码
            target_volume: 目标成交量
            direction: 交易方向
            dt: 当前时间
            
        Returns:
            实际可成交数量
        """
        if target_volume <= 0:
            return 0.0
        
        # 获取当日成交量
        key = (dt, vt_symbol)
        if key in self.history_data:
            bar = self.history_data[key]
            daily_volume = bar.volume
        else:
            # 如果没有当日数据，使用记录的成交量
            daily_volume = self._daily_volumes.get(vt_symbol, float('inf'))
        
        if daily_volume <= 0:
            return 0.0
        
        # 对于卖出，限制为当日成交量的 10% 以内（避免对市场造成过大冲击）
        if direction == Direction.SHORT:
            max_sell_volume = daily_volume * 0.10
            return min(target_volume, max_sell_volume)
        
        # 买入不受成交量限制（A股二级市场买入不影响流动性）
        return target_volume

    def _calculate_slippage(self, price: float, volume: float, direction: Direction) -> float:
        """计算滑点成本
        
        Args:
            price: 成交价格
            volume: 成交数量
            direction: 交易方向
            
        Returns:
            滑点成本（正数表示成本，负数表示收益）
        """
        if price <= 0 or volume <= 0:
            return 0.0
        # 滑点 = 价格 * 滑点率
        # 买入时：滑点使成本增加（正）
        # 卖出时：滑点使收益减少（正，即成本）
        slippage_cost = price * self.slippage_rate * volume
        return slippage_cost

    # ========== 策略引擎接口方法 ==========

    def get_signal(self) -> pl.DataFrame:
        """获取当前信号"""
        if not self.strategy or not self.datetime:
            return pl.DataFrame()

        return self.signal_data.get(self.datetime, pl.DataFrame())

    def send_order(
        self,
        strategy: AlphaStrategy,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float
    ) -> list[str]:
        """发送订单
        
        应用以下执行细节：
        1. 涨跌停限制
        2. 最小交易单位（100股）
        3. T+1 交易规则
        4. 流动性约束（部分成交）
        5. 滑点模拟
        """
        vt_orderids: list[str] = []
        current_date = self.datetime.date() if self.datetime else None

        # ========== 涨跌停限制 ==========
        # 获取前收盘价
        preclose = 0.0
        prev_dt = self._get_prev_trading_day(self.datetime) if self.datetime else None
        if prev_dt:
            prev_key = (prev_dt, vt_symbol)
            if prev_key in self.history_data:
                preclose = self.history_data[prev_key].close_price

        # 获取当日 K 线数据（用于判断 ST）
        bar = None
        if self.datetime:
            bar_key = (self.datetime, vt_symbol)
            bar = self.history_data.get(bar_key)

        # 计算涨跌停价格
        upper_limit, lower_limit = self._get_limit_prices(vt_symbol, preclose, bar)
        self._limit_prices[vt_symbol] = (upper_limit, lower_limit)

        # 应用涨跌停限制
        if direction == Direction.LONG:
            # 买入：不能高于涨停价
            exec_price = min(price, upper_limit)
        else:
            # 卖出：不能低于跌停价
            exec_price = max(price, lower_limit)

        # 如果涨跌停价无效（价格为0或涨跌停价不合法），使用原始价格
        if exec_price <= 0:
            exec_price = price

        # ========== 最小交易单位（100股） ==========
        volume = self._round_to_trading_unit(volume)
        if volume <= 0:
            logger.warning(f"{vt_symbol} 目标成交量 {volume} 调整为0，跳过交易")
            return vt_orderids

        # ========== T+1 交易规则 ==========
        # 卖出时检查 T+1 限制
        if direction == Direction.SHORT:
            if current_date and not self._can_sell(vt_symbol, current_date):
                logger.warning(f"{vt_symbol} 处于 T+1 限制，当日不能卖出")
                return vt_orderids

        # ========== 流动性约束（部分成交） ==========
        volume = self._apply_liquidity_constraint(vt_symbol, volume, direction, self.datetime)

        if volume <= 0:
            logger.warning(f"{vt_symbol} 流动性不足，实际成交量为0，跳过交易")
            return vt_orderids

        # ========== 滑点模拟 ==========
        slippage_cost = self._calculate_slippage(exec_price, volume, direction)

        # 创建订单
        order = OrderData(
            symbol=extract_vt_symbol(vt_symbol)[0],
            exchange=extract_vt_symbol(vt_symbol)[1],
            orderid=f"BACKTEST_{self.trade_count}",
            direction=direction,
            offset=offset,
            price=exec_price,
            volume=volume,
            traded=volume,
            status=Status.ALLTRADED,
            datetime=self.datetime,
            gateway_name=self.gateway_name
        )

        # 创建成交
        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=f"TRADE_{self.trade_count}",
            direction=direction,
            offset=offset,
            price=exec_price,
            volume=volume,
            datetime=order.datetime,
            gateway_name=self.gateway_name
        )

        # 更新持仓
        if direction == Direction.LONG:
            self.positions[vt_symbol] += volume
            # 记录买入日期（T+1 规则）
            if current_date:
                self._buy_dates[vt_symbol] = current_date
        else:
            self.positions[vt_symbol] -= volume

        # 更新资金（含滑点成本）
        turnover = exec_price * volume
        if direction == Direction.LONG:
            # 买入：检查可用资金
            required_cash = turnover + slippage_cost
            if self.cash < required_cash:
                logger.warning(f"{vt_symbol} 可用资金不足：需要 {required_cash:.2f}，当前 {self.cash:.2f}，跳过交易")
                return vt_orderids
            self.cash -= required_cash
        else:
            self.cash += (turnover - slippage_cost)

        # 更新当日成交量记录
        if bar:
            self._daily_volumes[vt_symbol] = bar.volume

        # 记录成交
        self.trades[trade.tradeid] = trade
        self.trade_count += 1

        # 日志记录
        logger.info(
            f"交易执行 | {vt_symbol} | {'买入' if direction == Direction.LONG else '卖出'} | "
            f"价格: {exec_price:.2f} | 数量: {volume} | "
            f"滑点成本: {slippage_cost:.2f}"
        )

        # 通知策略
        if self.strategy:
            self.strategy.update_trade(trade)

        vt_orderids.append(order.orderid)
        return vt_orderids

    def cancel_order(self, strategy: AlphaStrategy, vt_orderid: str) -> None:
        """取消订单"""
        # 回测中暂不支持撤单
        pass

    def get_cash_available(self) -> float:
        """获取可用资金"""
        return self.cash

    def get_holding_value(self) -> float:
        """获取持仓市值"""
        if not self.datetime:
            return 0

        holding_value = 0
        for vt_symbol, volume in self.positions.items():
            if volume > 0:
                key = (self.datetime, vt_symbol)
                if key in self.history_data:
                    bar = self.history_data[key]
                    holding_value += bar.close_price * volume

        return holding_value

    def get_portfolio_value(self) -> float:
        """获取组合总市值"""
        return self.get_cash_available() + self.get_holding_value()

    def write_log(self, msg: str, strategy: AlphaStrategy) -> None:
        """写日志"""
        self.logs.append(msg)
        logger.info(msg)

    # ========== 结果分析 ==========

    def calculate_result(self) -> Optional[pl.DataFrame]:
        """计算回测结果"""
        logger.info("开始计算回测结果")

        if not self.daily_results:
            logger.warning("每日结果为空")
            return None

        # 整理每日结果
        results: dict = defaultdict(list)

        for d, daily_result in sorted(self.daily_results.items()):
            results["date"].append(d)
            results["trade_count"].append(daily_result.trade_count)
            results["turnover"].append(daily_result.turnover)
            results["commission"].append(daily_result.commission)
            results["trading_pnl"].append(daily_result.trading_pnl)
            results["holding_pnl"].append(daily_result.holding_pnl)
            results["total_pnl"].append(daily_result.total_pnl)
            results["net_pnl"].append(daily_result.net_pnl)
            results["balance"].append(daily_result.balance)
            results["return"].append(daily_result.return_pct)

        if results["date"]:
            self.daily_df = pl.DataFrame(results)
            logger.info(f"回测结果计算完成：{len(self.daily_df)} 个交易日")
            return self.daily_df

        return None

    def calculate_statistics(self) -> dict:
        """计算统计指标"""
        logger.info("开始计算统计指标")

        # 如果还没计算结果，先计算
        if self.daily_df is None:
            self.calculate_result()
        
        if self.daily_df is None:
            logger.warning("每日结果为空，无法计算统计指标")
            return {}

        df = self.daily_df

        # 基础统计
        total_days = len(df)
        profit_days = df.filter(pl.col("net_pnl") > 0).height
        loss_days = df.filter(pl.col("net_pnl") < 0).height

        # 收益统计
        total_return = (df["balance"][-1] / self.capital - 1) * 100
        annual_return = total_return / total_days * self.annual_days

        # 风险统计
        daily_returns = df["return"].to_list()
        daily_return_mean = np.mean(daily_returns)
        daily_return_std = np.std(daily_returns)

        sharpe_ratio = 0
        if daily_return_std > 0:
            daily_risk_free = self.risk_free / np.sqrt(self.annual_days)
            sharpe_ratio = (daily_return_mean - daily_risk_free) / daily_return_std * np.sqrt(self.annual_days)

        # 回撤统计
        df_with_dd = df.with_columns(
            highwater=pl.col("balance").cum_max()
        ).with_columns(
            drawdown=(pl.col("balance") / pl.col("highwater") - 1) * 100
        )

        max_drawdown = df_with_dd["drawdown"].min()

        # 交易统计
        total_trade_count = df["trade_count"].sum()
        total_turnover = df["turnover"].sum()
        total_commission = df["commission"].sum()

        # 输出结果
        stats = {
            "总交易日": total_days,
            "盈利交易日": profit_days,
            "亏损交易日": loss_days,
            "胜率": f"{profit_days / total_days * 100:.2f}%" if total_days > 0 else "0%",
            "初始资金": f"{self.capital:,.0f}",
            "结束资金": f"{df['balance'][-1]:,.0f}",
            "总收益率": f"{total_return:.2f}%",
            "年化收益": f"{annual_return:.2f}%",
            "最大回撤": f"{max_drawdown:.2f}%",
            "夏普比率": f"{sharpe_ratio:.2f}",
            "总交易次数": int(total_trade_count),
            "总成交额": f"{total_turnover:,.0f}",
            "总手续费": f"{total_commission:,.0f}",
        }

        logger.info("=" * 60)
        logger.info("回测统计结果")
        logger.info("=" * 60)
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        logger.info("=" * 60)

        return stats

    def show_chart(self) -> None:
        """显示回测图表"""
        if self.daily_df is None:
            logger.warning("每日结果为空，无法显示图表")
            return

        df = self.daily_df

        # 创建子图
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.5, 0.25, 0.25],
            subplot_titles=("资金曲线", "每日盈亏", "回撤")
        )

        # 资金曲线
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["balance"],
                name="Balance",
                line=dict(color="blue", width=2)
            ),
            row=1, col=1
        )

        # 每日盈亏
        colors = ["red" if v > 0 else "green" for v in df["net_pnl"]]
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["net_pnl"],
                name="Daily PnL",
                marker_color=colors
            ),
            row=2, col=1
        )

        # 回撤
        df_with_dd = df.with_columns(
            highwater=pl.col("balance").cum_max()
        ).with_columns(
            drawdown=(pl.col("balance") / pl.col("highwater") - 1) * 100
        )

        fig.add_trace(
            go.Scatter(
                x=df_with_dd["date"],
                y=df_with_dd["drawdown"],
                name="Drawdown",
                line=dict(color="orange", width=2),
                fill="tozeroy"
            ),
            row=3, col=1
        )

        # 更新布局
        fig.update_layout(
            height=800,
            showlegend=False,
            title_text="截面回测结果",
            hovermode="x unified"
        )

        fig.show()


class CrossSectionalDailyResult:
    """截面回测每日结果"""

    def __init__(self, dt: datetime) -> None:
        """构造函数"""
        self.dt = dt
        self.date = dt.date()

        self.trade_count: int = 0
        self.turnover: float = 0.0
        self.commission: float = 0.0
        self.trading_pnl: float = 0.0
        self.holding_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.net_pnl: float = 0.0

        self.balance: float = 0.0
        self.return_pct: float = 0.0

        self.positions: dict[str, float] = {}
        self.close_prices: dict[str, float] = {}

    def calculate_daily_result(
        self,
        positions: dict[str, float],
        cash: float,
        bars: dict[str, BarData],
        pre_closes: dict[str, float]
    ) -> None:
        """计算每日结果"""
        self.positions = positions.copy()
        self.balance = cash

        # 计算持仓市值
        holding_value = 0
        for vt_symbol, volume in positions.items():
            if volume > 0 and vt_symbol in bars:
                bar = bars[vt_symbol]
                price = bar.close_price
                self.close_prices[vt_symbol] = price
                holding_value += price * volume

                # 计算持仓盈亏
                if vt_symbol in pre_closes:
                    pre_close = pre_closes[vt_symbol]
                    self.holding_pnl += (price - pre_close) * volume

        self.balance += holding_value

        # 计算收益率
        # 需要在外部传入初始资金

    def add_trade(self, trade: TradeData) -> None:
        """添加成交记录"""
        self.trade_count += 1
        self.turnover += trade.price * trade.volume
        # 手续费计算需要根据费率


# 便捷函数
def create_cross_sectional_engine(lab: AlphaLab) -> CrossSectionalBacktestingEngine:
    """创建截面回测引擎"""
    return CrossSectionalBacktestingEngine(lab)
