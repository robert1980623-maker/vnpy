"""
测试完整回测流程

使用模拟数据测试截面回测引擎
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
from vnpy.trader.constant import Interval


# ========== 配置 ==========

LAB_PATH = Path("./lab/mock_test")
DATA_PATH = Path("./data")


def create_test_strategy():
    """创建测试策略类"""
    from vnpy.alpha.strategy import AlphaStrategy
    from vnpy.trader.object import BarData
    from vnpy.trader.constant import Direction, Offset
    
    class SimpleTestStrategy(AlphaStrategy):
        """简单测试策略 - 等权重持有所有股票"""
        
        def on_init(self):
            """初始化"""
            self.write_log("策略初始化")
        
        def on_bars(self, bars: dict[str, BarData]):
            """K 线更新"""
            # 简单策略：等权重持有所有股票
            for vt_symbol, bar in bars.items():
                # 计算目标仓位（等权重）
                available_cash = self.get_cash_available()
                target_value = available_cash / len(bars)
                
                # 计算目标股数
                target_volume = target_value / bar.close_price
                
                # 获取当前持仓
                current_pos = self.get_pos(vt_symbol)
                
                # 调仓
                if target_volume > current_pos:
                    # 买入
                    volume = target_volume - current_pos
                    self.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        price=bar.close_price,
                        volume=volume
                    )
                elif target_volume < current_pos:
                    # 卖出
                    volume = current_pos - target_volume
                    self.send_order(
                        vt_symbol=vt_symbol,
                        direction=Direction.SHORT,
                        offset=Offset.CLOSE,
                        price=bar.close_price,
                        volume=volume
                    )
            
            # 输出每日持仓
            if self.datetime:
                portfolio_value = self.get_portfolio_value()
                self.write_log(f"{self.datetime.date()}: 组合价值 = {portfolio_value:,.0f}")
    
    return SimpleTestStrategy


def main():
    """主函数"""
    print("=" * 60)
    print("截面回测测试")
    print("=" * 60)
    
    # 1. 创建实验室
    print("\n📊 创建实验室...")
    lab = AlphaLab(str(LAB_PATH))
    print(f"  路径：{lab.lab_path}")
    
    # 2. 创建回测引擎
    print("\n📊 创建回测引擎...")
    engine = CrossSectionalBacktestingEngine(lab)
    
    # 3. 设置参数
    print("\n📊 设置回测参数...")
    vt_symbols = [
        "000001.SSE", "000002.SSE", "000003.SSE", 
        "000004.SSE", "000005.SSE", "000006.SSE",
        "000007.SSE", "000008.SSE", "000009.SSE",
        "000010.SSE"
    ]
    
    engine.set_parameters(
        vt_symbols=vt_symbols,
        interval=Interval.DAILY,
        start=datetime(2025, 1, 1),
        end=datetime(2026, 2, 28),
        capital=1_000_000,
        risk_free=0.03,
        annual_days=240
    )
    print(f"  股票数量：{len(vt_symbols)}")
    print(f"  时间范围：2025-01-01 - 2026-02-28")
    print(f"  初始资金：1,000,000")
    
    # 4. 添加策略
    print("\n📊 添加策略...")
    strategy_class = create_test_strategy()
    engine.add_strategy(strategy_class, setting={})
    
    # 5. 加载数据
    print("\n📊 加载数据...")
    engine.load_data()
    print(f"  加载完成：{len(engine.dts)} 个交易日")
    
    # 6. 运行回测
    print("\n📊 运行回测...")
    engine.run_backtesting()
    
    # 7. 计算结果
    print("\n📊 计算回测结果...")
    engine.calculate_result()
    
    # 8. 计算统计指标
    print("\n📊 计算统计指标...")
    stats = engine.calculate_statistics()
    
    # 9. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 60)
    
    # 10. 显示图表
    print("\n📊 准备显示图表...")
    try:
        engine.show_chart()
        print("✅ 图表已显示")
    except Exception as e:
        print(f"⚠️  图表显示失败：{e}")
        print("  （可能需要图形界面环境）")
    
    print("\n✅ 回测测试完成！")


if __name__ == "__main__":
    main()
