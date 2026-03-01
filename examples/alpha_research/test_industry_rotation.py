"""
行业轮动策略回测测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.strategy.industry_rotation import IndustryRotationStrategy, test_strategy


def run_backtest():
    """运行回测"""
    from test_realistic_backtest_full import SimpleBacktestEngine, load_data
    from vnpy.trader.constant import Direction, Offset, Interval, Exchange
    from vnpy.trader.object import BarData
    from datetime import datetime
    from typing import Dict, List
    import polars as pl
    
    print("=" * 60)
    print("行业轮动策略回测")
    print("=" * 60)
    
    # 1. 加载数据
    data_path = Path("./data_real")
    vt_symbols, history_data, dts = load_data(data_path)
    
    # 2. 创建简化版引擎
    print("\n📊 创建回测引擎...")
    
    class IndustryRotationEngine:
        """行业轮动回测引擎（简化版）"""
        
        def __init__(self, capital: float = 1_000_000):
            self.capital = capital
            self.cash = capital
            self.positions: Dict[str, float] = {}
            self.daily_values = []
            self.datetime = None
            self.trades = []
        
        def get_pos(self, vt_symbol: str) -> float:
            return self.positions.get(vt_symbol, 0.0)
        
        def get_cash_available(self) -> float:
            return self.cash
        
        def get_portfolio_value(self) -> float:
            stock_value = 0.0
            for vt_symbol, volume in self.positions.items():
                if volume > 0 and self.datetime:
                    key = (self.datetime, vt_symbol)
                    if key in history_data:
                        stock_value += history_data[key].close_price * volume
            return self.cash + stock_value
        
        def send_order(self, vt_symbol: str, direction: Direction, offset: Offset, price: float, volume: float):
            if direction == Direction.LONG:
                cost = price * volume
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[vt_symbol] = self.positions.get(vt_symbol, 0.0) + volume
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "买入",
                        "volume": volume,
                        "price": price
                    })
            else:
                if vt_symbol in self.positions:
                    sell_volume = min(volume, self.positions[vt_symbol])
                    if sell_volume > 0:
                        revenue = price * sell_volume
                        self.cash += revenue
                        self.positions[vt_symbol] -= sell_volume
                        self.trades.append({
                            "datetime": self.datetime,
                            "vt_symbol": vt_symbol,
                            "direction": "卖出",
                            "volume": sell_volume,
                            "price": price
                        })
        
        def record_daily_value(self, bars: Dict[str, BarData]):
            if not self.datetime:
                return
            
            stock_value = sum(
                bars[vt_symbol].close_price * volume
                for vt_symbol, volume in self.positions.items()
                if vt_symbol in bars and volume > 0
            )
            
            self.daily_values.append({
                "datetime": self.datetime,
                "total_value": self.cash + stock_value
            })
    
    engine = IndustryRotationEngine(capital=1_000_000)
    
    # 3. 创建策略
    print("\n📊 创建策略...")
    strategy = IndustryRotationStrategy(
        strategy_engine=engine,
        strategy_name="IndustryRotation",
        vt_symbols=vt_symbols,
        setting={
            "lookback_momentum": 20,
            "top_industries": 3,
            "stocks_per_industry": 5,
            "max_pe": 20,
            "max_pb": 3,
            "min_dividend_yield": 1.5,
            "rebalance_days": 5
        }
    )
    
    # 策略初始化
    strategy.on_init()
    strategy.universe = vt_symbols
    strategy.holdings = []
    
    # 4. 运行回测
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 100 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        strategy.datetime = dt
        
        # 获取当日 K 线
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if bars:
            # 策略逻辑
            strategy.on_bars(bars)
            
            # 记录每日净值
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 5. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if engine.daily_values:
        initial = engine.daily_values[0]["total_value"]
        final = engine.daily_values[-1]["total_value"]
        total_return = (final - initial) / initial * 100
        
        # 最大回撤
        max_dd = 0
        peak = initial
        for daily in engine.daily_values:
            value = daily["total_value"]
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 年化收益
        years = len(sorted_dts) / 240
        annual_return = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        print(f"  初始资金：{initial:,.0f}")
        print(f"  最终价值：{final:,.0f}")
        print(f"  总收益率：{total_return:.2f}%")
        print(f"  年化收益率：{annual_return:.2f}%")
        print(f"  最大回撤：{max_dd:.2f}%")
        print(f"  交易次数：{len(engine.trades)}")
        print(f"  最终持仓：{len([v for v in engine.positions.values() if v > 0])}")
    
    print("=" * 60)
    return engine


if __name__ == "__main__":
    # 先测试策略
    test_strategy()
    
    print("\n\n")
    
    # 运行回测
    engine = run_backtest()
