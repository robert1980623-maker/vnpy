"""
使用真实感数据测试回测
"""

import sys
from pathlib import Path

# 修改数据路径
DATA_PATH = Path("./data_real")

# 导入测试脚本（需要修改路径）
sys.path.insert(0, str(Path(__file__).parent))

from test_backtest_simple import load_data, SimpleBacktestEngine, EqualWeightStrategy, run_backtest

# 覆盖数据路径
import test_backtest_simple
test_backtest_simple.DATA_PATH = DATA_PATH

def main():
    """主函数"""
    print("=" * 60)
    print("真实感数据回测测试")
    print("=" * 60)
    print(f"数据路径：{DATA_PATH.absolute()}")
    print()
    
    # 运行回测
    engine = run_backtest()
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if engine.daily_values:
        initial = engine.daily_values[0]["total_value"]
        final = engine.daily_values[-1]["total_value"]
        
        print(f"✅ 回测成功完成")
        print(f"📊 初始资金：{initial:,.0f}")
        print(f"📈 最终价值：{final:,.0f}")
        print(f"📉 收益率：{(final-initial)/initial*100:.2f}%")
        print(f"💰 绝对收益：{final-initial:,.0f}")
        print(f"📊 交易次数：{len(engine.trades)}")
        print(f"📊 最终持仓：{len([p for p in engine.positions.values() if p.volume > 0])}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
