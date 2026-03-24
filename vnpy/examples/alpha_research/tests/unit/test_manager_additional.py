#!/usr/bin/env python3
"""
QuantManager 额外测试 - 覆盖剩余方法

目标：提高 manager_interface.py 覆盖率到 90%
"""

import pytest
import json
import shutil
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from manager_interface import QuantManager


class TestQuantManagerAdditional:
    """QuantManager 额外测试"""
    
    @pytest.fixture
    def test_manager(self):
        """创建测试 Manager"""
        original_dir = os.getcwd()
        test_dir = Path('./tests/fixtures/test_manager_add')
        test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(str(test_dir))
        
        manager = QuantManager()
        yield manager
        
        os.chdir(original_dir)
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_handle_p0_creates_task(self, test_manager):
        """测试 handle_p0 创建任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P0',
            error_type='CriticalError',
            error_message='严重错误'
        )
        
        task = {'type': 'critical_fix', 'priority': 'immediate'}
        
        # 应该不抛出异常
        result = test_manager.handle_p0(task, issue)
        assert result is not None
    
    def test_handle_p1_creates_task(self, test_manager):
        """测试 handle_p1 创建任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='ImportantError',
            error_message='重要错误'
        )
        
        task = {'type': 'important_fix', 'priority': 'high'}
        
        # 应该不抛出异常
        result = test_manager.handle_p1(task, issue)
        assert result is not None
    
    def test_handle_p2_creates_task(self, test_manager):
        """测试 handle_p2 创建任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P2',
            error_type='MinorError',
            error_message='小错误'
        )
        
        task = {'type': 'minor_fix', 'priority': 'normal'}
        
        # 应该不抛出异常
        result = test_manager.handle_p2(task, issue)
        assert result is not None
    
    def test_complete_task_with_active_task(self, test_manager):
        """测试完成活跃任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TaskError',
            error_message='任务错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 添加活跃任务
        test_manager.active_tasks[issue_id] = {
            'type': 'test_task',
            'status': 'running'
        }
        
        # 完成任务
        result = test_manager.complete_task(issue_id, '已完成', success=True)
        
        # 应该生成报告
        assert result is not None
        assert isinstance(result, dict)
    
    def test_complete_task_failure_reopens(self, test_manager):
        """测试完成任务失败时重新打开"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TaskError',
            error_message='任务错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 添加活跃任务
        test_manager.active_tasks[issue_id] = {
            'type': 'test_task',
            'status': 'running'
        }
        
        # 完成任务失败
        result = test_manager.complete_task(issue_id, '失败', success=False)
        
        # 应该返回 None（重新打开）
        assert result is None
        
        # 问题应该回到 pending
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated.status == 'pending'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
