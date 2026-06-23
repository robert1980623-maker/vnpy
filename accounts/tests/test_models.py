"""账户系统模型测试"""
import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime
from accounts.models import (
    Direction, TradeStatus, Balance, Position, Trade,
    Snapshot, TradeResult
)


class TestDirectionEnum:
    """测试交易方向枚举"""

    def test_direction_values(self):
        """测试方向枚举值"""
        assert Direction.BUY.value == "BUY"
        assert Direction.SELL.value == "SELL"

    def test_direction_str_behavior(self):
        """测试 Direction 可以像字符串一样使用"""
        trade_direction = Direction.BUY
        assert trade_direction == "BUY"  # 直接比较应该成立
        assert trade_direction == "BUY"


class TestTradeStatusEnum:
    """测试交易状态枚举"""

    def test_status_values(self):
        """测试状态枚举值"""
        assert TradeStatus.PENDING.value == "pending"
        assert TradeStatus.FILLED.value == "filled"
        assert TradeStatus.CANCELLED.value == "cancelled"
        assert TradeStatus.REJECTED.value == "rejected"


class TestBalanceModel:
    """测试余额模型"""

    def test_balance_creation(self):
        """测试余额创建"""
        balance = Balance(
            cash=10000.0,
            market_value=5000.0,
            total_assets=15000.0,
            unrealized_pnl=2000.0,
            realized_pnl=3000.0,
            updated_at=datetime.now().isoformat()
        )

        assert balance.cash == 10000.0
        assert balance.market_value == 5000.0
        assert balance.total_assets == 15000.0

    def test_balance_is_immutable(self):
        """测试余额模型是不可变的"""
        balance = Balance(
            cash=10000.0,
            market_value=5000.0,
            total_assets=15000.0,
            unrealized_pnl=2000.0,
            realized_pnl=3000.0,
            updated_at=datetime.now().isoformat()
        )

        with pytest.raises(FrozenInstanceError):
            balance.cash = 20000.0


class TestPositionModel:
    """测试持仓模型"""

    def test_position_creation(self):
        """测试持仓创建"""
        position = Position(
            symbol="000001.SZSE",
            name="平安银行",
            quantity=1000,
            avg_cost=15.5,
            current_price=16.0,
            market_value=16000.0,
            unrealized_pnl=500.0
        )

        assert position.symbol == "000001.SZSE"
        assert position.quantity == 1000
        assert position.avg_cost == 15.5
        assert position.cost_basis == 15500.0  # quantity * avg_cost

    def test_position_default_values(self):
        """测试持仓默认值"""
        position = Position(
            symbol="000001.SZSE",
            name="平安银行",
            quantity=1000,
            avg_cost=15.5
        )

        assert position.current_price == 0.0
        assert position.market_value == 0.0
        assert position.unrealized_pnl == 0.0

    def test_position_cost_basis_property(self):
        """测试持仓成本基数属性"""
        position = Position(
            symbol="000001.SZSE",
            name="平安银行",
            quantity=1000,
            avg_cost=15.5
        )

        assert position.cost_basis == 15500.0  # 1000 * 15.5


class TestTradeModel:
    """测试交易模型"""

    def test_trade_creation(self):
        """测试交易创建"""
        now_iso = datetime.now().isoformat()
        trade = Trade(
            trade_id="T123456",
            account_id="A001",
            symbol="000001.SZSE",
            name="平安银行",
            direction=Direction.BUY,
            quantity=1000,
            price=15.5,
            amount=15500.0,
            commission=15.5,
            trade_date="2023-01-01",
            trade_time="10:30:00",
            order_id="O123456",
            status=TradeStatus.FILLED,
            agent_id="system",
            reason="strategy signal",
            created_at=now_iso
        )

        assert trade.trade_id == "T123456"
        assert trade.direction == Direction.BUY
        assert trade.status == TradeStatus.FILLED
        assert trade.amount == 15500.0

    def test_trade_defaults(self):
        """测试交易默认值"""
        trade = Trade(
            trade_id="T123456",
            account_id="A001",
            symbol="000001.SZSE",
            name="平安银行",
            direction=Direction.BUY,
            quantity=1000,
            price=15.5,
            amount=15500.0
        )

        assert trade.commission == 0.0
        assert trade.trade_date == ""
        assert trade.trade_time == ""
        assert trade.order_id == ""
        assert trade.status == TradeStatus.FILLED
        assert trade.agent_id == "system"
        assert trade.reason == ""


class TestSnapshotModel:
    """测试快照模型"""

    def test_snapshot_creation(self):
        """测试快照创建"""
        now_iso = datetime.now().isoformat()
        snapshot = Snapshot(
            account_id="A001",
            trade_date="2023-01-01",
            cash=50000.0,
            market_value=100000.0,
            total_assets=150000.0,
            realized_pnl=10000.0,
            unrealized_pnl=5000.0,
            positions_count=5,
            trades_count=10,
            created_at=now_iso
        )

        assert snapshot.account_id == "A001"
        assert snapshot.cash == 50000.0
        assert snapshot.total_assets == 150000.0
        assert snapshot.positions_count == 5


class TestTradeResultModel:
    """测试交易结果模型"""

    def test_trade_result_creation(self):
        """测试交易结果创建"""
        result = TradeResult(
            success=True,
            trade_id="T123456",
            message="Buy order executed",
            cash_after=84500.0,
            position_quantity=1000
        )

        assert result.success is True
        assert result.trade_id == "T123456"
        assert result.message == "Buy order executed"
        assert result.cash_after == 84500.0
        assert result.position_quantity == 1000

    def test_trade_result_defaults(self):
        """测试交易结果默认值"""
        result = TradeResult(success=False)

        assert result.success is False
        assert result.trade_id == ""
        assert result.message == ""
        assert result.cash_after == 0.0
        assert result.position_quantity == 0