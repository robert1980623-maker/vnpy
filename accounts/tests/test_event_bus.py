"""账户系统事件总线测试"""
import pytest
from unittest.mock import Mock
from accounts.event_bus import EventBus, EventType, AccountEvent, trade_event


class TestEventTypeEnum:
    """测试事件类型枚举"""

    def test_event_type_values(self):
        """测试事件类型枚举值"""
        assert EventType.TRADE_EXECUTED.value == "trade_executed"
        assert EventType.BALANCE_CHANGED.value == "balance_changed"
        assert EventType.SNAPSHOT_CREATED.value == "snapshot_created"
        assert EventType.RISK_ALERT.value == "risk_alert"
        assert EventType.FEISHU_SYNC_REQUESTED.value == "feishu_sync"


class TestAccountEvent:
    """测试账户事件"""

    def test_account_event_creation(self):
        """测试账户事件创建"""
        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE", "quantity": 100}
        )

        assert event.type == EventType.TRADE_EXECUTED
        assert event.account_id == "A001"
        assert event.data["symbol"] == "000001.SZSE"
        assert event.data["quantity"] == 100

    def test_account_event_timestamp_auto_generation(self):
        """测试时间戳自动生成"""
        event = AccountEvent(
            type=EventType.BALANCE_CHANGED,
            account_id="A001"
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, str)

    def test_account_event_with_custom_timestamp(self):
        """测试自定义时间戳"""
        custom_ts = "2023-01-01T10:00:00"
        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            timestamp=custom_ts,
            data={}
        )

        assert event.timestamp == custom_ts


class TestEventBus:
    """测试事件总线"""

    def test_subscribe_and_emit(self):
        """测试订阅和发布事件"""
        bus = EventBus()
        mock_handler = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, mock_handler)

        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        bus.emit(event)

        mock_handler.assert_called_once_with(event)
        assert bus.handler_count == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()
        mock_handler = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, mock_handler)
        assert bus.handler_count == 1

        bus.unsubscribe(EventType.TRADE_EXECUTED, mock_handler)
        assert bus.handler_count == 0

        # 发布事件，handler 不应该被调用
        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        bus.emit(event)
        mock_handler.assert_not_called()

    def test_multiple_handlers_same_event_type(self):
        """测试同一事件类型的多个处理器"""
        bus = EventBus()
        mock_handler1 = Mock()
        mock_handler2 = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, mock_handler1)
        bus.subscribe(EventType.TRADE_EXECUTED, mock_handler2)

        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        bus.emit(event)

        mock_handler1.assert_called_once_with(event)
        mock_handler2.assert_called_once_with(event)
        assert bus.handler_count == 2

    def test_different_event_types(self):
        """测试不同事件类型"""
        bus = EventBus()
        mock_trade_handler = Mock()
        mock_balance_handler = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, mock_trade_handler)
        bus.subscribe(EventType.BALANCE_CHANGED, mock_balance_handler)

        trade_event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        balance_event = AccountEvent(
            type=EventType.BALANCE_CHANGED,
            account_id="A001",
            data={"cash": 10000.0}
        )

        bus.emit(trade_event)
        bus.emit(balance_event)

        mock_trade_handler.assert_called_once_with(trade_event)
        mock_balance_handler.assert_called_once_with(balance_event)

    def test_handler_exception_does_not_propagate(self):
        """测试处理器异常不会传播"""
        bus = EventBus()
        good_handler = Mock()
        bad_handler = Mock(side_effect=RuntimeError("Handler failed"))

        bus.subscribe(EventType.TRADE_EXECUTED, bad_handler)
        bus.subscribe(EventType.TRADE_EXECUTED, good_handler)

        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        # 发布事件不应该抛出异常
        bus.emit(event)

        # 好的处理器应该仍然被调用
        good_handler.assert_called_once_with(event)
        bad_handler.assert_called_once_with(event)

    def test_empty_event_bus(self):
        """测试空事件总线"""
        bus = EventBus()
        assert bus.handler_count == 0

        # 发布事件到空总线不应该出错
        event = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        bus.emit(event)  # 不应抛出异常

    def test_multiple_events_same_handler(self):
        """测试同一个处理器接收多个事件"""
        bus = EventBus()
        mock_handler = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, mock_handler)

        event1 = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A001",
            data={"symbol": "000001.SZSE"}
        )

        event2 = AccountEvent(
            type=EventType.TRADE_EXECUTED,
            account_id="A002",
            data={"symbol": "000002.SZSE"}
        )

        bus.emit(event1)
        bus.emit(event2)

        assert mock_handler.call_count == 2
        mock_handler.assert_any_call(event1)
        mock_handler.assert_any_call(event2)

    def test_handler_count_across_types(self):
        """测试跨类型处理器计数"""
        bus = EventBus()
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()

        bus.subscribe(EventType.TRADE_EXECUTED, handler1)
        bus.subscribe(EventType.BALANCE_CHANGED, handler2)
        bus.subscribe(EventType.TRADE_EXECUTED, handler3)

        assert bus.handler_count == 3


class TestTradeEventFactory:
    """测试交易事件工厂函数"""

    def test_trade_event_factory(self):
        """测试交易事件工厂函数"""
        event = trade_event(
            account_id="A001",
            symbol="000001.SZSE",
            direction="BUY",
            quantity=100,
            price=15.5,
            amount=1550.0,
            agent_id="algorithm"
        )

        assert event.type == EventType.TRADE_EXECUTED
        assert event.account_id == "A001"
        assert event.data["symbol"] == "000001.SZSE"
        assert event.data["direction"] == "BUY"
        assert event.data["quantity"] == 100
        assert event.data["price"] == 15.5
        assert event.data["amount"] == 1550.0
        assert event.data["agent_id"] == "algorithm"

    def test_trade_event_factory_defaults(self):
        """测试交易事件工厂函数默认值"""
        event = trade_event(
            account_id="A001",
            symbol="000001.SZSE",
            direction="SELL",
            quantity=200,
            price=20.0,
            amount=4000.0
        )

        assert event.data["agent_id"] == "system"  # 默认值
        assert event.account_id == "A001"