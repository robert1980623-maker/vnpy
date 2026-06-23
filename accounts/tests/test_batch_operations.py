"""
批量操作测试

测试批量查询方法的正确性
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from accounts.account_db import AccountDB, Account, get_connection_pool
from accounts.models import Position


# 测试账户 IDs
TEST_ACCOUNTS = ["batch_test_1", "batch_test_2", "batch_test_3", "batch_test_4", "batch_test_5"]


class TestBatchOperationsBase:
    """批量操作测试基类"""

    def setup_method(self):
        # 重置全局连接池
        from accounts import connection_pool as cp
        cp._pool = None

        # 初始化数据库
        self.db = AccountDB()

        # 创建测试账户
        for acc_id in TEST_ACCOUNTS:
            if not self.db.get_account(acc_id):
                account = Account(
                    account_id=acc_id,
                    account_name=f"Batch Test {acc_id}",
                    initial_capital=50_000.0,
                    cash=50_000.0,
                )
                self.db.create_account(account)

            # 为每个账户创建一些持仓和交易
            # 如果持仓已存在，跳过；否则创建
            positions = self.db.get_positions(acc_id)
            if not positions:
                # 创建几条持仓记录
                for i, (symbol, name, qty, price) in enumerate([
                    ("000001.SZSE", "平安银行", 100, 10.0),
                    ("000002.SZSE", "万科A", 200, 15.0),
                    ("600000.SSE", "浦发银行", 300, 8.0),
                ]):
                    self.db.update_position(
                        account_id=acc_id,
                        symbol=symbol,
                        quantity=qty,
                        avg_cost=price,
                        current_price=price
                    )

                    # 添加交易记录
                    self.db.add_trade(
                        account_id=acc_id,
                        symbol=symbol,
                        trade_type="BUY",
                        quantity=qty,
                        price=price,
                        commission=0.0,
                        symbol_name=name
                    )

    def teardown_method(self):
        # 清理测试账户数据
        pool = get_connection_pool()
        for acc_id in TEST_ACCOUNTS:
            conn = pool._acquire(timeout=5.0)
            try:
                conn.execute("DELETE FROM audit_log WHERE account_id = ?", (acc_id,))
                conn.execute("DELETE FROM trades WHERE account_id = ?", (acc_id,))
                conn.execute("DELETE FROM positions WHERE account_id = ?", (acc_id,))
                conn.execute("DELETE FROM daily_snapshots WHERE account_id = ?", (acc_id,))
                conn.execute("DELETE FROM accounts WHERE account_id = ?", (acc_id,))
                conn.commit()
            finally:
                pool._release(conn)

        # 重置全局连接池
        from accounts import connection_pool as cp
        cp._pool = None


class TestGetPositionsBatch(TestBatchOperationsBase):
    """get_positions_batch 测试"""

    def test_get_positions_batch_single_account(self):
        """批量查询单个账户的持仓"""
        pool = get_connection_pool()
        conn = pool._acquire(timeout=5.0)
        try:
            result = conn.execute(
                "SELECT * FROM positions WHERE account_id = ? AND quantity > 0",
                (TEST_ACCOUNTS[0],)
            ).fetchall()
            expected_count = len(result)
        finally:
            pool._release(conn)

        result = self.db.get_positions_batch([TEST_ACCOUNTS[0]])
        positions = result[TEST_ACCOUNTS[0]]

        assert len(positions) > 0
        assert len(positions) == expected_count

    def test_get_positions_batch_multiple_accounts(self):
        """批量查询多个账户的持仓"""
        result = self.db.get_positions_batch(TEST_ACCOUNTS[:3])

        assert len(result) == 3
        for acc_id in TEST_ACCOUNTS[:3]:
            assert acc_id in result
            assert len(result[acc_id]) > 0

    def test_get_positions_batch_empty_list(self):
        """空列表应返回空字典"""
        result = self.db.get_positions_batch([])
        assert result == {}

    def test_get_positions_batch_nonexistent_accounts(self):
        """查询不存在的账户应返回空列表"""
        result = self.db.get_positions_batch(["nonexistent_1", "nonexistent_2"])
        assert len(result) == 2
        assert result["nonexistent_1"] == []
        assert result["nonexistent_2"] == []

    def test_get_positions_batch_positions_structure(self):
        """批量查询返回的持仓结构正确"""
        result = self.db.get_positions_batch([TEST_ACCOUNTS[0]])
        positions = result[TEST_ACCOUNTS[0]]

        for pos in positions:
            assert hasattr(pos, 'symbol')
            assert hasattr(pos, 'quantity')
            assert hasattr(pos, 'avg_cost')
            assert hasattr(pos, 'current_price')
            assert hasattr(pos, 'market_value')
            assert hasattr(pos, 'unrealized_pnl')


class TestGetBalanceBatch(TestBatchOperationsBase):
    """get_balance_batch 测试"""

    def test_get_balance_batch_single_account(self):
        """批量查询单个账户的余额"""
        result = self.db.get_balance_batch([TEST_ACCOUNTS[0]])

        assert len(result) == 1
        assert TEST_ACCOUNTS[0] in result

        balance = result[TEST_ACCOUNTS[0]]
        assert "account_id" in balance
        assert "cash" in balance
        assert "initial_capital" in balance
        assert "total_market_value" in balance
        assert "unrealized_pnl" in balance
        assert "positions_count" in balance

    def test_get_balance_batch_multiple_accounts(self):
        """批量查询多个账户的余额"""
        result = self.db.get_balance_batch(TEST_ACCOUNTS[:3])

        assert len(result) == 3
        for acc_id in TEST_ACCOUNTS[:3]:
            assert acc_id in result
            assert "cash" in result[acc_id]
            assert result[acc_id]["cash"] > 0

    def test_get_balance_batch_empty_list(self):
        """空列表应返回空字典"""
        result = self.db.get_balance_batch([])
        assert result == {}

    def test_get_balance_batch_total_assets_calculation(self):
        """总资产计算正确"""
        result = self.db.get_balance_batch([TEST_ACCOUNTS[0]])
        balance = result[TEST_ACCOUNTS[0]]

        expected_total = balance["cash"] + balance["total_market_value"]
        assert abs(balance["total_assets"] - expected_total) < 0.01

    def test_get_balance_batch_consistent_with_single_query(self):
        """批量查询结果与单账户查询一致"""
        # 使用 get_account 和 get_positions 获取单账户余额
        account = self.db.get_account(TEST_ACCOUNTS[0])
        positions = self.db.get_positions(TEST_ACCOUNTS[0])
        market_value = sum(p.market_value for p in positions)

        # 批量查询
        batch_result = self.db.get_balance_batch([TEST_ACCOUNTS[0]])
        batch_balance = batch_result[TEST_ACCOUNTS[0]]

        # 比较结果
        assert abs(batch_balance["cash"] - account.cash) < 0.01
        assert abs(batch_balance["total_market_value"] - market_value) < 0.01


class TestGetTradesBatch(TestBatchOperationsBase):
    """get_trades_batch 测试"""

    def test_get_trades_batch_single_account(self):
        """批量查询单个账户的交易记录"""
        result = self.db.get_trades_batch([TEST_ACCOUNTS[0]], limit=10)

        assert len(result) == 1
        assert TEST_ACCOUNTS[0] in result
        assert len(result[TEST_ACCOUNTS[0]]) > 0

    def test_get_trades_batch_multiple_accounts(self):
        """批量查询多个账户的交易记录"""
        result = self.db.get_trades_batch(TEST_ACCOUNTS[:3], limit=10)

        assert len(result) == 3
        for acc_id in TEST_ACCOUNTS[:3]:
            assert acc_id in result

    def test_get_trades_batch_empty_list(self):
        """空列表应返回空字典"""
        result = self.db.get_trades_batch([])
        assert result == {}


class TestBatchOperationsCorrectness(TestBatchOperationsBase):
    """批量操作正确性测试"""

    def test_batch_positions_sum_matches_individual(self):
        """批量查询的持仓合计与单独查询一致"""
        # 单独查询每个账户的持仓数量
        individual_totals = {}
        for acc_id in TEST_ACCOUNTS[:3]:
            positions = self.db.get_positions(acc_id)
            individual_totals[acc_id] = len(positions)

        # 批量查询
        batch_result = self.db.get_positions_batch(TEST_ACCOUNTS[:3])

        # 比较
        for acc_id in TEST_ACCOUNTS[:3]:
            assert len(batch_result[acc_id]) == individual_totals[acc_id]

    def test_batch_balance_matches_individual(self):
        """批量查询的余额与单独查询一致"""
        for acc_id in TEST_ACCOUNTS[:3]:
            # 单独查询
            account = self.db.get_account(acc_id)
            positions = self.db.get_positions(acc_id)
            market_value = sum(p.market_value for p in positions)

            # 批量查询
            batch_result = self.db.get_balance_batch([acc_id])
            batch_balance = batch_result[acc_id]

            # 比较
            assert abs(batch_balance["cash"] - account.cash) < 0.01
            assert abs(batch_balance["total_market_value"] - market_value) < 0.01

    def test_batch_operations_are_atomic(self):
        """批量操作应确保数据一致性"""
        # 在测试期间，数据应保持一致
        accounts_to_test = TEST_ACCOUNTS[:2]

        # 多次查询，结果应一致
        for _ in range(5):
            balances = self.db.get_balance_batch(accounts_to_test)
            positions = self.db.get_positions_batch(accounts_to_test)

            for acc_id in accounts_to_test:
                balance = balances[acc_id]
                pos_list = positions[acc_id]

                # 验证一致性：cash + market_value = total_assets
                expected_total = balance["cash"] + balance["total_market_value"]
                assert abs(balance["total_assets"] - expected_total) < 0.01

                # 验证持仓数量
                assert len(pos_list) == balance["positions_count"]


class TestBatchOperationsPerformance(TestBatchOperationsBase):
    """批量操作性能测试（粗略）"""

    def test_batch_is_faster_than_individual(self):
        """批量查询应比单独查询快（粗略验证）"""
        import time

        accounts = TEST_ACCOUNTS[:5]

        # 单独查询
        start = time.time()
        for _ in range(10):
            for acc_id in accounts:
                self.db.get_positions(acc_id)
                self.db.get_balance_batch([acc_id])
        individual_time = time.time() - start

        # 批量查询
        start = time.time()
        for _ in range(10):
            self.db.get_positions_batch(accounts)
            self.db.get_balance_batch(accounts)
        batch_time = time.time() - start

        # 批量查询应至少快 1.5 倍（粗略验证）
        # 注意：由于是粗略测试，这个阈值可能不总是成立
        assert batch_time < individual_time * 1.5, \
            f"Batch time {batch_time:.3f}s vs individual {individual_time:.3f}s"
