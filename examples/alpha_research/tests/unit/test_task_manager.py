#!/usr/bin/env python3
"""
任务管理器单元测试

测试 Manager 派发 → Agent 执行 → Manager 检查 → QA 闭环 完整流程
"""

import pytest
import shutil
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from task_manager import TaskManager, TaskStatus


class TestTaskManager:
    """任务管理器测试"""
    
    @pytest.fixture
    def task_manager(self):
        """创建任务管理器"""
        tm = TaskManager()
        yield tm
        # 清理
        if hasattr(tm, 'tasks'):
            tm.tasks.clear()
    
    def test_create_task(self, task_manager):
        """测试创建任务"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        
        assert task_id is not None
        assert task_id in task_manager.tasks
        assert task_manager.tasks[task_id]['status'] == TaskStatus.PENDING
    
    def test_assign_task(self, task_manager):
        """测试派发任务"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        result = task_manager.assign_task(task_id)
        
        assert result is True
        assert task_manager.tasks[task_id]['status'] == TaskStatus.ASSIGNED
    
    def test_execute_task_success(self, task_manager):
        """测试执行任务成功"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        task_manager.assign_task(task_id)
        
        success, output = task_manager.execute_task(
            task_id,
            'python3 -c "print(\'成功\')"'
        )
        
        assert success is True
        assert task_manager.tasks[task_id]['status'] == TaskStatus.COMPLETED
    
    def test_execute_task_failure(self, task_manager):
        """测试执行任务失败"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        task_manager.assign_task(task_id)
        
        success, output = task_manager.execute_task(
            task_id,
            'python3 -c "exit(1)"'
        )
        
        assert success is False
        assert task_manager.tasks[task_id]['status'] == TaskStatus.FAILED
    
    def test_check_task_result_success(self, task_manager):
        """测试检查任务结果成功"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        task_manager.assign_task(task_id)
        task_manager.execute_task(task_id, 'python3 -c "print(\'成功\')"')
        
        result = task_manager.check_task_result(task_id)
        
        assert result is True
        # 任务已归档
        assert task_id not in task_manager.tasks
    
    def test_get_task_status(self, task_manager):
        """测试获取任务状态"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        
        status = task_manager.get_task_status(task_id)
        
        assert status is not None
        assert status['task_id'] == task_id
        assert status['issue_id'] == issue_id
    
    def test_generate_report(self, task_manager):
        """测试生成报告"""
        issue = task_manager.issue_queue.create_issue(
            agent='test',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        issue_id = task_manager.issue_queue.write_issue(issue)
        
        task_id = task_manager.create_task(issue_id, 'delta', 'code_fix')
        task_manager.assign_task(task_id)
        task_manager.execute_task(task_id, 'python3 -c "print(\'成功\')"')
        task_manager.check_task_result(task_id)
        
        report = task_manager.generate_report()
        
        assert isinstance(report, dict)
        assert 'total_tasks' in report
        assert 'active_tasks' in report
        assert 'completed_tasks' in report
        assert report['total_tasks'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
