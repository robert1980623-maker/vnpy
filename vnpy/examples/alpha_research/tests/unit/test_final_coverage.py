#!/usr/bin/env python3
"""
最终覆盖率补充测试

针对未覆盖的代码行添加测试
"""

import pytest
import shutil
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager


class TestIssueQueueFinal:
    """IssueQueue 最终补充测试"""
    
    @pytest.fixture
    def test_queue(self):
        test_dir = Path('./tests/fixtures/test_final')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        iq = IssueQueue(base_dir=str(test_dir))
        yield iq
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_update_status_all_params(self, test_queue):
        """测试 update_status 所有参数"""
        issue = test_queue.create_issue('agent', 'P1', 'Error', 'Msg')
        issue_id = test_queue.write_issue(issue)
        
        # 更新为 processing
        test_queue.update_status(issue_id, 'processing', 'reviewer')
        updated = test_queue.read_issue(issue_id)
        assert updated.status == 'processing'
        assert updated.assigned_to == 'reviewer'
    
    def test_get_issues_by_severity_all(self, test_queue):
        """测试获取所有严重性问题"""
        for sev in ['P0', 'P1', 'P2', 'P3']:
            issue = test_queue.create_issue('agent', sev, 'Error', 'Msg')
            test_queue.write_issue(issue)
        
        for sev in ['P0', 'P1', 'P2', 'P3']:
            issues = test_queue.get_issues_by_severity(sev)
            assert len(issues) >= 1


class TestManagerFinal:
    """QuantManager 最终补充测试"""
    
    @pytest.fixture
    def test_manager(self):
        orig_dir = os.getcwd()
        test_dir = Path('./tests/fixtures/test_mgr_final')
        test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(str(test_dir))
        mgr = QuantManager()
        yield mgr
        os.chdir(orig_dir)
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_handle_p0_with_agent(self, test_manager):
        """测试 handle_p0 带 agent 字段"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P0',
            error_type='Critical',
            error_message='严重错误'
        )
        task = {'type': 'fix', 'priority': 'immediate', 'agent': 'delta'}
        result = test_manager.handle_p0(task, issue)
        assert result is not None
    
    def test_handle_p1_with_agent(self, test_manager):
        """测试 handle_p1 带 agent 字段"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Important',
            error_message='重要错误'
        )
        task = {'type': 'fix', 'priority': 'high', 'agent': 'engineer'}
        result = test_manager.handle_p1(task, issue)
        assert result is not None
    
    def test_handle_p2_basic(self, test_manager):
        """测试 handle_p2 基本功能"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P2',
            error_type='Minor',
            error_message='小错误'
        )
        task = {'type': 'fix', 'priority': 'normal'}
        result = test_manager.handle_p2(task, issue)
        # handle_p2 可能返回 None
        assert result is None or isinstance(result, dict)
    
    def test_complete_task_with_active(self, test_manager):
        """测试完成活跃任务"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 添加活跃任务
        test_manager.active_tasks[issue_id] = {'status': 'running'}
        
        # 完成成功
        report = test_manager.complete_task(issue_id, '已完成', success=True)
        assert isinstance(report, dict)
        
        # 问题应被解决
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated.status == 'resolved'
    
    def test_complete_task_failure(self, test_manager):
        """测试完成任务失败"""
        issue = test_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = test_manager.issue_queue.write_issue(issue)
        
        # 添加活跃任务
        test_manager.active_tasks[issue_id] = {'status': 'running'}
        
        # 完成失败
        result = test_manager.complete_task(issue_id, '失败', success=False)
        assert result is None
        
        # 问题应回到 pending
        updated = test_manager.issue_queue.read_issue(issue_id)
        assert updated.status in ['pending', 'processing']
    
    def test_analyze_error_various_types(self, test_manager):
        """测试分析各种错误类型"""
        for error_type in ['DataError', 'NetworkError', 'CodeError']:
            issue = test_manager.issue_queue.create_issue(
                agent='test',
                severity='P1',
                error_type=error_type,
                error_message=f'{error_type} 消息'
            )
            analysis = test_manager.analyze_error(issue)
            assert isinstance(analysis, str)
            assert len(analysis) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
