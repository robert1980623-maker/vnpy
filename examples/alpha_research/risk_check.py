#!/usr/bin/env python3
"""
持仓风险检查脚本
执行时间: 工作日 15:00

迁移到 AccountService — 2026-06-23
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account
from risk_analyzer import RiskAnalyzer


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
    print("开始执行持仓风险检查...")
    try:
        # 初始化账户
        _ensure_account("virtual_2026")
        account = AccountService("virtual_2026")

        # 执行风险检查
        risk_analyzer = RiskAnalyzer(account)
        risk_report = risk_analyzer.analyze_portfolio_risk()

        print(f"风险检查完成: {risk_report}")

    except Exception as e:
        print(f"风险检查失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
