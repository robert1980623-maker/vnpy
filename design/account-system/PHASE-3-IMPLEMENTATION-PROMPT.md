实现账户系统 Phase 3 — 调用方迁移。

设计文档：design/account-system/PHASE-3-ARCHITECTURE.md

任务：
1. Batch 1 (P0) — 核心交易模块
   - daily_trading.py — import + 类名 + source_module
   - daily_trading_fixed.py — import + 类名 + source_module
   - manual_trade_today.py — import + 类名 + source_module
   - execute_trading.py — 删除 FeishuVirtualAccount，改用 AccountService + FeishuSyncService

2. Batch 2 (P1) — 风控/报表模块
   - risk_check.py — import + 类名
   - generate_reports.py — import + 类名
   - comprehensive_attribution.py — import + 类名
   - performance_attribution.py — import + 类名
   - realtime_monitor.py — 删除自行计算，改用 get_balance()
   - rebalance_portfolio.py — 删除自行计算，改用 get_balance()

3. Batch 3 (P2) — 策略/模拟模块
   - limit_up_strategy_runner.py — import + 类名
   - limit_up_leaders_20260415.py — import + 类名
   - limit_up_leaders_20260416.py — import + 类名
   - daily_portfolio_update.py — import + 类名
   - paper_trading_demo.py — import + 类名
   - main.py — import + 类名
   - advanced_trading_features.py — import + 类名
   - simulated_trading.py — 删除自实现，改用 AccountService
   - execute_stock_selection.py — 删除自行计算，改用 get_balance()
   - debug_virtual_account.py — import + 类名

4. 兼容层
   - 创建 accounts/virtual_account_compat.py — VirtualAccount 转发到 AccountService
   - 更新 examples/alpha_research/virtual_account.py — 导入兼容层

迁移模式：
- 只读模块：`from accounts.account_service import AccountService` + `AccountService("virtual_2026")`
- 交易模块：同上 + 添加 `source_module="xxx.py"` 参数
- 自实现模块：删除自实现代码，改用 AccountService

验收标准：
- 所有 20 个调用方迁移完成
- VirtualAccount 保留为兼容层（@deprecated）
- pytest accounts/tests/ 全部通过
- 无功能回归

输出：
- 代码提交到 examples/alpha_research/ 和 accounts/
- 报告输出到 design/account-system/PHASE-3-IMPLEMENTATION-REPORT.md
