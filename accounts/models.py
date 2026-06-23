"""账户系统统一数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    """交易方向枚举"""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    """交易状态枚举"""
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
        """成本基数 = 数量 * 平均成本"""
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