"""
简化回测测试 - 验证截面回测核心功能

不依赖 talib，直接测试回测引擎
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
import random

import polars as pl
import numpy as np

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


# ========== 简化版回测引擎 ==========

@dataclass
class Position:
    """持仓"""
    vt_symbol: str
    volume: float = 0.0
    avg_price: float = 0.0


@dataclass
class Order:
    """订单"""
    vt_symbol: str
    direction: Direction
    volume: float
    price: float
    traded: bool = False


class SimpleBacktestEngine:
    """简化回测引擎"""
    
    def __init__(self, capital: float = 1_000_000):
        self.capital = capital
        self.cash = capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[dict] = []
        self.daily_values: List[dict] = []
        self.datetime: Optional[datetime] = None
    
    def get_pos(self, vt_symbol: str) -> float:
        """获取持仓"""
        if vt_symbol in self.positions:
            return self.positions[vt_symbol].volume
        return 0.0
    
    def get_cash_available(self) -> float:
        """获取可用资金"""
        return self.cash
    
    def get_portfolio_value(self) -> float:
        """获取组合总价值"""
        # 股票价值
        stock_value = 0.0
        for pos in self.positions.values():
            if pos.volume > 0:
                # 使用最新收盘价估算
                stock_value += pos.avg_price * pos.volume
        
        return self.cash + stock_value
    
    def send_order(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float
    ) -> None:
        """发送订单"""
        order = Order(
            vt_symbol=vt_symbol,
            direction=direction,
            volume=volume,
            price=price
        )
        self.orders.append(order)
    
    def match_orders(self, bars: Dict[str, BarData]) -> None:
        """撮合订单"""
        for order in self.orders:
            if order.vt_symbol not in bars:
                continue
            
            bar = bars[order.vt_symbol]
            
            # 简单撮合：假设全部成交
            if order.direction == Direction.LONG:
                # 买入
                cost = order.price * order.volume
                
                if cost <= self.cash:
                    self.cash -= cost
                    
                    # 更新持仓
                    if order.vt_symbol not in self.positions:
                        self.positions[order.vt_symbol] = Position(vt_symbol=order.vt_symbol)
                    
                    pos = self.positions[order.vt_symbol]
                    old_value = pos.avg_price * pos.volume
                    new_value = cost
                    pos.volume += order.volume
                    pos.avg_price = (old_value + new_value) / pos.volume if pos.volume > 0 else order.price
                    
                    # 记录成交
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": order.vt_symbol,
                        "direction": "买入",
                        "volume": order.volume,
                        "price": order.price,
                        "amount": cost
                    })
            
            elif order.direction == Direction.SHORT:
                # 卖出
                if order.vt_symbol in self.positions:
                    pos = self.positions[order.vt_symbol]
                    sell_volume = min(order.volume, pos.volume)
                    
                    if sell_volume > 0:
                        revenue = order.price * sell_volume
                        self.cash += revenue
                        
                        pos.volume -= sell_volume
                        
                        # 记录成交
                        self.trades.append({
                            "datetime": self.datetime,
                            "vt_symbol": order.vt_symbol,
                            "direction": "卖出",
                            "volume": sell_volume,
                            "price": order.price,
                            "amount": revenue
                        })
        
        # 清空订单
        self.orders = []
    
    def record_daily_value(self, bars: Dict[str, BarData]) -> None:
        """记录每日净值"""
        if not self.datetime:
            return
        
        # 计算股票市值（使用最新收盘价）
        stock_value = 0.0
        for vt_symbol, pos in self.positions.items():
            if vt_symbol in bars and pos.volume > 0:
                stock_value += bars[vt_symbol].close_price * pos.volume
        
        total_value = self.cash + stock_value
        
        self.daily_values.append({
            "datetime": self.datetime,
            "cash": self.cash,
            "stock_value": stock_value,
            "total_value": total_value
        })


# ========== 测试策略 ==========

class EqualWeightStrategy:
    """等权重策略"""
    
    def __init__(self, engine: SimpleBacktestEngine):
        self.engine = engine
        self.name = "EqualWeight"
    
    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """K 线更新"""
        if not bars:
            return
        
        # 计算每只股票的目标价值
        total_value = self.engine.get_portfolio_value()
        target_per_stock = total_value / len(bars)
        
        # 调仓
        for vt_symbol, bar in bars.items():
            target_volume = target_per_stock / bar.close_price
            current_pos = self.engine.get_pos(vt_symbol)
            
            # 调仓阈值
            if abs(target_volume - current_pos) > 0.01:
                if target_volume > current_pos:
                    # 买入
                    volume = target_volume - current_pos
                    self.engine.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        price=bar.close_price,
                        volume=volume
                    )
                else:
                    # 卖出
                    volume = current_pos - target_volume
                    self.engine.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.SHORT,
                        offset=Offset.CLOSE,
                        price=bar.close_price,
                        volume=volume
                    )


# ========== 主测试流程 ==========

def load_data(data_path_override: Optional[Path] = None) -> tuple[List[str], Dict, set]:
    """加载模拟数据"""
    print("\n📊 加载数据...")
    
    data_path = data_path_override or Path("./data/daily")
    
    vt_symbols = []
    history_data = {}
    dts = set()
    
    for file_path in data_path.glob("*.parquet"):
        df = pl.read_parquet(file_path)
        vt_symbol = df["vt_symbol"][0]
        vt_symbols.append(vt_symbol)
        
        for row in df.iter_rows(named=True):
            dt = row["datetime"]
            dts.add(dt)
            
            # 判断交易所
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


def run_backtest(data_path: Optional[Path] = None):
    """运行回测"""
    print("=" * 60)
    print("简化回测测试")
    print("=" * 60)
    
    # 1. 加载数据
    vt_symbols, history_data, dts = load_data(data_path)
    
    # 2. 创建回测引擎
    print("\n📊 创建回测引擎...")
    engine = SimpleBacktestEngine(capital=1_000_000)
    
    # 3. 创建策略
    print("\n📊 创建策略...")
    strategy = EqualWeightStrategy(engine)
    print(f"  策略：{strategy.name}")
    
    # 4. 运行回测
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 50 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        
        # 获取当日所有股票的 K 线
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if bars:
            # 策略逻辑
            strategy.on_bars(bars)
            
            # 撮合订单
            engine.match_orders(bars)
            
            # 记录每日净值
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 5. 计算结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if engine.daily_values:
        initial_value = engine.daily_values[0]["total_value"]
        final_value = engine.daily_values[-1]["total_value"]
        
        total_return = (final_value - initial_value) / initial_value * 100
        
        print(f"  初始资金：{initial_value:,.0f}")
        print(f"  最终价值：{final_value:,.0f}")
        print(f"  总收益率：{total_return:.2f}%")
        print(f"  绝对收益：{final_value - initial_value:,.0f}")
        
        # 计算最大回撤
        max_drawdown = 0.0
        peak = initial_value
        
        for daily in engine.daily_values:
            value = daily["total_value"]
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        print(f"  最大回撤：{max_drawdown:.2f}%")
        
        # 交易统计
        print(f"\n  交易次数：{len(engine.trades)}")
        
        # 持仓统计
        active_positions = [pos for pos in engine.positions.values() if pos.volume > 0]
        print(f"  最终持仓数：{len(active_positions)}")
    
    print("=" * 60)
    
    # 6. 显示示例交易
    print("\n📊 示例交易（前 10 笔）:")
    for trade in engine.trades[:10]:
        print(f"  {trade['datetime'].date()} {trade['vt_symbol']} {trade['direction']} "
              f"{trade['volume']:.2f}股 @ {trade['price']:.2f}元")
    
    if len(engine.trades) > 10:
        print(f"  ... 还有 {len(engine.trades) - 10} 笔交易")
    
    print("\n✅ 回测测试完成！")
    
    return engine


if __name__ == "__main__":
    engine = run_backtest()
