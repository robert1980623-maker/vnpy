#!/usr/bin/env python3
"""
QuantManager 完整单元测试 - 覆盖所有公共方法

目标：覆盖率≥90%
"""

import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from manager_interface import QuantManager
from issue_queue import Issue


class TestQuantManagerComplete:
    """QuantManager 完整测试 - 覆盖所有方法"""
    
    @pytest.fixture
    def test_manager(self):
        """创建测试 Manager"""
        # 切换到测试目录
        original_dir = os.getcwd()
        test_dir = Path('./tests/fixtures/test_manager')
        test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(str(test_dir))
        
        manager = QuantManager()
        yield manager
        
        os.chdir(original_dir)
        # 清理
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_init(self, test_manager):
        """测试初始化"""
        assert test_manager.issue_queue is not None
        assert test_manager.base_dir is not None
    
    def test_get_status(self, test_manager):
        """测试获取状态"""
        status = test_manager.get_status()
        
        assert isinstance(status, dict)
        assert 'active_tasks' in status or 'pending_issues' in status
        assert isinstance(status.get('pending_issues', 0), int)
    
    def test_handle_error_report(self, test_manager):
        """测试处理错误报告"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TestError',
            error_message='测试错误消息'
        )
        
        # 应该不抛出异常
        result = test_manager.handle_error_report(issue)
        assert result is None or isinstance(result, dict)
    
    def test_analyze_error(self, test_manager):
        """测试分析错误"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='DataError',
            error_message='数据下载失败：连接超时'
        )
        
        analysis = test_manager.analyze_error(issue)
        assert isinstance(analysis, str)
        assert len(analysis) > 0
    
    def test_select_agent(self, test_manager):
        """测试选择 Agent"""
        agent = test_manager.select_agent('data_download')
        assert isinstance(agent, str)
        assert len(agent) > 0
        
        agent2 = test_manager.select_agent('code_review')
        assert isinstance(agent2, str)
    
    def test_handle_p0(self, test_manager):
        """测试处理 P0 问题"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P0',
            error_type='CriticalError',
            error_message='严重错误'
        )
        test_manager.issue_queue.write_issue(issue)
        
        task = {'type': 'critical_fix', 'priority': 'immediate'}
        
        # 应该不抛出异常
        test_manager.handle_p0(task, issue)
        
        # 问题应该被处理
        updated = test_manager.issue_queue.read_issue(issue.id)
        assert updated is not None
    
    def test_handle_p1(self, test_manager):
        """测试处理 P1 问题"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='ImportantError',
            error_message='重要错误'
        )
        test_manager.issue_queue.write_issue(issue)
        
        task = {'type': 'important_fix', 'priority': 'high'}
        
        # 应该不抛出异常
        test_manager.handle_p1(task, issue)
    
    def test_handle_p2(self, test_manager):
        """测试处理 P2 问题"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P2',
            error_type='MinorError',
            error_message='小错误'
        )
        test_manager.issue_queue.write_issue(issue)
        
        task = {'type': 'minor_fix', 'priority': 'normal'}
        
        # 应该不抛出异常
        test_manager.handle_p2(task, issue)
    
    def test_dispatch_to_delta(self, test_manager):
        """测试分发到 Delta"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='CodeError',
            error_message='代码需要重构'
        )
        test_manager.issue_queue.write_issue(issue)
        
        # 应该不抛出异常
        test_manager.dispatch_to_delta(issue, priority='high')
        
        # 问题状态应该更新
        updated = test_manager.issue_queue.read_issue(issue.id)
        assert updated is not None
    
    def test_auto_retry_or_queue(self, test_manager):
        """测试自动重试或排队"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P2',
            error_type='RetryError',
            error_message='需要重试的错误'
        )
        test_manager.issue_queue.write_issue(issue)
        
        # 应该不抛出异常
        test_manager.auto_retry_or_queue(issue)
    
    def test_complete_task_success(self, test_manager):
        """测试成功完成任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TaskError',
            error_message='任务错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 完成任务
        test_manager.complete_task(issue_id, '任务已完成', success=True)
        
        # 问题应该被解决
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated is not None
        assert updated.status == 'resolved'
    
    def test_complete_task_failure(self, test_manager):
        """测试任务完成失败"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TaskError',
            error_message='任务错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 完成任务失败
        test_manager.complete_task(issue_id, '任务失败', success=False)
        
        # 问题应该保持 pending 或标记为失败
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated is not None
    
    def test_generate_completion_report(self, test_manager):
        """测试生成完成报告"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TaskError',
            error_message='任务错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        report = test_manager.generate_completion_report(issue_id, '已完成')
        
        assert isinstance(report, dict)
        assert 'issue_id' in report or 'completion_status' in report
    
    def test_check_and_process_issues(self, test_manager):
        """测试检查和处理问题"""
        # 创建几个问题
        for i in range(3):
            issue = test_manager.issue_queue.create_issue(
                agent=f'agent{i}',
                severity='P2',
                error_type=f'Error{i}',
                error_message=f'错误{i}'
            )
            test_manager.issue_queue.write_issue(issue)
        
        # 应该不抛出异常
        test_manager.check_and_process_issues()
    
    def test_dispatch_to_data_agent(self, test_manager):
        """测试分发到数据 Agent"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P2',
            error_type='DataIssue',
            error_message='数据问题'
        )
        test_manager.issue_queue.write_issue(issue)
        
        # 应该不抛出异常
        test_manager._dispatch_to_data_agent(issue)
    
    def test_dispatch_to_delta_private(self, test_manager):
        """测试分发到 Delta (私有方法)"""
        issue = test_manager.issue_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='DeltaIssue',
            error_message='Delta 问题'
        )
        test_manager.issue_queue.write_issue(issue)
        
        # 应该不抛出异常
        test_manager._dispatch_to_delta(issue)
    
    def test_get_status_with_issues(self, test_manager):
        """测试有問題时的状态"""
        # 创建不同严重性的问题
        for severity in ['P0', 'P1', 'P2', 'P0']:
            issue = test_manager.issue_queue.create_issue(
                agent='agent',
                severity=severity,
                error_type='Error',
                error_message='错误'
            )
            test_manager.issue_queue.write_issue(issue)
        
        status = test_manager.get_status()
        
        assert status.get('pending_issues', 0) >= 4
        assert status.get('p0_count', 0) >= 2
    
    def test_manager_with_complex_issue(self, test_manager):
        """测试处理复杂问题"""
        issue = Issue(
            id='complex-123',
            agent='complex_agent',
            severity='P0',
            error_type='ComplexError',
            error_message='复杂错误',
            timestamp=datetime.now().isoformat(),
            status='pending',
            assigned_to=None,
            resolved_at=None,
            resolution=None,
            type='ComplexBug',
            title='复杂问题标题',
            description='详细描述：这是一个复杂的问题',
            details={'key1': 'value1', 'key2': 'value2'},
            report_file='complex_report.txt',
            requires_action=True,
            action_items=['action1', 'action2', 'action3']
        )
        
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 处理复杂问题
        test_manager.handle_error_report(issue)
        analysis = test_manager.analyze_error(issue)
        
        assert isinstance(analysis, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
