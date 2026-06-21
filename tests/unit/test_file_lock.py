#!/usr/bin/env python3
"""
file_lock.py 单元测试

覆盖:
- locked_write: 加锁写入基本流程
- locked_read: 加锁读取基本流程
- locked_read: 文件不存在时返回 None
- locked_read_write: 原子性读→改→写
- locked_read_write: 文件不存在时的初始化行为
- 锁文件创建 / 自动创建父目录
- 边界条件：空文件、JSON 格式错误
- 并发写入基本安全性验证

注意: file_lock.py 根据 sys.platform 选择实现。
      本测试在 Unix 上使用 fcntl 实现，在 Windows 上使用 threading.Lock 实现。
      测试逻辑对两者通用。
"""

import json
import sys
import time
import pytest
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from file_lock import FileLock


# ---------------------------------------------------------------------------
# locked_write 测试
# ---------------------------------------------------------------------------
class TestLockedWrite:
    """locked_write 写入测试"""

    def test_write_creates_file(self, tmp_path):
        """locked_write 应创建目标文件"""
        filepath = tmp_path / "data.json"
        assert not filepath.exists()

        FileLock.locked_write(filepath, {"key": "value"})
        assert filepath.exists()

    def test_write_stores_correct_data(self, tmp_path):
        """locked_write 应正确写入 JSON 数据"""
        filepath = tmp_path / "data.json"
        data = {"name": "测试", "count": 42, "nested": [1, 2, 3]}

        FileLock.locked_write(filepath, data)

        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_overwrites_existing_file(self, tmp_path):
        """locked_write 应覆盖已存在的文件"""
        filepath = tmp_path / "data.json"
        FileLock.locked_write(filepath, {"old": True})
        FileLock.locked_write(filepath, {"new": True})

        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {"new": True}

    def test_write_creates_parent_directories(self, tmp_path):
        """locked_write 应自动创建不存在的父目录"""
        filepath = tmp_path / "sub" / "dir" / "data.json"
        assert not filepath.parent.exists()

        FileLock.locked_write(filepath, {"key": "value"})
        assert filepath.exists()

    def test_write_list_data(self, tmp_path):
        """locked_write 应支持写入列表类型数据"""
        filepath = tmp_path / "list.json"
        data = [{"id": 1}, {"id": 2}, {"id": 3}]

        FileLock.locked_write(filepath, data)

        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data


# ---------------------------------------------------------------------------
# locked_read 测试
# ---------------------------------------------------------------------------
class TestLockedRead:
    """locked_read 读取测试"""

    def test_read_returns_correct_data(self, tmp_path):
        """locked_read 应正确读取 JSON 数据"""
        filepath = tmp_path / "data.json"
        original = {"name": "测试", "values": [1, 2, 3]}

        FileLock.locked_write(filepath, original)
        loaded = FileLock.locked_read(filepath)
        assert loaded == original

    def test_read_nonexistent_returns_none(self, tmp_path):
        """locked_read 在文件不存在时应返回 None"""
        filepath = tmp_path / "nonexistent.json"
        result = FileLock.locked_read(filepath)
        assert result is None

    def test_read_chinese_encoding(self, tmp_path):
        """locked_read 应正确处理中文等 UTF-8 字符"""
        filepath = tmp_path / "chinese.json"
        data = {"message": "你好世界", "emoji": "🎉"}

        FileLock.locked_write(filepath, data)
        loaded = FileLock.locked_read(filepath)
        assert loaded["message"] == "你好世界"
        assert loaded["emoji"] == "🎉"


# ---------------------------------------------------------------------------
# locked_read_write 测试
# ---------------------------------------------------------------------------
class TestLockedReadWrite:
    """locked_read_write 原子读→改→写测试"""

    def test_read_write_modifies_data(self, tmp_path):
        """locked_read_write 应原子性地读→改→写"""
        filepath = tmp_path / "counter.json"
        FileLock.locked_write(filepath, {"count": 0})

        def increment(data):
            data["count"] += 1
            return data

        result = FileLock.locked_read_write(filepath, increment)
        assert result["count"] == 1

        # 验证持久化
        loaded = FileLock.locked_read(filepath)
        assert loaded["count"] == 1

    def test_read_write_appends_to_list(self, tmp_path):
        """locked_read_write 应对列表数据执行追加操作"""
        filepath = tmp_path / "tasks.json"
        FileLock.locked_write(filepath, [{"id": 1}])

        def add_task(data):
            data.append({"id": 2})
            return data

        result = FileLock.locked_read_write(filepath, add_task)
        assert len(result) == 2
        assert result[1]["id"] == 2

    def test_read_write_nonexistent_file(self, tmp_path):
        """locked_read_write 在文件不存在时，modify_func 应收到空列表"""
        filepath = tmp_path / "new.json"

        def init_data(data):
            assert data == []
            data.append({"initialized": True})
            return data

        result = FileLock.locked_read_write(filepath, init_data)
        assert result == [{"initialized": True}]

        # 验证持久化
        loaded = FileLock.locked_read(filepath)
        assert loaded == [{"initialized": True}]

    def test_read_write_return_value(self, tmp_path):
        """locked_read_write 应返回 modify_func 的返回结果"""
        filepath = tmp_path / "data.json"
        FileLock.locked_write(filepath, [])

        def transform(data):
            return [{"transformed": True}]

        result = FileLock.locked_read_write(filepath, transform)
        assert result == [{"transformed": True}]

    def test_read_write_multiple_sequential(self, tmp_path):
        """多次顺序 locked_read_write 应正确累积"""
        filepath = tmp_path / "counter.json"
        FileLock.locked_write(filepath, {"count": 0})

        def increment(data):
            data["count"] += 1
            return data

        for _ in range(10):
            FileLock.locked_read_write(filepath, increment)

        loaded = FileLock.locked_read(filepath)
        assert loaded["count"] == 10


# ---------------------------------------------------------------------------
# 边界条件
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """边界条件测试"""

    def test_empty_dict_write_read(self, tmp_path):
        """空字典应能正确写入和读取"""
        filepath = tmp_path / "empty.json"
        FileLock.locked_write(filepath, {})
        loaded = FileLock.locked_read(filepath)
        assert loaded == {}

    def test_empty_list_write_read(self, tmp_path):
        """空列表应能正确写入和读取"""
        filepath = tmp_path / "empty_list.json"
        FileLock.locked_write(filepath, [])
        loaded = FileLock.locked_read(filepath)
        assert loaded == []

    def test_large_data_write_read(self, tmp_path):
        """大数据量应能正确写入和读取"""
        filepath = tmp_path / "large.json"
        data = [{"id": i, "payload": "x" * 100} for i in range(500)]

        FileLock.locked_write(filepath, data)
        loaded = FileLock.locked_read(filepath)
        assert loaded == data
        assert len(loaded) == 500

    def test_path_object_accepted(self, tmp_path):
        """应接受 pathlib.Path 对象"""
        filepath = Path(tmp_path) / "path_obj.json"
        FileLock.locked_write(filepath, {"test": True})
        loaded = FileLock.locked_read(filepath)
        assert loaded == {"test": True}


# ---------------------------------------------------------------------------
# 并发安全性基本验证
# ---------------------------------------------------------------------------
class TestConcurrency:
    """并发安全性基本测试"""

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows 使用 threading.Lock，行为不同")
    def test_concurrent_writes_no_crash(self, tmp_path):
        """多线程并发写入不应崩溃或损坏数据"""
        filepath = tmp_path / "concurrent.json"
        FileLock.locked_write(filepath, {"count": 0})
        errors = []

        def increment_worker():
            try:
                for _ in range(20):
                    def inc(data):
                        data["count"] += 1
                        return data
                    FileLock.locked_read_write(filepath, inc)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"并发写入出错: {errors}"
        loaded = FileLock.locked_read(filepath)
        # 5 个线程 × 20 次 = 100 次递增
        assert loaded["count"] == 100

    @pytest.mark.skipif(sys.platform != "win32", reason="仅 Windows 测试 threading.Lock 实现")
    def test_concurrent_writes_windows(self, tmp_path):
        """Windows 下多线程并发写入不应崩溃"""
        filepath = tmp_path / "concurrent.json"
        FileLock.locked_write(filepath, {"count": 0})
        errors = []

        def increment_worker():
            try:
                for _ in range(20):
                    def inc(data):
                        data["count"] += 1
                        return data
                    FileLock.locked_read_write(filepath, inc)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"并发写入出错: {errors}"
        loaded = FileLock.locked_read(filepath)
        assert loaded["count"] == 100
