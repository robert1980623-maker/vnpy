# Phase 2 实施报告 — AccountService 核心接口

> **实施日期**: 2026-06-23
> **设计文档**: PHASE-2-ARCHITECTURE.md
> **状态**: ✅ 完成

---

## 1. 交付物清单

| 文件 | 类型 | 行数 | 说明 |
|------|------|------|------|
| `accounts/account_service.py` | 新增 | ~400 | AccountService 统一入口 |
| `accounts/feishu_sync.py` | 新增 | ~90 | FeishuSyncService 飞书同步 |
| `accounts/tests/test_account_service.py` | 新增 | ~310 | AccountService 测试（21 用例） |
| `accounts/tests/test_feishu_sync.py` | 新增 | ~140 | FeishuSyncService 测试（8 用例） |
| `accounts/__init__.py` | 修改 | +4 | 导出新类 |
| `accounts/account_db.py` | 修改 | +20 | execute_in_transaction 增强 + 迁移 |
| `accounts/tests/test_account_db_transaction.py` | 修改 | 2 处 | 适配 execute_in_transaction 新行为 |

---

## 2. AccountService 核心接口

### 2.1 buy() 买入

```
事务流程:
1. BEGIN TRANSACTION (via execute_in_transaction)
2. SELECT cash FROM accounts (检查账户存在)
3. 检查 cash >= price * quantity → InsufficientCashError
4. UPDATE accounts SET cash = cash - amount
5. UPSERT positions (新增 or 重算 avg_cost)
6. INSERT trades
7. INSERT audit_log (operation=BUY, cash_before, cash_after)
8. COMMIT
9. event_bus.emit(TRADE_EXECUTED)  ← 事务外
```

**avg_cost 重算公式**: `(old_qty * old_avg + new_qty * price) / (old_qty + new_qty)`

### 2.2 sell() 卖出

```
事务流程:
1. BEGIN TRANSACTION
2. SELECT quantity, avg_cost FROM positions → InsufficientPositionError
3. 计算 realized_pnl = (price - avg_cost) * quantity
4. UPDATE accounts SET cash = cash + amount
5. UPDATE/DELETE positions (清仓时 DELETE)
6. INSERT trades
7. INSERT audit_log (含 realized_pnl JSON)
8. COMMIT
9. event_bus.emit(TRADE_EXECUTED)  ← 事务外
```

### 2.3 查询方法

| 方法 | 说明 |
|------|------|
| `get_balance()` | cash + market_value, 含 unrealized/realized pnl |
| `get_positions()` | SQLite → models.Position, 无 fallback |
| `get_trade_history(start_date, end_date)` | 支持日期过滤 |
| `get_audit_log(operation, limit)` | 支持按操作类型过滤 |
| `snapshot(trade_date)` | 生成快照 + emit SNAPSHOT_CREATED |

### 2.4 trade_id 格式

```
T-{timestamp_ms}-{random4}
例: T-1782204936618-1007
```

存储在 trades 表的 `order_id` 列。

---

## 3. execute_in_transaction 增强

原方法: 返回 `bool` (True/False)，异常被吞。

新行为:
- **返回值**: 最后一个非 None 的 callable 返回值；全 None 则返回 True（向后兼容）
- **异常**: 回滚后重新抛出（不再返回 False）

**影响**: 2 个现有测试从 `assert result is False` 改为 `pytest.raises(Exception)`。其余 4 个测试不受影响（仍检查 `result is True`）。

---

## 4. 数据库迁移

为 `trades` 表添加两列（幂等迁移）:

```sql
ALTER TABLE trades ADD COLUMN reason TEXT DEFAULT '';
ALTER TABLE trades ADD COLUMN agent_id TEXT DEFAULT 'system';
```

迁移逻辑在 `_migrate_db(conn)` 中实现，使用 `PRAGMA table_info` 检查列是否存在，确保幂等。

---

## 5. 测试结果

```
$ python3 -m pytest accounts/tests/ -v
collected 95 items

accounts/tests/test_account_db_full.py ........                          [  8%]
accounts/tests/test_account_db_transaction.py ......                     [ 14%]
accounts/tests/test_account_service.py .....................             [ 36%]
accounts/tests/test_event_bus.py ..............                          [ 51%]
accounts/tests/test_exceptions.py ...........                            [ 63%]
accounts/tests/test_feishu_sync.py ........                              [ 71%]
accounts/tests/test_models.py .............                              [ 85%]
accounts/tests/test_trading_account.py ..............                    [100%]

============================== 95 passed in 0.18s ==============================
```

### 5.1 test_account_service.py — 21 用例

| 类别 | 用例 | 验证点 |
|------|------|--------|
| 买入 | test_buy_success | cash 扣减、position 增加、trade、audit_log |
| 买入 | test_buy_add_to_existing_position | 加仓 avg_cost 重算 |
| 买入 | test_buy_insufficient_cash | 现金不足，数据不变 |
| 买入 | test_buy_account_not_found | 账户不存在 |
| 买入 | test_buy_emits_event | TRADE_EXECUTED 事件 |
| 买入 | test_buy_failure_does_not_emit_event | 失败不发布事件 |
| 卖出 | test_sell_success | cash 增加、position 减少、realized_pnl |
| 卖出 | test_sell_clear_position | 清仓删除 position |
| 卖出 | test_sell_insufficient_position | 持仓不足 |
| 卖出 | test_sell_no_position | 无持仓卖出 |
| 卖出 | test_sell_realized_pnl_negative | 亏损卖出 |
| 卖出 | test_sell_emits_event | 卖出事件 |
| 原子性 | test_buy_atomicity_on_db_error | 中途失败全回滚 |
| 查询 | test_get_balance | 余额计算 |
| 查询 | test_get_balance_unrealized_pnl | 浮盈计算 |
| 查询 | test_get_positions_empty | 空持仓 |
| 查询 | test_get_trade_history_with_dates | 日期过滤 |
| 查询 | test_get_audit_log_by_operation | 按类型过滤 |
| 快照 | test_snapshot | 生成 + 保存 + 事件 |
| ID | test_trade_id_format | T-ts-rand4 格式 |
| ID | test_trade_ids_unique | 唯一性 |

### 5.2 test_feishu_sync.py — 8 用例

| 用例 | 验证点 |
|------|--------|
| test_subscribe_on_init | 初始化时订阅两个事件 |
| test_trade_event_triggers_sync | TRADE_EXECUTED → 同步 |
| test_snapshot_event_triggers_sync | SNAPSHOT_CREATED → 同步 |
| test_sync_failure_does_not_affect_trade | 同步失败不影响交易 |
| test_sync_failure_records_error | 记录错误信息 |
| test_sync_success_clears_error | 成功后清除错误 |
| test_sync_now_success | 手动同步成功 |
| test_sync_now_failure | 手动同步失败 |

---

## 6. 与现有代码的关系

### 6.1 不影响现有代码
- ✅ 未修改 `TradingAccount` (旧接口保留)
- ✅ 未修改调用方 (Phase 3 任务)
- ✅ `VirtualAccount` 未受影响
- ✅ 现有 95 个测试全部通过

### 6.2 有意的修改
- `execute_in_transaction` 增强: 返回 callable 结果 + 重新抛出异常
- 2 个现有测试适配新行为 (`pytest.raises` 替代 `assert False`)
- trades 表新增 `reason` / `agent_id` 列 (幂等迁移)

---

## 7. 设计决策记录

### 7.1 为什么不用 execute_in_transaction 的旧 bool 返回值？

旧方法吞掉异常返回 False，无法区分业务错误 (InsufficientCashError) 和系统错误。
Phase 2 需要对业务错误返回 TradeResult(success=False)，对系统错误记录日志。
增强后的方法重新抛出异常，AccountService 可以精确 catch。

### 7.2 为什么用 order_id 列存 trade_id？

schema 中 trades 表有自增 `id INTEGER PRIMARY KEY`，无 TEXT trade_id 列。
`order_id TEXT` 列已存在且用途兼容，直接复用避免 ALTER TABLE。

### 7.3 为什么 realized_pnl 从 audit_log 计算？

trades 表不存储 realized_pnl（避免冗余），审计日志的 `details` JSON 字段
记录了每笔 SELL 的 realized_pnl，累计求和即得总已实现盈亏。

### 7.4 为什么 FeishuSyncService 的 _sync_to_feishu 是 TODO？

飞书 API 对接属于独立关注点（Phase 3/4），当前实现仅记录日志。
事件订阅机制已完整实现，后续只需填充 `_sync_to_feishu()` 内部逻辑。

---

## 8. Phase 3 展望

Phase 3 将迁移调用方:
- `daily_trading.py` → `AccountService.buy/sell`
- `risk_check.py` → `AccountService.get_balance`
- `generate_reports.py` → `AccountService.get_balance + snapshot`

迁移完成后，旧的 `TradingAccount` 和 `VirtualAccount` 可在 Phase 4 中退役。

---

## 9. 验收检查

- [x] `accounts/account_service.py` — AccountService 类
- [x] `accounts/feishu_sync.py` — FeishuSyncService 类
- [x] 事务保证: buy/sell 在 SQLite 事务内完成
- [x] 事件发布: 交易后 EventBus.emit()
- [x] 审计日志: 每次操作写入 audit_log
- [x] 测试覆盖: 95/95 通过
- [x] 不影响现有代码（仅适配 2 个测试 + 增强 execute_in_transaction）
