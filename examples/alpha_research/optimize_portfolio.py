#!/usr/bin/env python3
"""
持仓优化脚本

功能:
- 精简持仓到 5-10 只
- 优化现金比例到 5-10%
- 保留优质股票，卖出劣质股票
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def load_account() -> Dict:
    """加载账户"""
    account_file = Path('./accounts/virtual_2026_account.json')
    with open(account_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_account(account: Dict):
    """保存账户"""
    account_file = Path('./accounts/virtual_2026_account.json')
    with open(account_file, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)


def analyze_positions(positions: List[Dict]) -> List[Dict]:
    """分析持仓，返回排序后的持仓列表"""
    # 计算综合评分
    for pos in positions:
        profit_rate = pos.get('profit_rate', 0)
        market_value = pos.get('market_value', 0)
        
        # 评分规则:
        # 1. 盈利比例 (权重 50%)
        # 2. 市值大小 (权重 30%)
        # 3. 基本面 (权重 20%) - 简化为是否为龙头股
        
        # 盈利评分
        profit_score = min(profit_rate * 10, 100) if profit_rate > 0 else max(profit_rate * 5, -100)
        
        # 市值评分 (越大越好)
        market_score = min(market_value / 10000, 100)
        
        # 龙头股加分 (简化：茅台、五粮液、宁德等)
        dragon_bones = ['600519.SH', '000858.SZ', '300750.SZ']
        dragon_score = 50 if pos['symbol'] in dragon_bones else 0
        
        # 综合评分
        pos['score'] = profit_score * 0.5 + market_score * 0.3 + dragon_score * 0.2
    
    # 按评分排序
    return sorted(positions, key=lambda x: x.get('score', 0), reverse=True)


def optimize_portfolio(target_count: int = 8, target_cash_ratio: float = 0.08):
    """
    优化持仓
    
    Args:
        target_count: 目标持仓数量 (5-10)
        target_cash_ratio: 目标现金比例 (5-10%)
    """
    print("="*70)
    print(" " * 20 + "持仓优化")
    print("="*70)
    
    # 加载账户
    account = load_account()
    total_value = account['cash'] + sum(p['market_value'] for p in account['positions'])
    
    print(f"\n优化前:")
    print(f"  总资产：¥{total_value:,.2f}")
    print(f"  现金：¥{account['cash']:,.2f} ({account['cash']/total_value*100:.1f}%)")
    print(f"  持仓：{len(account['positions'])} 只")
    
    # 分析持仓
    positions = analyze_positions(account['positions'])
    
    # 确定保留的股票
    keep_count = min(target_count, len(positions))
    keep_positions = positions[:keep_count]
    sell_positions = positions[keep_count:]
    
    print(f"\n保留持仓 ({keep_count}只):")
    for i, pos in enumerate(keep_positions, 1):
        profit_rate = pos.get('profit_rate', 0) * 100
        print(f"  {i}. {pos['symbol']} {pos.get('name', ''):<10} ¥{pos['market_value']:>10,.0f} ({profit_rate:>7.1f}%)")
    
    if sell_positions:
        print(f"\n卖出持仓 ({len(sell_positions)}只):")
        sell_value = 0
        for pos in sell_positions:
            profit_rate = pos.get('profit_rate', 0) * 100
            sell_value += pos['market_value']
            print(f"  - {pos['symbol']} {pos.get('name', ''):<10} ¥{pos['market_value']:>10,.0f} ({profit_rate:>7.1f}%)")
        
        # 执行卖出 (模拟)
        print(f"\n执行卖出...")
        print(f"  卖出总额：¥{sell_value:,.2f}")
        
        # 更新账户
        account['positions'] = keep_positions
        account['cash'] += sell_value
        
        # 添加交易记录
        for pos in sell_positions:
            trade = {
                'trade_id': f"sell_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pos['symbol']}",
                'symbol': pos['symbol'],
                'name': pos.get('name', ''),
                'direction': 'sell',
                'volume': pos.get('volume', 0),
                'price': pos.get('current_price', 0),
                'amount': pos['market_value'],
                'fee': pos['market_value'] * 0.001,
                'datetime': datetime.now().isoformat(),
                'reason': '持仓优化 - 精简持仓'
            }
            account['trades'].append(trade)
        
        # 添加账户快照
        new_total = account['cash'] + sum(p['market_value'] for p in keep_positions)
        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'cash': account['cash'],
            'total_value': new_total,
            'market_value': sum(p['market_value'] for p in keep_positions),
            'daily_return': 0,
            'daily_return_rate': 0,
            'positions_count': len(keep_positions),
            'buy_count': 0,
            'sell_count': len(sell_positions),
            'positions': keep_positions
        }
        account['daily_snapshots'].append(snapshot)
        
        # 保存账户
        save_account(account)
        
        print(f"\n优化后:")
        print(f"  总资产：¥{new_total:,.2f}")
        print(f"  现金：¥{account['cash']:,.2f} ({account['cash']/new_total*100:.1f}%)")
        print(f"  持仓：{len(keep_positions)} 只")
        
        # 检查现金比例
        cash_ratio = account['cash'] / new_total
        if cash_ratio < target_cash_ratio:
            print(f"\n⚠️ 现金比例 {cash_ratio*100:.1f}% 仍低于目标 {target_cash_ratio*100:.1f}%")
            print(f"  建议：继续卖出 {int((target_cash_ratio - cash_ratio) * new_total):,.0f} 元持仓")
        else:
            print(f"\n✅ 现金比例 {cash_ratio*100:.1f}% 达到目标范围")
    else:
        print(f"\n✅ 持仓数量已符合要求 ({len(positions)}只)")
    
    print("\n" + "="*70)
    print(" " * 25 + "完成")
    print("="*70)
    
    return account


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='持仓优化')
    parser.add_argument('--count', type=int, default=8, help='目标持仓数量 (5-10)')
    parser.add_argument('--cash-ratio', type=float, default=0.08, help='目标现金比例 (0.05-0.10)')
    
    args = parser.parse_args()
    
    optimize_portfolio(args.count, args.cash_ratio)
