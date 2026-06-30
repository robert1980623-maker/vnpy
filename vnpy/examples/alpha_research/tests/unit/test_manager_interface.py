#!/usr/bin/env python3
"""
Manager Interface 单元测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager


class TestQuantManager:
    """QuantManager 测试"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """创建测试用 manager"""
        return QuantManager(base_dir=str(tmp_path))
    
    @pytest.fixture
    def sample_issue(self, tmp_path):
        """创建示例 Issue"""
        queue = IssueQueue(base_dir=str(tmp_path))
        return queue.create_issue(
            agent='test-agent',
            error_type="AssertionError",
            error_message="Test assertion failed",
            severity="P1"
        )
    
    def test_init(self, manager):
        """测试初始化"""
        assert manager.base_dir is not None
        assert manager.issue_queue is not None
        assert manager.active_tasks == {}
        assert isinstance(manager.agent_mapping, dict)
    
    def test_analyze_error_by_rules(self, manager, sample_issue):
        """测试规则分析"""
        result = manager._analyze_by_rules(
            sample_issue.error_type.lower(),
            sample_issue.error_message.lower()
        )
        assert 'task_type' in result
        assert 'confidence' in result
    
    def test_select_agent(self, manager):
        """测试 Agent 选择"""
        agent = manager.select_agent('qa')
        assert agent is not None
        
        agent = manager.select_agent('trading')
        assert agent is not None
        
        agent = manager.select_agent('unknown_type')
        assert agent is not None
    
    def test_handle_p0(self, manager, sample_issue):
        """测试 P0 级别处理"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P0',
            'status': 'assigned'
        }
        manager.handle_p0(task, sample_issue)
    
    def test_handle_p1(self, manager, sample_issue):
        """测试 P1 级别处理"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P1',
            'status': 'assigned'
        }
        manager.handle_p1(task, sample_issue)
    
    def test_handle_p2(self, manager, sample_issue):
        """测试 P2 级别处理"""
        task = {
            'issue_id': sample_issue.id,
            'agent': 'test-agent',
            'type': 'qa',
            'severity': 'P2',
            'status': 'assigned'
        }
        manager.handle_p2(task, sample_issue)
    
    def test_get_status(self, manager):
        """测试状态获取"""
        status = manager.get_status()
        assert 'active_tasks' in status
        assert 'pending_issues' in status
    
    def test_handle_error_report(self, manager, sample_issue):
        """测试错误报告处理"""
        task = manager.handle_error_report(sample_issue)
        assert task is not None
        assert 'issue_id' in task
        assert task['issue_id'] == sample_issue.id
    
    def test_analyze_error_llm_fallback(self, manager, sample_issue):
        """测试 LLM 分析失败时的回退"""
        with patch.object(manager.error_analyzer, 'analyze', side_effect=Exception("LLM error")):
            result = manager.analyze_error(sample_issue)
            assert result is not None


class TestIssueQueue:
    """IssueQueue 测试"""
    
    @pytest.fixture
    def queue(self, tmp_path):
        """创建测试用队列"""
        return IssueQueue(base_dir=str(tmp_path))
    
    def test_init(self, queue, tmp_path):
        """测试初始化"""
        assert queue.pending_dir.exists()
        assert queue.processing_dir.exists()
        assert queue.resolved_dir.exists()
        assert queue.archive_dir.exists()
    
    def test_create_issue(self, queue):
        """测试创建 Issue"""
        issue = queue.create_issue(
            agent='test-agent',
            error_type="ValueError",
            error_message="Test error",
            severity="P1"
        )
        assert issue is not None
        assert issue.id is not None
        assert issue.agent == 'test-agent'
    
    def test_create_and_write_issue(self, queue):
        """测试创建并写入 Issue"""
        issue = queue.create_issue(
            agent='test-agent',
            error_type="TestError",
            error_message="Test",
            severity="P2"
        )
        queue.write_issue(issue)
        
        retrieved = queue.read_issue(issue.id)
        assert retrieved is not None
        assert retrieved.id == issue.id
        assert retrieved.agent == 'test-agent'
    
    def test_write_issue(self, queue):
        """测试写入 Issue"""
        issue = Issue(
            id="TEST-001",
            agent='test-agent',
            error_type="TestError",
            error_message="Test",
            severity="P1"
        )
        queue.write_issue(issue)
        file_path = queue.pending_dir / "TEST-001.json"
        assert file_path.exists()
    
    def test_update_status(self, queue):
        """测试状态更新"""
        issue = queue.create_issue(
            agent='test-agent',
            error_type="TestError",
            error_message="Test",
            severity="P1"
        )
        queue.write_issue(issue)
        
        result = queue.update_status(issue.id, 'processing', assigned_to='test-agent')
        assert result is True
        
        updated = queue.read_issue(issue.id)
        assert updated is not None
        assert updated.status == 'processing'
    
    def test_get_pending_issues(self, queue):
        """测试获取待处理问题"""
        issue1 = queue.create_issue('agent1', "P1", "Error1", "Test1")
        issue2 = queue.create_issue('agent2', "P2", "Error2", "Test2")
        queue.write_issue(issue1)
        queue.write_issue(issue2)
        
        pending = queue.get_pending_issues()
        assert len(pending) >= 2
    
    def test_archive_issue(self, queue):
        """测试归档 Issue"""
        issue = queue.create_issue(
            agent='test-agent',
            error_type="TestError",
            error_message="Test",
            severity="P1"
        )
        queue.write_issue(issue)
        
        result = queue.archive_issue(issue.id)
        assert result is True
        
        archived_file = queue.archive_dir / f"{issue.id}.json"
        assert archived_file.exists()


class TestErrorAnalyzer:
    """ErrorAnalyzer 测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建测试用分析器"""
        from error_analyzer import ErrorAnalyzer
        return ErrorAnalyzer()
    
    def test_init(self, analyzer):
        """测试初始化"""
        assert analyzer is not None
    
    def test_analyze(self, analyzer):
        """测试分析方法"""
        result = analyzer.analyze(
            error_type="ValueError",
            error_message="Invalid value",
            context=None
        )
        assert result is not None
        assert 'task_type' in result


class TestQuantManagerAdvanced:
    """QuantManager 高级测试 - 提高覆盖率"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """创建测试用 manager"""
        return QuantManager(base_dir=str(tmp_path))
    
    @pytest.fixture
    def sample_issue(self, tmp_path):
        """创建示例 Issue"""
        queue = IssueQueue(base_dir=str(tmp_path))
        issue = queue.create_issue(
            agent='test-agent',
            error_type="AssertionError",
            error_message="Test assertion failed",
            severity="P1"
        )
        queue.write_issue(issue)
        return issue
    
    def test_handle_error_report_p0(self, manager, sample_issue):
        """测试 P0 错误报告处理"""
        sample_issue.severity = 'P0'
        task = manager.handle_error_report(sample_issue)
        assert task is not None
        assert task['severity'] == 'P0'
    
    def test_handle_error_report_p1(self, manager, sample_issue):
        """测试 P1 错误报告处理"""
        sample_issue.severity = 'P1'
        task = manager.handle_error_report(sample_issue)
        assert task is not None
    
    def test_handle_error_report_p2(self, manager, sample_issue):
        """测试 P2 错误报告处理"""
        sample_issue.severity = 'P2'
        task = manager.handle_error_report(sample_issue)
        assert task is not None
    
    def test_select_agent_all_types(self, manager):
        """测试所有 Agent 类型选择"""
        agents = ['qa', 'trading', 'risk', 'data', 'engineering', 'general', 'unknown']
        for agent_type in agents:
            result = manager.select_agent(agent_type)
            assert result is not None
    
    def test_analyze_error_low_confidence(self, manager, sample_issue):
        """测试低置信度分析"""
        with patch.object(manager.error_analyzer, 'analyze', return_value={'task_type': 'general', 'confidence': 0.5}):
            result = manager.analyze_error(sample_issue)
            assert result is not None
    
    def test_get_status_with_active_tasks(self, manager, sample_issue):
        """测试带活跃任务的状态"""
        manager.active_tasks['test-task'] = {'status': 'running'}
        status = manager.get_status()
        assert status['active_tasks'] >= 1
