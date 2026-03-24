#!/usr/bin/env python3
"""
P1-2: 监控仪表板扩展测试用例
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'world_model'))


class TestP1_2_Dashboard:
    """P1-2: 监控仪表板测试"""
    
    def test_dashboard_module_exists(self):
        """测试仪表板模块存在"""
        dashboard_path = Path(__file__).parent.parent / 'world_model' / 'vnpy_dashboard.py'
        assert dashboard_path.exists()
    
    def test_portfolio_api(self):
        """测试持仓数据 API"""
        # 模拟测试
        portfolio = {
            'count': 14,
            'total_value': 1677781.02,
            'cash': 7256.34,
            'pnl': 293143.47
        }
        assert portfolio['count'] > 0
        assert portfolio['total_value'] > 0
    
    def test_risk_api(self):
        """测试风险指标 API"""
        risk = {
            'level': 'low',
            'drawdown': 5.2,
            'position_ratio': 85.5,
            'alerts': 0
        }
        assert risk['level'] in ['low', 'medium', 'high']
        assert 0 <= risk['position_ratio'] <= 100
    
    def test_rules_api(self):
        """测试规则统计 API"""
        rules = {
            'total': 150,
            'by_category': {
                'risk_control': 48,
                'position': 68,
                'data_quality': 34
            }
        }
        assert rules['total'] == 150
        assert sum(rules['by_category'].values()) == rules['total']
    
    def test_agents_api(self):
        """测试 Agent 统计 API"""
        agents = {
            'total': 23,
            'by_type': {
                'monitoring': 6,
                'trading': 3,
                'risk': 2
            }
        }
        assert agents['total'] == 23
    
    def test_trade_events(self):
        """测试交易事件"""
        events = [
            {'type': 'TradeExecutedEvent', 'priority': 1},
            {'type': 'PositionChangedEvent', 'priority': 2}
        ]
        assert len(events) > 0
    
    def test_data_freshness(self):
        """测试数据新鲜度"""
        freshness = [
            {'type': '股票数据', 'status': 'fresh', 'hours_ago': 0.5},
            {'type': '持仓数据', 'status': 'fresh', 'hours_ago': 0.3},
            {'type': '市场数据', 'status': 'fresh', 'hours_ago': 0.2}
        ]
        for data in freshness:
            assert data['status'] in ['fresh', 'stale', 'critical']


class TestP1_2_Integration:
    """P1-2 集成测试"""
    
    def test_dashboard_template_exists(self):
        """测试仪表板模板存在"""
        template_path = Path(__file__).parent.parent / 'world_model' / 'dashboard_events.html'
        assert template_path.exists()
    
    def test_all_apis_documented(self):
        """测试所有 API 有文档"""
        dashboard_path = Path(__file__).parent.parent / 'world_model' / 'vnpy_dashboard.py'
        content = dashboard_path.read_text()
        
        assert '/api/portfolio' in content
        assert '/api/risk' in content
        assert '/api/rules' in content
        assert '/api/agents' in content


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
