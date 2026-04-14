#!/usr/bin/env python3
"""
调试全面复盘归因脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_attribution import PerformanceAttribution
from debug_virtual_account import DebugVirtualAccount

def main():
    print("开始执行调试版全面复盘归因...")
    try:
        # 初始化调试虚拟账户
        account = DebugVirtualAccount()
        
        # 执行归因分析
        attribution = PerformanceAttribution(account)
        attribution_report = attribution.generate_comprehensive_report()
        
        print(f"调试版全面复盘归因完成!")
        
    except Exception as e:
        import traceback
        print(f"调试版全面复盘归因失败: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()