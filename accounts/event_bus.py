"""进程内事件总线

Phase 1: 同步进程内实现
未来可升级为 Redis Pub/Sub 或消息队列
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型枚举"""
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


# 便捷工厂函数
def trade_event(account_id: str, symbol: str, direction: str,
                quantity: int, price: float, amount: float,
                agent_id: str = "system") -> AccountEvent:
    """创建交易事件的便捷函数"""
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
                    f"Event handler failed: {getattr(handler, '__name__', repr(handler))} "
                    f"for {event.type.value}: {e}"
                )

    @property
    def handler_count(self) -> int:
        """返回注册的处理器总数"""
        return sum(len(h) for h in self._handlers.values())