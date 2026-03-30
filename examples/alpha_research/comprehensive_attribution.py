#!/usr/bin/env python3
"""
全面复盘归因脚本
执行时间: 工作日 20:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_attribution import PerformanceAttribution
from virtual_account import VirtualAccount

def main():
    print("开始执行全面复盘归因...")
    try:
        # 初始化虚拟账户
        account = VirtualAccount()
        
        # 执行归因分析
        attribution = PerformanceAttribution(account)
        attribution_report = attribution.generate_comprehensive_report()
        
        print(f"全面复盘归因完成: {attribution_report}")
        
    except Exception as e:
        print(f"全面复盘归因失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
