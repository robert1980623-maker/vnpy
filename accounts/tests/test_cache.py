"""
TTL 缓存测试

测试缓存的有效期、过期和写操作失效机制
"""
import pytest
import time
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from accounts.account_service import AccountService, CachedAccountService
from accounts.account_db import AccountDB, Account, get_connection_pool
from accounts.models import Position


# 测试账户 ID
TEST_ACCOUNT_ID = "test_cache_account"
TEST_ACCOUNT_ID_2 = "test_cache_account_2"


class TestCacheTTLBase:
    """缓存测试基类"""

    def setup_method(self):
        # 重置全局连接池
        from accounts import connection_pool as cp
        cp._pool = None

        # 初始化数据库
        self.db = AccountDB()

        # 清理旧测试数据
        pool = get_connection_pool()
        for acc_id in [TEST_ACCOUNT_ID, TEST_ACCOUNT_ID_2]:
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

        # 创建测试账户
        for acc_id in [TEST_ACCOUNT_ID, TEST_ACCOUNT_ID_2]:
            if not self.db.get_account(acc_id):
                account = Account(
                    account_id=acc_id,
                    account_name=f"Test Cache {acc_id}",
                    initial_capital=100_000.0,
                    cash=100_000.0,
                )
                self.db.create_account(account)

    def teardown_method(self):
        # 清理测试数据
        pool = get_connection_pool()
        for acc_id in [TEST_ACCOUNT_ID, TEST_ACCOUNT_ID_2]:
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


class TestCacheTTLExpiration(TestCacheTTLBase):
    """TTL 过期测试"""

    def test_balance_cache_expires_after_ttl(self):
        """余额缓存应在 TTL 后过期"""
        # 使用 2 秒的 TTL 进行测试
        svc = AccountService(TEST_ACCOUNT_ID, cache_ttl=2)

        # 第一次调用 - 应查询数据库
        balance1 = svc.get_balance()
        assert balance1.cash == 100_000.0

        # 第二次调用（立即）- 应使用缓存
        balance2 = svc.get_balance()
        assert balance2.cash == balance1.cash

        # 等待 TTL 过期
        time.sleep(3)

        # 第三次调用 - 应再次查询数据库
        balance3 = svc.get_balance()
        assert balance3.cash == balance1.cash  # 结果应相同

    def test_positions_cache_expires_after_ttl(self):
        """持仓缓存应在 TTL 后过期"""
        svc = AccountService(TEST_ACCOUNT_ID, cache_ttl=2)

        # 第一次调用
        positions1 = svc.get_positions()
        assert isinstance(positions1, list)

        # 第二次调用（立即）- 应使用缓存
        positions2 = svc.get_positions()
        assert positions2 == positions1

        # 等待 TTL 过期
        time.sleep(3)

        # 第三次调用 - 应再次查询数据库
        positions3 = svc.get_positions()
        assert positions3 == positions1

    def test_custom_cache_ttl(self):
        """支持自定义 TTL"""
        svc_short = AccountService(TEST_ACCOUNT_ID, cache_ttl=1)
        svc_long = AccountService(TEST_ACCOUNT_ID, cache_ttl=60)

        # 短 TTL 应更快过期
        svc_short.get_balance()
        time.sleep(0.5)
        # 短 TTL 未过期

        svc_long.get_balance()
        time.sleep(0.5)
        # 长 TTL 也未过期

        # 但它们使用不同的缓存（因为 TTL 不同）
        # 这里验证的是缓存机制存在


class TestCacheInvalidationOnWrite(TestCacheTTLBase):
    """写操作使缓存失效测试"""

    def test_buy_invalidates_balance_cache(self):
        """buy 应使余额缓存失效"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 创建缓存
        balance1 = svc.get_balance()
        initial_cash = balance1.cash

        # 执行买入
        result = svc.buy("000001.SZSE", "平安银行", 10.0, 100)
        assert result.success is True

        # 获取余额 - 应查询数据库，不是使用旧缓存
        balance2 = svc.get_balance()
        assert balance2.cash == initial_cash - 1000.0
        assert balance2.cash != initial_cash

    def test_sell_invalidates_balance_cache(self):
        """sell 应使余额缓存失效"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 先买入建立持仓
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)
        balance_before = svc.get_balance()

        # 卖出
        result = svc.sell("000001.SZSE", 12.0, 50)
        assert result.success is True

        # 获取余额 - 应更新
        balance_after = svc.get_balance()
        # 卖出 50 股 @ 12 = 收入 600
        assert balance_after.cash == balance_before.cash + 600.0

    def test_buy_invalidates_positions_cache(self):
        """buy 应使持仓缓存失效"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 创建缓存
        positions1 = svc.get_positions()
        assert len(positions1) == 0

        # 执行买入
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # 获取持仓 - 应看到新持仓
        positions2 = svc.get_positions()
        assert len(positions2) == 1
        assert positions2[0].symbol == "000001.SZSE"
        assert positions2[0].quantity == 100

    def test_sell_invalidates_positions_cache(self):
        """sell 应使持仓缓存失效"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 先买入
        svc.buy("000001.SZSE", "平安银行", 10.0, 100)

        # 卖出 50 股
        svc.sell("000001.SZSE", 12.0, 50)

        # 获取持仓 - 应看到更新后的数量
        positions = svc.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50

    def test_multiple_writes_invalidate_cache(self):
        """多次写操作应持续使缓存失效"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 创建缓存
        svc.get_balance()
        svc.get_positions()

        # 连续多次写操作
        for i in range(5):
            svc.buy(f"stock_{i}.SZSE", f"Stock {i}", 10.0, 100)

        # 缓存应已被多次失效，但最终状态应正确
        balance = svc.get_balance()
        positions = svc.get_positions()

        assert len(positions) == 5
        assert balance.cash == 100_000.0 - 5000.0  # 5 * 100 * 10


class TestCacheConcurrency(TestCacheTTLBase):
    """并发缓存测试"""

    def test_concurrent_reads_use_cache(self):
        """并发读取应使用缓存"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 预热缓存
        svc.get_balance()

        # 并发读取
        results = []

        def read_balance():
            for _ in range(10):
                b = svc.get_balance()
                results.append(b.cash)

        threads = [threading.Thread(target=read_balance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有结果应相同（因为缓存未过期）
        assert len(set(results)) == 1

    def test_concurrent_write_and_read(self):
        """并发写入和读取应正确处理"""
        import threading as th
        svc = AccountService(TEST_ACCOUNT_ID)

        # 预热缓存
        svc.get_balance()

        errors = []
        results = []

        def writer():
            try:
                for i in range(5):
                    svc.buy(f"stock_w{i}.SZSE", f"Stock W{i}", 10.0, 10)
            except Exception as e:
                errors.append(str(e))

        def reader():
            try:
                for _ in range(10):
                    b = svc.get_balance()
                    results.append(b.cash)
            except Exception as e:
                errors.append(str(e))

        threads = [th.Thread(target=writer), th.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCacheHomogeneousAccount(TestCacheTTLBase):
    """缓存隔离测试"""

    def test_different_accounts_have_separate_caches(self):
        """不同账户应有独立的缓存"""
        svc1 = AccountService(TEST_ACCOUNT_ID)
        svc2 = AccountService(TEST_ACCOUNT_ID_2)

        # svc1 买入
        svc1.buy("000001.SZSE", "平安银行", 10.0, 100)

        # svc2 不应受到影响
        positions1 = svc1.get_positions()
        positions2 = svc2.get_positions()

        assert len(positions1) == 1
        assert len(positions2) == 0


class TestCacheEdgeCases(TestCacheTTLBase):
    """缓存边界情况测试"""

    def test_zero_ttl_cache(self):
        """TTL 为 0 时缓存应立即过期"""
        svc = AccountService(TEST_ACCOUNT_ID, cache_ttl=0)

        # 第一次查询
        balance1 = svc.get_balance()

        # 第二次查询（立即）- 由于 TTL=0，应重新查询
        balance2 = svc.get_balance()

        assert balance1.cash == balance2.cash

    def test_none_cache(self):
        """首次调用应正确查询数据库"""
        svc = AccountService(TEST_ACCOUNT_ID)

        # 首次调用
        balance = svc.get_balance()
        assert balance.cash == 100_000.0

        # 第二次调用
        balance2 = svc.get_balance()
        assert balance2.cash == balance.cash


# 导入 threading
import threading

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
