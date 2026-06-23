#!/usr/bin/env python3
"""
每日持仓盈亏自动更新

功能：
- 获取最新市场价格
- 更新持仓盈亏
- 生成每日快照
- 发送通知（可选）

迁移到 AccountService — 2026-06-23
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import tushare as ts

# 初始化 Tushare
ts.set_token('612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5')
pro = ts.pro_api()

# 账户系统 — Phase 3
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account


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


def update_portfolio():
    """更新持仓盈亏"""
    print("=" * 80)
    print(" " * 25 + "📊 每日持仓更新")
    print("=" * 80)
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 加载账户
    _ensure_account("virtual_2026")
    account = AccountService("virtual_2026")

    # 获取最新价格并更新
    print("【更新持仓价格】")
    print("-" * 80)

    positions = account.get_positions()
    balance = account.get_balance()

    for pos in positions:
        print(f"  {pos.name} ({pos.symbol})")
        print(f"    现价：¥{pos.current_price:.2f}")
        print(f"    盈亏：¥{pos.unrealized_pnl:,.2f} ({(pos.current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0:+.2f}%)")
        print()

    # 创建快照
    print("【创建账户快照】")
    print("-" * 80)

    today = datetime.now().strftime('%Y%m%d')
    snapshot = account.snapshot(trade_date=today)

    print(f"  日期：{snapshot.trade_date}")
    print(f"  总资产：¥{snapshot.total_assets:,.2f}")
    print(f"  已实现盈亏：¥{snapshot.realized_pnl:,.2f}")
    print()

    # 保存汇总
    summary = {
        'total_value': balance.total_assets,
        'cash': balance.cash,
        'position_value': balance.market_value,
        'total_profit': balance.realized_pnl + balance.unrealized_pnl,
        'total_return_pct': (
            (balance.total_assets - 1_000_000) / 1_000_000 * 100
            if 1_000_000 > 0 else 0
        ),
        'position_count': len(positions),
    }

    output_dir = Path('paper_trading_demo')
    output_dir.mkdir(exist_ok=True)

    # 保存每日快照
    snapshot_file = output_dir / f'snapshot_{today}.json'
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 更新最新汇总
    latest_file = output_dir / 'portfolio_summary.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ 快照已保存：{snapshot_file}")
    print(f"✅ 汇总已更新：{latest_file}")
    print()

    # 打印简报
    print("【今日简报】")
    print("-" * 80)
    print(f"  总资产：    ¥{summary['total_value']:>14,.2f}")
    print(f"  可用现金：  ¥{summary['cash']:>14,.2f}")
    print(f"  持仓市值：  ¥{summary['position_value']:>14,.2f}")
    print(f"  累计盈亏：  ¥{summary['total_profit']:>14,.2f}")
    print(f"  累计收益率：{summary['total_return_pct']:>+13.2f}%")
    print(f"  持仓数量：  {summary['position_count']:>14} 只")
    print()

    return summary


def main():
    """主函数"""
    try:
        summary = update_portfolio()
        print("=" * 80)
        print("✅ 持仓更新完成！")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"❌ 更新失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
