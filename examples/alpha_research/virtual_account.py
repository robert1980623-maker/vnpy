#!/usr/bin/env python3
"""
虚拟账户管理模块 — 向后兼容入口

@deprecated 请直接使用 AccountService：
    from accounts.account_service import AccountService
    account = AccountService("virtual_2026")

本模块将所有导入和类转发到 accounts.virtual_account_compat，
仅供旧代码过渡使用。新代码不应再 import 本模块。
"""

import warnings
import logging

logger = logging.getLogger(__name__)

warnings.warn(
    "virtual_account 模块已弃用，请使用 accounts.account_service.AccountService。"
    "详见 design/account-system/PHASE-3-ARCHITECTURE.md",
    DeprecationWarning,
    stacklevel=2,
)

# 转发所有导入到兼容层
from accounts.virtual_account_compat import VirtualAccount, Position  # noqa: F401, E402

# 常量保留（供旧代码使用）
VIRTUAL_ACCOUNT_ID = "virtual_2026"

__all__ = ["VirtualAccount", "Position", "VIRTUAL_ACCOUNT_ID"]


if __name__ == "__main__":
    # 测试
    account = VirtualAccount()
    logger.info(f"可用资金：¥{account.get_available_cash():,.2f}")
    logger.info(f"持仓：{len(account.get_positions())} 只")
    for pos in account.get_positions():
        logger.info(f"  {pos['symbol']}: {pos['quantity']}股 @ ¥{pos['avg_price']:.2f}")
