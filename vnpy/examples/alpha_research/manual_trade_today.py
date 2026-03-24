#!/usr/bin/env python3
"""
手动执行今日交易

修复交易计划格式问题后，手动执行今天的交易
"""

import json
from pathlib import Path
from datetime import datetime
from virtual_account import VirtualAccount

def execute_today_trades():
    print("=" * 70)
    print(" " * 20 + "手动执行今日交易")
    print("=" * 70)
    print()
    
    # 加载账户
    account = VirtualAccount(initial_capital=1000000, account_id="virtual_2026")
    print(f"✅ 加载账户：{account.account_id}")
    print(f"   现金：¥{account.cash:,.2f}")
    print(f"   持仓：{len(account.positions)} 只")
    print()
    
    # 加载交易计划
    plan_file = Path('reports/trading_plan_2026-03-09.json')
    with open(plan_file, 'r') as f:
        plan = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 执行卖出
    print("【执行卖出】")
    sell_count = 0
    for symbol in plan['sell']:
        # 查找持仓
        position = next((p for p in account.positions if p.symbol == symbol), None)
        if position:
            # 获取当前价格
            current_price = position.current_price
            trade = account.sell(
                symbol=symbol,
                price=current_price,
                volume=position.volume,
                date=today,
                reason="调仓卖出"
            )
            if trade:
                print(f"  卖出 {symbol} {position.volume}股 @ ¥{current_price:.2f}")
                sell_count += 1
        else:
            print(f"  ⚠️ {symbol} 不在持仓中")
    
    print(f"  完成：{sell_count} 笔卖出")
    print()
    
    # 执行买入
    print("【执行买入】")
    buy_count = 0
    buy_list = plan['buy']
    
    if buy_list:
        # 计算每只股票的买入金额 (留 10% 现金)
        available_cash = account.cash * 0.9
        position_size = available_cash / len(buy_list)
        
        print(f"  可用现金：¥{available_cash:,.2f}")
        print(f"  每只股票：¥{position_size:,.2f}")
        print()
        
        for stock in buy_list:
            symbol = stock['symbol']
            price = stock.get('price', 10.0)
            
            # 计算买入数量 (100 股的整数倍)
            volume = int(position_size / price / 100) * 100
            
            if volume >= 100:
                trade = account.buy(
                    symbol=symbol,
                    price=price,
                    volume=volume,
                    date=today,
                    reason=stock.get('reason', '策略买入')
                )
                if trade:
                    print(f"  买入 {symbol} {volume}股 @ ¥{price:.2f} = ¥{trade.amount:,.2f}")
                    buy_count += 1
            else:
                print(f"  ⚠️ {symbol} 资金不足 (需要¥{price*100:,.2f}, 可用¥{position_size:,.2f})")
    
    print(f"  完成：{buy_count} 笔买入")
    print()
    
    # 更新持仓价格
    account.update_positions({})
    
    # 生成快照
    account.create_snapshot(
        date=today,
        buy_count=buy_count,
        sell_count=sell_count
    )
    
    # 保存账户
    account._save_account()
    
    # 打印结果
    print("=" * 70)
    print("  交易完成")
    print("=" * 70)
    print(f"  买入：{buy_count} 笔")
    print(f"  卖出：{sell_count} 笔")
    print(f"  现金：¥{account.cash:,.2f}")
    print(f"  持仓：{len(account.positions)} 只")
    print()
    
    return buy_count, sell_count

if __name__ == '__main__':
    execute_today_trades()
