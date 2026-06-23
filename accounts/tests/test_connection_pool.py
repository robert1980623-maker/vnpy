"""
连接池测试

测试线程安全连接池的并发性能和资源管理
"""
import pytest
import threading
import time
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from accounts.connection_pool import ConnectionPool, get_connection_pool, get_connection, close_connection
from accounts.account_db import AccountDB, Account
import sqlite3


# 测试账户 ID
TEST_POOL_ACCOUNT_ID = "test_pool_account"


class TestConnectionPoolBase:
    """连接池测试基类"""

    def setup_method(self):
        # 重置全局连接池
        import accounts.connection_pool as cp
        cp._pool = None

        # 初始化数据库
        db = AccountDB()

        # 创建测试账户
        if not db.get_account(TEST_POOL_ACCOUNT_ID):
            account = Account(
                account_id=TEST_POOL_ACCOUNT_ID,
                account_name="Test Pool Account",
                initial_capital=100_000.0,
                cash=100_000.0,
            )
            db.create_account(account)

    def teardown_method(self):
        # 清理测试账户数据
        try:
            from accounts.connection_pool import get_connection_pool
            pool = get_connection_pool()
            conn = pool._acquire(timeout=5.0)
            try:
                conn.execute("DELETE FROM audit_log WHERE account_id = ?", (TEST_POOL_ACCOUNT_ID,))
                conn.execute("DELETE FROM trades WHERE account_id = ?", (TEST_POOL_ACCOUNT_ID,))
                conn.execute("DELETE FROM positions WHERE account_id = ?", (TEST_POOL_ACCOUNT_ID,))
                conn.execute("DELETE FROM daily_snapshots WHERE account_id = ?", (TEST_POOL_ACCOUNT_ID,))
                conn.execute("DELETE FROM accounts WHERE account_id = ?", (TEST_POOL_ACCOUNT_ID,))
                conn.commit()
            finally:
                pool._release(conn)
        except Exception:
            pass

        # 重置全局连接池
        import accounts.connection_pool as cp
        cp._pool = None


class TestConnectionPoolBasic(TestConnectionPoolBase):
    """基本连接池功能测试"""

    def test_get_connection_pool_singleton(self):
        """连接池应为单例"""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2

    def test_get_connection_pool_max_connections(self):
        """连接池应配置最大连接数"""
        pool = get_connection_pool(max_connections=8)
        assert pool._max == 8

    def test_get_connection_returns_valid_connection(self):
        """get_connection 应返回有效连接"""
        conn = get_connection()
        try:
            assert conn is not None
            # 验证连接有效
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
        finally:
            close_connection(conn)

    def test_connection_auto_returned_to_pool(self):
        """连接使用后应自动返回池中"""
        pool = get_connection_pool(max_connections=2)

        # 获取并释放连接
        conn1 = pool._acquire(timeout=1.0)
        pool._release(conn1)

        # 应能再次获取同一个连接（被池化）
        conn2 = pool._acquire(timeout=1.0)
        assert conn2 is not None
        pool._release(conn2)

    def test_pool_stats(self):
        """连接池应提供统计信息"""
        pool = get_connection_pool(max_connections=4)
        stats = pool.stats

        assert "max_connections" in stats
        assert "created" in stats
        assert "available" in stats


class TestConnectionPoolConcurrency(TestConnectionPoolBase):
    """并发连接池测试"""

    def test_concurrent_connections_without_deadlock(self):
        """并发获取连接不应导致死锁"""
        pool = get_connection_pool(max_connections=8)
        errors = []
        success_count = [0]

        def worker(worker_id):
            try:
                conn = pool._acquire(timeout=5.0)
                # 执行简单查询
                result = conn.execute("SELECT 1").fetchone()
                assert result[0] == 1
                pool._release(conn)
                success_count[0] += 1
            except Exception as e:
                errors.append((worker_id, str(e)))

        # 启动 16 个线程并发获取连接
        threads = []
        for i in range(16):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        # 验证所有线程完成，无死锁
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert success_count[0] == 16, f"Only {success_count[0]} of 16 workers completed"

    def test_connection_pool_no_leak(self):
        """连接池不应泄漏连接"""
        pool = get_connection_pool(max_connections=4)
        initial_stats = pool.stats

        # 执行多次连接操作
        for _ in range(20):
            conn = pool._acquire(timeout=5.0)
            conn.execute("SELECT 1").fetchone()
            pool._release(conn)

        final_stats = pool.stats

        # 连接数应保持稳定
        assert final_stats["created"] <= pool._max

    def test_max_connections_enforced(self):
        """应强制执行最大连接数"""
        pool = get_connection_pool(max_connections=4)

        # 获取所有连接
        conns = []
        for i in range(4):
            conn = pool._acquire(timeout=1.0)
            conns.append(conn)

        # 第 5 个请求应超时
        with pytest.raises(TimeoutError):
            pool._acquire(timeout=0.5)

        # 释放所有连接
        for conn in conns:
            pool._release(conn)


class TestConnectionPoolStress(TestConnectionPoolBase):
    """连接池压力测试"""

    def test_stress_acquire_release(self):
        """压力测试：快速获取和释放"""
        pool = get_connection_pool(max_connections=8)
        iterations = 100
        errors = []

        def worker():
            for _ in range(iterations):
                conn = pool._acquire(timeout=5.0)
                try:
                    conn.execute("SELECT 1").fetchone()
                finally:
                    pool._release(conn)

        threads = [threading.Thread(target=worker) for _ in range(8)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60.0)

        assert len(errors) == 0, f"Errors: {errors}"


class TestConnectionPoolIntegration(TestConnectionPoolBase):
    """连接池集成测试"""

    def test_account_operations_with_pool(self):
        """使用连接池的账户操作应正常工作"""
        db = AccountDB()

        # 创建测试账户
        test_id = f"pool_test_{threading.current_thread().ident}"
        account = Account(
            account_id=test_id,
            account_name="Pool Test",
            initial_capital=50_000.0,
            cash=50_000.0,
        )
        assert db.create_account(account)

        # 使用连接池获取连接进行操作
        pool = get_connection_pool()
        conn = pool._acquire(timeout=5.0)
        try:
            row = conn.execute(
                "SELECT cash FROM accounts WHERE account_id = ?",
                (test_id,)
            ).fetchone()
            assert row is not None
            assert row[0] == 50_000.0
        finally:
            pool._release(conn)

        # 清理
        conn = pool._acquire(timeout=5.0)
        try:
            conn.execute("DELETE FROM accounts WHERE account_id = ?", (test_id,))
            conn.commit()
        finally:
            pool._release(conn)


class TestConnectionPoolThreadSafety(TestConnectionPoolBase):
    """线程安全性测试"""

    def test_rapid_interleaved_operations(self):
        """快速交错的数据库操作"""
        pool = get_connection_pool(max_connections=4)
        results = {"select": 0, "insert": 0, "error": 0}
        lock = threading.Lock()

        def select_worker():
            for _ in range(50):
                conn = pool._acquire(timeout=5.0)
                try:
                    conn.execute("SELECT 1").fetchone()
                    with lock:
                        results["select"] += 1
                finally:
                    pool._release(conn)

        def insert_worker():
            for i in range(50):
                conn = pool._acquire(timeout=5.0)
                try:
                    conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
                    with lock:
                        results["insert"] += 1
                finally:
                    pool._release(conn)

        threads = [
            threading.Thread(target=select_worker),
            threading.Thread(target=select_worker),
            threading.Thread(target=insert_worker),
            threading.Thread(target=insert_worker),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        assert results["select"] == 100
        assert results["insert"] == 100
