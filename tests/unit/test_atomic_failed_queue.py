#!/usr/bin/env python3
"""
atomic_failed_queue.py 单元测试

覆盖:
- AtomicFailedQueue 基本操作（add, remove, get_all, clear）
- 原子写入（tmp + fsync + os.replace）
- 崩溃安全（写入中断不损坏现有文件）
- 向后兼容（读取旧格式 count/last_try）
- get_retry_candidates（重试次数过滤）
- 线程安全（多线程并发写入）
- 跨进程安全（文件锁验证）
- 错误处理（文件不存在、文件损坏）

注意: 所有测试使用 tmp_path，不影响真实数据。
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'examples' / 'alpha_research'))

from atomic_failed_queue import AtomicFailedQueue


# ---------------------------------------------------------------------------
# 基本操作测试
# ---------------------------------------------------------------------------
class TestBasicOperations:
    """AtomicFailedQueue 基本操作测试"""

    @pytest.fixture
    def queue(self, tmp_path):
        """创建临时队列"""
        return AtomicFailedQueue(tmp_path / 'failed.json')

    def test_add_single(self, queue, tmp_path):
        """添加单条失败记录"""
        queue.add('000001.SZSE', 'API timeout')

        all_items = queue.get_all()
        assert '000001.SZSE' in all_items
        info = all_items['000001.SZSE']
        assert info['error'] == 'API timeout'
        assert info['retries'] == 1
        assert 'timestamp' in info

    def test_add_increments_retries(self, queue):
        """多次添加同一 symbol 应递增 retries"""
        queue.add('000001.SZSE', 'error 1')
        queue.add('000001.SZSE', 'error 2')
        queue.add('000001.SZSE', 'error 3')

        all_items = queue.get_all()
        assert all_items['000001.SZSE']['retries'] == 3
        assert all_items['000001.SZSE']['error'] == 'error 3'  # 更新为最新错误

    def test_remove(self, queue):
        """移除已有的 symbol"""
        queue.add('000001.SZSE', 'error')
        queue.add('000002.SZSE', 'error')

        queue.remove('000001.SZSE')

        all_items = queue.get_all()
        assert '000001.SZSE' not in all_items
        assert '000002.SZSE' in all_items

    def test_remove_nonexistent(self, queue):
        """移除不存在的 symbol 不应报错"""
        queue.remove('NONEXIST.SZSE')  # 不应抛异常

    def test_get_all_empty(self, queue):
        """空队列返回空字典"""
        assert queue.get_all() == {}

    def test_clear(self, queue):
        """清空队列"""
        queue.add('000001.SZSE', 'error')
        queue.add('000002.SZSE', 'error')
        queue.clear()
        assert queue.get_all() == {}

    def test_len(self, queue):
        """__len__ 返回队列大小"""
        assert len(queue) == 0
        queue.add('000001.SZSE', 'error')
        assert len(queue) == 1
        queue.add('000002.SZSE', 'error')
        assert len(queue) == 2
        queue.remove('000001.SZSE')
        assert len(queue) == 1

    def test_contains(self, queue):
        """__contains__ 检查 symbol 是否存在"""
        assert '000001.SZSE' not in queue
        queue.add('000001.SZSE', 'error')
        assert '000001.SZSE' in queue


# ---------------------------------------------------------------------------
# 原子写入测试
# ---------------------------------------------------------------------------
class TestAtomicWrite:
    """原子写入（tmp + fsync + os.replace）测试"""

    @pytest.fixture
    def queue(self, tmp_path):
        return AtomicFailedQueue(tmp_path / 'failed.json')

    def test_no_tmp_file_after_write(self, queue, tmp_path):
        """写入后不应残留 .tmp 文件"""
        queue.add('000001.SZSE', 'error')

        tmp_file = tmp_path / 'failed.json.tmp'
        assert not tmp_file.exists(), ".tmp 文件应已被清理"

        json_file = tmp_path / 'failed.json'
        assert json_file.exists(), "目标文件应已创建"

    def test_valid_json_after_write(self, queue, tmp_path):
        """写入后文件应是有效 JSON"""
        queue.add('000001.SZSE', 'error with special chars: 你好"世界')

        json_file = tmp_path / 'failed.json'
        with open(json_file) as f:
            data = json.load(f)
        assert '000001.SZSE' in data
        assert data['000001.SZSE']['error'] == 'error with special chars: 你好"世界'

    def test_atomic_write_crash_safety(self, queue, tmp_path):
        """
        写入中途崩溃不应损坏现有文件

        模拟: 先写一个正常文件，然后在 _save_atomic 的 os.replace 前抛异常，
        验证原文件保持不变。
        """
        json_file = tmp_path / 'failed.json'

        # 先写入一个正常文件
        original_data = {'EXIST.SZSE': {'error': 'original', 'retries': 1, 'timestamp': 'now'}}
        json_file.write_text(json.dumps(original_data))

        # 模拟 os.replace 抛异常（写入 tmp 后崩溃）
        with patch('atomic_failed_queue.os.replace', side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                queue.add('NEW.SZSE', 'new error')

        # 原文件应保持不变
        with open(json_file) as f:
            data = json.load(f)
        assert data == original_data
        assert 'NEW.SZSE' not in data

        # .tmp 文件应已被清理
        tmp_file = tmp_path / 'failed.json.tmp'
        assert not tmp_file.exists()

    def test_fsync_called(self, queue, tmp_path):
        """验证 fsync 被调用"""
        fsync_calls = []
        original_fsync = os.fsync

        def tracking_fsync(fd):
            fsync_calls.append(fd)
            return original_fsync(fd)

        with patch('atomic_failed_queue.os.fsync', side_effect=tracking_fsync):
            queue.add('000001.SZSE', 'error')

        assert len(fsync_calls) > 0, "fsync 应被调用"


# ---------------------------------------------------------------------------
# 向后兼容测试
# ---------------------------------------------------------------------------
class TestBackwardCompat:
    """向后兼容（旧格式 count/last_try）测试"""

    @pytest.fixture
    def queue(self, tmp_path):
        return AtomicFailedQueue(tmp_path / 'failed.json')

    def test_read_old_format(self, queue, tmp_path):
        """可读取旧格式（count/last_try）"""
        json_file = tmp_path / 'failed.json'
        old_data = {
            '000001.SZSE': {
                'error': 'old error',
                'count': 2,
                'last_try': '2026-06-23T10:00:00',
            }
        }
        json_file.write_text(json.dumps(old_data))

        all_items = queue.get_all()
        assert '000001.SZSE' in all_items
        assert all_items['000001.SZSE']['count'] == 2

    def test_add_to_old_format_inherits_count(self, queue, tmp_path):
        """向旧格式记录追加时，应继承 count 作为 retries 起点"""
        json_file = tmp_path / 'failed.json'
        old_data = {
            '000001.SZSE': {
                'error': 'old error',
                'count': 3,
                'last_try': '2026-06-23T10:00:00',
            }
        }
        json_file.write_text(json.dumps(old_data))

        queue.add('000001.SZSE', 'new error')

        all_items = queue.get_all()
        info = all_items['000001.SZSE']
        # 旧 count=3 + 1 = retries=4
        assert info['retries'] == 4
        assert info['error'] == 'new error'
        assert 'timestamp' in info  # 新格式

    def test_get_retry_candidates_old_format(self, queue, tmp_path):
        """get_retry_candidates 兼容旧格式"""
        json_file = tmp_path / 'failed.json'
        old_data = {
            'A.SZSE': {'error': 'e', 'count': 1, 'last_try': 'now'},  # 可重试
            'B.SZSE': {'error': 'e', 'count': 3, 'last_try': 'now'},  # 已达上限
            'C.SZSE': {'error': 'e', 'retries': 2, 'timestamp': 'now'},  # 新格式，可重试
        }
        json_file.write_text(json.dumps(old_data))

        candidates = queue.get_retry_candidates(max_retries=3)
        assert set(candidates) == {'A.SZSE', 'C.SZSE'}


# ---------------------------------------------------------------------------
# get_retry_candidates 测试
# ---------------------------------------------------------------------------
class TestRetryCandidates:
    """get_retry_candidates 重试候选测试"""

    @pytest.fixture
    def queue(self, tmp_path):
        return AtomicFailedQueue(tmp_path / 'failed.json')

    def test_empty_queue(self, queue):
        """空队列返回空列表"""
        assert queue.get_retry_candidates() == []

    def test_all_below_limit(self, queue):
        """全部低于限制时返回全部"""
        queue.add('A.SZSE', 'error')  # retries=1
        queue.add('B.SZSE', 'error')  # retries=1

        candidates = queue.get_retry_candidates(max_retries=3)
        assert set(candidates) == {'A.SZSE', 'B.SZSE'}

    def test_excludes_at_limit(self, queue):
        """已达上限的不包括在内"""
        for _ in range(3):
            queue.add('A.SZSE', 'error')  # retries=3
        queue.add('B.SZSE', 'error')  # retries=1

        candidates = queue.get_retry_candidates(max_retries=3)
        assert candidates == ['B.SZSE']

    def test_custom_max_retries(self, queue):
        """自定义 max_retries"""
        for _ in range(5):
            queue.add('A.SZSE', 'error')  # retries=5

        assert queue.get_retry_candidates(max_retries=3) == []
        assert queue.get_retry_candidates(max_retries=6) == ['A.SZSE']


# ---------------------------------------------------------------------------
# 错误处理测试
# ---------------------------------------------------------------------------
class TestErrorHandling:
    """错误处理测试"""

    def test_missing_file_returns_empty(self, tmp_path):
        """文件不存在时返回空字典"""
        queue = AtomicFailedQueue(tmp_path / 'nonexistent.json')
        assert queue.get_all() == {}
        assert queue.get_retry_candidates() == []

    def test_corrupt_json_returns_empty(self, tmp_path):
        """损坏的 JSON 文件返回空字典"""
        json_file = tmp_path / 'failed.json'
        json_file.write_text("not valid json {{{")

        queue = AtomicFailedQueue(json_file)
        assert queue.get_all() == {}

    def test_non_dict_json_returns_empty(self, tmp_path):
        """非字典 JSON 返回空字典"""
        json_file = tmp_path / 'failed.json'
        json_file.write_text("[1, 2, 3]")

        queue = AtomicFailedQueue(json_file)
        assert queue.get_all() == {}

    def test_creates_parent_directories(self, tmp_path):
        """自动创建父目录"""
        deep_path = tmp_path / 'a' / 'b' / 'c' / 'failed.json'
        queue = AtomicFailedQueue(deep_path)
        queue.add('000001.SZSE', 'error')
        assert deep_path.exists()


# ---------------------------------------------------------------------------
# 线程安全测试
# ---------------------------------------------------------------------------
class TestThreadSafety:
    """多线程并发写入测试"""

    def test_concurrent_adds(self, tmp_path):
        """多线程并发 add 不丢数据"""
        queue = AtomicFailedQueue(tmp_path / 'failed.json')
        num_threads = 10
        adds_per_thread = 20

        def add_batch(thread_id):
            for i in range(adds_per_thread):
                symbol = f'T{thread_id:02d}_{i:04d}.SZSE'
                queue.add(symbol, f'error from thread {thread_id}')

        threads = [
            threading.Thread(target=add_batch, args=(t,))
            for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_items = queue.get_all()
        expected = num_threads * adds_per_thread
        assert len(all_items) == expected, (
            f"预期 {expected} 条记录，实际 {len(all_items)} 条"
        )

    def test_concurrent_add_same_symbol(self, tmp_path):
        """多线程并发 add 同一 symbol，retries 应正确累加"""
        queue = AtomicFailedQueue(tmp_path / 'failed.json')
        num_threads = 8
        adds_per_thread = 10

        def add_same():
            for _ in range(adds_per_thread):
                queue.add('000001.SZSE', 'concurrent error')

        threads = [
            threading.Thread(target=add_same)
            for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_items = queue.get_all()
        assert '000001.SZSE' in all_items
        expected_retries = num_threads * adds_per_thread
        assert all_items['000001.SZSE']['retries'] == expected_retries, (
            f"预期 retries={expected_retries}，"
            f"实际 {all_items['000001.SZSE']['retries']}"
        )

    def test_concurrent_add_remove(self, tmp_path):
        """并发 add 和 remove 不损坏数据"""
        queue = AtomicFailedQueue(tmp_path / 'failed.json')
        errors = []

        def adder():
            try:
                for i in range(50):
                    queue.add(f'S{i}.SZSE', 'error')
            except Exception as e:
                errors.append(e)

        def remover():
            try:
                for i in range(50):
                    queue.remove(f'S{i}.SZSE')
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=adder),
            threading.Thread(target=remover),
            threading.Thread(target=adder),
            threading.Thread(target=remover),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发操作出错: {errors}"
        # 验证文件仍是有效 JSON
        all_items = queue.get_all()
        assert isinstance(all_items, dict)


# ---------------------------------------------------------------------------
# 跨进程安全测试（文件锁）
# ---------------------------------------------------------------------------
class TestFileLock:
    """文件锁测试"""

    def test_lock_file_created_and_cleaned(self, tmp_path):
        """锁文件在操作期间创建、操作后清理"""
        queue_path = tmp_path / 'failed.json'
        queue = AtomicFailedQueue(queue_path)

        lock_file = tmp_path / 'failed.lock'

        # 操作前无锁文件
        assert not lock_file.exists()

        queue.add('000001.SZSE', 'error')

        # 操作后锁文件应被清理
        assert not lock_file.exists(), "锁文件应在操作后清理"

    def test_sequential_access_safe(self, tmp_path):
        """顺序访问（模拟多进程）不丢数据"""
        queue_path = tmp_path / 'failed.json'

        # 模拟进程 1
        q1 = AtomicFailedQueue(queue_path)
        q1.add('A.SZSE', 'error from proc 1')

        # 模拟进程 2（使用不同实例，同一文件）
        q2 = AtomicFailedQueue(queue_path)
        q2.add('B.SZSE', 'error from proc 2')

        # 验证两边数据都在
        q3 = AtomicFailedQueue(queue_path)
        all_items = q3.get_all()
        assert 'A.SZSE' in all_items
        assert 'B.SZSE' in all_items


# ---------------------------------------------------------------------------
# 与 data_downloader 集成测试
# ---------------------------------------------------------------------------
class TestDataDownloaderIntegration:
    """与 data_downloader 模块级函数的集成测试"""

    def test_module_functions_use_atomic_queue(self, tmp_path):
        """验证模块级函数委托给 AtomicFailedQueue"""
        import data_downloader
        from atomic_failed_queue import AtomicFailedQueue

        # 替换模块级队列为临时队列
        test_queue_path = tmp_path / 'test_failed.json'
        test_queue = AtomicFailedQueue(test_queue_path)
        original_queue = data_downloader._failed_queue

        try:
            data_downloader._failed_queue = test_queue

            # 测试 add
            data_downloader.add_to_failed_queue('X.SZSE', 'test error')
            all_items = data_downloader.load_failed_downloads()
            assert 'X.SZSE' in all_items

            # 测试 remove
            data_downloader.remove_from_failed_queue('X.SZSE')
            all_items = data_downloader.load_failed_downloads()
            assert 'X.SZSE' not in all_items

            # 测试 get_retry_candidates
            data_downloader.add_to_failed_queue('Y.SZSE', 'error')
            candidates = data_downloader.get_retry_candidates(max_retry_count=3)
            assert 'Y.SZSE' in candidates
        finally:
            data_downloader._failed_queue = original_queue
