"""
线程安全连接池

Phase 5: 性能优化 - 连接池管理
- 单例模式，全局一个连接池
- 最大连接数: 8 (SQLite 建议不超过 16)
- 连接复用，避免频繁创建/销毁
- 超时等待 (5s)，避免阻塞
- 线程安全 (使用 Lock 保护共享状态)
"""
import sqlite3
import threading
import logging
from contextlib import contextmanager
from queue import Queue, Empty
from typing import Optional
from pathlib import Path


DB_PATH = Path(__file__).parent / "trading.db"

logger = logging.getLogger(__name__)


class ConnectionPool:
    """线程安全 SQLite 连接池

    设计原则:
    1. 单例模式，全局一个连接池
    2. 最大连接数: 8 (SQLite 建议不超过 16)
    3. 连接复用，避免频繁创建/销毁
    4. 超时等待 (5s)，避免阻塞
    5. WAL 模式支持并发读写
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_connections: int = 8):
        """单例模式 - 最多创建一次实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pool = Queue(maxsize=max_connections)
                    cls._instance._created = 0
                    cls._instance._max = max_connections
                    cls._instance._active_connections = set()
                    cls._instance._state_lock = threading.Lock()
        return cls._instance

    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """获取连接的上下文管理器

        Args:
            timeout: 等待连接的最大时间（秒）

        Yields:
            sqlite3.Connection: 数据库连接

        Raises:
            TimeoutError: 超时未获取到连接
        """
        conn = self._acquire(timeout)
        try:
            yield conn
        finally:
            self._release(conn)

    def _acquire(self, timeout: float) -> sqlite3.Connection:
        """获取连接（内部方法）

        Args:
            timeout: 等待时间（秒）

        Returns:
            sqlite3.Connection: 数据库连接

        Raises:
            TimeoutError: 超时未获取到连接
        """
        # 尝试从池中获取空闲连接
        try:
            conn = self._pool.get_nowait()
            return conn
        except Empty:
            pass

        # 池为空，尝试创建新连接（如果未达上限）
        with self._state_lock:
            if self._created < self._max:
                conn = self._create_connection()
                self._created += 1
                self._active_connections.add(conn)
                return conn

        # 所有连接都在使用中，等待可用连接
        try:
            conn = self._pool.get(timeout=timeout)
            return conn
        except Empty:
            raise TimeoutError(
                f"Failed to acquire connection within {timeout}s. "
                f"All {self._max} connections are in use."
            )

    def _release(self, conn: sqlite3.Connection) -> None:
        """释放连接回池中（内部方法）

        Args:
            conn: 要释放的连接
        """
        try:
            # 检查连接是否仍然有效
            conn.execute("SELECT 1").fetchone()
            self._pool.put_nowait(conn)
        except Exception as e:
            # 连接已损坏，关闭并从活动连接中移除
            logger.warning(f"Database connection check failed: {e}")
            with self._state_lock:
                self._active_connections.discard(conn)
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"Failed to close damaged connection: {close_error}")

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接

        Returns:
            sqlite3.Connection: 创建的连接
        """
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # 启用 WAL 模式：支持并发读写，提升并发性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")  # 30秒等待锁
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @property
    def stats(self) -> dict:
        """获取连接池统计信息"""
        return {
            "max_connections": self._max,
            "created": self._created,
            "available": self._pool.qsize() if hasattr(self._pool, 'qsize') else "N/A",
        }

    def close_all(self) -> None:
        """关闭所有连接（用于测试或清理）"""
        with self._state_lock:
            # 关闭所有活动连接
            for conn in list(self._active_connections):
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Failed to close active connection: {e}")
            self._active_connections.clear()

            # 清空池中的连接
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Failed to close pooled connection: {e}")
                    pass
            self._created = 0


# 全局连接池实例
_pool: Optional[ConnectionPool] = None


def get_connection_pool(max_connections: int = 8) -> ConnectionPool:
    """获取全局连接池实例

    Args:
        max_connections: 最大连接数

    Returns:
        ConnectionPool: 连接池实例
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(max_connections=max_connections)
    return _pool


def get_connection() -> sqlite3.Connection:
    """获取数据库连接（通过连接池）

    这是 weakened 的 get_connection，用于向后兼容。

    Returns:
        sqlite3.Connection: 数据库连接
    """
    pool = get_connection_pool()
    # 使用上下文管理器获取连接，但这里不使用 with
    # 调用方需要自行 close，或者使用 pool.get_connection() with 语句
    conn = pool._acquire(timeout=5.0)
    return conn


def close_connection(conn: sqlite3.Connection) -> None:
    """关闭数据库连接（归还到池中）

    这是 weakened close_connection，用于向后兼容。

    Args:
        conn: 要关闭的连接
    """
    pool = get_connection_pool()
    pool._release(conn)


if __name__ == '__main__':
    # 简单测试
    pool = get_connection_pool(max_connections=4)

    # 测试获取连接
    with pool.get_connection() as conn:
        result = conn.execute("SELECT 1").fetchone()
        print(f"Connection test: {result[0]}")

    # 测试统计
    print(f"Pool stats: {pool.stats}")

    # 测试多连接
    print("Testing multiple connections...")
    conns = []
    for i in range(4):
        conns.append(pool._acquire(timeout=1.0))
    print(f"Acquired {len(conns)} connections")

    # 归还所有连接
    for c in conns:
        pool._release(c)
    print("All connections released")
