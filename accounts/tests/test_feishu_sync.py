"""FeishuSyncService 测试"""
import pytest
from unittest.mock import patch, MagicMock

from accounts.feishu_sync import FeishuSyncService
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, get_connection, Account
from accounts.event_bus import EventBus, EventType, AccountEvent


TEST_ACCOUNT_ID = "test_feishu_sync_account"


class TestFeishuSyncBase:
    """测试基类"""

    def setup_method(self):
        self.db = AccountDB()
        self._cleanup()
        account = Account(
            account_id=TEST_ACCOUNT_ID,
            account_name="Test Feishu Sync Account",
            initial_capital=100_000.0,
            cash=100_000.0,
        )
        assert self.db.create_account(account)

    def teardown_method(self):
        self._cleanup()

    def _cleanup(self):
        try:
            conn = get_connection()
            conn.execute("DELETE FROM audit_log WHERE account_id = ?", (TEST_ACCOUNT_ID,))
            conn.execute("DELETE FROM trades WHERE account_id = ?", (TEST_ACCOUNT_ID,))
            conn.execute("DELETE FROM positions WHERE account_id = ?", (TEST_ACCOUNT_ID,))
            conn.execute("DELETE FROM daily_snapshots WHERE account_id = ?", (TEST_ACCOUNT_ID,))
            conn.execute("DELETE FROM accounts WHERE account_id = ?", (TEST_ACCOUNT_ID,))
            conn.commit()
            conn.close()
        except Exception:
            pass


class TestFeishuSyncSubscriptions(TestFeishuSyncBase):
    """事件订阅测试"""

    def test_subscribe_on_init(self):
        """初始化时订阅 TRADE_EXECUTED 和 SNAPSHOT_CREATED"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        # 验证: 2 个事件类型各有一个 handler
        trade_handlers = bus._handlers.get(EventType.TRADE_EXECUTED, [])
        snapshot_handlers = bus._handlers.get(EventType.SNAPSHOT_CREATED, [])

        assert sync._on_trade in trade_handlers
        assert sync._on_snapshot in snapshot_handlers

    def test_trade_event_triggers_sync(self):
        """TRADE_EXECUTED 事件触发同步"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)

        with patch.object(FeishuSyncService, "_sync_to_feishu") as mock_sync:
            sync = FeishuSyncService(svc, bus)

            # 买入 → 触发事件 → 触发同步
            svc.buy("000001.SZSE", "平安银行", 10.0, 100)

            assert mock_sync.called

    def test_snapshot_event_triggers_sync(self):
        """SNAPSHOT_CREATED 事件触发同步"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)

        with patch.object(FeishuSyncService, "_sync_to_feishu") as mock_sync:
            sync = FeishuSyncService(svc, bus)

            svc.snapshot(trade_date="20260623")

            assert mock_sync.called


class TestFeishuSyncFailureIsolation(TestFeishuSyncBase):
    """同步失败不传播测试"""

    def test_sync_failure_does_not_affect_trade(self):
        """飞书同步失败不影响交易"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        # Mock _sync_to_feishu 抛出异常
        with patch.object(sync, "_sync_to_feishu", side_effect=RuntimeError("API error")):
            result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # 交易成功
        assert result.success is True

        # 数据正确
        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 99_000.0
        assert len(svc.get_positions()) == 1

    def test_sync_failure_records_error(self):
        """同步失败记录错误信息"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        with patch.object(sync, "_sync_to_feishu", side_effect=RuntimeError("API error")):
            svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert sync.last_sync_error == "API error"

    def test_sync_success_clears_error(self):
        """同步成功后清除错误信息"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        # 先模拟失败
        with patch.object(sync, "_sync_to_feishu", side_effect=RuntimeError("API error")):
            svc.buy("000001.SZSE", "平安银行", 10.0, 100)
        assert sync.last_sync_error is not None

        # 再模拟成功
        with patch.object(sync, "_sync_to_feishu"):
            svc.sell("000001.SZSE", 12.0, 50)
        assert sync.last_sync_error is None


class TestFeishuSyncManual(TestFeishuSyncBase):
    """手动同步测试"""

    def test_sync_now_success(self):
        """sync_now 成功返回 True"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        result = sync.sync_now()
        assert result is True

    def test_sync_now_failure(self):
        """sync_now 失败返回 False"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        sync = FeishuSyncService(svc, bus)

        with patch.object(sync, "_sync_to_feishu", side_effect=RuntimeError("API error")):
            result = sync.sync_now()

        assert result is False
        assert sync.last_sync_error == "API error"
