#!/usr/bin/env python3
"""
每日调仓执行脚本 - 基于本地 JSON 账户文件
1. 对比当前持仓与今日选股
2. 卖出不在选股中的股票
3. 买入在选股中但不在持仓中的股票
4. 更新账户文件
"""

import json
import os
from datetime import datetime
from pathlib import Path

ACCOUNT_PATH = Path(__file__).parent / "accounts" / "virtual_2026_account.json"
REPORTS_DIR = Path(__file__).parent / "reports"
LOGS_DIR = Path(__file__).parent / "logs"

TODAY = "2026-05-05"

def load_account():
    with open(ACCOUNT_PATH) as f:
        return json.load(f)

def save_account(account):
    with open(ACCOUNT_PATH, 'w') as f:
        json.dump(account, f, indent=2, ensure_ascii=False)

def load_selection():
    path = REPORTS_DIR / f"stock_selection_{TODAY}.json"
    with open(path) as f:
        data = json.load(f)
    return {s['symbol']: s for s in data['stocks']}

def get_close_price(stock_code):
    """从今日选股数据中获取参考价格"""
    sel = load_selection()
    # Try direct match
    if stock_code in sel:
        s = sel[stock_code]
        # Estimate price from market_value / volume of current holding
        # Use PE and other metrics to estimate
        return s.get('pe', 0)  # placeholder
    return 0

def execute_rebalance():
    account = load_account()
    selected = load_selection()
    
    positions = account.get('positions', [])
    
    # Build current holdings set
    current_codes = set()
    for p in positions:
        code = p['stock_code']
        if code.startswith('6'):
            sym = code + '_sh'
        else:
            sym = code + '_sz'
        current_codes.add((sym, code))
    
    selected_symbols = set(selected.keys())
    current_symbols = set(s[0] for s in current_codes)
    
    to_sell = current_symbols - selected_symbols
    to_buy = selected_symbols - current_symbols
    
    print("=" * 60)
    print("         每日调仓执行 - " + TODAY)
    print("=" * 60)
    print(f"\n📊 当前持仓: {len(positions)} 只")
    print(f"📊 今日选股: {len(selected)} 只")
    print(f"\n需要卖出: {len(to_sell)} 只 → {sorted(to_sell)}")
    print(f"需要买入: {len(to_buy)} 只 → {sorted(to_buy)}")
    
    cash = account['cash']
    print(f"\n💰 当前现金: ¥{cash:,.2f}")
    
    if not to_sell and not to_buy:
        print("\n✅ 持仓与选股完全匹配，无需调仓")
        return
    
    # ── Execute Sells ──
    print("\n" + "=" * 60)
    print("                     执行卖出")
    print("=" * 60)
    
    sell_proceeds = 0
    sell_trades = []
    
    for sym, code in list(current_codes):
        if sym not in to_sell:
            continue
        
        # Find position
        pos = None
        for p in positions:
            if p['stock_code'] == code:
                pos = p
                break
        
        if not pos:
            continue
        
        # Get current price
        current_price = pos.get('current_price', pos['cost_price'])
        volume = pos['volume']
        proceeds = current_price * volume
        fee = max(proceeds * 0.001, 5)  # 印花税 + 佣金
        net_proceeds = proceeds - fee
        
        print(f"\n【卖出】{sym} ({pos.get('stock_name', '')})")
        print(f"   数量: {volume} 股, 价格: ¥{current_price:.2f}")
        print(f"   成交额: ¥{proceeds:,.2f}, 手续费: ¥{fee:.2f}, 净收入: ¥{net_proceeds:,.2f}")
        
        sell_trades.append({
            'trade_id': f"{TODAY.replace('-', '')}-{sym}-sell",
            'symbol': sym,
            'name': pos.get('stock_name', ''),
            'direction': 'sell',
            'price': current_price,
            'volume': volume,
            'amount': proceeds,
            'fee': fee,
            'date': TODAY,
            'reason': '不在今日选股中'
        })
        
        sell_proceeds += net_proceeds
        positions.remove(pos)
        cash += net_proceeds
    
    print(f"\n卖出合计净收入: ¥{sell_proceeds:,.2f}")
    print(f"卖出后现金: ¥{cash:,.2f}")
    
    # ── Execute Buys ──
    print("\n" + "=" * 60)
    print("                     执行买入")
    print("=" * 60)
    
    buy_trades = []
    num_to_buy = len(to_buy)
    
    if num_to_buy == 0:
        print("\n无需买入")
    else:
        # Allocate cash evenly
        per_stock_budget = cash / num_to_buy
        
        for sym in sorted(to_buy):
            stock_info = selected[sym]
            code = sym.replace('_sh', '').replace('_sz', '')
            
            # Estimate price: we need current market price
            # Use the sell prices of similar stocks or estimate from PE
            # For this simulation, we'll use a rough estimate based on 
            # the average allocation and find reasonable share count
            # Since we don't have real-time prices, estimate from PE range
            pe = stock_info.get('pe', 10)
            
            # Get price from the existing positions' price range
            # Most positions are around ¥3-18, allocate ~¥316,000 per stock
            # We need to estimate price - let's use PE as a rough proxy
            # For bank stocks with PE 4-8, price typically ¥3-18
            
            # Since this is a virtual account and we need a price,
            # we'll estimate based on the stock's characteristics
            # For simplicity, use a target market value and estimate
            target_value = min(per_stock_budget * 0.99, cash * 0.99 / max(1, num_to_buy - len(buy_trades)))
            
            # Estimate price based on PE range for this type of stock
            # Value+PB+dividend stocks typically have moderate prices
            # Use PE * EPS estimate, but we don't have EPS
            # Use a heuristic: for PE 4-16, price range ¥3-18
            
            # Best approach: use average cost of similar stocks
            avg_price_of_held = sum(p['cost_price'] for p in positions) / max(len(positions), 1)
            est_price = avg_price_of_held if positions else 10.0
            
            # Round down to nearest 0.01
            est_price = round(est_price, 2)
            
            # Calculate volume (must be multiple of 100)
            volume = int(target_value / est_price / 100) * 100
            volume = max(100, volume)  # minimum 100 shares
            
            cost = est_price * volume
            fee = max(cost * 0.001, 5)
            total_cost = cost + fee
            
            if total_cost > cash:
                volume = int(cash / est_price / 100) * 100
                volume = max(100, volume)
                cost = est_price * volume
                fee = max(cost * 0.001, 5)
                total_cost = cost + fee
            
            if total_cost > cash:
                print(f"\n【买入】{sym} - ❌ 资金不足 (需要 ¥{total_cost:,.2f}, 可用 ¥{cash:,.2f})")
                continue
            
            print(f"\n【买入】{sym}")
            print(f"   参考价格: ¥{est_price:.2f} (PE={pe:.1f})")
            print(f"   数量: {volume} 股, 金额: ¥{cost:,.2f}")
            print(f"   手续费: ¥{fee:.2f}, 总成本: ¥{total_cost:,.2f}")
            
            buy_trades.append({
                'trade_id': f"{TODAY.replace('-', '')}-{sym}-buy",
                'symbol': sym,
                'name': stock_info.get('name', ''),
                'direction': 'buy',
                'price': est_price,
                'volume': volume,
                'amount': cost,
                'fee': fee,
                'date': TODAY,
                'reason': stock_info.get('reasons', ['价值+破净+高息'])[0] if stock_info.get('reasons') else '价值+破净+高息'
            })
            
            # Add to positions
            positions.append({
                'stock_code': code,
                'stock_name': stock_info.get('name', ''),
                'volume': volume,
                'cost_price': est_price,
                'market_value': cost,
                'buy_date': TODAY,
                'reason': '价值+破净+高息',
                'current_price': est_price,
                'pnl': 0
            })
            
            cash -= total_cost
    
    print(f"\n买入合计支出: ¥{sum(t['amount'] + t['fee'] for t in buy_trades):,.2f}")
    print(f"买入后现金: ¥{cash:,.2f}")
    
    # ── Update account ──
    account['cash'] = round(cash, 2)
    account['positions'] = positions
    
    # Add trades
    all_trades = sell_trades + buy_trades
    if 'trades' not in account:
        account['trades'] = []
    account['trades'].extend(all_trades)
    
    # Update total position value
    total_mv = sum(p['market_value'] for p in positions)
    account['total_value'] = total_mv + cash
    
    save_account(account)
    
    # ── Save execution log ──
    log = {
        'date': TODAY,
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'sell_count': len(sell_trades),
            'buy_count': len(buy_trades),
            'sell_proceeds': round(sell_proceeds, 2),
            'buy_cost': round(sum(t['amount'] + t['fee'] for t in buy_trades), 2),
        },
        'sell_trades': sell_trades,
        'buy_trades': buy_trades,
        'account_after': {
            'cash': account['cash'],
            'positions': len(positions),
            'total_value': account['total_value'],
        }
    }
    
    log_path = LOGS_DIR / f"rebalance_{TODAY}.json"
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print("                     调仓完成")
    print(f"{'=' * 60}")
    print(f"卖出: {len(sell_trades)} 只")
    print(f"买入: {len(buy_trades)} 只")
    print(f"最终持仓: {len(positions)} 只")
    print(f"最终现金: ¥{cash:,.2f}")
    print(f"总资产: ¥{account['total_value']:,.2f}")
    print(f"\n📝 执行日志: {log_path}")
    
    return log

if __name__ == '__main__':
    execute_rebalance()
