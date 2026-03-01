"""
真实感数据回测（完整独立版）
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import random
import math

import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


@dataclass
class Position:
    vt_symbol: str
    volume: float = 0.0
    avg_price: float = 0.0


@dataclass
class Order:
    vt_symbol: str
    direction: Direction
    volume: float
    price: float


class SimpleBacktestEngine:
    def __init__(self, capital: float = 1_000_000):
        self.capital = capital
        self.cash = capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[dict] = []
        self.daily_values: List[dict] = []
        self.datetime: Optional[datetime] = None
    
    def get_pos(self, vt_symbol: str) -> float:
        if vt_symbol in self.positions:
            return self.positions[vt_symbol].volume
        return 0.0
    
    def get_cash_available(self) -> float:
        return self.cash
    
    def get_portfolio_value(self) -> float:
        stock_value = sum(
            pos.avg_price * pos.volume 
            for pos in self.positions.values() 
            if pos.volume > 0
        )
        return self.cash + stock_value
    
    def send_order(self, vt_symbol: str, direction: Direction, offset: Offset, price: float, volume: float):
        self.orders.append(Order(vt_symbol=vt_symbol, direction=direction, volume=volume, price=price))
    
    def match_orders(self, bars: Dict[str, BarData]):
        for order in self.orders:
            if order.vt_symbol not in bars:
                continue
            
            bar = bars[order.vt_symbol]
            
            if order.direction == Direction.LONG:
                cost = order.price * order.volume
                if cost <= self.cash:
                    self.cash -= cost
                    
                    if order.vt_symbol not in self.positions:
                        self.positions[order.vt_symbol] = Position(vt_symbol=order.vt_symbol)
                    
                    pos = self.positions[order.vt_symbol]
                    old_value = pos.avg_price * pos.volume
                    pos.volume += order.volume
                    pos.avg_price = (old_value + cost) / pos.volume if pos.volume > 0 else order.price
                    
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": order.vt_symbol,
                        "direction": "买入",
                        "volume": order.volume,
                        "price": order.price,
                        "amount": cost
                    })
            
            elif order.direction == Direction.SHORT:
                if order.vt_symbol in self.positions:
                    pos = self.positions[order.vt_symbol]
                    sell_volume = min(order.volume, pos.volume)
                    
                    if sell_volume > 0:
                        revenue = order.price * sell_volume
                        self.cash += revenue
                        pos.volume -= sell_volume
                        
                        self.trades.append({
                            "datetime": self.datetime,
                            "vt_symbol": order.vt_symbol,
                            "direction": "卖出",
                            "volume": sell_volume,
                            "price": order.price,
                            "amount": revenue
                        })
        
        self.orders = []
    
    def record_daily_value(self, bars: Dict[str, BarData]):
        if not self.datetime:
            return
        
        stock_value = sum(
            bars[vt_symbol].close_price * pos.volume
            for vt_symbol, pos in self.positions.items()
            if vt_symbol in bars and pos.volume > 0
        )
        
        self.daily_values.append({
            "datetime": self.datetime,
            "cash": self.cash,
            "stock_value": stock_value,
            "total_value": self.cash + stock_value
        })


class EqualWeightStrategy:
    def __init__(self, engine: SimpleBacktestEngine):
        self.engine = engine
    
    def on_bars(self, bars: Dict[str, BarData]):
        if not bars:
            return
        
        total_value = self.engine.get_portfolio_value()
        target_per_stock = total_value / len(bars)
        
        for vt_symbol, bar in bars.items():
            target_volume = target_per_stock / bar.close_price
            current_pos = self.engine.get_pos(vt_symbol)
            
            if abs(target_volume - current_pos) > 0.01:
                if target_volume > current_pos:
                    self.engine.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        price=bar.close_price,
                        volume=target_volume - current_pos
                    )
                else:
                    self.engine.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.SHORT,
                        offset=Offset.CLOSE,
                        price=bar.close_price,
                        volume=current_pos - target_volume
                    )


def load_data(data_path: Path) -> tuple[List[str], Dict, set]:
    print("\n📊 加载数据...")
    
    daily_path = data_path / "daily"
    
    vt_symbols = []
    history_data = {}
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
            
            history_data[(dt, vt_symbol)] = bar
    
    print(f"  股票数量：{len(vt_symbols)}")
    print(f"  交易日数：{len(dts)}")
    print(f"  总记录数：{len(history_data)}")
    
    return vt_symbols, history_data, dts


def run_backtest(data_path: Path):
    print("=" * 60)
    print("真实感数据回测测试")
    print("=" * 60)
    print(f"数据路径：{data_path.absolute()}")
    
    # 加载数据
    vt_symbols, history_data, dts = load_data(data_path)
    
    # 创建引擎
    print("\n📊 创建回测引擎...")
    engine = SimpleBacktestEngine(capital=1_000_000)
    
    # 创建策略
    print("\n📊 创建策略...")
    strategy = EqualWeightStrategy(engine)
    
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
            strategy.on_bars(bars)
            engine.match_orders(bars)
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 结果
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
        
        print(f"  初始资金：{initial:,.0f}")
        print(f"  最终价值：{final:,.0f}")
        print(f"  总收益率：{total_return:.2f}%")
        print(f"  绝对收益：{final - initial:,.0f}")
        print(f"  最大回撤：{max_dd:.2f}%")
        print(f"  交易次数：{len(engine.trades)}")
        print(f"  最终持仓：{len([p for p in engine.positions.values() if p.volume > 0])}")
    
    print("=" * 60)
    return engine


if __name__ == "__main__":
    data_path = Path("./data_real")
    engine = run_backtest(data_path)
