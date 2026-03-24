#!/usr/bin/env python3
"""
Agent 系统集成测试
测试各个 Agent 的完整功能
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAgentScripts:
    """Agent 脚本存在性测试"""
    
    def test_manager_interface_exists(self):
        """测试 Manager 接口存在"""
        script = Path('./manager_interface.py')
        assert script.exists(), f"Manager 接口不存在：{script}"
    
    def test_issue_queue_exists(self):
        """测试问题队列存在"""
        script = Path('./issue_queue.py')
        assert script.exists(), f"问题队列不存在：{script}"
    
    def test_qa_test_generator_exists(self):
        """测试 QA 测试生成器存在"""
        script = Path('./qa_test_generator.py')
        assert script.exists(), f"QA 测试生成器不存在：{script}"
    
    def test_architect_reviewer_exists(self):
        """测试架构师审核器存在"""
        script = Path('./architect_test_reviewer.py')
        assert script.exists(), f"架构师审核器不存在：{script}"


class TestAgentDataFlow:
    """Agent 数据流测试"""
    
    def test_issues_directory_exists(self):
        """测试问题目录存在"""
        issues_dir = Path('./issues')
        assert issues_dir.exists(), f"问题目录不存在：{issues_dir}"
    
    def test_issue_subdirectories_exist(self):
        """测试问题子目录存在"""
        base_dir = Path('./issues')
        if base_dir.exists():
            expected_dirs = ['pending', 'processing', 'resolved', 'archive']
            for subdir in expected_dirs:
                dir_path = base_dir / subdir
                assert dir_path.exists(), f"问题子目录不存在：{dir_path}"
    
    def test_review_history_directory_exists(self):
        """测试审核历史目录存在"""
        review_dir = Path('./reports/review_history')
        assert review_dir.exists(), f"审核历史目录不存在：{review_dir}"


class TestAgentConfiguration:
    """Agent 配置测试"""
    
    def test_cron_jobs_valid(self):
        """测试 Cron 任务配置有效"""
        cron_file = Path.home() / '.openclaw' / 'cron' / 'jobs.json'
        if cron_file.exists():
            with open(cron_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert 'jobs' in data, "Cron 配置缺少 jobs 字段"
                assert isinstance(data['jobs'], list), "jobs 应为数组"
    
    def test_agent_models_configured(self):
        """测试 Agent 模型配置"""
        cron_file = Path.home() / '.openclaw' / 'cron' / 'jobs.json'
        if cron_file.exists():
            with open(cron_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                jobs = data.get('jobs', [])
                # 检查所有任务都有模型配置
                for job in jobs[:10]:  # 检查前 10 个
                    model = job.get('payload', {}).get('model', '')
                    assert model != '', f"任务 {job.get('name')} 缺少模型配置"


class TestManagerSystem:
    """Manager 系统测试"""
    
    def test_manager_can_load(self):
        """测试 Manager 可以加载"""
        try:
            from manager_interface import QuantManager
            manager = QuantManager()
            assert manager is not None, "Manager 加载失败"
        except ImportError as e:
            pytest.fail(f"Manager 导入失败：{e}")
    
    def test_manager_get_status(self):
        """测试 Manager 获取状态"""
        try:
            from manager_interface import QuantManager
            manager = QuantManager()
            status = manager.get_status()
            assert isinstance(status, dict), "状态应为字典"
            assert 'active_tasks' in status or 'pending_issues' in status, "状态缺少关键字段"
        except Exception as e:
            pytest.fail(f"Manager 获取状态失败：{e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
