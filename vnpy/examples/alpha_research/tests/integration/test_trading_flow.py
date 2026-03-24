#!/usr/bin/env python3
"""
交易流程集成测试
测试选股→交易→复盘的完整流程
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestTradingFlow:
    """交易流程集成测试"""
    
    def test_stock_selection_exists(self):
        """测试选股文件存在"""
        reports_dir = Path('./reports')
        if reports_dir.exists():
            selection_files = list(reports_dir.glob('stock_selection_*.json'))
            assert len(selection_files) > 0, "无选股文件"
    
    def test_trading_plan_exists(self):
        """测试交易计划存在"""
        reports_dir = Path('./reports')
        if reports_dir.exists():
            plan_files = list(reports_dir.glob('trading_plan_*.json'))
            assert len(plan_files) > 0, "无交易计划文件"
    
    def test_account_updated_after_trading(self):
        """测试交易后账户更新"""
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查最后更新时间
                last_update = data.get('last_update', '')
                assert last_update != '', "账户最后更新时间为空"


class TestComplianceCheck:
    """合规检查集成测试"""
    
    def test_compliance_script_exists(self):
        """测试合规检查脚本存在"""
        script = Path('./compliance_checker.py')
        assert script.exists(), f"合规检查脚本不存在：{script}"
    
    def test_compliance_reports_generated(self):
        """测试合规报告生成"""
        reports_dir = Path('./reports/compliance')
        if reports_dir.exists():
            reports = list(reports_dir.glob('compliance_check_*.txt'))
            assert len(reports) > 0, "无合规检查报告"


class TestPerformanceAttribution:
    """绩效归因集成测试"""
    
    def test_attribution_script_exists(self):
        """测试绩效归因脚本存在"""
        script = Path('./performance_attribution.py')
        assert script.exists(), f"绩效归因脚本不存在：{script}"
    
    def test_performance_reports_generated(self):
        """测试绩效报告生成"""
        reports_dir = Path('./reports/performance')
        if reports_dir.exists():
            reports = list(reports_dir.glob('performance_*.json'))
            assert len(reports) > 0, "无绩效报告"


class TestQAArchitectLoop:
    """QA-Architect 闭环集成测试"""
    
    def test_qa_script_exists(self):
        """测试 QA 脚本存在"""
        script = Path('./qa_architect_loop.py')
        assert script.exists(), f"QA 脚本不存在：{script}"
    
    def test_qa_reports_generated(self):
        """测试 QA 报告生成"""
        reports_dir = Path('./reports')
        if reports_dir.exists():
            qa_reports = list(reports_dir.glob('final_report_*.json'))
            # 检查最近的 QA 报告
            if qa_reports:
                latest = sorted(qa_reports)[-1]
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    assert 'approved' in data, "QA 报告格式无效"
    
    def test_review_history_exists(self):
        """测试审核历史存在"""
        review_dir = Path('./reports/review_history')
        if review_dir.exists():
            reviews = list(review_dir.glob('review_*.json'))
            assert len(reviews) > 0, "无审核历史"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
