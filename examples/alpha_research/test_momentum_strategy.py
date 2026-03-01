"""
纯动量策略

策略逻辑：
1. 计算所有股票过去 N 日收益率
2. 选择收益率最高的前 K 只股票
3. 等权重配置
4. 定期调仓（5 天/10 天/20 天）

核心参数：
- lookback: 回看天数（默认 20）
- top_k: 选股数量（默认 9）
- rebalance_days: 调仓周期（默认 5）
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random

import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


class MomentumStrategy:
    """
    纯动量策略
    
    参数:
        lookback: 回看天数（默认 20）
        top_k: 选股数量（默认 9）
        rebalance_days: 调仓周期（默认 5）
        exclude_st: 是否排除 ST 股票（默认 True）
    """
    
    def __init__(self, setting: dict = None):
        self.setting = setting or {}
        self.lookback = self.setting.get("lookback", 20)
        self.top_k = self.setting.get("top_k", 9)
        self.rebalance_days = self.setting.get("rebalance_days", 5)
        self.exclude_st = self.setting.get("exclude_st", True)
        
        self.last_rebalance: Optional[datetime] = None
        self.holdings: List[str] = []
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def should_rebalance(self, current_date: datetime) -> bool:
        """检查是否需要调仓"""
        if self.last_rebalance is None:
            return True
        days = (current_date - self.last_rebalance).days
        return days >= self.rebalance_days
    
    def update_price_history(self, bars: Dict[str, BarData]):
        """更新价格历史"""
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            self.price_history[vt_symbol].append((bar.datetime, bar.close_price))
            
            # 保留足够长的历史数据
            max_history = max(self.lookback * 2, 60)
            if len(self.price_history[vt_symbol]) > max_history:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-max_history:]
    
    def calculate_momentum(self, vt_symbol: str) -> float:
        """
        计算动量（过去 N 日收益率）
        
        Returns:
            收益率百分比
        """
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
    
    def is_st_stock(self, vt_symbol: str) -> bool:
        """检查是否是 ST 股票"""
        symbol = vt_symbol.split(".")[0]
        return "ST" in symbol or "*ST" in symbol
    
    def select_stocks(self, bars: Dict[str, BarData]) -> List[str]:
        """
        选股逻辑
        
        1. 计算所有股票动量
        2. 排除 ST 股票（可选）
        3. 按动量排序
        4. 选择前 N 只
        """
        candidates = []
        
        for vt_symbol in bars.keys():
            # 排除 ST 股票
            if self.exclude_st and self.is_st_stock(vt_symbol):
                continue
            
            # 计算动量
            momentum = self.calculate_momentum(vt_symbol)
            
            # 需要足够的历史数据
            if vt_symbol in self.price_history:
                history_len = len(self.price_history[vt_symbol])
                if history_len >= self.lookback:
                    candidates.append((vt_symbol, momentum))
        
        # 按动量排序（从高到低）
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 只
        selected = [c[0] for c in candidates[:self.top_k]]
        
        return selected
    
    def on_bars(self, bars: Dict[str, BarData], current_date: datetime) -> List[str]:
        """
        处理 K 线数据
        
        Returns:
            目标持仓列表
        """
        # 更新价格历史
        self.update_price_history(bars)
        
        # 检查调仓
        if not self.should_rebalance(current_date):
            return self.holdings
        
        # 选股
        selected = self.select_stocks(bars)
        
        self.holdings = selected
        self.last_rebalance = current_date
        
        return selected


class SimpleBacktestEngine:
    """简化回测引擎"""
    
    def __init__(self, capital: float = 1_000_000):
        self.capital = capital
        self.cash = capital
        self.positions: Dict[str, float] = {}
        self.daily_values = []
        self.datetime: Optional[datetime] = None
        self.trades = []
        self.daily_returns = []
    
    def get_pos(self, vt_symbol: str) -> float:
        return self.positions.get(vt_symbol, 0.0)
    
    def get_portfolio_value(self) -> float:
        global history_data
        stock_value = 0.0
        for vt_symbol, volume in self.positions.items():
            if volume > 0 and self.datetime:
                key = (self.datetime, vt_symbol)
                if key in history_data:
                    stock_value += history_data[key].close_price * volume
        return self.cash + stock_value
    
    def rebalance_to(self, target_holdings: List[str], bars: Dict[str, BarData]):
        """调仓到目标持仓"""
        if not target_holdings:
            return
        
        portfolio_value = self.get_portfolio_value()
        target_per_stock = portfolio_value / len(target_holdings)
        
        # 先卖出不在目标持仓中的股票
        for vt_symbol in list(self.positions.keys()):
            if vt_symbol not in target_holdings:
                volume = self.positions[vt_symbol]
                if volume > 0 and vt_symbol in bars:
                    revenue = bars[vt_symbol].close_price * volume
                    self.cash += revenue
                    self.positions[vt_symbol] = 0.0
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "卖出",
                        "volume": volume,
                        "price": bars[vt_symbol].close_price
                    })
        
        # 再买入目标持仓
        for vt_symbol in target_holdings:
            if vt_symbol not in bars:
                continue
            
            bar = bars[vt_symbol]
            target_volume = target_per_stock / bar.close_price
            current_pos = self.get_pos(vt_symbol)
            
            if target_volume > current_pos * 1.05:
                volume = target_volume - current_pos
                cost = bar.close_price * volume
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[vt_symbol] = target_volume
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "买入",
                        "volume": volume,
                        "price": bar.close_price
                    })
    
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
            "total_value": total_value
        })
        
        # 计算日收益率
        if len(self.daily_values) > 1:
            prev_value = self.daily_values[-2]["total_value"]
            daily_return = (total_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)


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


# 全局变量
history_data = {}


def calculate_statistics(daily_values: List[dict], daily_returns: List[float]) -> dict:
    """计算统计指标"""
    if not daily_values:
        return {}
    
    import math
    import numpy as np
    
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
    
    # 夏普比率（假设无风险利率 3%）
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


def run_backtest(setting: dict = None):
    """运行回测"""
    print("=" * 60)
    print("纯动量策略回测")
    print("=" * 60)
    
    # 加载数据
    data_path = Path("./data_real")
    vt_symbols, history_data_g, dts = load_data(data_path)
    
    global history_data
    history_data = history_data_g
    
    # 策略参数
    setting = setting or {
        "lookback": 20,
        "top_k": 9,
        "rebalance_days": 5
    }
    
    print("\n📊 策略参数:")
    print(f"  回看天数：{setting['lookback']}天")
    print(f"  选股数量：{setting['top_k']}只")
    print(f"  调仓周期：{setting['rebalance_days']}天")
    print(f"  排除 ST: {setting.get('exclude_st', True)}")
    
    # 创建策略
    strategy = MomentumStrategy(setting=setting)
    
    # 创建引擎
    engine = SimpleBacktestEngine(capital=1_000_000)
    
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
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if stats:
        print(f"  初始资金：{stats['initial']:,.0f}")
        print(f"  最终价值：{stats['final']:,.0f}")
        print(f"  总收益率：{stats['total_return']:.2f}%")
        print(f"  年化收益率：{stats['annual_return']:.2f}%")
        print(f"  年化波动率：{stats['annual_volatility']:.2f}%")
        print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")
        print(f"  最大回撤：{stats['max_drawdown']:.2f}%")
        print(f"  胜率：{stats['win_rate']:.1f}%")
        print(f"  交易次数：{len(engine.trades)}")
        
        final_holdings = [k for k, v in engine.positions.items() if v > 0]
        print(f"  最终持仓：{len(final_holdings)}只")
        if final_holdings:
            print(f"  持仓：{', '.join(final_holdings)}")
    
    print("=" * 60)
    
    return engine, stats


def compare_strategies():
    """对比不同参数"""
    print("=" * 60)
    print("动量策略参数对比")
    print("=" * 60)
    
    # 测试不同参数组合
    param_sets = [
        {"lookback": 10, "top_k": 9, "rebalance_days": 5},
        {"lookback": 20, "top_k": 9, "rebalance_days": 5},
        {"lookback": 20, "top_k": 9, "rebalance_days": 10},
        {"lookback": 20, "top_k": 6, "rebalance_days": 5},
        {"lookback": 30, "top_k": 9, "rebalance_days": 10},
    ]
    
    results = []
    
    for params in param_sets:
        print(f"\n测试参数：{params}")
        _, stats = run_backtest(params)
        
        if stats:
            results.append({
                "params": params,
                "annual_return": stats["annual_return"],
                "sharpe": stats["sharpe_ratio"],
                "max_dd": stats["max_drawdown"]
            })
    
    # 输出对比
    print("\n" + "=" * 60)
    print("参数对比结果")
    print("=" * 60)
    print(f"{'参数':<30} {'年化收益':>10} {'夏普':>8} {'最大回撤':>10}")
    print("-" * 60)
    
    for r in results:
        p = r["params"]
        param_str = f"L{p['lookback']}_K{p['top_k']}_R{p['rebalance_days']}"
        print(f"{param_str:<30} {r['annual_return']:>10.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>10.2f}%")
    
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        # 参数对比
        compare_strategies()
    else:
        # 默认回测
        engine, stats = run_backtest()
