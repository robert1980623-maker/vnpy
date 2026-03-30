#!/usr/bin/env python3
"""
周末数据/策略维护脚本
执行时间：周末 10:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_freshness_guard import DataFreshnessGuard
from strategy_optimizer import StrategyOptimizer

def main():
    print("开始执行周末数据/策略维护...")
    try:
        # 执行数据新鲜度检查
        data_guard = DataFreshnessGuard()
        result = data_guard.run_guard_cycle(auto_fix=True)
        print(f"数据检查结果：{result.get('status', 'unknown')}")
        
        # 执行策略优化
        optimizer = StrategyOptimizer()
        optimizer.optimize_strategies()
        
        print("周末数据/策略维护完成")
        
    except Exception as e:
        print(f"周末数据/策略维护失败：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
