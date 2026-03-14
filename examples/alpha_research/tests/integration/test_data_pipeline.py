#!/usr/bin/env python3
"""
数据管道集成测试
测试数据下载、处理、存储的完整流程
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDataPipeline:
    """数据管道集成测试"""
    
    def test_data_directory_exists(self):
        """测试数据目录存在"""
        data_dir = Path('./data')
        assert data_dir.exists(), f"数据目录不存在：{data_dir}"
    
    def test_data_files_not_empty(self):
        """测试数据文件不为空"""
        data_dir = Path('./data')
        if data_dir.exists():
            json_files = list(data_dir.glob('*.json'))
            # 如果有数据文件，检查不为空
            for f in json_files[:3]:  # 检查前 3 个
                assert f.stat().st_size > 0, f"数据文件为空：{f}"
    
    def test_data_format_valid(self):
        """测试数据格式有效"""
        data_dir = Path('./data')
        if data_dir.exists():
            json_files = list(data_dir.glob('*.json'))
            for f in json_files[:1]:  # 检查 1 个
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        assert isinstance(data, (dict, list)), f"数据格式无效：{f}"
                except json.JSONDecodeError as e:
                    pytest.fail(f"JSON 解析失败 {f}: {e}")


class TestStockSelection:
    """选股流程集成测试"""
    
    def test_selection_script_exists(self):
        """测试选股脚本存在"""
        script = Path('./daily_stock_selection.py')
        assert script.exists(), f"选股脚本不存在：{script}"
    
    def test_selection_report_generated(self):
        """测试选股报告生成"""
        reports_dir = Path('./reports')
        if reports_dir.exists():
            selection_reports = list(reports_dir.glob('stock_selection_*.json'))
            # 如果有报告，检查格式
            if selection_reports:
                latest = sorted(selection_reports)[-1]
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    assert 'selected_stocks' in data or 'stocks' in data, "选股报告格式无效"


class TestVirtualAccount:
    """虚拟账户集成测试"""
    
    def test_account_file_exists(self):
        """测试账户文件存在"""
        account_file = Path('./accounts/virtual_2026_account.json')
        assert account_file.exists(), f"账户文件不存在：{account_file}"
    
    def test_account_format_valid(self):
        """测试账户格式有效"""
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert 'cash' in data, "账户文件缺少 cash 字段"
                assert 'positions' in data, "账户文件缺少 positions 字段"
    
    def test_account_balance_positive(self):
        """测试账户余额为正"""
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data.get('cash', 0) > 0, "账户现金余额应为正"


class TestReportsGeneration:
    """报告生成集成测试"""
    
    def test_reports_directory_exists(self):
        """测试报告目录存在"""
        reports_dir = Path('./reports')
        assert reports_dir.exists(), f"报告目录不存在：{reports_dir}"
    
    def test_daily_reports_generated(self):
        """测试每日报告生成"""
        reports_dir = Path('./reports')
        if reports_dir.exists():
            # 检查是否有最近的报告
            import time
            now = time.time()
            recent_reports = [
                f for f in reports_dir.glob('*.json')
                if now - f.stat().st_mtime < 86400 * 7  # 7 天内
            ]
            assert len(recent_reports) > 0, "7 天内无报告生成"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
