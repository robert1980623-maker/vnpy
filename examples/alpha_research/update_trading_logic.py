#!/usr/bin/env python3
"""
更新交易逻辑以匹配新的持仓配置

更新内容:
- 选股数量：100 → 10
- 最大持仓：25 → 10
- 现金比例：0% → 5-10%
"""

import json
from pathlib import Path
from datetime import datetime

def update_daily_trading():
    """更新每日交易脚本"""
    filename = 'daily_trading.py'
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新持仓数量限制
        content = content.replace(
            'max_positions = 25',
            'max_positions = 10  # 精简持仓'
        )
        
        # 更新现金比例
        content = content.replace(
            'min_cash_ratio = 0.0',
            'min_cash_ratio = 0.05  # 最少 5% 现金'
        )
        content = content.replace(
            'target_cash_ratio = 0.0',
            'target_cash_ratio = 0.08  # 目标 8% 现金'
        )
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filename}: 已更新持仓逻辑")
        
    except FileNotFoundError:
        print(f"⚠️ {filename} 不存在")

def update_compliance_checker():
    """更新合规检查脚本"""
    filename = 'compliance_checker.py'
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新最大持仓数检查
        if 'max_positions' not in content:
            # 添加持仓数量检查
            old_rules = """self.rules = {
            'max_single_position': 0.15,      # 单只股票最大持仓 15%
            'max_industry_weight': 0.30,      # 行业集中度 30%
            'min_liquidity': 10000000,        # 最小日均成交 1000 万
            'forbid_st': True,                # 禁止 ST 股票
            'forbid_suspended': True,         # 禁止停牌股票
        }"""
        
        new_rules = """self.rules = {
            'max_positions': 10,              # 最大持仓数量 10 只
            'max_single_position': 0.25,      # 单只股票最大持仓 25%
            'max_industry_weight': 0.30,      # 行业集中度 30%
            'min_cash_ratio': 0.05,           # 最小现金比例 5%
            'min_liquidity': 10000000,        # 最小日均成交 1000 万
            'forbid_st': True,                # 禁止 ST 股票
            'forbid_suspended': True,         # 禁止停牌股票
        }"""
            
            content = content.replace(old_rules, new_rules)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filename}: 已更新合规规则")
        
    except FileNotFoundError:
        print(f"⚠️ {filename} 不存在")

if __name__ == '__main__':
    print("🔄 更新交易逻辑...")
    update_daily_trading()
    update_compliance_checker()
    print("\n✅ 交易逻辑已更新")
