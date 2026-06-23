#!/usr/bin/env python3
"""
执行选股结果迁移到虚拟账户

功能：
1. 读取今日选股结果和交易计划
2. 获取股票最新价格
3. 执行买入操作
4. 使用 AccountService 更新账户状态

迁移到 AccountService — 2026-06-23
"""

import json
from pathlib import Path
from datetime import datetime

# 账户系统 — Phase 3
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account

# 配置
TRADING_PLAN_FILE = './reports/trading_plan_2026-04-16.json'
DATA_DIR = Path('./data/akshare/bars')


def _ensure_account(account_id: str = "virtual_2026", initial_capital: float = 1_000_000):
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


def load_trading_plan():
    """加载交易计划"""
    with open(TRADING_PLAN_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_stock_price(symbol):
    """从数据文件获取股票最新价格"""
    symbol_file = symbol.replace('.', '_')
    csv_file = DATA_DIR / f'{symbol_file}.csv'

    if not csv_file.exists():
        for f in DATA_DIR.glob('*.csv'):
            if f.stem == symbol_file or f.stem.startswith(symbol.replace('.', '_').split('_')[0]):
                csv_file = f
                break

    if not csv_file.exists():
        return None

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None

            last_line = lines[-1].strip()
            parts = last_line.split(',')

            if len(parts) >= 5:
                return float(parts[4])
    except Exception as e:
        print(f"  ⚠️  读取价格失败 {symbol}: {e}")
        return None

    return None


def execute_buy_plan(account: AccountService, buy_list):
    """执行买入计划 — 使用 AccountService"""
    total_invested = 0
    executed_count = 0

    balance = account.get_balance()
    available_cash = balance.cash
    per_stock_amount = available_cash / len(buy_list) if buy_list else 0

    print(f"\n可用资金：¥{available_cash:,.2f}")
    print(f"计划买入：{len(buy_list)} 只")
    print(f"每只分配：¥{per_stock_amount:,.2f}")
    print("\n执行买入:")

    for stock in buy_list:
        symbol = stock['symbol']
        name = stock.get('name', '')
        reason = stock.get('reason', '选股策略')

        price = get_stock_price(symbol)
        if not price:
            pe = stock.get('pe', 15)
            price = 10.0
            print(f"  使用估算价格：{symbol} @ ¥{price:.2f}")

        quantity = int(per_stock_amount / price / 100) * 100

        if quantity < 100:
            quantity = 100

        cost = price * quantity

        # 检查资金
        balance = account.get_balance()
        if cost > balance.cash:
            quantity = int(balance.cash / price / 100) * 100
            if quantity < 100:
                print(f"  ⚠️  资金不足，跳过 {symbol}")
                continue
            cost = price * quantity

        # 通过 AccountService 执行买入
        result = account.buy(
            symbol=symbol,
            name=name,
            price=price,
            quantity=quantity,
            reason=f"{reason} (PE={stock.get('pe', 'N/A')}, ROE={stock.get('roe', 'N/A')}%)",
            source_module="execute_stock_selection.py",
        )

        if result.success:
            total_invested += cost
            executed_count += 1
            print(f"  ✓ {symbol}: {quantity}股 @ ¥{price:.2f} = ¥{cost:,.2f}")
        else:
            print(f"  ✗ {symbol}: {result.message}")

    print(f"\n执行完成：{executed_count}/{len(buy_list)} 只")
    print(f"总投资：¥{total_invested:,.2f}")

    balance = account.get_balance()
    print(f"剩余现金：¥{balance.cash:,.2f}")

    return executed_count, total_invested


def main():
    print("=" * 70)
    print(" " * 20 + "执行选股结果迁移")
    print("=" * 70)
    print(f"日期：2026-04-16")
    print(f"时间：{datetime.now().strftime('%H:%M:%S')}")

    # 加载交易计划
    print("\n【步骤 1】加载交易计划")
    plan = load_trading_plan()
    buy_list = plan.get('buy', [])
    print(f"  买入候选：{len(buy_list)} 只")

    if not buy_list:
        print("  ⚠️  无买入候选，结束")
        return

    # 初始化账户
    print("\n【步骤 2】加载虚拟账户 (AccountService)")
    _ensure_account("virtual_2026")
    account = AccountService("virtual_2026")

    balance = account.get_balance()
    positions = account.get_positions()
    print(f"  当前现金：¥{balance.cash:,.2f}")
    print(f"  当前持仓：{len(positions)} 只")

    # 执行买入
    print("\n【步骤 3】执行买入")
    executed, invested = execute_buy_plan(account, buy_list)

    if executed == 0:
        print("\n⚠️  无股票买入，结束")
        return

    # 创建快照
    print("\n【步骤 4】创建每日快照")
    account.snapshot(trade_date="20260416")

    # 打印最终状态
    balance = account.get_balance()
    positions = account.get_positions()
    print("\n" + "=" * 70)
    print(" " * 25 + "完成")
    print("=" * 70)
    print(f"最终状态:")
    print(f"  现金：¥{balance.cash:,.2f}")
    print(f"  持仓：{len(positions)} 只")
    print(f"  总资产：¥{balance.total_assets:,.2f}")
    print(f"\n持仓明细:")
    for p in positions:
        print(f"  - {p.symbol}: {p.quantity}股 @ ¥{p.avg_cost:.2f} (¥{p.market_value:,.2f})")


if __name__ == '__main__':
    main()
