"""
动量策略回测 - 加入交易成本

交易成本包括：
1. 手续费：券商佣金 + 印花税 + 过户费
2. 滑点：买卖价差 + 市场冲击

A 股收费标准：
- 券商佣金：万分之 2.5（双向，最低 5 元）
- 印花税：千分之 1（仅卖出）
- 过户费：万分之 0.1（双向）
- 滑点：0.1% - 0.3%（取决于流动性）
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


@dataclass
class TradingCostConfig:
    """交易成本配置"""
    # 手续费
    commission_rate: float = 0.00025  # 万分之 2.5
    commission_min: float = 5.0  # 最低 5 元
    stamp_tax: float = 0.001  # 千分之 1（卖出）
    transfer_fee: float = 0.00001  # 万分之 0.1
    
    # 滑点
    slippage_rate: float = 0.001  # 0.1%
    
    # 市场冲击（大单额外成本）
    market_impact_rate: float = 0.0005  # 0.05%


class TradingCostCalculator:
    """交易成本计算器"""
    
    def __init__(self, config: TradingCostConfig = None):
        self.config = config or TradingCostConfig()
        self.total_commission = 0.0  # 累计手续费
        self.total_slippage = 0.0  # 累计滑点
        self.total_tax = 0.0  # 累计印花税
        self.trade_count = 0  # 交易次数
    
    def calculate_cost(self, 
                       vt_symbol: str,
                       direction: Direction,
                       volume: float,
                       price: float,
                       daily_volume: float = None) -> Tuple[float, float, float]:
        """
        计算交易成本
        
        Args:
            vt_symbol: 股票代码
            direction: 买卖方向
            volume: 成交量
            price: 成交价格
            daily_volume: 当日成交量（用于计算市场冲击）
        
        Returns:
            (总成本，手续费，滑点)
        """
        # 成交金额
        turnover = volume * price
        
        # 1. 券商佣金（双向）
        commission = turnover * self.config.commission_rate
        commission = max(commission, self.config.commission_min)
        
        # 2. 印花税（仅卖出）
        tax = 0.0
        if direction == Direction.SHORT:
            tax = turnover * self.config.stamp_tax
        
        # 3. 过户费（双向）
        transfer_fee = turnover * self.config.transfer_fee
        
        # 总手续费
        total_fee = commission + tax + transfer_fee
        
        # 4. 滑点
        slippage = turnover * self.config.slippage_rate
        
        # 5. 市场冲击（简化：假设超过日均成交 1% 才有冲击）
        market_impact = 0.0
        if daily_volume and volume > daily_volume * 0.01:
            impact_ratio = volume / daily_volume
            market_impact = turnover * self.config.market_impact_rate * impact_ratio
        
        total_slippage = slippage + market_impact
        
        # 更新累计值
        self.total_commission += commission
        self.total_tax += tax
        self.total_slippage += total_slippage
        self.trade_count += 1
        
        return total_fee + total_slippage, total_fee, total_slippage
    
    def get_summary(self) -> dict:
        """获取成本汇总"""
        return {
            "total_commission": self.total_commission,
            "total_tax": self.total_tax,
            "total_slippage": self.total_slippage,
            "total_cost": self.total_commission + self.total_tax + self.total_slippage,
            "trade_count": self.trade_count
        }
    
    def reset(self):
        """重置累计值"""
        self.total_commission = 0.0
        self.total_tax = 0.0
        self.total_slippage = 0.0
        self.trade_count = 0


class MomentumStrategyWithCost:
    """带交易成本的动量策略"""
    
    def __init__(self, setting: dict = None):
        self.setting = setting or {}
        self.lookback = self.setting.get("lookback", 10)
        self.top_k = self.setting.get("top_k", 9)
        self.rebalance_days = self.setting.get("rebalance_days", 5)
        
        self.last_rebalance: Optional[datetime] = None
        self.holdings: List[str] = []
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def should_rebalance(self, current_date: datetime) -> bool:
        if self.last_rebalance is None:
            return True
        days = (current_date - self.last_rebalance).days
        return days >= self.rebalance_days
    
    def update_price_history(self, bars: Dict[str, BarData]):
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            self.price_history[vt_symbol].append((bar.datetime, bar.close_price))
            if len(self.price_history[vt_symbol]) > 60:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-60:]
    
    def calculate_momentum(self, vt_symbol: str) -> float:
        if vt_symbol not in self.price_history:
            return 0.0
        history = self.price_history[vt_symbol]
        if len(history) < self.lookback:
            return 0.0
        
        old_price = history[-self.lookback][1]
        current_price = history[-1][1]
        
        if old_price > 0:
            return (current_price - old_price) / old_price * 100
        return 0.0
    
    def select_stocks(self, bars: Dict[str, BarData]) -> List[str]:
        candidates = []
        
        for vt_symbol in bars.keys():
            if "ST" in vt_symbol:
                continue
            
            momentum = self.calculate_momentum(vt_symbol)
            
            if vt_symbol in self.price_history:
                history_len = len(self.price_history[vt_symbol])
                if history_len >= self.lookback:
                    candidates.append((vt_symbol, momentum))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = [c[0] for c in candidates[:self.top_k]]
        
        return selected
    
    def on_bars(self, bars: Dict[str, BarData], current_date: datetime) -> List[str]:
        self.update_price_history(bars)
        
        if not self.should_rebalance(current_date):
            return self.holdings
        
        selected = self.select_stocks(bars)
        
        self.holdings = selected
        self.last_rebalance = current_date
        
        return selected


class BacktestEngineWithCost:
    """带交易成本的回测引擎"""
    
    def __init__(self, 
                 capital: float = 1_000_000,
                 cost_config: TradingCostConfig = None):
        self.capital = capital
        self.cash = capital
        self.initial_cash = capital
        self.positions: Dict[str, float] = {}
        self.daily_values = []
        self.datetime: Optional[datetime] = None
        self.trades = []
        self.daily_returns = []
        
        # 交易成本
        self.cost_calculator = TradingCostCalculator(cost_config)
        self.cost_config = cost_config or TradingCostConfig()
        
        # 统计
        self.total_turnover = 0.0  # 累计成交金额
    
    def get_pos(self, vt_symbol: str) -> float:
        return self.positions.get(vt_symbol, 0.0)
    
    def get_portfolio_value(self, bars: Dict[str, BarData]) -> float:
        global history_data
        stock_value = 0.0
        for vt_symbol, volume in self.positions.items():
            if volume > 0 and self.datetime:
                key = (self.datetime, vt_symbol)
                if key in history_data:
                    stock_value += history_data[key].close_price * volume
        return self.cash + stock_value
    
    def execute_trade(self,
                      vt_symbol: str,
                      direction: Direction,
                      volume: float,
                      bars: Dict[str, BarData]) -> bool:
        """执行交易（扣除成本）"""
        if vt_symbol not in bars:
            return False
        
        bar = bars[vt_symbol]
        
        # 计算成本
        cost, fee, slippage = self.cost_calculator.calculate_cost(
            vt_symbol=vt_symbol,
            direction=direction,
            volume=volume,
            price=bar.close_price
        )
        
        if direction == Direction.LONG:
            # 买入：需要现金 + 成本
            total_cost = volume * bar.close_price + cost
            
            if total_cost <= self.cash:
                self.cash -= total_cost
                self.positions[vt_symbol] = self.positions.get(vt_symbol, 0.0) + volume
                
                self.trades.append({
                    "datetime": self.datetime,
                    "vt_symbol": vt_symbol,
                    "direction": "买入",
                    "volume": volume,
                    "price": bar.close_price,
                    "cost": cost,
                    "fee": fee,
                    "slippage": slippage
                })
                
                self.total_turnover += volume * bar.close_price
                return True
        
        elif direction == Direction.SHORT:
            # 卖出：收入 - 成本
            if vt_symbol in self.positions:
                sell_volume = min(volume, self.positions[vt_symbol])
                
                if sell_volume > 0:
                    revenue = sell_volume * bar.close_price - cost
                    self.cash += revenue
                    self.positions[vt_symbol] -= sell_volume
                    
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "卖出",
                        "volume": sell_volume,
                        "price": bar.close_price,
                        "cost": cost,
                        "fee": fee,
                        "slippage": slippage
                    })
                    
                    self.total_turnover += sell_volume * bar.close_price
                    return True
        
        return False
    
    def rebalance_to(self, target_holdings: List[str], bars: Dict[str, BarData]):
        """调仓到目标持仓"""
        if not target_holdings:
            return
        
        portfolio_value = self.get_portfolio_value(bars)
        target_per_stock = portfolio_value / len(target_holdings)
        
        # 先卖出不在目标持仓中的股票
        for vt_symbol in list(self.positions.keys()):
            if vt_symbol not in target_holdings:
                volume = self.positions[vt_symbol]
                if volume > 0:
                    self.execute_trade(vt_symbol, Direction.SHORT, volume, bars)
        
        # 再买入目标持仓
        for vt_symbol in target_holdings:
            if vt_symbol not in bars:
                continue
            
            bar = bars[vt_symbol]
            target_volume = target_per_stock / bar.close_price
            current_pos = self.get_pos(vt_symbol)
            
            if target_volume > current_pos * 1.05:
                volume = target_volume - current_pos
                self.execute_trade(vt_symbol, Direction.LONG, volume, bars)
    
    def record_daily_value(self, bars: Dict[str, BarData]):
        """记录每日净值"""
        if not self.datetime:
            return
        
        stock_value = sum(
            bars[vt_symbol].close_price * volume
            for vt_symbol, volume in self.positions.items()
            if vt_symbol in bars and volume > 0
        )
        
        total_value = self.cash + stock_value
        
        self.daily_values.append({
            "datetime": self.datetime,
            "total_value": total_value,
            "cash": self.cash,
            "stock_value": stock_value
        })
        
        # 计算日收益率
        if len(self.daily_values) > 1:
            prev_value = self.daily_values[-2]["total_value"]
            daily_return = (total_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
    
    def get_cost_summary(self) -> dict:
        """获取交易成本汇总"""
        summary = self.cost_calculator.get_summary()
        summary["total_turnover"] = self.total_turnover
        summary["cost_ratio"] = summary["total_cost"] / self.total_turnover * 100 if self.total_turnover > 0 else 0
        summary["initial_cash"] = self.initial_cash
        return summary


def load_data(data_path: Path):
    """加载数据"""
    print("\n📊 加载数据...")
    daily_path = data_path / "daily"
    
    vt_symbols = []
    history = {}
    dts = set()
    
    for file_path in daily_path.glob("*.parquet"):
        df = pl.read_parquet(file_path)
        vt_symbol = df["vt_symbol"][0]
        vt_symbols.append(vt_symbol)
        
        for row in df.iter_rows(named=True):
            dt = row["datetime"]
            dts.add(dt)
            exchange = Exchange.SSE if "SSE" in vt_symbol else Exchange.SZSE
            
            bar = BarData(
                symbol=vt_symbol.split(".")[0],
                exchange=exchange,
                datetime=dt,
                interval=Interval.DAILY,
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=0,
                gateway_name="MOCK"
            )
            
            history[(dt, vt_symbol)] = bar
    
    print(f"  股票数量：{len(vt_symbols)}")
    print(f"  交易日数：{len(dts)}")
    
    return vt_symbols, history, dts


history_data = {}


def calculate_statistics(daily_values: List[dict], daily_returns: List[float]) -> dict:
    """计算统计指标"""
    if not daily_values:
        return {}
    
    import math
    
    initial = daily_values[0]["total_value"]
    final = daily_values[-1]["total_value"]
    total_return = (final - initial) / initial * 100
    
    # 最大回撤
    max_dd = 0.0
    peak = initial
    for daily in daily_values:
        value = daily["total_value"]
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    # 年化收益
    n_days = len(daily_values)
    years = n_days / 240
    annual_return = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # 波动率
    if len(daily_returns) > 1:
        daily_vol = np.std(daily_returns)
        annual_vol = daily_vol * math.sqrt(240) * 100
    else:
        annual_vol = 0
    
    # 夏普比率
    if annual_vol > 0:
        sharpe = (annual_return - 3.0) / (annual_vol / 100)
    else:
        sharpe = 0
    
    # 胜率
    if daily_returns:
        win_days = sum(1 for r in daily_returns if r > 0)
        win_rate = win_days / len(daily_returns) * 100
    else:
        win_rate = 0
    
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_dd,
        "annual_volatility": annual_vol,
        "sharpe_ratio": sharpe,
        "win_rate": win_rate,
        "initial": initial,
        "final": final,
        "n_days": n_days
    }


def run_backtest(setting: dict = None, 
                 cost_config: TradingCostConfig = None,
                 show_cost_detail: bool = True):
    """运行回测"""
    print("=" * 60)
    print("动量策略回测 - 含交易成本")
    print("=" * 60)
    
    # 加载数据
    data_path = Path("./data_real")
    vt_symbols, history_data_g, dts = load_data(data_path)
    
    global history_data
    history_data = history_data_g
    
    # 策略参数
    setting = setting or {
        "lookback": 10,
        "top_k": 9,
        "rebalance_days": 5
    }
    
    # 成本配置
    cost_config = cost_config or TradingCostConfig(
        commission_rate=0.00025,  # 万分之 2.5
        commission_min=5.0,
        stamp_tax=0.001,  # 千分之 1
        transfer_fee=0.00001,  # 万分之 0.1
        slippage_rate=0.001  # 0.1%
    )
    
    print("\n📊 策略参数:")
    print(f"  回看天数：{setting['lookback']}天")
    print(f"  选股数量：{setting['top_k']}只")
    print(f"  调仓周期：{setting['rebalance_days']}天")
    
    print("\n💰 交易成本配置:")
    print(f"  券商佣金：{cost_config.commission_rate*10000:.1f}‱ (最低{cost_config.commission_min}元)")
    print(f"  印花税：{cost_config.stamp_tax*1000:.1f}‰ (卖出)")
    print(f"  过户费：{cost_config.transfer_fee*10000:.1f}‱")
    print(f"  滑点：{cost_config.slippage_rate*1000:.1f}‰")
    
    # 创建策略
    strategy = MomentumStrategyWithCost(setting=setting)
    
    # 创建引擎
    engine = BacktestEngineWithCost(capital=1_000_000, cost_config=cost_config)
    
    # 运行回测
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 100 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if bars:
            target_holdings = strategy.on_bars(bars, dt)
            engine.rebalance_to(target_holdings, bars)
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 计算统计
    stats = calculate_statistics(engine.daily_values, engine.daily_returns)
    cost_summary = engine.get_cost_summary()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if stats:
        print(f"\n📈 收益指标:")
        print(f"  初始资金：{stats['initial']:,.0f}")
        print(f"  最终价值：{stats['final']:,.0f}")
        print(f"  总收益率：{stats['total_return']:.2f}%")
        print(f"  年化收益率：{stats['annual_return']:.2f}%")
        print(f"  年化波动率：{stats['annual_volatility']:.2f}%")
        print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")
        print(f"  最大回撤：{stats['max_drawdown']:.2f}%")
        print(f"  胜率：{stats['win_rate']:.1f}%")
        
        print(f"\n💰 交易成本:")
        print(f"  成交金额：{cost_summary['total_turnover']:,.0f}")
        print(f"  手续费：{cost_summary['total_commission']:,.0f}")
        print(f"  印花税：{cost_summary['total_tax']:,.0f}")
        print(f"  滑点成本：{cost_summary['total_slippage']:,.0f}")
        print(f"  总成本：{cost_summary['total_cost']:,.0f}")
        print(f"  成本占比：{cost_summary['cost_ratio']:.2f}%")
        print(f"  交易次数：{cost_summary['trade_count']}")
        
        final_holdings = [k for k, v in engine.positions.items() if v > 0]
        print(f"\n📊 最终持仓：{len(final_holdings)}只")
        if final_holdings:
            print(f"  持仓：{', '.join(final_holdings)}")
    
    print("=" * 60)
    
    return engine, stats, cost_summary


def compare_with_without_cost():
    """对比含/不含交易成本的结果"""
    print("=" * 60)
    print("交易成本影响对比")
    print("=" * 60)
    
    setting = {"lookback": 10, "top_k": 9, "rebalance_days": 5}
    
    # 不含成本
    print("\n📊 回测 1：不含交易成本")
    print("-" * 60)
    cost_free_config = TradingCostConfig(
        commission_rate=0,
        commission_min=0,
        stamp_tax=0,
        transfer_fee=0,
        slippage_rate=0
    )
    _, stats_no_cost, _ = run_backtest(setting, cost_free_config, show_cost_detail=False)
    
    # 含成本
    print("\n\n📊 回测 2：含交易成本")
    print("-" * 60)
    _, stats_with_cost, cost_summary = run_backtest(setting, show_cost_detail=True)
    
    # 对比
    print("\n" + "=" * 60)
    print("成本影响分析")
    print("=" * 60)
    
    if stats_no_cost and stats_with_cost:
        return_diff = stats_no_cost["annual_return"] - stats_with_cost["annual_return"]
        sharpe_diff = stats_no_cost["sharpe_ratio"] - stats_with_cost["sharpe_ratio"]
        
        print(f"\n{'指标':<20} {'无成本':>12} {'含成本':>12} {'差异':>10}")
        print("-" * 60)
        print(f"{'年化收益':<20} {stats_no_cost['annual_return']:>11.2f}% {stats_with_cost['annual_return']:>11.2f}% {return_diff:>9.2f}%")
        print(f"{'夏普比率':<20} {stats_no_cost['sharpe_ratio']:>12.2f} {stats_with_cost['sharpe_ratio']:>12.2f} {sharpe_diff:>10.2f}")
        print(f"{'最大回撤':<20} {stats_no_cost['max_drawdown']:>11.2f}% {stats_with_cost['max_drawdown']:>11.2f}%")
        
        print(f"\n💰 交易成本总计：{cost_summary['total_cost']:,.0f}元")
        print(f"   占成交金额：{cost_summary['cost_ratio']:.2f}%")
        print(f"   占初始资金：{cost_summary['total_cost']/cost_summary['initial_cash']*100:.2f}%")
    
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        # 对比含/不含成本
        compare_with_without_cost()
    else:
        # 默认回测（含成本）
        engine, stats, cost_summary = run_backtest()
