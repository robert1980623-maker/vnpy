#!/usr/bin/env python3
"""
IssueQueue 完整单元测试

目标：覆盖所有核心方法
"""

import pytest
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue


class TestIssueQueueFull:
    """IssueQueue 完整测试"""
    
    @pytest.fixture
    def test_queue(self):
        """创建测试队列"""
        test_dir = Path('./tests/fixtures/test_issues_full')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        iq = IssueQueue(base_dir=str(test_dir))
        yield iq
        
        # 清理
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
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
        assert issue.status == 'pending'
        assert issue.id is not None
    
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
    
    def test_update_status(self, test_queue):
        """测试更新状态"""
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
    
    def test_resolve_issue(self, test_queue):
        """测试解决问题"""
        issue = test_queue.create_issue(
            agent='agent4',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        test_queue.resolve_issue(issue_id, resolution='已修复')
        
        resolved = test_queue.read_issue(issue_id)
        assert resolved.status == 'resolved'
        assert resolved.resolution == '已修复'
    
    def test_archive_issue(self, test_queue):
        """测试归档问题"""
        issue = test_queue.create_issue(
            agent='agent5',
            severity='P1',
            error_type='Error',
            error_message='错误'
        )
        
        issue_id = test_queue.write_issue(issue)
        test_queue.archive_issue(issue_id)
        
        # 检查是否在归档目录
        archive_file = test_queue.archive_dir / f"{issue_id}.json"
        assert archive_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
