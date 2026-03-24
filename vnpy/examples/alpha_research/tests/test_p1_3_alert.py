#!/usr/bin/env python3
"""
P1-3: 智能告警系统测试用例
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'world_model'))


class TestP1_3_SmartAlert:
    """P1-3: 智能告警系统测试"""
    
    def test_alert_module_exists(self):
        """测试告警模块存在"""
        alert_path = Path(__file__).parent.parent / 'world_model' / 'smart_alert.py'
        assert alert_path.exists()
    
    def test_alert_level_enum(self):
        """测试告警级别枚举"""
        from smart_alert import AlertLevel
        
        assert AlertLevel.LOW.value == "low"
        assert AlertLevel.MEDIUM.value == "medium"
        assert AlertLevel.HIGH.value == "high"
        assert AlertLevel.CRITICAL.value == "critical"
    
    def test_alert_type_enum(self):
        """测试告警类型枚举"""
        from smart_alert import AlertType
        
        assert AlertType.TRADE_ANOMALY.value == "trade_anomaly"
        assert AlertType.DATA_QUALITY.value == "data_quality"
        assert AlertType.AGENT_FAILURE.value == "agent_failure"
        assert AlertType.RISK_WARNING.value == "risk_warning"
    
    def test_alert_system_init(self):
        """测试告警系统初始化"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        assert alert is not None
        alert.close()
    
    def test_create_alert(self):
        """测试创建告警"""
        from smart_alert import SmartAlertSystem, AlertLevel, AlertType
        
        alert = SmartAlertSystem()
        result = alert.create_alert(
            level=AlertLevel.HIGH,
            alert_type=AlertType.TRADE_ANOMALY,
            title="测试告警",
            message="这是一条测试告警",
            metadata={'test': True}
        )
        
        assert result['level'] == 'high'
        assert result['type'] == 'trade_anomaly'
        assert result['title'] == "测试告警"
        alert.close()
    
    def test_alert_stats(self):
        """测试告警统计"""
        from smart_alert import SmartAlertSystem, AlertLevel, AlertType
        
        alert = SmartAlertSystem()
        alert.create_alert(AlertLevel.HIGH, AlertType.TRADE_ANOMALY, "测试 1", "消息")
        alert.create_alert(AlertLevel.MEDIUM, AlertType.DATA_QUALITY, "测试 2", "消息")
        
        stats = alert.get_stats()
        assert stats['total'] >= 2
        assert 'high' in stats['by_level']
        alert.close()
    
    def test_alert_history(self):
        """测试告警历史"""
        from smart_alert import SmartAlertSystem, AlertLevel, AlertType
        
        alert = SmartAlertSystem()
        alert.create_alert(AlertLevel.LOW, AlertType.RISK_WARNING, "测试", "消息")
        
        history = alert.get_alert_history(limit=10)
        assert isinstance(history, list)
        alert.close()


class TestP1_3_Checks:
    """P1-3: 告警检查测试"""
    
    def test_trade_anomaly_check(self):
        """测试异常交易检测"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        anomalies = alert.check_trade_anomalies()
        assert isinstance(anomalies, list)
        alert.close()
    
    def test_data_quality_check(self):
        """测试数据质量检查"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        alerts = alert.check_data_quality()
        assert isinstance(alerts, list)
        alert.close()
    
    def test_agent_health_check(self):
        """测试 Agent 健康检查"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        alerts = alert.check_agent_health()
        assert isinstance(alerts, list)
        alert.close()
    
    def test_risk_warning_check(self):
        """测试风险警告检查"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        alerts = alert.check_risk_warnings()
        assert isinstance(alerts, list)
        alert.close()
    
    def test_run_all_checks(self):
        """测试运行所有检查"""
        from smart_alert import SmartAlertSystem
        
        alert = SmartAlertSystem()
        results = alert.run_all_checks()
        
        assert 'checks' in results
        assert 'trade_anomalies' in results['checks']
        assert 'data_quality' in results['checks']
        assert 'agent_health' in results['checks']
        assert 'risk_warnings' in results['checks']
        assert 'total_alerts' in results
        alert.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
