"""账户数据库功能测试"""
import pytest
from accounts.account_db import AccountDB, get_connection, Account
from datetime import datetime


class TestAccountDBFull:
    """测试账户数据库的所有功能"""

    def setup_method(self):
        """测试前设置"""
        self.db = AccountDB()
        # 确保测试账户不存在，避免冲突
        self.test_account_id = "test_db_functionality"
        self._cleanup_test_data()

    def teardown_method(self):
        """测试后清理"""
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """清理测试数据"""
        try:
            conn = get_connection()
            conn.execute("DELETE FROM trades WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM positions WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM accounts WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM daily_snapshots WHERE account_id = ?", (self.test_account_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass  # 忽略清理错误

    def test_create_and_get_account(self):
        """测试创建和获取账户"""
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )

        # 创建账户
        result = self.db.create_account(test_account)
        assert result is True

        # 获取账户
        retrieved = self.db.get_account(self.test_account_id)
        assert retrieved is not None
        assert retrieved.account_id == self.test_account_id
        assert retrieved.account_name == "Test DB Account"
        assert retrieved.initial_capital == 50000.0
        assert retrieved.cash == 50000.0

    def test_create_duplicate_account(self):
        """测试创建重复账户"""
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )

        # 第一次创建应该成功
        result1 = self.db.create_account(test_account)
        assert result1 is True

        # 第二次创建应该失败
        result2 = self.db.create_account(test_account)
        assert result2 is False

    def test_update_cash(self):
        """测试更新现金"""
        # 先创建账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )
        self.db.create_account(test_account)

        # 更新现金
        new_cash = 45000.0
        result = self.db.update_cash(self.test_account_id, new_cash)
        assert result is True

        # 验证现金已更新
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == new_cash

    def test_update_position_new(self):
        """测试更新新持仓"""
        # 先创建账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )
        self.db.create_account(test_account)

        # 更新新持仓
        result = self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.5,
            current_price=16.0
        )
        assert result is True

        # 验证持仓已创建
        positions = self.db.get_positions(self.test_account_id)
        assert len(positions) == 1
        assert positions[0].symbol == "000001.SZSE"
        assert positions[0].quantity == 1000
        assert positions[0].avg_cost == 15.5
        assert positions[0].current_price == 16.0
        assert positions[0].market_value == 16000.0  # quantity * current_price
        assert positions[0].unrealized_pnl == 500.0  # (16.0 - 15.5) * 1000

    def test_update_position_existing(self):
        """测试更新现有持仓"""
        # 先创建账户和持仓
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )
        self.db.create_account(test_account)

        # 初始持仓
        self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.5,
            current_price=16.0
        )

        # 更新相同持仓（加仓）
        result = self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1500,  # 增加到1500股
            avg_cost=15.2,  # 新的平均成本
            current_price=16.5
        )
        assert result is True

        # 验证持仓已更新
        positions = self.db.get_positions(self.test_account_id)
        assert len(positions) == 1
        assert positions[0].quantity == 1500
        assert positions[0].avg_cost == 15.2
        assert positions[0].current_price == 16.5
        assert positions[0].market_value == 24750.0  # 1500 * 16.5
        # 使用近似比较处理浮点数精度问题
        assert abs(positions[0].unrealized_pnl - 1950.0) < 0.01  # (16.5 - 15.2) * 1500

    def test_get_positions_empty(self):
        """测试获取空持仓"""
        # 创建账户但不添加持仓
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )
        self.db.create_account(test_account)

        positions = self.db.get_positions(self.test_account_id)
        assert len(positions) == 0

    def test_add_and_get_trades(self):
        """测试添加和获取交易记录"""
        # 先创建账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=50000.0,
            cash=50000.0
        )
        self.db.create_account(test_account)

        # 添加交易记录
        trade_id = self.db.add_trade(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            trade_type="BUY",
            quantity=1000,
            price=15.5,
            commission=15.5,
            symbol_name="平安银行",
            order_id="ORDER_001"
        )
        assert trade_id is not None and trade_id > 0

        # 获取交易记录
        trades = self.db.get_trades(self.test_account_id, limit=10)
        assert len(trades) == 1
        assert trades[0]['symbol'] == "000001.SZSE"
        assert trades[0]['quantity'] == 1000
        assert trades[0]['price'] == 15.5
        assert trades[0]['amount'] == 15500.0  # quantity * price
        assert trades[0]['commission'] == 15.5

    def test_save_and_get_account_summary(self):
        """测试保存快照和获取账户摘要"""
        # 先创建账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test DB Account",
            initial_capital=100000.0,
            cash=80000.0
        )
        self.db.create_account(test_account)

        # 添加一些持仓
        self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.0,
            current_price=16.0
        )

        # 添加交易记录
        self.db.add_trade(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            trade_type="BUY",
            quantity=1000,
            price=15.0,
            commission=15.0
        )

        # 保存快照
        today = datetime.now().strftime('%Y%m%d')
        result = self.db.save_snapshot(
            account_id=self.test_account_id,
            trade_date=today,
            cash=75000.0,
            market_value=16000.0,
            realized_pnl=1000.0,
            unrealized_pnl=1000.0
        )
        assert result is True

        # 获取账户摘要
        summary = self.db.get_account_summary(self.test_account_id)
        assert summary is not None
        assert summary['account'] is not None
        assert summary['account']['account_id'] == self.test_account_id
        assert summary['positions_count'] == 1
        assert summary['total_market_value'] == 16000.0
        assert summary['unrealized_pnl'] == 1000.0