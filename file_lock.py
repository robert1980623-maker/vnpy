#!/usr/bin/env python3
"""
文件锁工具 - 解决 JSON 文件并发读写的 race condition

问题: 三个模块通过 JSON 文件通信，无锁。
      读→改→写是经典的 race condition，高并发下任务丢失。

解决: 统一使用 fcntl 文件锁，确保读→改→写的原子性。
      Windows fallback 到 threading.Lock 对象模式。
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

# Windows fallback - 暴露模块级锁字典供外部使用
if sys.platform == 'win32':
    import threading
    _file_locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    class FileLock:
        """Windows 下的文件锁实现（基于 threading.Lock）"""
        
        @staticmethod
        def locked_write(filepath: Path, data: Any):
            """写锁 - 整个 write 过程加锁"""
            path_str = str(filepath.absolute())
            with _locks_lock:
                if path_str not in _file_locks:
                    _file_locks[path_str] = threading.Lock()
                lock = _file_locks[path_str]
            
            with lock:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        
        @staticmethod
        def locked_read(filepath: Path) -> Optional[Any]:
            """读锁 - 读完整过程加锁（共享锁可并发读）"""
            if not filepath.exists():
                return None
            path_str = str(filepath.absolute())
            with _locks_lock:
                if path_str not in _file_locks:
                    _file_locks[path_str] = threading.Lock()
                lock = _file_locks[path_str]
            
            with lock:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        @staticmethod
        def locked_read_write(filepath: Path, modify_func) -> Any:
            """原子性读→改→写（用于 dispatch_to_delta 等场景）"""
            path_str = str(filepath.absolute())
            with _locks_lock:
                if path_str not in _file_locks:
                    _file_locks[path_str] = threading.Lock()
                lock = _file_locks[path_str]
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with lock:
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = []
                
                data = modify_func(data)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return data

else:
    import fcntl

    class FileLock:
        """Unix 下的文件锁实现（基于 fcntl.flock）"""
        
        @staticmethod
        def locked_write(filepath: Path, data: Any):
            """写锁 - 整个 write 过程加排他锁"""
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        @staticmethod
        def locked_read(filepath: Path) -> Optional[Any]:
            """读锁 - 读完整过程加共享锁（多个读者可并发）"""
            if not filepath.exists():
                return None
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        @staticmethod
        def locked_read_write(filepath: Path, modify_func) -> Any:
            """原子性读→改→写（用于 dispatch_to_delta 等场景）"""
            filepath.parent.mkdir(parents=True, exist_ok=True)
            file_exists = filepath.exists()
            
            if file_exists:
                with open(filepath, 'r+', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        f.seek(0)
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = []
                        data = modify_func(data)
                        f.seek(0)
                        f.truncate()
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.flush()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return data
            else:
                data = modify_func([])
                with open(filepath, 'w', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.flush()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return data
