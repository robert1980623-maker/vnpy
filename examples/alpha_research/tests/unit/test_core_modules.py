#!/usr/bin/env python3
"""
核心模块单元测试

目标：核心代码覆盖率达到 90% 以上
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestIssueQueue:
    """IssueQueue 核心功能测试"""
    
    def test_create_issue(self):
        """测试创建问题"""
        from issue_queue import IssueQueue, Issue
        
        iq = IssueQueue(base_dir='./tests/fixtures/test_issues')
        issue = iq.create_issue(
            agent='test_agent',
            severity='P1',
            error_type='TestError',
            error_message='测试错误消息'
        )
        
        assert issue.agent == 'test_agent'
        assert issue.severity == 'P1'
        assert issue.error_type == 'TestError'
        assert issue.status == 'pending'
    
    def test_write_and_read_issue(self):
        """测试写入和读取问题"""
        from issue_queue import IssueQueue
        
        iq = IssueQueue(base_dir='./tests/fixtures/test_issues')
        issue = iq.create_issue(
            agent='test_agent',
            severity='P0',
            error_type='CriticalError',
            error_message='严重错误'
        )
        
        issue_id = iq.write_issue(issue)
        assert issue_id is not None
        
        # 读取问题
        read_issue = iq.read_issue(issue_id)
        assert read_issue is not None
        assert read_issue.severity == 'P0'
    
    def test_get_pending_issues(self):
        """测试获取待处理问题"""
        from issue_queue import IssueQueue
        
        iq = IssueQueue(base_dir='./tests/fixtures/test_issues')
        pending = iq.get_pending_issues()
        assert isinstance(pending, list)


class TestManagerInterface:
    """QuantManager 核心功能测试"""
    
    def test_get_status(self):
        """测试获取 Manager 状态"""
        from manager_interface import QuantManager
        
        manager = QuantManager()
        status = manager.get_status()
        
        assert isinstance(status, dict)
        assert 'active_tasks' in status or 'pending_issues' in status
    
    def test_issue_queue_access(self):
        """测试访问问题队列"""
        from manager_interface import QuantManager
        
        manager = QuantManager()
        assert manager.issue_queue is not None
        
        pending = manager.issue_queue.get_pending_issues()
        assert isinstance(pending, list)


class TestVirtualAccount:
    """虚拟账户核心功能测试"""
    
    def test_account_file_structure(self):
        """测试账户文件结构"""
        account_file = Path('./accounts/virtual_2026_account.json')
        
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 必需字段
            assert 'cash' in data
            assert 'positions' in data
            assert isinstance(data['cash'], (int, float))
            assert isinstance(data['positions'], list)
    
    def test_account_balance(self):
        """测试账户余额"""
        account_file = Path('./accounts/virtual_2026_account.json')
        
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data['cash'] > 0, "账户现金余额应为正"
            
            # 计算总资产
            total_value = data['cash'] + sum(
                p.get('market_value', 0) for p in data['positions']
            )
            assert total_value > 0, "总资产应为正"


class TestDataValidator:
    """数据验证器测试"""
    
    def test_data_directory_structure(self):
        """测试数据目录结构"""
        data_dir = Path('./data')
        
        if data_dir.exists():
            # 检查是否有数据文件
            json_files = list(data_dir.glob('*.json'))
            assert len(json_files) > 0, "数据目录应有数据文件"
    
    def test_data_file_format(self):
        """测试数据文件格式"""
        data_dir = Path('./data')
        
        if data_dir.exists():
            json_files = list(data_dir.glob('*.json'))
            for f in json_files[:3]:  # 检查前 3 个
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    assert isinstance(data, (dict, list)), f"数据格式无效：{f}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
