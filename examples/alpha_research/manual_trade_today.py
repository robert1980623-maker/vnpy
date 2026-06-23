#!/usr/bin/env python3
"""
手动执行今日交易

从当日交易计划读取并执行交易

迁移到 AccountService — 2026-06-23
"""

import json
from pathlib import Path
from datetime import datetime
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account


def _ensure_account(account_id: str, initial_capital: float):
    """确保 SQLite 中存在该账户"""
    db = AccountDB()
    if not db.get_account(account_id):
        acct = Account(
            account_id=account_id,
            account_name="虚拟账户",
            initial_capital=initial_capital,
            cash=initial_capital,
        )
        db.create_account(acct)


def execute_today_trades():
    print("=" * 70)
    print(" " * 20 + "手动执行今日交易")
    print("=" * 70)
    print()

    # 加载账户
    _ensure_account("virtual_2026", 1_000_000)
    account = AccountService("virtual_2026")
    balance = account.get_balance()
    positions = account.get_positions()
    print(f"✅ 加载账户：{account.account_id}")
    print(f"   现金：¥{balance.cash:,.2f}")
    print(f"   持仓：{len(positions)} 只")
    print()

    # 加载当日交易计划
    today = datetime.now().strftime('%Y-%m-%d')
    plan_file = Path(f'reports/trading_plan_{today}.json')

    if not plan_file.exists():
        # 查找最新的交易计划
        plan_files = sorted(Path('reports').glob('trading_plan_*.json'))
        if plan_files:
            plan_file = plan_files[-1]
            print(f"⚠️  今日交易计划不存在，使用最新：{plan_file.name}")
        else:
            print(f"❌ 无交易计划文件")
            return 0, 0

    with open(plan_file, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    print(f"✅ 加载交易计划：{plan_file.name}")
    print(f"   日期：{plan.get('date', 'N/A')}")
    print(f"   买入：{len(plan.get('buy', []))} 只")
    print(f"   卖出：{len(plan.get('sell', []))} 只")
    print()

    # 构建持仓字典
    pos_dict = {p.symbol: p for p in positions}

    # 执行卖出
    print("【执行卖出】")
    sell_count = 0
    for symbol in plan.get('sell', []):
        position = pos_dict.get(symbol)
        if position:
            current_price = position.current_price
            result = account.sell(
                symbol=symbol,
                price=current_price,
                quantity=position.quantity,
                reason="调仓卖出",
                source_module="manual_trade_today.py",
            )
            if result.success:
                print(f"  卖出 {symbol} {position.quantity}股 @ ¥{current_price:.2f}")
                sell_count += 1
        else:
            print(f"  ⚠️ {symbol} 不在持仓中")

    print(f"  完成：{sell_count} 笔卖出")
    print()

    # 执行买入
    print("【执行买入】")
    buy_count = 0
    buy_list = plan.get('buy', [])

    if buy_list:
        # 检查买入列表格式
        if isinstance(buy_list[0], str):
            print(f"⚠️ 交易计划为旧格式，跳过买入执行")
        else:
            # 重新读取现金
            balance = account.get_balance()
            available_cash = balance.cash * 0.9
            position_size = available_cash / len(buy_list) if buy_list else 0

            print(f"  可用现金：¥{available_cash:,.2f}")
            print(f"  每只股票：¥{position_size:,.2f}")
            print()

            for stock in buy_list:
                symbol = stock.get('symbol', '')
                price = stock.get('price', 10.0)
                reason = stock.get('reason', '策略买入')

                volume = int(position_size / price / 100) * 100 if price > 0 else 0

                if volume >= 100:
                    result = account.buy(
                        symbol=symbol,
                        name=stock.get('name', ''),
                        price=price,
                        quantity=volume,
                        reason=reason,
                        source_module="manual_trade_today.py",
                    )
                    if result.success:
                        print(f"  买入 {symbol} {volume}股 @ ¥{price:.2f} = ¥{price * volume:,.2f}")
                        buy_count += 1
                else:
                    print(f"  ⚠️ {symbol} 资金不足或价格无效")

    print(f"  完成：{buy_count} 笔买入")
    print()

    # 创建快照
    balance = account.get_balance()
    account.snapshot(trade_date=today.replace('-', ''))

    # 打印结果
    print("=" * 70)
    print("  交易完成")
    print("=" * 70)
    print(f"  买入：{buy_count} 笔")
    print(f"  卖出：{sell_count} 笔")
    balance = account.get_balance()
    positions = account.get_positions()
    print(f"  现金：¥{balance.cash:,.2f}")
    print(f"  持仓：{len(positions)} 只")
    print()

    return buy_count, sell_count

if __name__ == '__main__':
    execute_today_trades()
