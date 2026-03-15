#!/usr/bin/env python3
"""
IssueQueue 最终测试 - 验证所有功能行
"""

import pytest
import os
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import sys
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from issue_queue import IssueQueue, Issue


class TestIssueQueueFinalLines:
    """IssueQueue 最终行测试"""
    
    @pytest.fixture
    def test_queue(self, tmp_path):
        """创建测试队列"""
        test_dir = tmp_path / "test_final_lines"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for d in ['pending', 'resolved', 'archive']:
            dir_path = test_dir / d
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        return IssueQueue(base_dir=str(test_dir))
    
    def test_clear_old_issues_archives(self, test_queue):
        """测试清理旧问题会归档"""
        # 创建旧 issue (直接设置 timestamp 为 60 天前)
        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        old_issue = Issue(
            id="",
            agent='test',
            severity='P2',
            error_type='OldError',
            error_message='旧错误',
            timestamp=old_timestamp
        )
        old_issue_id = test_queue.write_issue(old_issue)
        
        # 移动到 resolved
        test_queue.update_status(old_issue_id, 'resolved')
        
        # 验证 resolved 文件存在
        resolved_file = test_queue.resolved_dir / f"{old_issue_id}.json"
        assert resolved_file.exists()
        
        # 现在调用 clear_old_issues (清理 30 天前的)
        test_queue.clear_old_issues(days=30)
        
        # 应该被移动到 archive
        archive_file = test_queue.archive_dir / f"{old_issue_id}.json"
        # resolved 文件应该不存在 (已移动到 archive)
        assert archive_file.exists()
        assert not resolved_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
