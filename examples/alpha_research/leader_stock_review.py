#!/usr/bin/env python3
"""
龙头股复盘脚本
执行时间: 工作日 17:00
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_analyst import MarketAnalyst

def main():
    print("开始执行龙头股复盘...")
    try:
        # 执行龙头股分析
        analyst = MarketAnalyst()
        leader_stock_report = analyst.analyze_leader_stocks()
        
        print(f"龙头股复盘完成: {leader_stock_report}")
        
    except Exception as e:
        print(f"龙头股复盘失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
