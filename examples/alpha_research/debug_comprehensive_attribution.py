#!/usr/bin/env python3
"""
调试全面复盘归因脚本

迁移到 AccountService — 2026-06-23
使用 AccountService 替代 DebugVirtualAccount
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_attribution import PerformanceAttribution
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account


def _ensure_account(account_id: str = "virtual_2026", initial_capital: float = 1_000_000):
    """确保 SQLite 中存在该账户"""
    db = AccountDB()
    if not db.get_account(account_id):
        acct = Account(
            account_id=account_id,
            account_name="调试虚拟账户",
            initial_capital=initial_capital,
            cash=initial_capital,
        )
        db.create_account(acct)


def main():
    print("开始执行调试版全面复盘归因...")
    try:
        # 确保账户存在
        _ensure_account("virtual_2026")
        # 使用 AccountService
        account = AccountService("virtual_2026")

        # 执行归因分析
        attribution = PerformanceAttribution(account)
        attribution_report = attribution.generate_comprehensive_report()

        print(f"调试版全面复盘归因完成!")

    except Exception as e:
        import traceback
        print(f"调试版全面复盘归因失败: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()