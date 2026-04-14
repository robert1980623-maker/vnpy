#!/usr/bin/env python3
"""从 trades 重建持仓（positions 数组为空时使用）"""
import json, sys
from pathlib import Path

def rebuild_positions(account_file: str = './accounts/virtual_2026_account.json'):
    f = Path(account_file)
    if not f.exists():
        print(f"❌ 文件不存在: {f}")
        return
    with open(f) as fh:
        account = json.load(fh)
    
    positions = {}
    for t in account.get('trades', []):
        if t.get('status') != 'filled':
            continue
        sym = t['symbol']
        if '.' not in sym:
            sym = f"{sym}.{'SH' if sym[:1] in '69' else 'SZ'}"
        if sym not in positions:
            positions[sym] = {'symbol': sym, 'name': t.get('name',''), 'quantity': 0, 'total_cost': 0}
        if t['direction'] == 'buy':
            positions[sym]['quantity'] += t['quantity']
            positions[sym]['total_cost'] += t['quantity'] * t['price']
        else:
            positions[sym]['quantity'] -= t['quantity']
    
    active = [v for v in positions.values() if v['quantity'] > 0]
    for p in active:
        p['avg_cost'] = round(p['total_cost'] / p['quantity'], 2)
    
    account['positions'] = active
    with open(f, 'w') as fh:
        json.dump(account, fh, ensure_ascii=False, indent=2)
    
    print(f"✅ 重建完成：{len(active)} 只持仓")
    for p in active:
        print(f"  {p['symbol']} {p['name']} {p['quantity']}股 @ {p['avg_cost']}")

if __name__ == '__main__':
    f = sys.argv[1] if len(sys.argv) > 1 else './accounts/virtual_2026_account.json'
    rebuild_positions(f)
