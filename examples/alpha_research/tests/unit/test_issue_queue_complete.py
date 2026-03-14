#!/usr/bin/env python3
"""
IssueQueue 完整单元测试 - 覆盖所有公共方法

目标：覆盖率≥90%
"""

import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue


class TestIssueQueueComplete:
    """IssueQueue 完整测试 - 覆盖所有方法"""
    
    @pytest.fixture
    def test_queue(self):
        """创建测试队列"""
        test_dir = Path('./tests/fixtures/test_issues_complete')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        iq = IssueQueue(base_dir=str(test_dir))
        yield iq
        
        # 清理
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_init_creates_directories(self, test_queue):
        """测试初始化时创建目录"""
        assert test_queue.pending_dir.exists()
        assert test_queue.processing_dir.exists()
        assert test_queue.resolved_dir.exists()
        assert test_queue.archive_dir.exists()
    
    def test_create_issue(self, test_queue):
        """测试创建问题"""
        issue = test_queue.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TestError',
            error_message='测试错误'
        )
        
        assert issue.agent == 'test_agent'
        assert issue.severity == 'P1'
        assert issue.error_type == 'TestError'
        assert issue.error_message == '测试错误'
        assert issue.status == 'pending'
        assert issue.id is not None
        assert issue.timestamp is not None
    
    def test_create_issue_auto_id(self, test_queue):
        """测试自动生成 ID"""
        issue1 = test_queue.create_issue('agent', 'P1', 'Error', 'Msg1')
        issue2 = test_queue.create_issue('agent', 'P1', 'Error', 'Msg2')
        
        assert issue1.id != issue2.id
        assert issue1.id.startswith('issue_')
    
    def test_write_issue(self, test_queue):
        """测试写入问题"""
        issue = test_queue.create_issue(
            agent='agent1',
            severity='P0',
            error_type='CriticalError',
            error_message='严重错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        assert issue_id is not None
        
        # 检查文件是否存在
        issue_file = test_queue.pending_dir / f"{issue_id}.json"
        assert issue_file.exists()
        
        # 检查文件内容
        with open(issue_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['agent'] == 'agent1'
            assert data['severity'] == 'P0'
    
    def test_read_issue(self, test_queue):
        """测试读取问题"""
        issue = test_queue.create_issue(
            agent='agent2',
            severity='P2',
            error_type='MinorError',
            error_message='小错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue is not None
        assert read_issue.agent == 'agent2'
        assert read_issue.severity == 'P2'
    
    def test_read_issue_not_found(self, test_queue):
        """测试读取不存在的问题"""
        result = test_queue.read_issue('non_existent_id')
        assert result is None
    
    def test_get_pending_issues(self, test_queue):
        """测试获取待处理问题"""
        # 创建多个问题
        for i in range(3):
            issue = test_queue.create_issue(
                agent=f'agent{i}',
                severity='P1',
                error_type=f'Error{i}',
                error_message=f'错误{i}'
            )
            test_queue.write_issue(issue)
        
        pending = test_queue.get_pending_issues()
        assert len(pending) == 3
    
    def test_get_pending_issues_empty(self, test_queue):
        """测试空队列"""
        pending = test_queue.get_pending_issues()
        assert len(pending) == 0
    
    def test_update_status_to_processing(self, test_queue):
        """测试更新状态为 processing"""
        issue = test_queue.create_issue(
            agent='agent3',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        test_queue.update_status(issue_id, 'processing', assigned_to='reviewer')
        
        updated = test_queue.read_issue(issue_id)
        assert updated.status == 'processing'
        assert updated.assigned_to == 'reviewer'
    
    def test_update_status_to_resolved(self, test_queue):
        """测试更新状态为 resolved"""
        issue = test_queue.create_issue(
            agent='agent4',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        test_queue.update_status(
            issue_id,
            'resolved',
            assigned_to='reviewer',
            resolution='已修复',
            resolved_at=datetime.now().isoformat()
        )
        
        updated = test_queue.read_issue(issue_id)
        assert updated.status == 'resolved'
        assert updated.resolution == '已修复'
    
    def test_update_status_moves_file(self, test_queue):
        """测试更新状态时移动文件"""
        issue = test_queue.create_issue(
            agent='agent5',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        
        # 初始在 pending 目录
        pending_file = test_queue.pending_dir / f"{issue_id}.json"
        assert pending_file.exists()
        
        # 更新为 processing
        test_queue.update_status(issue_id, 'processing')
        
        # 应该移动到 processing 目录
        processing_file = test_queue.processing_dir / f"{issue_id}.json"
        assert processing_file.exists()
        assert not pending_file.exists()
    
    def test_get_issues_by_severity(self, test_queue):
        """测试按严重性获取问题"""
        # 创建不同严重性的问题
        for severity in ['P0', 'P1', 'P2', 'P0']:
            issue = test_queue.create_issue(
                agent='agent',
                severity=severity,
                error_type='Error',
                error_message='错误'
            )
            test_queue.write_issue(issue)
        
        p0_issues = test_queue.get_issues_by_severity('P0')
        assert len(p0_issues) == 2
        
        p1_issues = test_queue.get_issues_by_severity('P1')
        assert len(p1_issues) == 1
    
    def test_get_p0_issues(self, test_queue):
        """测试获取 P0 问题"""
        # 创建 P0 和其他问题
        for severity in ['P0', 'P1', 'P0', 'P2']:
            issue = test_queue.create_issue(
                agent='agent',
                severity=severity,
                error_type='Error',
                error_message='错误'
            )
            test_queue.write_issue(issue)
        
        p0_issues = test_queue.get_p0_issues()
        assert len(p0_issues) == 2
        
        for issue in p0_issues:
            assert issue.severity == 'P0'
    
    def test_clear_old_issues(self, test_queue):
        """测试清理旧问题"""
        # 创建一个旧问题 (手动修改时间戳)
        old_issue = test_queue.create_issue(
            agent='old_agent',
            severity='P2',
            error_type='OldError',
            error_message='旧错误'
        )
        old_issue.timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        old_issue_id = test_queue.write_issue(old_issue)
        
        # 创建一个新问题
        new_issue = test_queue.create_issue(
            agent='new_agent',
            severity='P1',
            error_type='NewError',
            error_message='新错误'
        )
        new_issue_id = test_queue.write_issue(new_issue)
        
        # 清理 30 天以上的问题
        test_queue.clear_old_issues(days=30)
        
        # 旧问题应该被清理
        old_result = test_queue.read_issue(old_issue_id)
        assert old_result is None
        
        # 新问题应该保留
        new_result = test_queue.read_issue(new_issue_id)
        assert new_result is not None
    
    def test_issue_with_all_fields(self, test_queue):
        """测试包含所有字段的问题"""
        issue = Issue(
            id='test-123',
            agent='test_agent',
            severity='P0',
            error_type='TestError',
            error_message='测试错误消息',
            timestamp=datetime.now().isoformat(),
            status='pending',
            assigned_to='reviewer',
            resolved_at=None,
            resolution=None,
            type='Bug',
            title='测试标题',
            description='详细描述',
            details={'key': 'value'},
            report_file='report.txt',
            requires_action=True,
            action_items=['item1', 'item2']
        )
        
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue.title == '测试标题'
        assert read_issue.description == '详细描述'
        assert read_issue.details == {'key': 'value'}
        assert read_issue.action_items == ['item1', 'item2']
        assert read_issue.requires_action == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
