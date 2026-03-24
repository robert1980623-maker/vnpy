#!/usr/bin/env python3
"""
量化 Agent - 负责选股和交易执行

功能:
- 多策略选股 (价值、成长、质量、股息)
- 交易计划生成
- 虚拟账户交易执行
- 风险控制和止盈止损
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class QuantAgent:
    def __init__(self):
        self.project_root = Path("/Users/rowang/projects/vnpy/examples/alpha_research")
        self.account_file = self.project_root / "accounts" / "virtual_2026_account.json"
        self.reports_dir = self.project_root / "reports"
        
    def run_stock_selection(self):
        """执行多策略选股"""
        print("🔍 执行多策略选股...")
        try:
            # 调用现有的选股脚本
            os.system(f"cd {self.project_root} && python3 daily_stock_selection.py")
            print("✅ 选股完成")
            return True
        except Exception as e:
            print(f"❌ 选股失败: {e}")
            return False
            
    def execute_trading(self):
        """执行交易"""
        print("💱 执行交易...")
        try:
            # 调用现有的交易脚本
            os.system(f"cd {self.project_root} && python3 daily_trading.py")
            print("✅ 交易执行完成")
            return True
        except Exception as e:
            print(f"❌ 交易执行失败: {e}")
            return False
            
    def run(self):
        """主运行函数"""
        print("=" * 50)
        print("🤖 量化 Agent 启动")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # 执行选股
        selection_success = self.run_stock_selection()
        
        # 执行交易
        trading_success = self.execute_trading()
        
        print("=" * 50)
        if selection_success and trading_success:
            print("✅ 量化 Agent 执行成功")
            return 0
        else:
            print("❌ 量化 Agent 执行失败")
            return 1


if __name__ == "__main__":
    agent = QuantAgent()
    sys.exit(agent.run())
