#!/bin/bash
# 虚拟账户状态检查

ACCOUNT_FILE="./accounts/virtual_2026_account.json"
TODAY=$(date +%Y-%m-%d)

echo "======================================================================"
echo "                    虚拟账户状态"
echo "======================================================================"
echo "日期：$TODAY"
echo ""

if [ ! -f "$ACCOUNT_FILE" ]; then
    echo "❌ 账户文件不存在"
    exit 1
fi

python3 << PYTHON
import json
from datetime import datetime

with open('$ACCOUNT_FILE', 'r') as f:
    account = json.load(f)

print(f"账户 ID: {account['account_id']}")
print(f"初始资金：¥{account['initial_capital']:,.2f}")
print(f"当前现金：¥{account['cash']:,.2f}")
print(f"持仓数量：{len(account['positions'])} 只")
print()

total_market = sum(p['market_value'] for p in account['positions'])
total_value = account['cash'] + total_market
total_cost = sum(p['cost'] for p in account['positions'])
total_profit = total_market - total_cost
profit_rate = total_profit / total_cost * 100 if total_cost > 0 else 0

print(f"持仓市值：¥{total_market:,.2f}")
print(f"总资产：¥{total_value:,.2f}")
print(f"总盈亏：¥{total_profit:,.2f} ({profit_rate:+.2f}%)")
print()

if account.get('daily_snapshots'):
    last_snapshot = account['daily_snapshots'][-1]
    print(f"最后更新：{last_snapshot.get('date', 'N/A')}")
    print(f"当日收益：¥{last_snapshot.get('daily_return', 0):,.2f} ({last_snapshot.get('daily_return_rate', 0):+.2f}%)")
else:
    print("最后更新：无快照记录")

print()
print("=" * 70)
print("当前持仓:")
print("=" * 70)
print(f"{'代码':<12} {'名称':<10} {'股数':>8} {'成本':>10} {'现价':>10} {'市值':>12} {'盈亏':>10}")
print("-" * 70)

for pos in sorted(account['positions'], key=lambda x: x['market_value'], reverse=True):
    name = pos.get('name', '')[:10]
    print(f"{pos['symbol']:<12} {name:<10} {pos['volume']:>8} ¥{pos['avg_price']:>8.2f} ¥{pos['current_price']:>8.2f} ¥{pos['market_value']:>10,.0f} {pos['profit_rate']:>+8.2f}%")

print("=" * 70)
PYTHON

echo ""
echo "📁 相关文件:"
echo "  账户文件：$ACCOUNT_FILE"
echo "  今日选股：./reports/stock_selection_$TODAY.json"
echo "  交易计划：./reports/trading_plan_$TODAY.json"
echo "======================================================================"
