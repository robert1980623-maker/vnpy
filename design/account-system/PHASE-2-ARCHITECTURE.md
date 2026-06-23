# Phase 2 架构设计 — AccountService 核心接口

> **设计日期**: 2026-06-23
> **依赖**: Phase 1 已完成 (models.py, event_bus.py, exceptions.py, account_db.py)
> **目标**: 实现账户系统统一入口，所有交易操作原子化

---

## 1. 设计目标

1. **统一入口** — 所有 buy/sell/get_balance 操作通过 AccountService
2. **事务保证** — cash + position 更新在同一 SQLite 事务内
3. **事件驱动** — 交易完成后发布事件，解耦飞书同步
4. **审计日志** — 每次操作记录到 audit_log 表
5. **并发安全** — 支持多进程读写（SQLite WAL 模式）

**不做**：
- ❌ 不迁移调用方（Phase 3）
- ❌ 不删除 VirtualAccount（Phase 4）

---

## 2. 文件清单

```
accounts/
├── account_service.py      # 🆕 统一入口 AccountService
├── feishu_sync.py          # 🆕 飞书输出同步服务
└── tests/
    ├── test_account_service.py    # 🆕 核心接口测试
    └── test_feishu_sync.py        # 🆕 飞书同步测试
```

---

## 3. AccountService 核心接口

```python
# accounts/account_service.py

from accounts.models import Balance, Position, Trade, Snapshot, TradeResult, Direction
from accounts.exceptions import InsufficientCashError, InsufficientPositionError
from accounts.event_bus import EventBus, EventType, trade_event
from accounts.account_db import AccountDB, get_connection


class AccountService:
    """账户系统统一入口

    设计原则:
    1. SQLite 唯一数据源 (Single Source of Truth)
    2. 所有 buy/sell 操作在事务内完成 (Atomic)
    3. 每次交易发布事件，解耦通知 (Event-Driven)
    4. 所有操作记录审计日志 (Auditable)
    """

    def __init__(self, account_id: str, event_bus: EventBus = None):
        self.db = AccountDB()
        self.account_id = account_id
        self.event_bus = event_bus or EventBus()

    # ── 交易操作 (事务保证) ─────────────────────────────

    def buy(self, symbol: str, name: str, price: float, quantity: int,
            reason: str = "", agent_id: str = "system",
            source_module: str = "") -> TradeResult:
        """买入 — cash 扣减 + position 更新 + trade 记录 原子完成

        事务流程:
        1. BEGIN TRANSACTION
        2. SELECT cash FROM accounts WHERE account_id = ? (FOR UPDATE)
        3. 检查 cash >= price * quantity
        4. UPDATE accounts SET cash = cash - amount
        5. INSERT OR REPLACE positions (quantity += N, avg_cost 重算)
        6. INSERT trades (trade_id, symbol, BUY, ...)
        7. INSERT audit_log (op=BUY, cash_before, cash_after, ...)
        8. COMMIT
        9. event_bus.emit(TradeEvent(...))

        Raises:
            InsufficientCashError: 现金不足
            AccountNotFoundError: 账户不存在
        """

    def sell(self, symbol: str, price: float, quantity: int,
             reason: str = "", agent_id: str = "system",
             source_module: str = "") -> TradeResult:
        """卖出 — cash 增加 + position 扣减 + trade 记录 原子完成

        事务流程:
        1. BEGIN TRANSACTION
        2. SELECT quantity FROM positions WHERE symbol = ?
        3. 检查 quantity >= sell_quantity
        4. 计算 realized_pnl = (price - avg_cost) * quantity
        5. UPDATE accounts SET cash = cash + amount
        6. UPDATE/DELETE positions (quantity -= N, 或 0 时删除)
        7. INSERT trades (trade_id, symbol, SELL, ...)
        8. INSERT audit_log (op=SELL, cash_before, cash_after, realized_pnl)
        9. COMMIT
        10. event_bus.emit(TradeEvent(...))

        Raises:
            InsufficientPositionError: 持仓不足
        """

    # ── 查询操作 (只读) ─────────────────────────────────

    def get_balance(self) -> Balance:
        """统一余额计算: cash + sum(quantity * current_price)

        current_price 从行情缓存获取，非持仓成本价
        如果无法获取实时价格，fallback 到 avg_cost
        """

    def get_positions(self) -> List[Position]:
        """从 SQLite 读取持仓，无 fallback 链"""

    def get_trade_history(self, start_date: str = None,
                          end_date: str = None) -> List[Trade]:
        """从 trades 表读取交易记录"""

    def get_audit_log(self, operation: str = None,
                      limit: int = 100) -> List[dict]:
        """从 audit_log 表读取操作记录"""

    # ── 快照操作 ─────────────────────────────────────────

    def snapshot(self, trade_date: str = None) -> Snapshot:
        """生成并保存每日快照

        1. 计算当前 balance
        2. 统计 positions_count, trades_count
        3. INSERT INTO daily_snapshots
        4. event_bus.emit(SNAPSHOT_CREATED)
        """

    # ── 辅助方法 ─────────────────────────────────────────

    def _generate_trade_id(self) -> str:
        """生成唯一 trade_id: T-{timestamp}-{random}"""

    def _get_current_price(self, symbol: str) -> float:
        """获取当前价格 (从行情缓存或 fallback 到 avg_cost)"""
```

---

## 4. 事务实现细节

### 4.1 buy() 事务

```python
def buy(self, symbol: str, name: str, price: float, quantity: int,
        reason: str = "", agent_id: str = "system",
        source_module: str = "") -> TradeResult:
    amount = price * quantity
    trade_id = self._generate_trade_id()

    def do_buy(conn):
        # 1. 读取当前 cash (FOR UPDATE 锁行)
        row = conn.execute(
            "SELECT cash FROM accounts WHERE account_id = ?",
            (self.account_id,)
        ).fetchone()
        if not row:
            raise AccountNotFoundError(self.account_id)
        cash_before = row[0]

        # 2. 检查现金
        if cash_before < amount:
            raise InsufficientCashError(amount, cash_before)

        cash_after = cash_before - amount

        # 3. 更新 cash
        conn.execute(
            "UPDATE accounts SET cash = ? WHERE account_id = ?",
            (cash_after, self.account_id)
        )

        # 4. 更新 position (upsert)
        pos_row = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE account_id = ? AND symbol = ?",
            (self.account_id, symbol)
        ).fetchone()

        if pos_row:
            old_qty, old_avg = pos_row
            new_qty = old_qty + quantity
            new_avg = (old_qty * old_avg + quantity * price) / new_qty
            conn.execute(
                """UPDATE positions
                   SET quantity = ?, avg_cost = ?, market_value = ?
                   WHERE account_id = ? AND symbol = ?""",
                (new_qty, new_avg, new_qty * price, self.account_id, symbol)
            )
            position_quantity = new_qty
        else:
            conn.execute(
                """INSERT INTO positions
                   (account_id, symbol, name, quantity, avg_cost, market_value)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.account_id, symbol, name, quantity, price, quantity * price)
            )
            position_quantity = quantity

        # 5. 记录 trade
        conn.execute(
            """INSERT INTO trades
               (trade_id, account_id, symbol, name, direction, quantity, price,
                amount, reason, agent_id, trade_date, trade_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), time('now'))""",
            (trade_id, self.account_id, symbol, name, 'BUY', quantity, price,
             amount, reason, agent_id)
        )

        # 6. 记录审计日志
        conn.execute(
            """INSERT INTO audit_log
               (account_id, operation, symbol, quantity, price, amount,
                cash_before, cash_after, agent_id, source_module, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.account_id, 'BUY', symbol, quantity, price, amount,
             cash_before, cash_after, agent_id, source_module,
             json.dumps({"reason": reason, "trade_id": trade_id}))
        )

        return cash_after, position_quantity

    # 执行事务
    try:
        cash_after, position_quantity = self.db.execute_in_transaction([do_buy])

        # 发布事件 (事务外)
        self.event_bus.emit(trade_event(
            account_id=self.account_id,
            symbol=symbol,
            direction="BUY",
            quantity=quantity,
            price=price,
            amount=amount,
            agent_id=agent_id
        ))

        return TradeResult(
            success=True,
            trade_id=trade_id,
            message=f"买入成功: {symbol} {quantity}@{price}",
            cash_after=cash_after,
            position_quantity=position_quantity
        )
    except (InsufficientCashError, AccountNotFoundError) as e:
        return TradeResult(success=False, message=str(e))
    except Exception as e:
        logger.error(f"Buy failed: {e}")
        return TradeResult(success=False, message=f"交易失败: {e}")
```

### 4.2 sell() 事务

```python
def sell(self, symbol: str, price: float, quantity: int,
         reason: str = "", agent_id: str = "system",
         source_module: str = "") -> TradeResult:
    amount = price * quantity
    trade_id = self._generate_trade_id()

    def do_sell(conn):
        # 1. 读取持仓
        pos_row = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE account_id = ? AND symbol = ?",
            (self.account_id, symbol)
        ).fetchone()
        if not pos_row:
            raise InsufficientPositionError(symbol, quantity, 0)

        pos_qty, avg_cost = pos_row
        if pos_qty < quantity:
            raise InsufficientPositionError(symbol, quantity, pos_qty)

        # 2. 计算 realized_pnl
        realized_pnl = (price - avg_cost) * quantity

        # 3. 读取当前 cash
        cash_row = conn.execute(
            "SELECT cash FROM accounts WHERE account_id = ?",
            (self.account_id,)
        ).fetchone()
        cash_before = cash_row[0]
        cash_after = cash_before + amount

        # 4. 更新 cash
        conn.execute(
            "UPDATE accounts SET cash = ? WHERE account_id = ?",
            (cash_after, self.account_id)
        )

        # 5. 更新 position
        new_qty = pos_qty - quantity
        if new_qty == 0:
            conn.execute(
                "DELETE FROM positions WHERE account_id = ? AND symbol = ?",
                (self.account_id, symbol)
            )
            position_quantity = 0
        else:
            conn.execute(
                """UPDATE positions
                   SET quantity = ?, market_value = ?
                   WHERE account_id = ? AND symbol = ?""",
                (new_qty, new_qty * price, self.account_id, symbol)
            )
            position_quantity = new_qty

        # 6. 记录 trade
        conn.execute(
            """INSERT INTO trades
               (trade_id, account_id, symbol, direction, quantity, price,
                amount, reason, agent_id, trade_date, trade_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), time('now'))""",
            (trade_id, self.account_id, symbol, 'SELL', quantity, price,
             amount, reason, agent_id)
        )

        # 7. 记录审计日志
        conn.execute(
            """INSERT INTO audit_log
               (account_id, operation, symbol, quantity, price, amount,
                cash_before, cash_after, agent_id, source_module, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.account_id, 'SELL', symbol, quantity, price, amount,
             cash_before, cash_after, agent_id, source_module,
             json.dumps({"reason": reason, "trade_id": trade_id,
                         "realized_pnl": realized_pnl}))
        )

        return cash_after, position_quantity, realized_pnl

    # 执行事务
    try:
        cash_after, position_quantity, realized_pnl = self.db.execute_in_transaction([do_sell])

        # 发布事件
        self.event_bus.emit(trade_event(
            account_id=self.account_id,
            symbol=symbol,
            direction="SELL",
            quantity=quantity,
            price=price,
            amount=amount,
            agent_id=agent_id
        ))

        return TradeResult(
            success=True,
            trade_id=trade_id,
            message=f"卖出成功: {symbol} {quantity}@{price}, 盈亏: {realized_pnl:.2f}",
            cash_after=cash_after,
            position_quantity=position_quantity
        )
    except InsufficientPositionError as e:
        return TradeResult(success=False, message=str(e))
    except Exception as e:
        logger.error(f"Sell failed: {e}")
        return TradeResult(success=False, message=f"交易失败: {e}")
```

---

## 5. 飞书同步服务

```python
# accounts/feishu_sync.py

from accounts.event_bus import EventBus, EventType, AccountEvent
from accounts.account_service import AccountService
import logging

logger = logging.getLogger(__name__)


class FeishuSyncService:
    """飞书输出同步服务

    设计原则:
    1. 只订阅事件，不参与交易读路径
    2. 同步失败仅记录日志，不影响交易
    3. 支持手动触发全量同步
    """

    def __init__(self, account_service: AccountService, event_bus: EventBus):
        self.service = account_service
        self.bus = event_bus

        # 订阅事件
        self.bus.subscribe(EventType.TRADE_EXECUTED, self._on_trade)
        self.bus.subscribe(EventType.SNAPSHOT_CREATED, self._on_snapshot)

    def _on_trade(self, event: AccountEvent):
        """交易事件 → 同步到飞书"""
        try:
            self._sync_to_feishu()
        except Exception as e:
            logger.error(f"飞书同步失败 (trade): {e}")

    def _on_snapshot(self, event: AccountEvent):
        """快照事件 → 同步到飞书"""
        try:
            self._sync_to_feishu()
        except Exception as e:
            logger.error(f"飞书同步失败 (snapshot): {e}")

    def _sync_to_feishu(self):
        """执行飞书同步

        1. 读取当前 balance + positions
        2. 调用飞书 API 更新多维表格
        3. 失败抛出异常，由调用方处理
        """
        balance = self.service.get_balance()
        positions = self.service.get_positions()

        # TODO: 调用飞书 API
        # 这部分逻辑从 virtual_account.py 的 sync_to_feishu() 迁移
        logger.info(f"飞书同步: cash={balance.cash}, positions={len(positions)}")

    def sync_now(self) -> bool:
        """手动触发同步"""
        try:
            self._sync_to_feishu()
            return True
        except Exception as e:
            logger.error(f"手动同步失败: {e}")
            return False
```

---

## 6. 测试要求

### 6.1 test_account_service.py

| 用例 | 验证点 |
|------|--------|
| buy 成功 | cash 扣减、position 增加、trade 记录、audit_log 记录 |
| buy 现金不足 | 抛 InsufficientCashError，数据不变 |
| buy 账户不存在 | 抛 AccountNotFoundError |
| sell 成功 | cash 增加、position 减少、realized_pnl 计算正确 |
| sell 持仓不足 | 抛 InsufficientPositionError |
| sell 清仓 | position 记录被删除 |
| get_balance | 计算正确（含浮盈/浮亏） |
| get_positions | 从 SQLite 读取，无 fallback |
| snapshot | 生成并保存到 daily_snapshots |
| 事务原子性 | buy 中途失败，cash 和 position 都回滚 |
| 事件发布 | buy/sell 后 EventBus 收到正确事件 |

### 6.2 test_feishu_sync.py

| 用例 | 验证点 |
|------|--------|
| 订阅事件 | TRADE_EXECUTED 触发同步 |
| 同步失败不传播 | 飞书 API 失败，交易仍成功 |
| 手动同步 | sync_now() 返回 bool |

---

## 7. 验收标准

Phase 2 完成条件：

- [ ] `accounts/account_service.py` — AccountService 类，buy/sell/get_balance/snapshot
- [ ] `accounts/feishu_sync.py` — FeishuSyncService 类
- [ ] 事务保证：buy/sell 在 SQLite 事务内完成
- [ ] 事件发布：交易后 EventBus.emit()
- [ ] 审计日志：每次操作写入 audit_log
- [ ] 测试覆盖：buy/sell 成功 + 失败场景
- [ ] 不影响现有代码（无 import 变更）

---

## 8. 与后续 Phase 的关系

```
Phase 1 ✅          Phase 2 (本设计)        Phase 3
──────────          ──────────────          ──────────────
models.py     ───→  AccountService    ───→  调用方迁移
event_bus.py  ───→  FeishuSyncService ───→  调用方迁移
exceptions.py ───→  AccountService    ───→  调用方迁移
db.transaction ───→ buy/sell 原子操作  ───→  调用方迁移
```

Phase 2 完成后，Phase 3 将逐步迁移调用方：
- daily_trading.py → AccountService.buy/sell
- risk_check.py → AccountService.get_balance
- generate_reports.py → AccountService.get_balance + snapshot
