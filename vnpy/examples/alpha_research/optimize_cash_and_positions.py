#!/usr/bin/env python3
"""
现金比例和持仓优化

目标:
- 现金比例：0.2% → 8%
- 持仓数量：12 只 → 8 只
"""

import json
from pathlib import Path
from datetime import datetime


def optimize_portfolio():
    """优化持仓和现金比例"""
    print("="*70)
    print(" " * 20 + "现金比例和持仓优化")
    print("="*70)
    
    # 加载账户
    account_file = Path('./accounts/virtual_2026_account.json')
    with open(account_file, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    total_value = account['cash'] + sum(p.get('market_value', 0) for p in account['positions'])
    
    print(f"\n优化前:")
    print(f"  总资产：¥{total_value:,.2f}")
    print(f"  现金：¥{account['cash']:,.2f} ({account['cash']/total_value*100:.1f}%)")
    print(f"  持仓：{len(account['positions'])} 只")
    
    # 分析持仓
    positions = account['positions']
    
    # 分类持仓
    zero_value = [p for p in positions if p.get('market_value', 0) == 0]
    losing = [p for p in positions if p.get('profit_rate', 0) < 0 and p.get('market_value', 0) > 0]
    small_profit = [p for p in positions if 0 <= p.get('profit_rate', 0) < 0.05 and p.get('market_value', 0) > 0]
    good_profit = [p for p in positions if p.get('profit_rate', 0) >= 0.05]
    
    print(f"\n持仓分析:")
    print(f"  零市值：{len(zero_value)} 只 (应卖出)")
    print(f"  亏损：{len(losing)} 只")
    print(f"  微利 (<5%): {len(small_profit)} 只")
    print(f"  盈利 (≥5%): {len(good_profit)} 只")
    
    # 确定卖出列表
    to_sell = []
    
    # 1. 卖出零市值股票
    for pos in zero_value:
        to_sell.append({
            'symbol': pos['symbol'],
            'reason': '零市值',
            'value': 0
        })
    
    # 2. 卖出亏损股票 (优先卖出亏损少的)
    losing_sorted = sorted(losing, key=lambda x: x.get('profit_rate', 0), reverse=True)
    for pos in losing_sorted[:2]:  # 卖出 2 只亏损最少的
        to_sell.append({
            'symbol': pos['symbol'],
            'reason': f"亏损 {pos.get('profit_rate', 0)*100:.1f}%",
            'value': pos.get('market_value', 0)
        })
    
    # 3. 计算还需要卖出多少达到 8% 现金
    target_cash = total_value * 0.08
    current_cash = account['cash']
    cash_from_zero = sum(p.get('market_value', 0) for p in zero_value)
    cash_from_losing = sum(p.get('market_value', 0) for p in losing_sorted[:2])
    
    still_needed = target_cash - current_cash - cash_from_zero - cash_from_losing
    
    print(f"\n卖出计划:")
    print(f"  零市值股票：{len(zero_value)} 只")
    print(f"  亏损股票：{min(2, len(losing))} 只")
    
    if still_needed > 0:
        # 还需要卖出微利股票
        small_sorted = sorted(small_profit, key=lambda x: x.get('market_value', 0))
        for pos in small_sorted:
            if still_needed <= 0:
                break
            to_sell.append({
                'symbol': pos['symbol'],
                'reason': f"微利 {pos.get('profit_rate', 0)*100:.1f}%",
                'value': pos.get('market_value', 0)
            })
            still_needed -= pos.get('market_value', 0)
            print(f"  微利股票：{pos['symbol']} (¥{pos.get('market_value', 0):,.0f})")
    
    # 执行卖出 (模拟)
    print(f"\n执行卖出...")
    
    remaining_positions = []
    sell_symbols = [s['symbol'] for s in to_sell]
    sell_value = 0
    
    for pos in positions:
        if pos['symbol'] in sell_symbols:
            sell_value += pos.get('market_value', 0)
            # 添加交易记录
            trade = {
                'trade_id': f"sell_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pos['symbol']}",
                'symbol': pos['symbol'],
                'name': pos.get('name', ''),
                'direction': 'sell',
                'volume': pos.get('volume', 0),
                'price': pos.get('current_price', 0),
                'amount': pos.get('market_value', 0),
                'fee': pos.get('market_value', 0) * 0.001,
                'datetime': datetime.now().isoformat(),
                'reason': '持仓优化 - 现金比例调整'
            }
            account['trades'].append(trade)
        else:
            remaining_positions.append(pos)
    
    # 更新账户
    account['positions'] = remaining_positions
    account['cash'] += sell_value
    
    # 添加账户快照
    new_total = account['cash'] + sum(p.get('market_value', 0) for p in remaining_positions)
    snapshot = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'cash': account['cash'],
        'total_value': new_total,
        'market_value': sum(p.get('market_value', 0) for p in remaining_positions),
        'daily_return': 0,
        'daily_return_rate': 0,
        'positions_count': len(remaining_positions),
        'buy_count': 0,
        'sell_count': len(to_sell),
        'positions': remaining_positions
    }
    account['daily_snapshots'].append(snapshot)
    
    # 保存账户
    with open(account_file, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    
    # 打印结果
    print(f"\n优化后:")
    print(f"  总资产：¥{new_total:,.2f}")
    print(f"  现金：¥{account['cash']:,.2f} ({account['cash']/new_total*100:.1f}%)")
    print(f"  持仓：{len(remaining_positions)} 只")
    
    print(f"\n卖出股票 ({len(to_sell)}只):")
    for s in to_sell:
        print(f"  - {s['symbol']}: {s['reason']}")
    
    print(f"\n保留持仓 ({len(remaining_positions)}只):")
    remaining_sorted = sorted(remaining_positions, key=lambda x: x.get('market_value', 0), reverse=True)
    for i, pos in enumerate(remaining_sorted, 1):
        profit_rate = pos.get('profit_rate', 0) * 100
        print(f"  {i}. {pos['symbol']} ¥{pos.get('market_value', 0):,.0f} ({profit_rate:.1f}%)")
    
    # 检查是否达标
    cash_ratio = account['cash'] / new_total * 100
    position_count = len(remaining_positions)
    
    print(f"\n{'='*70}")
    if cash_ratio >= 5 and position_count <= 10:
        print("✅ 优化成功！达到目标")
        print(f"   现金比例：{cash_ratio:.1f}% (目标 5-10%)")
        print(f"   持仓数量：{position_count} 只 (目标 8-10 只)")
    else:
        print("⚠️ 部分达标")
        if cash_ratio < 5:
            print(f"   现金比例：{cash_ratio:.1f}% (仍需提升)")
        if position_count > 10:
            print(f"   持仓数量：{position_count} 只 (仍需精简)")
    print(f"{'='*70}")
    
    return account


if __name__ == '__main__':
    optimize_portfolio()
