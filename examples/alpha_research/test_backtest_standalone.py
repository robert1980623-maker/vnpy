"""
独立回测测试 - 不依赖完整 vnpy 环境

直接测试截面回测引擎核心功能
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import polars as pl
import numpy as np

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 直接导入需要的模块
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine, CrossSectionalDailyResult
from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


# ========== 配置 ==========

DATA_PATH = Path("./data")
LAB_PATH = Path("./lab/mock_test")


def load_mock_data() -> tuple[list[str], dict, set]:
    """加载模拟数据"""
    print("\n📊 加载模拟数据...")
    
    daily_path = DATA_PATH / "daily"
    
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
            
            bar = BarData(
                symbol=vt_symbol.split(".")[0],
                exchange=Exchange.SSE if "SSE" in vt_symbol else Exchange.SZSE,
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


def create_simple_strategy():
    """创建简单策略"""
    from vnpy.alpha.strategy.template import AlphaStrategy
    from vnpy.trader.object import BarData
    
    class EqualWeightStrategy(AlphaStrategy):
        """等权重策略"""
        
        def on_init(self):
            self.write_log("策略初始化")
        
        def on_bars(self, bars: dict[str, BarData]):
            # 等权重配置
            if not bars:
                return
            
            # 计算每只股票的目标价值
            portfolio_value = self.get_portfolio_value()
            target_per_stock = portfolio_value / len(bars)
            
            for vt_symbol, bar in bars.items():
                target_volume = target_per_stock / bar.close_price
                current_pos = self.get_pos(vt_symbol)
                
                # 简单调仓（允许 fractional shares）
                if abs(target_volume - current_pos) > 0.01:
                    if target_volume > current_pos:
                        self.send_order(
                            vt_symbol=vt_symbol,
                            direction=Direction.LONG,
                            offset=Offset.OPEN,
                            price=bar.close_price,
                            volume=target_volume - current_pos
                        )
                    else:
                        self.send_order(
                            vt_symbol=vt_symbol,
                            direction=Direction.SHORT,
                            offset=Offset.CLOSE,
                            price=bar.close_price,
                            volume=current_pos - target_volume
                        )
    
    return EqualWeightStrategy


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("截面回测测试（独立版）")
    print("=" * 60)
    
    # 1. 加载数据
    vt_symbols, history_data, dts = load_mock_data()
    
    # 2. 创建实验室（简化版）
    print("\n📊 创建实验室...")
    from vnpy.alpha.lab import AlphaLab
    lab = AlphaLab(str(LAB_PATH))
    
    # 3. 创建回测引擎
    print("\n📊 创建回测引擎...")
    engine = CrossSectionalBacktestingEngine(lab)
    
    # 手动设置数据
    engine.vt_symbols = vt_symbols
    engine.history_data = history_data
    engine.dts = dts
    engine.capital = 1_000_000
    engine.cash = 1_000_000
    engine.start = datetime(2025, 1, 1)
    engine.end = datetime(2026, 2, 28)
    
    # 4. 添加策略
    print("\n📊 添加策略...")
    strategy_class = create_simple_strategy()
    engine.strategy_class = strategy_class
    engine.strategy = strategy_class(
        strategy_engine=engine,
        strategy_name="EqualWeightStrategy",
        vt_symbols=vt_symbols.copy(),
        setting={}
    )
    engine.strategy.on_init()
    
    # 5. 运行回测
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 50 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if engine.strategy:
            engine.strategy.bars = bars
            engine.strategy.datetime = dt
        
        if bars:
            engine.strategy.on_bars(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 6. 计算结果
    print("\n📊 计算结果...")
    portfolio_value = engine.get_portfolio_value()
    print(f"  初始资金：1,000,000")
    print(f"  最终价值：{portfolio_value:,.0f}")
    print(f"  总收益：{(portfolio_value - 1_000_000) / 1_000_000 * 100:.2f}%")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    run_backtest()
