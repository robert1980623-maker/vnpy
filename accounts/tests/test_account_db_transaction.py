"""账户数据库事务测试"""
import pytest
import sqlite3
from accounts.account_db import AccountDB, get_connection, Account
from accounts.models import Trade


class TestAccountDbTransaction:
    """测试账户数据库事务功能"""

    def setup_method(self):
        """测试前设置"""
        self.db = AccountDB()
        # 确保测试账户不存在，避免冲突
        self.test_account_id = "test_transaction_account"
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

    def test_execute_in_transaction_success_case(self):
        """测试事务成功执行"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0

        def update_cash_op(conn):
            """更新现金的操作"""
            conn.execute(
                "UPDATE accounts SET cash = ? WHERE account_id = ?",
                (initial_cash - 1000.0, self.test_account_id)
            )

        def insert_position_op(conn):
            """插入持仓的操作"""
            conn.execute("""
                INSERT INTO positions (account_id, symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.test_account_id, "000001.SZSE", 100, 10.0, 10.0, 1000.0, 0.0, "2023-01-01T00:00:00"
            ))

        # 执行事务
        result = self.db.execute_in_transaction([update_cash_op, insert_position_op])

        assert result is True  # 事务成功

        # 验证数据都已更新
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == initial_cash - 1000.0

        positions = self.db.get_positions(self.test_account_id)
        assert len(positions) == 1
        assert positions[0].symbol == "000001.SZSE"
        assert positions[0].quantity == 100

    def test_execute_in_transaction_rollback_on_error(self):
        """测试事务失败时回滚"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0
        target_cash = initial_cash - 1000.0

        def update_cash_op(conn):
            """更新现金的操作"""
            conn.execute(
                "UPDATE accounts SET cash = ? WHERE account_id = ?",
                (target_cash, self.test_account_id)
            )

        def failing_op(conn):
            """故意失败的操作 - 通过无效的SQL语法或违反约束来触发错误"""
            # 使用无效SQL语句触发错误
            conn.execute("INSERT INTO nonexistent_table (account_id) VALUES (?)", (self.test_account_id,))

        # 执行事务 - 应该失败并回滚，异常被重新抛出
        with pytest.raises(Exception):
            self.db.execute_in_transaction([update_cash_op, failing_op])

        # 验证数据没有被部分更新（回滚生效）
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == initial_cash  # 现金应该保持不变

        positions = self.db.get_positions(self.test_account_id)
        assert len(positions) == 0  # 持仓应该没有被插入

    def test_execute_in_transaction_with_single_operation(self):
        """测试只包含单个操作的事务"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0
        target_cash = initial_cash - 500.0

        def update_cash_op(conn):
            """更新现金的操作"""
            conn.execute(
                "UPDATE accounts SET cash = ? WHERE account_id = ?",
                (target_cash, self.test_account_id)
            )

        # 执行只包含单个操作的事务
        result = self.db.execute_in_transaction([update_cash_op])

        assert result is True  # 事务成功

        # 验证数据更新
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == target_cash

    def test_execute_in_transaction_with_empty_list(self):
        """测试空操作列表的事务"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0

        # 执行空操作列表的事务
        result = self.db.execute_in_transaction([])

        assert result is True  # 空事务也应该成功

        # 验证数据没有变化
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == initial_cash

    def test_execute_in_transaction_second_operation_fails(self):
        """测试第二个操作失败时第一个操作也会回滚"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0
        target_cash = initial_cash - 500.0

        def first_update_op(conn):
            """第一个操作 - 应该成功"""
            conn.execute(
                "UPDATE accounts SET cash = ? WHERE account_id = ?",
                (target_cash, self.test_account_id)
            )

        def second_failing_op(conn):
            """第二个操作 - 故意失败"""
            conn.execute("INVALID SQL STATEMENT")  # 无效SQL导致失败

        # 执行事务 - 应该失败，异常被重新抛出
        with pytest.raises(Exception):
            self.db.execute_in_transaction([first_update_op, second_failing_op])

        # 验证第一个操作也被回滚了
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == initial_cash  # 现金保持原始值

    def test_execute_in_transaction_with_valid_operations_that_depend_on_each_other(self):
        """测试相互依赖的事务操作"""
        # 准备测试账户
        test_account = Account(
            account_id=self.test_account_id,
            account_name="Test Transaction Account",
            initial_capital=10000.0,
            cash=10000.0
        )
        assert self.db.create_account(test_account)

        initial_cash = 10000.0
        amount_to_deduct = 1000.0
        final_cash = initial_cash - amount_to_deduct

        def update_cash_op(conn):
            """更新现金"""
            conn.execute(
                "UPDATE accounts SET cash = ? WHERE account_id = ?",
                (final_cash, self.test_account_id)
            )

        def insert_related_trade_op(conn):
            """插入相关的交易记录 - 依赖于账户存在"""
            from datetime import datetime
            now = datetime.now()
            trade_date = now.strftime('%Y%m%d')
            trade_time = now.strftime('%H:%M:%S')

            conn.execute("""
                INSERT INTO trades (account_id, symbol, symbol_name, trade_type,
                    quantity, price, amount, commission, trade_date, trade_time,
                    order_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.test_account_id,  # 依赖于账户存在
                "000001.SZSE",
                "测试股票",
                "BUY",
                100,
                10.0,
                1000.0,
                1.0,
                trade_date,
                trade_time,
                "TEST_ORDER_001",
                "filled",
                now.isoformat()
            ))

        # 执行事务
        result = self.db.execute_in_transaction([update_cash_op, insert_related_trade_op])

        assert result is True  # 事务成功

        # 验证两个操作都完成
        updated_account = self.db.get_account(self.test_account_id)
        assert updated_account.cash == final_cash

        trades = self.db.get_trades(self.test_account_id, limit=10)
        assert len(trades) == 1
        assert trades[0]['symbol'] == "000001.SZSE"
        assert trades[0]['amount'] == 1000.0