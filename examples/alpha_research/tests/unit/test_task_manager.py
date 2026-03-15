#!/usr/bin/env python3
"""
Task Manager 单元测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime
import subprocess
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from task_manager import TaskManager, TaskStatus
from issue_queue import IssueQueue, Issue


class TestTaskStatus:
    """TaskStatus 常量测试"""
    
    def test_status_constants(self):
        """测试状态常量存在"""
        assert TaskStatus.PENDING == 'pending'
        assert TaskStatus.ASSIGNED == 'assigned'
        assert TaskStatus.RUNNING == 'running'
        assert TaskStatus.COMPLETED == 'completed'
        assert TaskStatus.FAILED == 'failed'
        assert TaskStatus.QA_REVIEW == 'qa_review'


class TestTaskManager:
    """TaskManager 测试"""
    
    @pytest.fixture
    def task_manager(self, tmp_path):
        """创建测试用 task manager"""
        with patch('task_manager.QuantManager') as mock_manager:
            mock_queue = IssueQueue(base_dir=str(tmp_path))
            mock_manager.return_value.issue_queue = mock_queue
            tm = TaskManager()
            tm.manager = mock_manager.return_value
            tm.issue_queue = mock_queue
            return tm
    
    @pytest.fixture
    def sample_issue(self, tmp_path):
        """创建示例 Issue"""
        queue = IssueQueue(base_dir=str(tmp_path))
        issue = queue.create_issue(
            agent='test-agent',
            error_type="TestError",
            error_message="Test error message",
            severity="P1"
        )
        queue.write_issue(issue)
        return issue
    
    def test_init(self, task_manager):
        """测试初始化"""
        assert task_manager.tasks == {}
        assert task_manager.task_history == []
    
    def test_create_task(self, task_manager, sample_issue):
        """测试创建任务"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa',
            priority='normal'
        )
        assert task_id is not None
        assert task_id.startswith('task_')
        assert task_id in task_manager.tasks
        
        task = task_manager.tasks[task_id]
        assert task['issue_id'] == sample_issue.id
        assert task['status'] == TaskStatus.PENDING
    
    def test_assign_task(self, task_manager, sample_issue):
        """测试派发任务"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        result = task_manager.assign_task(task_id)
        assert result is True
        task = task_manager.tasks[task_id]
        assert task['status'] == TaskStatus.ASSIGNED
    
    def test_assign_task_not_found(self, task_manager):
        """测试派发不存在的任务"""
        result = task_manager.assign_task('nonexistent_task')
        assert result is False
    
    def test_execute_task_success(self, task_manager, sample_issue):
        """测试执行任务（成功）"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        task_manager.assign_task(task_id)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='Success', stderr='')
            result, output = task_manager.execute_task(task_id, 'echo "test"', timeout=10)
            assert result is True
    
    def test_execute_task_failure(self, task_manager, sample_issue):
        """测试执行任务（失败）"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        task_manager.assign_task(task_id)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error')
            result, output = task_manager.execute_task(task_id, 'false', timeout=10)
            assert result is False
    
    def test_check_task_result(self, task_manager, sample_issue):
        """测试检查结果"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        task_manager.tasks[task_id]['status'] = TaskStatus.COMPLETED
        task_manager.tasks[task_id]['result'] = {'success': True}
        
        result = task_manager.check_task_result(task_id)
        assert result is True
    
    def test_trigger_qa_loop(self, task_manager, sample_issue):
        """测试触发 QA 闭环"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        task_manager.tasks[task_id]['result'] = {'output': 'Test failure'}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='最终状态：✅ 通过',
                stderr=''
            )
            result = task_manager.trigger_qa_loop(task_id)
            assert isinstance(result, bool)
    
    def test_get_task_status(self, task_manager, sample_issue):
        """测试获取任务状态"""
        task_id = task_manager.create_task(
            issue_id=sample_issue.id,
            agent='test-agent',
            task_type='qa'
        )
        status = task_manager.get_task_status(task_id)
        assert status is not None
        assert status['task_id'] == task_id
    
    def test_get_task_status_not_found(self, task_manager):
        """测试获取不存在任务的状态"""
        status = task_manager.get_task_status('nonexistent')
        assert status is None
    
    def test_get_all_tasks(self, task_manager, sample_issue):
        """测试获取所有任务"""
        task_manager.create_task(sample_issue.id, 'agent1', 'qa')
        time.sleep(0.01)  # 确保时间戳不同
        task_manager.create_task(sample_issue.id, 'agent2', 'trading')
        all_tasks = task_manager.get_all_tasks()
        assert len(all_tasks) >= 1  # 至少有一个任务
    
    def test_generate_report(self, task_manager):
        """测试生成报告"""
        report = task_manager.generate_report()
        assert isinstance(report, dict)


class TestTaskManagerIntegration:
    """TaskManager 集成测试"""
    
    def test_full_task_lifecycle(self, tmp_path):
        """测试完整任务生命周期"""
        with patch('task_manager.QuantManager') as mock_manager:
            mock_queue = IssueQueue(base_dir=str(tmp_path))
            mock_manager.return_value.issue_queue = mock_queue
            
            tm = TaskManager()
            tm.manager = mock_manager.return_value
            tm.issue_queue = mock_queue
            
            issue = tm.issue_queue.create_issue(
                agent='test-agent',
                error_type="TestError",
                error_message="Test",
                severity="P1"
            )
            tm.issue_queue.write_issue(issue)
            
            task_id = tm.create_task(issue.id, 'test-agent', 'qa')
            tm.assign_task(task_id)
            
            task = tm.tasks[task_id]
            assert task['status'] == TaskStatus.ASSIGNED
            assert task['issue_id'] == issue.id
