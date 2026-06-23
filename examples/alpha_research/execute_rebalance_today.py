#!/usr/bin/env python3
"""
每日调仓执行脚本 - 本地 JSON 账户版
基于今日选股结果执行调仓
"""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

ACCOUNT_PATH = Path(__file__).parent / "accounts" / "virtual_2026_account.json"
REPORTS_DIR = Path(__file__).parent / "reports"
LAB_DIR = Path("/Users/rowang/projects/vnpy/lab/data/daily")

TODAY = datetime.now().strftime("%Y-%m-%d")

def normalize(symbol):
    return symbol.replace('_sh','').replace('_sse','').replace('_sz','')

def load_account():
    with open(ACCOUNT_PATH, encoding='utf-8') as f:
        return json.load(f)

def save_account(account):
    with open(ACCOUNT_PATH, 'w', encoding='utf-8') as f:
        json.dump(account, f, indent=2, ensure_ascii=False)

def load_selection():
    path = REPORTS_DIR / f"stock_selection_{TODAY}.json"
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {normalize(s['symbol']): s for s in data['stocks']}

def get_latest_close(code):
    """从 parquet 获取最新收盘价"""
    if code.startswith('6'):
        sym = f'{code}.SSE'
    else:
        sym = f'{code}.SZSE'
    fname = sym + '.parquet'
    fpath = LAB_DIR / fname
    if fpath.exists():
        df = pd.read_parquet(fpath)
        return float(df.iloc[-1]['close']), str(df.iloc[-1]['datetime'])[:10]
    return None, None

def execute_rebalance():
    account = load_account()
    selected = load_selection()
    
    positions = account.get('positions', [])
    current_codes = {p['stock_code']: p for p in positions}
    selected_codes = set(selected.keys())
    current_set = set(current_codes.keys())
    
    to_sell_codes = sorted(current_set - selected_codes)
    to_buy_codes = sorted(selected_codes - current_set)
    
    print("=" * 70)
    print(f"         每日调仓执行 - {TODAY}")
    print("=" * 70)
    print(f"📊 持仓: {len(positions)} 只 | 选股: {len(selected)} 只")
    print(f"📌 持有不变: {len(current_set & selected_codes)} 只")
    print(f"🔴 卖出: {len(to_sell_codes)} 只 → {to_sell_codes}")
    print(f"🟢 买入: {len(to_buy_codes)} 只 → {to_buy_codes}")
    print(f"💰 当前现金: ¥{account['cash']:,.2f}")
    
    new_trades = []
    
    # === 1. 卖出 ===
    print("\n" + "-" * 50)
    print("  🔴 卖出执行")
    print("-" * 50)
    
    sell_proceeds = 0
    for code in to_sell_codes:
        pos = current_codes[code]
        price = pos.get('current_price', pos['cost_price'])
        volume = pos['volume']
        proceeds = round(price * volume, 2)
        pnl = round(proceeds - pos['cost_price'] * volume, 2)
        
        print(f"  {code} {pos['stock_name']}: {volume}股 @ {price:.2f} = ¥{proceeds:,.2f} (盈亏: {pnl:+,.2f})")
        
        sell_proceeds += proceeds
        new_trades.append({
            "trade_id": f"{TODAY}-{code}-sell",
            "date": TODAY,
            "direction": "sell",
            "symbol": code,
            "name": pos['stock_name'],
            "volume": volume,
            "price": price,
            "amount": proceeds,
            "pnl": pnl,
            "reason": "不在今日选股中，调仓卖出"
        })
    
    # Remove sold positions
    new_positions = [p for p in positions if p['stock_code'] not in to_sell_codes]
    
    cash_after_sell = account['cash'] + sell_proceeds
    print(f"\n  卖出回笼: ¥{sell_proceeds:,.2f}")
    print(f"  卖出后现金: ¥{cash_after_sell:,.2f}")
    
    # === 2. 买入 ===
    print("\n" + "-" * 50)
    print("  🟢 买入执行")
    print("-" * 50)
    
    per_stock = cash_after_sell / len(to_buy_codes) if to_buy_codes else 0
    print(f"  每只分配: ¥{per_stock:,.2f}")
    
    total_buy_cost = 0
    for code in to_buy_codes:
        sel = selected[code]
        price, price_date = get_latest_close(code)
        
        if price is None:
            print(f"  ⚠️ {code}: 无法获取价格，跳过")
            continue
        
        # 计算买入数量 (100股整数倍)
        volume = int(per_stock / price / 100) * 100
        if volume < 100:
            volume = 100
        
        cost = round(price * volume, 2)
        
        # 检查资金
        if total_buy_cost + cost > cash_after_sell * 0.99:
            # 资金不足，调整
            remaining = cash_after_sell * 0.99 - total_buy_cost
            volume = int(remaining / price / 100) * 100
            if volume < 100:
                print(f"  ⚠️ {code}: 资金不足，跳过")
                continue
            cost = round(price * volume, 2)
        
        # 获取股票名称
        name = sel.get('name', '')
        strategies = ', '.join(sel.get('strategies', []))
        pe = sel.get('pe', 0)
        pb_str = ""
        dy_str = ""
        for r in sel.get('reasons', []):
            if 'PB=' in r:
                pb_str = r
            if '股息率' in r or '股息' in r:
                dy_str = r
        
        print(f"  {code} {name}: {volume}股 @ {price:.2f} ({price_date}收盘) = ¥{cost:,.2f} | {strategies} PE={pe:.1f}")
        
        new_positions.append({
            "stock_code": code,
            "stock_name": name,
            "volume": volume,
            "cost_price": price,
            "market_value": cost,
            "buy_date": TODAY,
            "reason": strategies,
            "current_price": price,
            "pnl": 0.0
        })
        
        new_trades.append({
            "trade_id": f"{TODAY}-{code}-buy",
            "date": TODAY,
            "direction": "buy",
            "symbol": code,
            "name": name,
            "volume": volume,
            "price": price,
            "amount": cost,
            "pnl": 0,
            "reason": f"{strategies} (PE={pe:.1f})"
        })
        
        total_buy_cost += cost
    
    # === 3. 保存 ===
    final_cash = round(cash_after_sell - total_buy_cost, 2)
    account['cash'] = final_cash
    account['positions'] = new_positions
    account['trades'].extend(new_trades)
    
    total_mv = sum(p['market_value'] for p in new_positions)
    total_asset = final_cash + total_mv
    
    if 'daily_snapshots' not in account:
        account['daily_snapshots'] = []
    account['daily_snapshots'].append({
        "date": TODAY,
        "cash": final_cash,
        "position_value": round(total_mv, 2),
        "total_value": round(total_asset, 2),
        "num_positions": len(new_positions)
    })
    
    # 持久化 total_asset 到账户对象
    account['total_value'] = round(total_asset, 2)
    account['total_asset'] = round(total_asset, 2)
    
    save_account(account)
    
    # === 汇总 ===
    print("\n" + "=" * 70)
    print("  ✅ 执行完成")
    print("=" * 70)
    print(f"卖出 {len(to_sell_codes)} 只 → 回笼 ¥{sell_proceeds:,.2f}")
    print(f"买入 {len(to_buy_codes)} 只 → 支出 ¥{total_buy_cost:,.2f}")
    print(f"剩余现金: ¥{final_cash:,.2f}")
    print(f"持仓市值: ¥{total_mv:,.2f}")
    print(f"总资产: ¥{total_asset:,.2f}")
    print(f"仓位: {total_mv/total_asset*100:.1f}%")
    print(f"共执行 {len(new_trades)} 笔交易")
    
    print(f"\n持仓明细 ({len(new_positions)} 只):")
    for pos in sorted(new_positions, key=lambda x: x['stock_code']):
        flag = "新" if pos['buy_date'] == TODAY else "持"
        print(f"  [{flag}] {pos['stock_code']} {pos.get('stock_name',''):6s}: {pos['volume']:>6}股 @ {pos['cost_price']:>6.2f}, 市值=¥{pos['market_value']:>10,.2f}")
    
    return {
        "date": TODAY,
        "sells": len(to_sell_codes),
        "buys": len(to_buy_codes),
        "sell_proceeds": sell_proceeds,
        "total_buy_cost": total_buy_cost,
        "cash_remaining": final_cash,
        "total_asset": total_asset,
        "num_trades": len(new_trades)
    }

if __name__ == "__main__":
    result = execute_rebalance()
    print(f"\n✅ 调仓完成，共 {result['num_trades']} 笔交易")
