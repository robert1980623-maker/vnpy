#!/usr/bin/env python3
"""
全面复盘归因脚本
执行时间: 工作日 20:00

迁移到 AccountService — 2026-06-23
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
            account_name="虚拟账户",
            initial_capital=initial_capital,
            cash=initial_capital,
        )
        db.create_account(acct)


def main():
    print("开始执行全面复盘归因...")
    try:
        # 初始化账户
        _ensure_account("virtual_2026")
        account = AccountService("virtual_2026")

        # 执行归因分析
        attribution = PerformanceAttribution(account)
        attribution_report = attribution.generate_comprehensive_report()

        print(f"全面复盘归因完成: {attribution_report}")

    except Exception as e:
        print(f"全面复盘归因失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
