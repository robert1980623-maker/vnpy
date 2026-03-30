#!/usr/bin/env python3
"""
调仓执行脚本
执行时间: 工作日 16:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rebalance_portfolio import PortfolioRebalancer
from non_interactive_helper import setup_non_interactive_mode

def main():
    print("开始执行调仓操作...")
    try:
        # 启用无人值守模式
        setup_non_interactive_mode(True)
        
        # 执行调仓
        rebalancer = PortfolioRebalancer(target_stocks=5)
        rebalancer.run()
        
        print("调仓执行完成")
        
    except Exception as e:
        print(f"调仓执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()