# Phase 1 架构设计 — 账户系统基础设施

> **设计日期**: 2026-06-23
> **调研报告**: `design/account-system/RESEARCH-REPORT.md`
> **目标**: 建立统一账户服务的基础设施层，为 Phase 2-4 迁移铺路

---

## 1. 设计目标

Phase 1 **不改变任何现有调用方**，只新增基础设施：

1. **统一数据模型** — `Balance`, `Position`, `Trade`, `Snapshot`
2. **事务保证** — `account_db.py` 支持原子操作
3. **事件总线** — 进程内发布/订阅，解耦通知
4. **审计日志** — `audit_log` 表，记录所有账户操作
5. **统一异常** — 明确的错误类型

**不做**：
- ❌ 不迁移调用方（Phase 3）
- ❌ 不删除 VirtualAccount / PaperTradingAccount（Phase 4）
- ❌ 不改变飞书同步逻辑（Phase 2）

---

## 2. 文件清单

```
accounts/
├── __init__.py              # 导出公共接口
├── schema.sql               # 现有 + 新增 audit_log 表
├── account_db.py            # 现有 + 增强事务支持
├── models.py                # 🆕 统一数据模型
├── event_bus.py             # 🆕 事件总线
├── exceptions.py            # 🆕 统一异常
└── tests/
    ├── test_models.py
    ├── test_event_bus.py
    └── test_account_db_transaction.py
```

---

## 3. 数据模型 (`accounts/models.py`)

```python
"""账户系统统一数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Balance:
    """账户余额快照"""
    cash: float
    market_value: float       # sum(quantity * current_price)
    total_assets: float       # cash + market_value
    unrealized_pnl: float     # sum((current_price - avg_cost) * quantity)
    realized_pnl: float       # 已实现盈亏（累计）
    updated_at: str           # ISO 8601


@dataclass(frozen=True)
class Position:
    """持仓"""
    symbol: str
    name: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    account_id: str
    symbol: str
    name: str
    direction: Direction
    quantity: int
    price: float
    amount: float             # quantity * price
    commission: float = 0.0
    trade_date: str = ""      # YYYY-MM-DD
    trade_time: str = ""      # HH:MM:SS
    order_id: str = ""
    status: TradeStatus = TradeStatus.FILLED
    agent_id: str = "system"  # 操作来源
    reason: str = ""          # 操作原因
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Snapshot:
    """每日快照"""
    account_id: str
    trade_date: str
    cash: float
    market_value: float
    total_assets: float
    realized_pnl: float
    unrealized_pnl: float
    positions_count: int
    trades_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TradeResult:
    """交易操作结果"""
    success: bool
    trade_id: str = ""
    message: str = ""
    cash_after: float = 0.0
    position_quantity: int = 0
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| `Balance` / `Position` 用 `frozen=True` | ✅ | 只读快照，防止意外修改 |
| `Trade` 不用 frozen | ❌ | 创建后可能需要更新 status |
| `Direction` 用 str Enum | ✅ | JSON 序列化友好，DB 存储直观 |
| `amount = quantity * price` | 显式字段 | 避免重复计算，审计需要精确值 |

---

## 4. 异常定义 (`accounts/exceptions.py`)

```python
"""账户系统统一异常"""


class AccountError(Exception):
    """账户系统基础异常"""
    pass


class InsufficientCashError(AccountError):
    """现金不足"""
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(
            f"现金不足: 需要 {required:.2f}, 可用 {available:.2f}"
        )


class InsufficientPositionError(AccountError):
    """持仓不足"""
    def __init__(self, symbol: str, required: int, available: int):
        self.symbol = symbol
        self.required = required
        self.available = available
        super().__init__(
            f"持仓不足 [{symbol}]: 需要 {required}, 可用 {available}"
        )


class AccountNotFoundError(AccountError):
    """账户不存在"""
    def __init__(self, account_id: str):
        self.account_id = account_id
        super().__init__(f"账户不存在: {account_id}")


class DuplicateTradeError(AccountError):
    """重复交易 ID"""
    pass


class TransactionError(AccountError):
    """事务执行失败（自动回滚）"""
    pass
```

---

## 5. 事件总线 (`accounts/event_bus.py`)

```python
"""进程内事件总线

Phase 1: 同步进程内实现
未来可升级为 Redis Pub/Sub 或消息队列
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    TRADE_EXECUTED = "trade_executed"
    BALANCE_CHANGED = "balance_changed"
    SNAPSHOT_CREATED = "snapshot_created"
    RISK_ALERT = "risk_alert"
    FEISHU_SYNC_REQUESTED = "feishu_sync"


@dataclass
class AccountEvent:
    """账户事件基类"""
    type: EventType
    account_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)


# 便捷工厂
def trade_event(account_id: str, symbol: str, direction: str,
                quantity: int, price: float, amount: float,
                agent_id: str = "system") -> AccountEvent:
    return AccountEvent(
        type=EventType.TRADE_EXECUTED,
        account_id=account_id,
        data={
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "agent_id": agent_id,
        }
    )


class EventBus:
    """进程内事件总线

    用法:
        bus = EventBus()
        bus.subscribe(EventType.TRADE_EXECUTED, my_handler)
        bus.emit(event)

    设计原则:
    1. Handler 异常不传播（记录日志，继续执行其他 handler）
    2. emit 是同步的（Phase 1），未来可改为 async
    3. 支持通配符订阅（可选，Phase 2 再加）
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """订阅事件"""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """取消订阅"""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: AccountEvent) -> None:
        """发布事件"""
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Event handler failed: {handler.__name__} "
                    f"for {event.type.value}: {e}"
                )

    @property
    def handler_count(self) -> int:
        return sum(len(h) for h in self._handlers.values())
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 同步 emit | ✅ Phase 1 | 单进程 cron 场景，不需要 async |
| Handler 异常吞掉 | ✅ | 飞书同步失败不应影响交易 |
| 不用 asyncio | ✅ | 当前无并发需求，保持简单 |
| 通配符订阅 | ❌ Phase 1 | 无明确需求，YAGNI |

---

## 6. Schema 扩展 (`accounts/schema.sql` 增量)

```sql
-- 🆕 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    operation       TEXT NOT NULL,  -- BUY, SELL, SYNC, SNAPSHOT, ADJUST, MANUAL
    symbol          TEXT,
    quantity        REAL,
    price           REAL,
    amount          REAL,
    cash_before     REAL,
    cash_after      REAL,
    agent_id        TEXT DEFAULT 'system',
    source_module   TEXT,           -- 调用方模块名 (e.g. "daily_trading.py")
    details         TEXT,           -- JSON 扩展字段
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_account_date
    ON audit_log(account_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_operation
    ON audit_log(account_id, operation);
```

### 字段说明

| 字段 | 用途 | 示例 |
|------|------|------|
| `operation` | 操作类型 | `BUY`, `SELL`, `SYNC`, `SNAPSHOT`, `ADJUST`, `MANUAL` |
| `source_module` | 哪个模块发起的 | `daily_trading.py`, `manual_trade_today.py` |
| `cash_before/after` | 操作前后现金 | 用于审计和调试 |
| `details` | JSON 扩展 | `{"reason": "止损", "strategy": "limit_up"}` |

---

## 7. account_db.py 事务增强

在现有 `AccountDB` 类中新增事务支持：

```python
def execute_in_transaction(self, operations: List[Callable]) -> bool:
    """在单个事务内执行多个数据库操作

    Args:
        operations: 接收 conn 的 callable 列表

    Returns:
        True 如果全部成功, False 如果回滚

    用法:
        def update_cash(conn):
            conn.execute("UPDATE accounts SET cash = ? WHERE account_id = ?",
                        (new_cash, account_id))

        def update_position(conn):
            conn.execute("INSERT OR REPLACE INTO positions ...")

        db.execute_in_transaction([update_cash, update_position])
    """
    conn = get_connection()
    try:
        for op in operations:
            op(conn)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed, rolled back: {e}")
        return False
    finally:
        conn.close()
```

### 关键约束

1. **SQLite WAL 模式** — 已在 `get_connection()` 中启用
2. **busy_timeout = 30s** — 已配置，应对并发读
3. **每个 operation 不自己 commit** — 由 `execute_in_transaction` 统一控制
4. **异常自动回滚** — 任何 operation 抛异常，全部回滚

---

## 8. 测试要求

### 8.1 `test_models.py`

| 用例 | 验证点 |
|------|--------|
| Balance 不可变 | `frozen=True`, 修改属性抛 `FrozenInstanceError` |
| Position.cost_basis | `quantity * avg_cost` 计算正确 |
| Direction 序列化 | `Direction.BUY.value == "BUY"` |
| TradeResult 默认值 | `success=False` 时其他字段有合理默认 |

### 8.2 `test_event_bus.py`

| 用例 | 验证点 |
|------|--------|
| subscribe + emit | handler 被调用，收到正确 event |
| handler 异常不传播 | 一个 handler 抛异常，其他 handler 仍执行 |
| unsubscribe | 取消后不再收到事件 |
| 多事件类型 | 不同类型的事件路由到不同 handler |
| handler_count | 统计正确 |

### 8.3 `test_account_db_transaction.py`

| 用例 | 验证点 |
|------|--------|
| 全部成功 | 3 个 operation 都执行，数据一致 |
| 中间失败回滚 | 第 2 个 operation 抛异常，第 1 个的数据被回滚 |
| 并发安全 | 两个线程同时 `execute_in_transaction`，不丢数据 |
| 空操作列表 | 返回 True，无副作用 |

---

## 9. 验收标准

Phase 1 完成条件：

- [ ] `accounts/models.py` — 5 个 dataclass + 2 个 enum，全部有 docstring
- [ ] `accounts/exceptions.py` — 5 个异常类，继承 `AccountError`
- [ ] `accounts/event_bus.py` — EventBus + EventType + AccountEvent，通过 5 个测试
- [ ] `accounts/schema.sql` — 新增 `audit_log` 表 + 2 个索引
- [ ] `accounts/account_db.py` — 新增 `execute_in_transaction()` 方法
- [ ] 测试覆盖率 ≥ 90%（models / event_bus / transaction）
- [ ] 所有测试通过 `pytest accounts/tests/`
- [ ] 不影响现有代码（无 import 变更）

---

## 10. 与后续 Phase 的关系

```
Phase 1 (本设计)          Phase 2                 Phase 3
─────────────────        ──────────────          ──────────────
models.py          ───→  AccountService    ───→  调用方迁移
event_bus.py       ───→  AccountService    ───→  调用方迁移
exceptions.py      ───→  AccountService    ───→  调用方迁移
schema.sql +audit  ───→  AccountService    ───→  调用方迁移
db.transaction()   ───→  buy/sell 原子操作  ───→  调用方迁移
```

Phase 1 的每个文件都是 Phase 2 的依赖。设计时已考虑向后兼容：
- `models.py` 的 dataclass 直接作为 AccountService 的返回类型
- `EventBus` 被 AccountService 持有，buy/sell 后 emit 事件
- `audit_log` 表在 buy/sell 事务中写入
- `execute_in_transaction` 是 buy/sell 原子性的基础
