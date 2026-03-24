#!/usr/bin/env python3
"""
持仓风险检查脚本
执行时间: 工作日 15:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from virtual_account import VirtualAccount
from risk_analyzer import RiskAnalyzer

def main():
    print("开始执行持仓风险检查...")
    try:
        # 初始化虚拟账户
        account = VirtualAccount()
        
        # 执行风险检查
        risk_analyzer = RiskAnalyzer(account)
        risk_report = risk_analyzer.analyze_portfolio_risk()
        
        print(f"风险检查完成: {risk_report}")
        
    except Exception as e:
        print(f"风险检查失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
