#!/usr/bin/env python3
"""
Manager Interface 边界条件和异常情况测试

目标：
- 测试边界条件（空值、None、特殊字符等）
- 测试异常情况（文件读写失败、权限问题等）
- 提高测试覆盖率
"""

import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager


class TestQuantManagerEdgeCases:
    """QuantManager 边界条件和异常情况测试"""
    
    @pytest.fixture
    def manager(self):
        """创建测试用 manager"""
        test_dir = Path('./tests/fixtures/test_manager_edge_cases')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        return QuantManager(base_dir=str(test_dir))
    
    @pytest.fixture
    def sample_issue(self):
        """创建示例 Issue"""
        return Issue(
            id='test-issue',
            agent='test-agent',
            error_type="AssertionError",
            error_message="Test assertion failed",
            severity="P1"
        )
    
    # ==================== 边界条件测试 ====================
    
    def test_init_with_empty_base_dir(self):
        """测试空 base_dir"""
        manager = QuantManager(base_dir='')
        assert manager.base_dir is not None
        assert manager.issue_queue is not None
    
    def test_init_with_special_characters_base_dir(self):
        """测试特殊字符 base_dir"""
        manager = QuantManager(base_dir='./test@dir#1')
        assert manager.base_dir is not None
        assert manager.issue_queue is not None
    
    def test_select_agent_with_empty_string(self, manager):
        """测试空字符串 Agent"""
        agent = manager.select_agent('')
        assert agent is not None
    
    def test_select_agent_with_none(self, manager):
        """测试 None Agent"""
        agent = manager.select_agent(None)
        assert agent is not None
    
    def test_select_agent_with_special_characters(self, manager):
        """测试特殊字符 Agent"""
        agent = manager.select_agent('test@agent#1')
        assert agent is not None
    
    def test_analyze_error_with_empty_strings(self, manager):
        """测试空字符串错误分析"""
        issue = Issue(
            id='test',
            agent='test',
            error_type='',
            error_message='',
            severity='P1'
        )
        result = manager.analyze_error(issue)
        assert result is not None
    
    def test_analyze_error_with_none_strings(self, manager):
        """测试 None 字符串错误分析 - 代码不处理 None"""
        issue = Issue(
            id='test',
            agent='test',
            error_type=None,
            error_message=None,
            severity='P1'
        )
        result = manager.analyze_error(issue)
        assert result is not None
    
    def test_handle_p0_with_empty_task(self, manager, sample_issue):
        """测试空 P0 任务 - 代码不设置 status"""
        task = {}
        manager.handle_p0(task, sample_issue)
        assert 'agent' in task
    
    def test_handle_p1_with_empty_task(self, manager, sample_issue):
        """测试空 P1 任务 - 代码不设置 status"""
        task = {}
        manager.handle_p1(task, sample_issue)
        assert 'agent' in task
    
    def test_handle_p2_with_empty_task(self, manager, sample_issue):
        """测试空 P2 任务 - 代码不设置 status"""
        task = {}
        manager.handle_p2(task, sample_issue)
        assert 'agent' in task
    
    def test_dispatch_to_delta_with_empty_issue(self, manager):
        """测试空 Issue 调度 Delta"""
        issue = Issue(
            id='test',
            agent='',
            error_type='',
            error_message='',
            severity='P2'
        )
        manager.dispatch_to_delta(issue)
        # 应该不会抛出异常
    
    def test_complete_task_with_empty_issue_id(self, manager):
        """测试空 issue_id 完成任务 - 返回 {}"""
        result = manager.complete_task('', 'Test resolution', success=True)
        assert result == {}
    
    def test_complete_task_with_nonexistent_issue_id(self, manager):
        """测试不存在的问题完成任务 - 返回 {}"""
        result = manager.complete_task('non_existent_id', 'Test resolution', success=True)
        assert result == {}
    
    def test_resolve_issue_with_empty_issue_id(self, manager):
        """测试空 issue_id 解决问题 - 返回 {}"""
        result = manager.resolve_issue('', 'Test resolution')
        assert result == {}
    
    def test_resolve_issue_with_nonexistent_issue_id(self, manager):
        """测试不存在的问题解决问题 - 返回 {}"""
        result = manager.resolve_issue('non_existent_id', 'Test resolution')
        assert result == {}
    
    def test_get_status_with_empty_active_tasks(self, manager):
        """测试空活跃任务状态"""
        status = manager.get_status()
        assert 'active_tasks' in status
        assert 'pending_issues' in status
    
    def test_check_and_process_issues_with_empty_queue(self, manager):
        """测试空队列检查处理"""
        manager.check_and_process_issues()
        # 应该不会抛出异常
    
    # ==================== 异常情况测试 ====================
    
    def test_handle_error_report_with_empty_issue(self, manager):
        """测试空 Issue 错误报告"""
        issue = Issue(
            id='',
            agent='',
            error_type='',
            error_message='',
            severity='P1'
        )
        task = manager.handle_error_report(issue)
        assert task is not None
    
    def test_handle_error_report_with_none_issue(self, manager):
        """测试 None Issue 错误报告"""
        with pytest.raises((AttributeError, TypeError)):
            manager.handle_error_report(None)
    
    def test_dispatch_to_delta_with_invalid_priority(self, manager):
        """测试无效优先级调度 Delta"""
        issue = Issue(
            id='test',
            agent='test',
            error_type='Error',
            error_message='Test',
            severity='P2'
        )
        manager.dispatch_to_delta(issue, priority='invalid_priority')
        # 应该不会抛出异常
    
    def test_complete_task_with_invalid_resolution(self, manager):
        """测试无效 resolution 完成任务 - 返回 {}"""
        result = manager.complete_task('test-issue', '', success=True)
        assert result == {}
    
    def test_complete_task_with_success_false(self, manager):
        """测试失败的任务完成 - 返回 None"""
        result = manager.complete_task('test-issue', 'Test resolution', success=False)
        assert result is None
    
    def test_complete_task_with_success_true_and_active_task(self, manager, sample_issue):
        """测试成功完成任务（有活跃任务）"""
        manager.handle_error_report(sample_issue)
        result = manager.complete_task(sample_issue.id, 'Test resolution', success=True)
        assert result is not None
        assert 'issue_id' in result
    
    def test_complete_task_with_success_false_and_active_task(self, manager, sample_issue):
        """测试失败完成任务（有活跃任务）- 返回 None"""
        manager.handle_error_report(sample_issue)
        result = manager.complete_task(sample_issue.id, 'Test resolution', success=False)
        assert result is None
    
    def test_generate_completion_report_with_empty_issue_id(self, manager):
        """测试空 issue_id 生成完成报告 - 返回 {}"""
        result = manager.generate_completion_report('', 'Test resolution')
        assert result == {}
    
    def test_generate_completion_report_with_nonexistent_issue(self, manager):
        """测试不存在的问题生成完成报告 - 返回 {}"""
        result = manager.generate_completion_report('non_existent_id', 'Test resolution')
        assert result == {}
    
    def test_analyze_error_with_exception(self, manager):
        """测试分析错误时抛出异常"""
        issue = Issue(
            id='test',
            agent='test',
            error_type='TestError',
            error_message='Test',
            severity='P1'
        )
        with patch.object(manager.glm_analyzer, 'analyze', side_effect=Exception("GLM error")):
            result = manager.analyze_error(issue)
            assert result is not None
    
    def test_handle_p0_with_exception(self, manager, sample_issue):
        """测试 P0 处理时抛出异常 - 异常被捕获"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P0',
            'status': 'assigned'
        }
        with patch.object(manager.notifier, 'send_alert', side_effect=Exception("Alert error")):
            result = manager.handle_p0(task, sample_issue)
            assert 'agent' in result
    
    def test_handle_p1_with_exception(self, manager, sample_issue):
        """测试 P1 处理时抛出异常 - 异常被捕获"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P1',
            'status': 'assigned'
        }
        with patch.object(manager.notifier, 'send_alert', side_effect=Exception("Alert error")):
            result = manager.handle_p1(task, sample_issue)
            assert 'agent' in result
    
    def test_handle_p2_with_exception(self, manager, sample_issue):
        """测试 P2 处理时抛出异常 - 异常被捕获"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P2',
            'status': 'assigned'
        }
        with patch.object(manager, 'auto_retry_or_queue', side_effect=Exception("Retry error")):
            result = manager.handle_p2(task, sample_issue)
            assert 'agent' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
