"""
原子写入的失败队列 (Phase 4B)

提供 AtomicFailedQueue 类，用于安全地持久化下载失败记录：
- 原子写入：tmp + fsync + os.replace，崩溃不会丢失/损坏队列
- 跨进程安全：fcntl.flock 文件锁
- 线程安全：内部 threading.Lock
- 向后兼容：可读取旧格式（count/last_try），新写入使用 retries/timestamp

用法:
    from atomic_failed_queue import AtomicFailedQueue

    queue = AtomicFailedQueue(Path("data/failed_downloads.json"))
    queue.add("000001.SZSE", "API timeout")
    queue.remove("000001.SZSE")  # 下载成功后移除
    candidates = queue.get_retry_candidates(max_retries=3)
"""

import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# fcntl 仅在 POSIX 上可用；Windows 回退到无文件锁（仅靠 threading.Lock）
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


class AtomicFailedQueue:
    """
    原子写入的失败队列

    持久化下载失败记录到 JSON 文件，保证：
    1. 崩溃安全：写入 tmp → fsync → os.replace（原子替换）
    2. 跨进程安全：fcntl.flock 排他锁（POSIX）
    3. 线程安全：threading.Lock 保护内存操作

    文件格式:
    {
        "000001.SZSE": {
            "error": "API timeout",
            "retries": 2,
            "timestamp": "2026-06-23T17:30:00.000000"
        }
    }

    向后兼容：可读取旧格式（count/last_try 字段），
    新写入统一使用 retries/timestamp。
    """

    def __init__(self, path: Path):
        """
        Args:
            path: 失败队列 JSON 文件路径
        """
        self.path = Path(path)
        self.lock_file = self.path.with_suffix('.lock')
        self._lock = Lock()  # 进程内线程安全

    # ==================== 公开 API ====================

    def add(self, symbol: str, error: str):
        """
        添加/更新一条失败记录

        Args:
            symbol: 股票代码
            error: 错误信息
        """
        with self._combined_lock():
            failed = self._load()
            old = failed.get(symbol, {})
            # 向后兼容：如果旧记录用 count 字段，从中继承重试次数
            old_retries = old.get("retries", old.get("count", 0))
            failed[symbol] = {
                "error": error,
                "retries": old_retries + 1,
                "timestamp": datetime.now().isoformat(),
            }
            self._save_atomic(failed)

    def remove(self, symbol: str):
        """
        移除一条失败记录（下载成功后调用）

        Args:
            symbol: 股票代码
        """
        with self._combined_lock():
            failed = self._load()
            if symbol in failed:
                del failed[symbol]
                self._save_atomic(failed)

    def get_all(self) -> Dict:
        """
        获取全部失败记录

        Returns:
            dict: {symbol: {error, retries, timestamp}}
        """
        with self._combined_lock():
            return self._load()

    def get_retry_candidates(self, max_retries: int = 3) -> List[str]:
        """
        获取可重试的股票列表（重试次数 < max_retries）

        Args:
            max_retries: 最大重试次数

        Returns:
            list: 可重试的 symbol 列表
        """
        failed = self.get_all()
        candidates = []
        for symbol, info in failed.items():
            # 向后兼容：retries 或 count
            retries = info.get("retries", info.get("count", 0))
            if retries < max_retries:
                candidates.append(symbol)
        return candidates

    def clear(self):
        """清空失败队列"""
        with self._combined_lock():
            self._save_atomic({})

    def __len__(self) -> int:
        return len(self.get_all())

    def __contains__(self, symbol: str) -> bool:
        return symbol in self.get_all()

    # ==================== 内部方法 ====================

    @contextmanager
    def _combined_lock(self):
        """
        组合锁：threading.Lock（进程内）+ fcntl.flock（跨进程）

        文件锁在 POSIX 上使用 flock(2) 排他锁；
        Windows 上 fcntl 不可用，仅靠 threading.Lock。
        """
        with self._lock:
            lock_fd = None
            try:
                if _HAS_FCNTL:
                    # 确保锁文件所在目录存在
                    self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                    lock_fd = open(self.lock_file, 'w')
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                if lock_fd is not None:
                    try:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                        lock_fd.close()
                    except (OSError, ValueError):
                        pass
                # 清理锁文件（可选，忽略错误）
                try:
                    if self.lock_file.exists():
                        self.lock_file.unlink(missing_ok=True)
                except OSError:
                    pass

    def _load(self) -> Dict:
        """
        从文件加载失败队列

        Returns:
            dict: 失败记录，文件不存在或损坏时返回空字典
        """
        if not self.path.exists():
            return {}
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("Failed queue file %s is not a dict, resetting", self.path)
                return {}
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load queue from %s: %s", self.path, e)
            return {}

    def _save_atomic(self, data: Dict):
        """
        原子写入：tmp + fsync + os.replace

        1. 写入 .tmp 临时文件
        2. flush + fsync 确保数据落盘
        3. os.replace 原子替换目标文件（POSIX 上是原子操作）

        Args:
            data: 要写入的字典数据
        """
        # 确保目标目录存在
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = str(self.path) + '.tmp'
        try:
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # 确保数据写入磁盘
            os.replace(tmp_path, str(self.path))  # 原子替换
        except Exception:
            # 清理临时文件
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass
            raise
