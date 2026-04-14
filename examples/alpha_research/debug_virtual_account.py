#!/usr/bin/env python3
"""
调试虚拟账户，使用本地持仓数据
"""

import json
from pathlib import Path

class DebugVirtualAccount:
    def __init__(self):
        self.account_data = {
            "account_id": "ACC001",
            "account_name": "王雅轩主账户",
            "initial_capital": 1000000,
            "current_cash": 1000000 - 996546.4,  # 初始资金减去持仓成本
            "currency": "CNY",
            "status": "active",
            "created_at": "2026-03-24",
            "updated_at": "2026-04-02T20:00:00"
        }
        
        # 从 debug_positions.json 加载持仓
        with open('debug_positions.json', 'r', encoding='utf-8') as f:
            self.positions = json.load(f)
        
        self.trade_log = {"trades": []}
    
    def get_available_cash(self):
        return self.account_data.get("current_cash", 0)
    
    def get_positions(self):
        return self.positions
    
    def get_position_value(self):
        total = 0
        for pos in self.get_positions():
            total += pos["cost"]
        return total

if __name__ == "__main__":
    account = DebugVirtualAccount()
    print(f"可用资金：¥{account.get_available_cash():,.2f}")
    print(f"持仓：{len(account.get_positions())} 只")
    for pos in account.get_positions():
        print(f"  {pos['symbol']}: {pos['quantity']}股 @ ¥{pos['avg_price']:.2f}")