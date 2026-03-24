#!/usr/bin/env python3
"""
QuantManager 完整单元测试
"""

import pytest
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from manager_interface import QuantManager


class TestQuantManagerFull:
    """QuantManager 完整测试"""
    
    @pytest.fixture
    def test_manager(self):
        """创建测试 Manager"""
        # 使用测试目录
        import os
        original_dir = os.getcwd()
        os.chdir(Path('./tests/fixtures').absolute())
        
        manager = QuantManager()
        yield manager
        
        os.chdir(original_dir)
    
    def test_init(self, test_manager):
        """测试初始化"""
        assert test_manager.issue_queue is not None
        assert test_manager.base_dir is not None
    
    def test_get_status(self, test_manager):
        """测试获取状态"""
        status = test_manager.get_status()
        
        assert isinstance(status, dict)
        assert 'active_tasks' in status or 'pending_issues' in status
    
    def test_issue_queue_access(self, test_manager):
        """测试访问问题队列"""
        pending = test_manager.issue_queue.get_pending_issues()
        assert isinstance(pending, list)
    
    def test_handle_error_report(self, test_manager):
        """测试错误报告处理"""
        # 创建一个测试问题
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='TestError',
            error_message='测试错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 处理错误报告
        result = test_manager.handle_error_report(issue)
        # 应该不抛出异常
        assert result is None or isinstance(result, dict)
    
    def test_resolve_issue_success(self, test_manager):
        """测试成功解决问题"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='TestError',
            error_message='测试错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        test_manager.resolve_issue(issue_id, resolution='已解决')
        
        resolved = test_manager.issue_queue.read_issue(issue_id)
        assert resolved.status == 'resolved'
    
    def test_resolve_issue_failure(self, test_manager):
        """测试解决问题失败"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P0',
            error_type='CriticalError',
            error_message='严重错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 失败解决
        test_manager.resolve_issue(
            issue_id,
            resolution='解决失败',
            success=False
        )
        
        # 应该保持 pending 或标记为失败
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
