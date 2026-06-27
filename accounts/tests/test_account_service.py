"""AccountService 核心接口测试"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from accounts.account_service import AccountService
from accounts.account_db import AccountDB, get_connection, Account
from accounts.event_bus import EventBus, EventType
from accounts.exceptions import (
    InsufficientCashError,
    InsufficientPositionError,
    AccountNotFoundError,
)
from accounts.models import TradeResult


TEST_ACCOUNT_ID = "test_service_account"


class TestAccountServiceBase:
    """测试基类：提供 setup/teardown"""

    def setup_method(self):
        self.db = AccountDB()
        self._cleanup()
        # 创建测试账户，初始资金 100,000
        account = Account(
            account_id=TEST_ACCOUNT_ID,
            account_name="Test Service Account",
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


class TestAccountServiceBuy(TestAccountServiceBase):
    """买入操作测试"""

    def test_buy_success(self):
        """买入成功: cash 扣减、position 增加、trade 记录、audit_log 记录"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)

        result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert result.success is True
        assert result.trade_id.startswith("T-")
        assert result.cash_after == 100_000.0 - 10.0 * 100
        assert result.position_quantity == 100

        # 验证账户现金
        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 99_000.0

        # 验证持仓
        positions = svc.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "000001.SZSE"
        assert positions[0].name == "平安银行"
        assert positions[0].quantity == 100
        assert positions[0].avg_cost == 10.0

        # 验证交易记录
        trades = svc.get_trade_history()
        assert len(trades) == 1
        assert trades[0].symbol == "000001.SZSE"
        assert trades[0].quantity == 100
        assert trades[0].direction.value == "BUY"

        # 验证审计日志
        logs = svc.get_audit_log()
        assert len(logs) == 1
        assert logs[0]["operation"] == "BUY"
        assert logs[0]["cash_before"] == 100_000.0
        assert logs[0]["cash_after"] == 99_000.0

    def test_buy_add_to_existing_position(self):
        """加仓: 重算 avg_cost"""
        svc = AccountService(TEST_ACCOUNT_ID)

        svc.buy("000001.SZSE", "平安银行", 10.0, 100)
        svc.buy("000001.SZSE", "平安银行", 12.0, 100)

        positions = svc.get_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos.quantity == 200
        # avg_cost = (100*10 + 100*12) / 200 = 11.0
        assert abs(pos.avg_cost - 11.0) < 0.01

        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 100_000.0 - 10.0 * 100 - 12.0 * 100

    def test_buy_insufficient_cash(self):
        """现金不足: 返回失败 TradeResult，数据不变"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 尝试买入超过可用现金的股票
        result = svc.buy("000001.SZSE", "平安银行", 1000.0, 200)

        assert result.success is False
        assert "现金不足" in result.message

        # 验证数据未变
        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 100_000.0
        assert len(svc.get_positions()) == 0
        assert len(svc.get_trade_history()) == 0

    def test_buy_account_not_found(self):
        """账户不存在: 返回失败 TradeResult"""
        svc = AccountService("nonexistent_account")

        result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert result.success is False
        assert "不存在" in result.message

    def test_buy_emits_event(self):
        """买入成功后发布 TRADE_EXECUTED 事件"""
        bus = EventBus()
        received = []
        bus.subscribe(EventType.TRADE_EXECUTED, lambda e: received.append(e))

        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert len(received) == 1
        event = received[0]
        assert event.type == EventType.TRADE_EXECUTED
        assert event.data["symbol"] == "000001.SZSE"
        assert event.data["direction"] == "BUY"
        assert event.data["quantity"] == 100
        assert event.data["price"] == 10.0
        assert event.data["amount"] == 1000.0

    def test_buy_failure_does_not_emit_event(self):
        """买入失败时不发布事件"""
        bus = EventBus()
        received = []
        bus.subscribe(EventType.TRADE_EXECUTED, lambda e: received.append(e))

        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        svc.buy("000001.SZSE", "平安银行", 1000.0, 200)  # 现金不足

        assert len(received) == 0


class TestAccountServiceSell(TestAccountServiceBase):
    """卖出操作测试"""

    def _setup_position(self, svc, symbol="000001.SZSE", name="平安银行",
                        price=10.0, quantity=100):
        """辅助: 先买入建立持仓"""
        result = svc.buy(symbol, name, price, quantity)
        assert result.success is True
        return result

    def test_sell_success(self):
        """卖出成功: cash 增加、position 减少、realized_pnl 计算正确"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)

        self._setup_position(svc, price=10.0, quantity=100)
        # cash = 99,000

        result = svc.sell("000001.SZSE", 12.0, 50)
        assert result.success is True
        assert result.cash_after == 99_000.0 + 12.0 * 50
        assert result.position_quantity == 50
        assert "盈亏" in result.message

        # realized_pnl = (12 - 10) * 50 = 100
        # cash_after = 99,000 + 600 = 99,600
        assert result.cash_after == 99_600.0

        positions = svc.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50
        assert positions[0].avg_cost == 10.0  # avg_cost 不变

    def test_sell_clear_position(self):
        """清仓: position 记录被删除"""
        svc = AccountService(TEST_ACCOUNT_ID)

        self._setup_position(svc, price=10.0, quantity=100)

        result = svc.sell("000001.SZSE", 12.0, 100)
        assert result.success is True
        assert result.position_quantity == 0

        positions = svc.get_positions()
        assert len(positions) == 0

        # 验证 cash
        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 99_000.0 + 12.0 * 100

    def test_sell_insufficient_position(self):
        """持仓不足: 返回失败 TradeResult"""
        svc = AccountService(TEST_ACCOUNT_ID)

        self._setup_position(svc, price=10.0, quantity=100)

        result = svc.sell("000001.SZSE", 12.0, 200)
        assert result.success is False
        assert "持仓不足" in result.message

        # 数据不变
        positions = svc.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 100

    def test_sell_no_position(self):
        """卖出没有持仓的股票: 返回失败 TradeResult"""
        svc = AccountService(TEST_ACCOUNT_ID)

        result = svc.sell("999999.SZSE", 10.0, 100)
        assert result.success is False
        assert "持仓不足" in result.message

    def test_sell_realized_pnl_negative(self):
        """卖出亏损: realized_pnl 为负"""
        svc = AccountService(TEST_ACCOUNT_ID)

        self._setup_position(svc, price=10.0, quantity=100)
        result = svc.sell("000001.SZSE", 8.0, 100)

        assert result.success is True
        # realized_pnl = (8 - 10) * 100 = -200
        assert "盈亏" in result.message

        # 从审计日志中验证 realized_pnl
        logs = svc.get_audit_log(operation="SELL")
        assert len(logs) == 1
        import json
        details = json.loads(logs[0]["details"])
        assert details["realized_pnl"] == -200.0

    def test_sell_emits_event(self):
        """卖出成功后发布 TRADE_EXECUTED 事件"""
        bus = EventBus()
        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        self._setup_position(svc)

        # 重置事件列表，只捕获 sell 事件
        received = []
        bus.subscribe(EventType.TRADE_EXECUTED, lambda e: received.append(e))

        svc.sell("000001.SZSE", 12.0, 50)

        assert len(received) == 1
        assert received[0].data["direction"] == "SELL"


class TestAccountServiceAtomicity(TestAccountServiceBase):
    """事务原子性测试"""

    def test_buy_atomicity_on_db_error(self):
        """buy 中途 DB 错误: cash 和 position 都回滚"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # Mock: 在 trade 记录插入时抛出异常
        original_get_conn = get_connection

        def failing_get_conn(*args, **kwargs):
            conn = original_get_conn(*args, **kwargs)
            original_exec = conn.execute

            def mock_execute(sql, params=()):
                # 在 INSERT INTO trades 时失败
                if "INSERT INTO trades" in str(sql):
                    raise RuntimeError("Simulated DB error")
                return original_exec(sql, params)

            conn.execute = mock_execute
            return conn

        with patch("accounts.account_db.get_connection", side_effect=failing_get_conn):
            result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert result.success is False

        # 验证: cash 未变
        acct = self.db.get_account(TEST_ACCOUNT_ID)
        assert acct.cash == 100_000.0

        # 验证: 无持仓
        assert len(svc.get_positions()) == 0


class TestAccountServiceQueries(TestAccountServiceBase):
    """查询操作测试"""

    def test_get_balance(self):
        """get_balance: 计算正确"""
        svc = AccountService(TEST_ACCOUNT_ID)

        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        balance = svc.get_balance()
        assert balance.cash == 99_000.0
        # market_value: 100 * 10 (current_price == price on buy)
        assert balance.market_value == 1000.0
        assert balance.total_assets == 99_000.0 + 1000.0
        assert balance.unrealized_pnl == 0.0  # current_price == avg_cost

    def test_get_balance_unrealized_pnl(self):
        """get_balance: 浮盈计算正确（通过卖出后更新 current_price 模拟）"""
        svc = AccountService(TEST_ACCOUNT_ID)

        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # 模拟价格变动: 手动更新 current_price
        conn = get_connection()
        conn.execute(
            """UPDATE positions SET current_price = 12.0,
               market_value = 1200.0, unrealized_pnl = 200.0
               WHERE account_id = ? AND symbol = ?""",
            (TEST_ACCOUNT_ID, "000001.SZSE"),
        )
        conn.commit()
        conn.close()

        balance = svc.get_balance()
        assert balance.market_value == 1200.0
        assert balance.unrealized_pnl == 200.0
        assert balance.total_assets == 99_000.0 + 1200.0

    def test_get_positions_empty(self):
        """get_positions: 无持仓返回空列表"""
        svc = AccountService(TEST_ACCOUNT_ID)
        assert svc.get_positions() == []

    def test_get_trade_history_with_dates(self):
        """get_trade_history: 支持日期过滤"""
        svc = AccountService(TEST_ACCOUNT_ID)

        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        today = datetime.now().strftime("%Y%m%d")
        trades = svc.get_trade_history(start_date=today, end_date=today)
        assert len(trades) == 1

        # 过滤未来日期应该无结果
        trades = svc.get_trade_history(start_date="20990101")
        assert len(trades) == 0

    def test_get_audit_log_by_operation(self):
        """get_audit_log: 支持按操作类型过滤"""
        svc = AccountService(TEST_ACCOUNT_ID)

        svc.buy("000001.SZSE", "平安银行", 10.0, 100)
        svc.sell("000001.SZSE", 12.0, 50)

        buy_logs = svc.get_audit_log(operation="BUY")
        assert len(buy_logs) == 1
        assert buy_logs[0]["operation"] == "BUY"

        sell_logs = svc.get_audit_log(operation="SELL")
        assert len(sell_logs) == 1
        assert sell_logs[0]["operation"] == "SELL"

        all_logs = svc.get_audit_log()
        assert len(all_logs) == 2


class TestAccountServiceSnapshot(TestAccountServiceBase):
    """快照测试"""

    def test_snapshot(self):
        """snapshot: 生成并保存到 daily_snapshots"""
        bus = EventBus()
        received = []
        bus.subscribe(EventType.SNAPSHOT_CREATED, lambda e: received.append(e))

        svc = AccountService(TEST_ACCOUNT_ID, event_bus=bus)
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        snap = svc.snapshot(trade_date="20260623")

        assert snap.account_id == TEST_ACCOUNT_ID
        assert snap.trade_date == "20260623"
        assert snap.cash == 99_000.0
        assert snap.positions_count == 1
        assert snap.trades_count == 1

        # 验证事件已发布
        assert len(received) == 1
        assert received[0].type == EventType.SNAPSHOT_CREATED

        # 验证已保存到 DB
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM daily_snapshots WHERE account_id = ? AND trade_date = ?",
                (TEST_ACCOUNT_ID, "20260623"),
            ).fetchone()
            assert row is not None
            assert row["cash"] == 99_000.0
            assert row["positions_count"] == 1
        finally:
            conn.close()


class TestTradeIdGeneration(TestAccountServiceBase):
    """trade_id 生成测试"""

    def test_trade_id_format(self):
        """trade_id 格式: T-{timestamp}-{random4}"""
        svc = AccountService(TEST_ACCOUNT_ID)

        result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        assert result.trade_id.startswith("T-")
        parts = result.trade_id.split("-")
        assert len(parts) == 3
        assert parts[0] == "T"
        assert parts[1].isdigit()  # timestamp
        assert len(parts[2]) == 4  # random 4 digits

    def test_trade_ids_unique(self):
        """trade_id 唯一性"""
        svc = AccountService(TEST_ACCOUNT_ID)

        ids = set()
        for _ in range(10):
            result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)
            ids.add(result.trade_id)

        assert len(ids) == 10


class TestAccountServiceRefreshPrices(TestAccountServiceBase):
    """Phase 6: 价格刷新测试"""

    def test_refresh_prices(self):
        """refresh_prices: 更新持仓价格"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 先买入一只股票
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # 验证初始状态
        positions = svc.get_positions()
        assert len(positions) == 1
        assert positions[0].current_price == 10.0  # 买入时价格
        assert positions[0].unrealized_pnl == 0.0

        # 调用 refresh_prices (会从 CSV 读取最新价格)
        updated = svc.refresh_prices()

        # 应该返回 1 (CSV 文件存在，更新了 1 个持仓)
        assert updated == 1

        # 验证价格已更新 (CSV 中最新收盘价 11.08)
        positions = svc.get_positions()
        assert positions[0].current_price == 11.08
        # 浮盈 = 100 * (11.08 - 10.0) = 108.0
        assert positions[0].unrealized_pnl == 108.0

    def test_refresh_prices_with_mock(self):
        """refresh_prices: 使用 mock PriceUpdater"""
        from unittest.mock import patch, MagicMock
        from accounts.price_updater import PriceUpdater

        svc = AccountService(TEST_ACCOUNT_ID)
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # Mock PriceUpdater.refresh_positions
        with patch.object(PriceUpdater, 'refresh_positions', return_value=1) as mock_refresh:
            updated = svc.refresh_prices()

            assert updated == 1
            mock_refresh.assert_called_once_with(TEST_ACCOUNT_ID)

    def test_snapshot_calls_refresh_prices(self):
        """snapshot: 开头调用 refresh_prices"""
        from unittest.mock import patch, MagicMock
        from accounts.price_updater import PriceUpdater

        svc = AccountService(TEST_ACCOUNT_ID)
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # Mock refresh_prices
        with patch.object(svc, 'refresh_prices', return_value=0) as mock_refresh:
            snap = svc.snapshot(trade_date="20260627")

            # 验证 refresh_prices 被调用
            mock_refresh.assert_called_once()

            # 验证快照数据正确
            assert snap.account_id == TEST_ACCOUNT_ID
            assert snap.trade_date == "20260627"
            assert snap.cash == 99_000.0
