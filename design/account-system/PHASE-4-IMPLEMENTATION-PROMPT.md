实现账户系统 Phase 4 — 清理旧代码。

任务：
1. 删除 examples/alpha_research/paper_trading.py 中的 PaperTradingAccount 类（已迁移到 AccountService）
2. 删除 examples/alpha_research/paper_trading_system.py 中的 PaperTradingAccount 类（已迁移）
3. 删除 examples/alpha_research/debug_virtual_account.py（已迁移）
4. 删除 examples/alpha_research/simulated_trading.py 中的自实现账户逻辑（已迁移）
5. 删除 examples/alpha_research/execute_stock_selection.py 中的自行计算 balance 逻辑（已迁移）
6. 清理 accounts/account_db.py 中不再使用的方法（如果有）
7. 更新 accounts/__init__.py 导出

验收标准：
- 删除的类/方法不再被任何模块引用
- pytest accounts/tests/ 全部通过
- pytest examples/alpha_research/tests/ 全部通过（如果有）
- 无功能回归

输出：
- 代码提交
- 报告输出到 design/account-system/PHASE-4-IMPLEMENTATION-REPORT.md
