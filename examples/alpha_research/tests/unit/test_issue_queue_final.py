#!/usr/bin/env python3
"""
IssueQueue 最终测试 - 覆盖剩余代码行
"""

import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue


class TestIssueQueueFinalLines:
    """覆盖 issue_queue.py 剩余代码行"""
    
    @pytest.fixture
    def test_queue(self):
        test_dir = Path('./tests/fixtures/test_final_lines')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        iq = IssueQueue(base_dir=str(test_dir))
        yield iq
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_issue_post_init_with_type(self, test_queue):
        """测试 Issue 的 __post_init__ 使用 type 字段"""
        issue = Issue(
            id='test-1',
            type='BugType',
            description='描述消息'
        )
        
        # __post_init__ 应该复制 type 到 error_type
        assert issue.error_type == 'BugType'
    
    def test_issue_post_init_with_description(self, test_queue):
        """测试 Issue 的 __post_init__ 使用 description 字段"""
        long_desc = '这是一个很长的描述消息' * 10
        issue = Issue(
            id='test-2',
            description=long_desc
        )
        
        # __post_init__ 应该复制 description 到 error_message (截断到 200 字)
        assert issue.error_message is not None
        assert len(issue.error_message) <= 200
    
    def test_clear_old_issues_archives(self, test_queue):
        """测试 clear_old_issues 归档旧问题"""
        # 创建一个已解决的问题
        old_issue = test_queue.create_issue(
            agent='old',
            severity='P2',
            error_type='OldError',
            error_message='旧错误'
        )
        old_issue_id = test_queue.write_issue(old_issue)
        
        # 手动移动到 resolved 目录
        import os
        pending_file = test_queue.pending_dir / f"{old_issue_id}.json"
        resolved_file = test_queue.resolved_dir / f"{old_issue_id}.json"
        
        if pending_file.exists():
            # 修改文件时间戳为 60 天前
            old_time = (datetime.now() - timedelta(days=60)).timestamp()
            os.utime(pending_file, (old_time, old_time))
            
            # 移动到 resolved
            test_queue.update_status(old_issue_id, 'resolved')
            
            # 现在调用 clear_old_issues
            test_queue.clear_old_issues(days=30)
            
            # 应该被移动到 archive
            archive_file = test_queue.archive_dir / f"{old_issue_id}.json"
            # 检查归档目录
            assert archive_file.exists() or not resolved_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
