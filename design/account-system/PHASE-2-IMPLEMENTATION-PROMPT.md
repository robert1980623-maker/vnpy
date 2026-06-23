实现账户系统 Phase 2 — AccountService 核心接口。

设计文档：design/account-system/PHASE-2-ARCHITECTURE.md

任务：
1. 创建 `accounts/account_service.py` — AccountService 类
   - buy() / sell() — SQLite 事务内原子操作
   - get_balance() — 统一余额计算
   - get_positions() — SQLite 唯一数据源
   - get_trade_history() — 交易记录查询
   - get_audit_log() — 审计日志查询
   - snapshot() — 每日快照
   - 每次 buy/sell 发布 EventBus 事件
   - 每次操作写入 audit_log

2. 创建 `accounts/feishu_sync.py` — FeishuSyncService 类
   - 订阅 EventBus 的 TRADE_EXECUTED / SNAPSHOT_CREATED 事件
   - 同步失败仅记录日志，不影响交易
   - 支持 sync_now() 手动触发

3. 创建测试：
   - `accounts/tests/test_account_service.py` — buy/sell 成功+失败、事务原子性、事件发布
   - `accounts/tests/test_feishu_sync.py` — 事件订阅、同步失败不传播

关键实现细节：
- buy: cash 扣减 + position upsert (重算 avg_cost) + trade 记录 + audit_log
- sell: cash 增加 + position 扣减 (清仓时 delete) + realized_pnl 计算 + trade + audit_log
- 事务使用 db.execute_in_transaction()，失败自动回滚
- 事件在事务提交后 emit
- trade_id 格式: T-{timestamp}-{random4}

验收标准：
- 所有 buy/sell 场景测试通过（成功/现金不足/持仓不足/清仓）
- 事务原子性测试（模拟中途失败，验证回滚）
- 事件发布测试
- pytest accounts/tests/ 全部通过
- 不影响现有代码

输出：
- 代码提交到 accounts/ 目录
- 报告输出到 design/account-system/PHASE-2-IMPLEMENTATION-REPORT.md
