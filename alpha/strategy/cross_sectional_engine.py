"""
截面回测引擎

支持多股票同时回测，模拟真实选股策略的执行过程：
- 定期调仓
- 仓位管理
- 交易成本
- 绩效统计
"""

from typing import List, Dict, Optional, Any, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from pathlib import Path

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.stock_screener_strategy import StockScreenerStrategy

# 可选导入 Interval
try:
    from vnpy.trader.constant import Interval
except ImportError:
    Interval = Any


@dataclass
class Position:
    """持仓信息"""
    vt_symbol: str
    size: float
    price: float
    entry_date: datetime
    
    def market_value(self, current_price: float) -> float:
        """计算市值"""
        return self.size * current_price
    
    def pnl(self, current_price: float) -> float:
        """计算盈亏"""
        return (current_price - self.price) * self.size
    
    def pnl_pct(self, current_price: float) -> float:
        """计算盈亏比例"""
        return (current_price - self.price) / self.price if self.price > 0 else 0


@dataclass
class Trade:
    """交易记录"""
    vt_symbol: str
    direction: str  # "buy" or "sell"
    size: float
    price: float
    date: datetime
    commission: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "vt_symbol": self.vt_symbol,
            "direction": self.direction,
            "size": self.size,
            "price": self.price,
            "date": self.date.isoformat(),
            "commission": self.commission
        }


@dataclass
class DailySnapshot:
    """每日快照"""
    date: datetime
    total_value: float
    cash: float
    position_count: int
    positions: Dict[str, Dict]
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "total_value": self.total_value,
            "cash": self.cash,
            "position_count": self.position_count,
            "positions": self.positions
        }


class CrossSectionalEngine:
    """
    截面回测引擎
    
    模拟选股策略的实际执行过程
    """
    
    def __init__(
        self,
        lab: AlphaLab,
        initial_capital: float = 1_000_000,
        commission_rate: float = 0.0003,  # 万三
        slippage: float = 0.001,  # 千一滑点
        max_positions: int = 30,
        position_size: float = 0.03  # 单只股票 3% 仓位
    ):
        """
        初始化回测引擎
        
        Args:
            lab: AlphaLab 实例
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage: 滑点
            max_positions: 最大持仓数
            position_size: 单只股票仓位比例
        """
        self.lab = lab
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.max_positions = max_positions
        self.position_size = position_size
        
        # 状态
        self._cash = initial_capital
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []
        self._daily_snapshots: List[DailySnapshot] = []
        self._strategy: Optional[StockScreenerStrategy] = None
        
        # 回测参数
        self._vt_symbols: List[str] = []
        self._interval: Interval = Interval.DAILY
        self._start: datetime = None
        self._end: datetime = None
        self._current_date: datetime = None
        self._bars_dict: Dict[str, List] = {}
    
    def set_parameters(
        self,
        vt_symbols: List[str],
        interval: Interval,
        start: datetime,
        end: datetime,
        capital: Optional[float] = None
    ) -> None:
        """
        设置回测参数
        
        Args:
            vt_symbols: 股票代码列表
            interval: K 线周期
            start: 开始日期
            end: 结束日期
            capital: 初始资金（可选）
        """
        self._vt_symbols = vt_symbols
        self._interval = interval
        self._start = start
        self._end = end
        
        if capital is not None:
            self.initial_capital = capital
            self._cash = capital
    
    def add_strategy(
        self,
        strategy_class: Type[StockScreenerStrategy],
        setting: Optional[Dict] = None
    ) -> None:
        """
        添加策略
        
        Args:
            strategy_class: 策略类
            setting: 策略参数
        """
        if setting is None:
            setting = {}
        
        self._strategy = strategy_class(**setting)
        
        # 同步策略的持仓限制
        self.max_positions = self._strategy.max_positions
        self.position_size = self._strategy.position_size
    
    def load_data(self) -> None:
        """加载数据"""
        if not self._vt_symbols:
            raise ValueError("请先设置 vt_symbols")
        
        self._bars_dict = {}
        
        for vt_symbol in self._vt_symbols:
            bars = self.lab.get_bars(
                vt_symbol=vt_symbol,
                interval=self._interval,
                start=self._start,
                end=self._end
            )
            if bars:
                self._bars_dict[vt_symbol] = bars
    
    def _get_price(self, vt_symbol: str, date: datetime) -> Optional[float]:
        """
        获取指定日期的收盘价
        
        Args:
            vt_symbol: 股票代码
            date: 日期
            
        Returns:
            Optional[float]: 收盘价
        """
        if vt_symbol not in self._bars_dict:
            return None
        
        bars = self._bars_dict[vt_symbol]
        for bar in bars:
            if bar.datetime.date() == date.date():
                return bar.close_price
        
        return None
    
    def _calculate_commission(self, amount: float) -> float:
        """
        计算手续费
        
        Args:
            amount: 交易金额
            
        Returns:
            float: 手续费
        """
        return max(amount * self.commission_rate, 5.0)  # 最低 5 元
    
    def _execute_buy(
        self,
        vt_symbol: str,
        target_size: float,
        date: datetime
    ) -> Optional[Trade]:
        """
        执行买入
        
        Args:
            vt_symbol: 股票代码
            target_size: 目标股数
            date: 交易日期
            
        Returns:
            Optional[Trade]: 交易记录
        """
        price = self._get_price(vt_symbol, date)
        if price is None:
            return None
        
        # 加上滑点
        exec_price = price * (1 + self.slippage)
        amount = target_size * exec_price
        
        # 检查资金是否足够
        commission = self._calculate_commission(amount)
        total_cost = amount + commission
        
        if total_cost > self._cash:
            # 资金不足，减少买入数量
            target_size = (self._cash - commission) / exec_price
            if target_size <= 0:
                return None
            amount = target_size * exec_price
            total_cost = amount + commission
        
        # 执行买入
        self._cash -= total_cost
        
        trade = Trade(
            vt_symbol=vt_symbol,
            direction="buy",
            size=target_size,
            price=exec_price,
            date=date,
            commission=commission
        )
        self._trades.append(trade)
        
        # 更新持仓
        self._positions[vt_symbol] = Position(
            vt_symbol=vt_symbol,
            size=target_size,
            price=exec_price,
            entry_date=date
        )
        
        return trade
    
    def _execute_sell(
        self,
        vt_symbol: str,
        date: datetime
    ) -> Optional[Trade]:
        """
        执行卖出
        
        Args:
            vt_symbol: 股票代码
            date: 交易日期
            
        Returns:
            Optional[Trade]: 交易记录
        """
        if vt_symbol not in self._positions:
            return None
        
        position = self._positions[vt_symbol]
        price = self._get_price(vt_symbol, date)
        if price is None:
            return None
        
        # 减去滑点
        exec_price = price * (1 - self.slippage)
        amount = position.size * exec_price
        commission = self._calculate_commission(amount)
        
        # 执行卖出
        self._cash += amount - commission
        
        trade = Trade(
            vt_symbol=vt_symbol,
            direction="sell",
            size=position.size,
            price=exec_price,
            date=date,
            commission=commission
        )
        self._trades.append(trade)
        
        # 清除持仓
        del self._positions[vt_symbol]
        
        return trade
    
    def _rebalance(self, date: datetime, fundamental_data: Dict[str, Any]) -> None:
        """
        执行调仓
        
        Args:
            date: 交易日期
            fundamental_data: 财务数据
        """
        if self._strategy is None:
            return
        
        # 获取目标持仓
        target_stocks = self._strategy.screen_stocks(
            stock_pool=self._vt_symbols,
            fundamental_data=fundamental_data,
            current_date=date
        )
        
        # 限制持仓数量
        target_stocks = target_stocks[:self.max_positions]
        
        # 计算每只股票的目标仓位
        target_position_size = self.position_size
        
        # 卖出不在目标列表中的股票
        current_holdings = list(self._positions.keys())
        for vt_symbol in current_holdings:
            if vt_symbol not in target_stocks:
                self._execute_sell(vt_symbol, date)
        
        # 买入新股票
        for vt_symbol in target_stocks:
            if vt_symbol not in self._positions:
                # 计算买入金额
                target_amount = self.initial_capital * target_position_size
                price = self._get_price(vt_symbol, date)
                
                if price and price > 0:
                    target_size = target_amount / price
                    self._execute_buy(vt_symbol, target_size, date)
    
    def _update_snapshot(self, date: datetime) -> None:
        """
        更新每日快照
        
        Args:
            date: 交易日期
        """
        # 计算持仓市值
        position_values = {}
        total_position_value = 0
        
        for vt_symbol, position in self._positions.items():
            current_price = self._get_price(vt_symbol, date)
            if current_price:
                value = position.market_value(current_price)
                position_values[vt_symbol] = {
                    "size": position.size,
                    "price": position.price,
                    "current_price": current_price,
                    "value": value,
                    "pnl_pct": position.pnl_pct(current_price)
                }
                total_position_value += value
        
        total_value = self._cash + total_position_value
        
        snapshot = DailySnapshot(
            date=date,
            total_value=total_value,
            cash=self._cash,
            position_count=len(self._positions),
            positions=position_values
        )
        
        self._daily_snapshots.append(snapshot)
    
    def run_backtesting(self) -> None:
        """运行回测"""
        if self._strategy is None:
            raise ValueError("请先添加策略")
        
        if not self._bars_dict:
            raise ValueError("请先加载数据")
        
        # 获取所有交易日期
        all_dates = set()
        for vt_symbol, bars in self._bars_dict.items():
            for bar in bars:
                all_dates.add(bar.datetime)
        
        all_dates = sorted(list(all_dates))
        
        # 初始化策略
        self._strategy.clear() if hasattr(self._strategy, 'clear') else None
        
        # 逐日回测
        for i, date in enumerate(all_dates):
            self._current_date = date
            
            # 获取财务数据（使用最新可用数据）
            fundamental_data = self._get_fundamental_data(date)
            
            # 判断是否需要调仓
            if self._strategy.should_rebalance(date):
                self._rebalance(date, fundamental_data)
            
            # 更新快照
            self._update_snapshot(date)
            
            # 更新策略天数
            self._strategy.increment_days(1)
    
    def _get_fundamental_data(self, date: datetime) -> Dict[str, Any]:
        """
        获取指定日期的财务数据
        
        Args:
            date: 日期
            
        Returns:
            Dict[str, Any]: 财务数据字典
        """
        # 从 lab 获取财务数据
        # 这里简化处理，实际应该根据报告期获取
        fundamental_data = {}
        
        for vt_symbol in self._vt_symbols:
            indicator = self.lab.get_fundamental(vt_symbol, date)
            if indicator:
                fundamental_data[vt_symbol] = indicator
        
        return fundamental_data
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        计算统计指标
        
        Returns:
            Dict[str, Any]: 统计结果
        """
        if not self._daily_snapshots:
            return {}
        
        # 提取每日净值
        dates = []
        values = []
        
        for snapshot in self._daily_snapshots:
            dates.append(snapshot.date)
            values.append(snapshot.total_value)
        
        # 计算收益
        total_return = (values[-1] - values[0]) / values[0]
        
        # 计算年化收益
        days = (dates[-1] - dates[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # 计算波动率
        import statistics
        
        daily_returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)
        
        volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
        annual_volatility = volatility * (252 ** 0.5)
        
        # 计算最大回撤
        max_drawdown = 0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算夏普比率
        risk_free_rate = 0.03  # 假设无风险利率 3%
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # 计算交易统计
        total_trades = len(self._trades)
        buy_trades = [t for t in self._trades if t.direction == "buy"]
        sell_trades = [t for t in self._trades if t.direction == "sell"]
        total_commission = sum(t.commission for t in self._trades)
        
        return {
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "annual_return": annual_return,
            "annual_return_pct": annual_return * 100,
            "volatility": annual_volatility,
            "volatility_pct": annual_volatility * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown * 100,
            "total_trades": total_trades,
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_commission": total_commission,
            "final_value": values[-1],
            "initial_value": values[0],
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "trading_days": len(dates)
        }
    
    def get_trades(self) -> List[Dict]:
        """
        获取交易记录
        
        Returns:
            List[Dict]: 交易记录列表
        """
        return [trade.to_dict() for trade in self._trades]
    
    def get_daily_values(self) -> List[Dict]:
        """
        获取每日净值
        
        Returns:
            List[Dict]: 每日快照列表
        """
        return [snapshot.to_dict() for snapshot in self._daily_snapshots]
    
    def show_chart(self) -> None:
        """显示回测图表"""
        try:
            import matplotlib.pyplot as plt
            
            if not self._daily_snapshots:
                print("没有回测数据")
                return
            
            # 提取数据
            dates = [s.date for s in self._daily_snapshots]
            values = [s.total_value for s in self._daily_snapshots]
            
            # 创建图表
            fig, axes = plt.subplots(2, 1, figsize=(14, 10))
            
            # 净值曲线
            axes[0].plot(dates, values, linewidth=1.5)
            axes[0].set_title('Portfolio Value')
            axes[0].set_xlabel('Date')
            axes[0].set_ylabel('Value')
            axes[0].grid(True, alpha=0.3)
            
            # 添加初始资金线
            axes[0].axhline(y=self.initial_capital, color='gray', linestyle='--', 
                          label='Initial Capital', alpha=0.5)
            axes[0].legend()
            
            # 收益分布
            if len(self._daily_snapshots) > 1:
                daily_returns = []
                for i in range(1, len(values)):
                    ret = (values[i] - values[i-1]) / values[i-1]
                    daily_returns.append(ret)
                
                axes[1].hist(daily_returns, bins=50, edgecolor='black', alpha=0.7)
                axes[1].set_title('Daily Returns Distribution')
                axes[1].set_xlabel('Return')
                axes[1].set_ylabel('Frequency')
                axes[1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            print("请安装 matplotlib: pip install matplotlib")


def create_cross_sectional_engine(
    lab: AlphaLab,
    **kwargs
) -> CrossSectionalEngine:
    """
    创建截面回测引擎
    
    Args:
        lab: AlphaLab 实例
        **kwargs: 其他参数
        
    Returns:
        CrossSectionalEngine: 回测引擎实例
    """
    return CrossSectionalEngine(lab, **kwargs)
