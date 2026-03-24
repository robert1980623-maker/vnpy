#!/usr/bin/env python3
"""
IssueQueue 边界条件和异常情况测试

目标：
- 测试边界条件（空值、None、特殊字符等）
- 测试异常情况（文件读写失败、权限问题等）
- 提高测试覆盖率
"""

import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue


class TestIssueQueueEdgeCases:
    """IssueQueue 边界条件和异常情况测试"""
    
    @pytest.fixture
    def test_queue(self):
        """创建测试队列"""
        test_dir = Path('./tests/fixtures/test_issues_edge_cases')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        iq = IssueQueue(base_dir=str(test_dir))
        yield iq
        
        # 清理
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    # ==================== 边界条件测试 ====================
    
    def test_create_issue_with_empty_string_values(self, test_queue):
        """测试空字符串值"""
        issue = test_queue.create_issue(
            agent='',
            severity='',
            error_type='',
            error_message=''
        )
        
        assert issue.agent == ''
        assert issue.severity == ''
        assert issue.error_type == ''
        assert issue.error_message == ''
        assert issue.status == 'pending'
        assert issue.id is not None
    
    def test_create_issue_with_none_values(self, test_queue):
        """测试 None 值 - 代码不处理 None，保持 None"""
        issue = test_queue.create_issue(
            agent=None,
            severity=None,
            error_type=None,
            error_message=None
        )
        
        assert issue.agent is None
        assert issue.severity is None
        assert issue.error_type is None
        assert issue.error_message is None
        assert issue.status == 'pending'
        assert issue.id is not None
    
    def test_create_issue_with_special_characters(self, test_queue):
        """测试特殊字符"""
        issue = test_queue.create_issue(
            agent='test@agent#1',
            severity='P0',
            error_type='Test/Error',
            error_message='Error: \n\t特殊字符 &<>'
        )
        
        assert issue.agent == 'test@agent#1'
        assert issue.error_type == 'Test/Error'
        assert '特殊字符' in issue.error_message
    
    def test_create_issue_with_very_long_strings(self, test_queue):
        """测试超长字符串"""
        long_string = 'a' * 10000
        issue = test_queue.create_issue(
            agent=long_string,
            severity=long_string,
            error_type=long_string,
            error_message=long_string
        )
        
        assert len(issue.agent) == 10000
        assert len(issue.severity) == 10000
        assert len(issue.error_type) == 10000
        assert len(issue.error_message) == 10000
    
    def test_create_issue_with_unicode(self, test_queue):
        """测试 Unicode 字符"""
        issue = test_queue.create_issue(
            agent='测试用户',
            severity='P0',
            error_type='错误类型',
            error_message='错误消息：你好世界！'
        )
        
        assert issue.agent == '测试用户'
        assert issue.error_type == '错误类型'
        assert '你好世界' in issue.error_message
    
    def test_write_issue_with_empty_id(self, test_queue):
        """测试空 ID - 代码会自动生成"""
        issue = Issue(
            id='',
            agent='test',
            severity='P0',
            error_type='Error',
            error_message='Test'
        )
        
        issue_id = test_queue.write_issue(issue)
        assert issue_id is not None
        assert issue_id.startswith('issue_')
    
    def test_write_issue_with_special_id_chars(self, test_queue):
        """测试特殊字符 ID"""
        issue = Issue(
            id='test-issue_123',
            agent='test',
            severity='P0',
            error_type='Error',
            error_message='Test'
        )
        
        issue_id = test_queue.write_issue(issue)
        assert issue_id == 'test-issue_123'
    
    def test_read_issue_with_special_id(self, test_queue):
        """测试特殊字符 ID 读取"""
        issue = test_queue.create_issue(
            agent='test',
            severity='P0',
            error_type='Error',
            error_message='Test'
        )
        
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue is not None
        assert read_issue.id == issue_id
    
    def test_update_status_with_empty_id(self, test_queue):
        """测试空 ID 更新状态 - 返回 False"""
        result = test_queue.update_status('', 'processing')
        assert result == False
    
    def test_update_status_with_invalid_status(self, test_queue):
        """测试无效状态 - 代码接受任何字符串"""
        issue = test_queue.create_issue(
            agent='test',
            severity='P0',
            error_type='Error',
            error_message='Test'
        )
        
        issue_id = test_queue.write_issue(issue)
        result = test_queue.update_status(issue_id, 'invalid_status')
        assert result == True  # 代码接受任何状态字符串
    
    def test_get_pending_issues_with_empty_queue(self, test_queue):
        """测试空队列"""
        pending = test_queue.get_pending_issues()
        assert len(pending) == 0
    
    def test_get_issues_by_severity_with_empty_queue(self, test_queue):
        """测试空队列按严重性查询"""
        p0_issues = test_queue.get_issues_by_severity('P0')
        assert len(p0_issues) == 0
    
    def test_get_p0_issues_with_empty_queue(self, test_queue):
        """测试空队列获取 P0"""
        p0_issues = test_queue.get_p0_issues()
        assert len(p0_issues) == 0
    
    def test_clear_old_issues_with_empty_queue(self, test_queue):
        """测试空队列清理"""
        removed = test_queue.clear_old_issues(days=30)
        assert len(removed) == 0
    
    def test_clear_old_issues_with_zero_days(self, test_queue):
        """测试清理 0 天的问题 - 代码会清理"""
        issue = test_queue.create_issue(
            agent='test',
            severity='P2',
            error_type='Error',
            error_message='Test'
        )
        issue_id = test_queue.write_issue(issue)
        
        removed = test_queue.clear_old_issues(days=0)
        assert len(removed) == 1  # 代码会清理 0 天的问题
    
    def test_clear_old_issues_with_negative_days(self, test_queue):
        """测试清理负天数的问题 - 代码会清理"""
        issue = test_queue.create_issue(
            agent='test',
            severity='P2',
            error_type='Error',
            error_message='Test'
        )
        issue_id = test_queue.write_issue(issue)
        
        removed = test_queue.clear_old_issues(days=-1)
        assert len(removed) == 1  # 代码会清理负天数的问题
    
    def test_archive_issue_with_empty_id(self, test_queue):
        """测试空 ID 归档 - 返回 False"""
        result = test_queue.archive_issue('')
        assert result == False
    
    def test_archive_issue_with_invalid_id(self, test_queue):
        """测试无效 ID 归档 - 返回 False"""
        result = test_queue.archive_issue('non_existent_id')
        assert result == False
    
    # ==================== 异常情况测试 ====================
    
    def test_read_issue_not_found(self, test_queue):
        """测试读取不存在的问题"""
        result = test_queue.read_issue('non_existent_id')
        assert result is None
    
    def test_update_status_with_nonexistent_issue(self, test_queue):
        """测试更新不存在的问题状态 - 返回 False"""
        result = test_queue.update_status('non_existent_id', 'processing')
        assert result == False
    
    def test_resolve_issue_with_nonexistent_issue(self, test_queue):
        """测试解决不存在的问题 - 返回 False"""
        result = test_queue.resolve_issue('non_existent_id', 'Test resolution')
        assert result == False
    
    def test_get_issues_by_severity_with_nonexistent_severity(self, test_queue):
        """测试查询不存在的严重性"""
        issues = test_queue.get_issues_by_severity('P99')
        assert len(issues) == 0
    
    def test_issue_with_all_none_fields(self, test_queue):
        """测试所有字段为 None - 代码不处理 None"""
        issue = Issue(
            id=None,
            agent=None,
            severity=None,
            error_type=None,
            error_message=None,
            timestamp=None,
            status=None,
            assigned_to=None,
            resolved_at=None,
            resolution=None,
            type=None,
            title=None,
            description=None,
            details=None,
            report_file=None,
            requires_action=None,
            action_items=None
        )
        
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue is not None
        assert read_issue.id is not None
        assert read_issue.agent is None
        assert read_issue.severity is None
        assert read_issue.error_type is None
        assert read_issue.error_message is None
    
    def test_issue_with_only_id(self, test_queue):
        """测试只有 ID 的问题"""
        issue = Issue(id='test-only-id')
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue is not None
        assert read_issue.id == 'test-only-id'
        assert read_issue.agent == ''
    
    def test_issue_with_only_timestamp(self, test_queue):
        """测试只有时间戳的问题"""
        issue = Issue(
            id='test-timestamp',
            timestamp=datetime.now().isoformat()
        )
        issue_id = test_queue.write_issue(issue)
        read_issue = test_queue.read_issue(issue_id)
        
        assert read_issue is not None
        assert read_issue.id == 'test-timestamp'
        assert read_issue.timestamp is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
