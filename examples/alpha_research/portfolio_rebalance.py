#!/usr/bin/env python3
"""
调仓执行脚本
执行时间: 工作日 16:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from virtual_account import VirtualAccount
from rebalance_portfolio import RebalancePortfolio

def main():
    print("开始执行调仓操作...")
    try:
        # 初始化虚拟账户
        account = VirtualAccount()
        
        # 执行调仓
        rebalancer = RebalancePortfolio(account)
        rebalance_result = rebalancer.execute_rebalance()
        
        print(f"调仓执行完成: {rebalance_result}")
        
    except Exception as e:
        print(f"调仓执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
