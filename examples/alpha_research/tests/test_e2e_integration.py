#!/usr/bin/env python3
"""端到端集成测试"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'world_model'))


class TestE2E_DataFlow:
    """端到端数据流测试"""
    
    def test_data_download_to_sync(self):
        """测试数据下载→同步流程"""
        test_data = {'symbol': '600519.SH', 'datetime': datetime.now(), 'close': 1440.11, 'volume': 100}
        try:
            from neo4j_sync import Neo4jSync
            sync = Neo4jSync()
            sync.sync_stock_data(test_data)
            sync.close()
            assert True
        except Exception as e:
            pytest.fail(f"数据同步失败：{e}")
    
    def test_data_to_event_publishing(self):
        """测试数据→事件发布流程"""
        try:
            from event_publisher import EventPublisher
            publisher = EventPublisher()
            msg_id = publisher.publish_trade_event('600519.SH', 'buy', 1440.11, 100, 'virtual_2026')
            assert msg_id is not None
            publisher.close()
        except Exception as e:
            pytest.fail(f"事件发布失败：{e}")
    
    def test_event_to_dashboard(self):
        """测试事件→仪表板展示流程"""
        try:
            dashboard_data = {
                'positions': {'count': 14, 'total_value': 1677781.02},
                'risk': {'level': 'low'},
                'rules': {'total': 150},
                'agents': {'total': 23}
            }
            assert dashboard_data['positions']['count'] > 0
            assert dashboard_data['rules']['total'] > 0
        except Exception as e:
            pytest.fail(f"仪表板数据获取失败：{e}")


class TestE2E_AlertFlow:
    """端到端告警流程测试"""
    
    def test_anomaly_detection_to_alert(self):
        """测试异常检测→告警流程"""
        try:
            from smart_alert import SmartAlertSystem, AlertLevel, AlertType
            alert = SmartAlertSystem()
            result = alert.create_alert(
                level=AlertLevel.HIGH,
                alert_type=AlertType.TRADE_ANOMALY,
                title="测试异常交易",
                message="测试大额交易检测"
            )
            assert result['level'] == 'high'
            assert result['status'] == 'new'
            alert.close()
        except Exception as e:
            pytest.fail(f"告警流程失败：{e}")
    
    def test_alert_to_notification(self):
        """测试告警→通知流程"""
        try:
            from smart_alert import SmartAlertSystem, AlertLevel, AlertType
            alert = SmartAlertSystem()
            result = alert.create_alert(
                level=AlertLevel.CRITICAL,
                alert_type=AlertType.AGENT_FAILURE,
                title="测试严重告警",
                message="测试多渠道通知"
            )
            assert result['level'] == 'critical'
            alert.close()
        except Exception as e:
            pytest.fail(f"通知流程失败：{e}")


class TestE2E_Maintenance:
    """端到端维护流程测试"""
    
    def test_health_check_to_prediction(self):
        """测试健康检查→故障预测流程"""
        try:
            from predictive_maintenance import PredictiveMaintenance
            pm = PredictiveMaintenance()
            report = pm.get_system_health_report()
            assert 'overall_health' in report
            assert 'health_level' in report
            assert 'predictions' in report
            pm.close()
        except Exception as e:
            pytest.fail(f"健康检查失败：{e}")
    
    def test_prediction_to_recommendation(self):
        """测试预测→建议流程"""
        try:
            from predictive_maintenance import PredictiveMaintenance
            pm = PredictiveMaintenance()
            recommendations = pm.get_scaling_recommendations()
            assert isinstance(recommendations, list)
            pm.close()
        except Exception as e:
            pytest.fail(f"建议生成失败：{e}")


class TestE2E_Knowledge:
    """端到端知识流程测试"""
    
    def test_rule_query_to_advice(self):
        """测试规则查询→建议流程"""
        try:
            from knowledge_reasoning import KnowledgeReasoning
            kr = KnowledgeReasoning()
            advice = kr.get_trading_advice('600519.SH')
            assert 'recommendation' in advice
            assert 'confidence' in advice
            kr.close()
        except Exception as e:
            pytest.fail(f"知识推理失败：{e}")
    
    def test_question_to_answer(self):
        """测试问答流程"""
        try:
            from knowledge_reasoning import KnowledgeReasoning
            kr = KnowledgeReasoning()
            answer = kr.ask_question("止损规则是什么？")
            assert 'answer' in answer
            assert 'confidence' in answer
            kr.close()
        except Exception as e:
            pytest.fail(f"问答失败：{e}")


class TestE2E_Ops:
    """端到端运维流程测试"""
    
    def test_backup_to_recovery(self):
        """测试备份→恢复流程"""
        try:
            from auto_ops import AutoOps
            ops = AutoOps()
            backup = ops.backup_system('test')
            assert backup['status'] in ['success', 'failed']
            ops.close()
        except Exception as e:
            pytest.fail(f"备份流程失败：{e}")
    
    def test_monitoring_to_healing(self):
        """测试监控→自愈流程"""
        try:
            from auto_ops import AutoOps
            ops = AutoOps()
            healing = ops.auto_healing()
            assert 'checks' in healing
            assert 'issues_found' in healing
            ops.close()
        except Exception as e:
            pytest.fail(f"自愈流程失败：{e}")


class TestE2E_Complete:
    """完整端到端流程测试"""
    
    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 数据同步
        test_data = {'symbol': '600519.SH', 'datetime': datetime.now(), 'close': 1440.11, 'volume': 100}
        from neo4j_sync import Neo4jSync
        sync = Neo4jSync()
        sync.sync_stock_data(test_data)
        
        # 2. 事件发布
        from event_publisher import EventPublisher
        publisher = EventPublisher()
        publisher.publish_trade_event('600519.SH', 'buy', 1440.11, 100, 'virtual_2026')
        
        # 3. 告警检查
        from smart_alert import SmartAlertSystem
        alert = SmartAlertSystem()
        alert.run_all_checks()
        
        # 4. 健康检查
        from predictive_maintenance import PredictiveMaintenance
        pm = PredictiveMaintenance()
        pm.get_system_health_report()
        
        # 5. 知识推理
        from knowledge_reasoning import KnowledgeReasoning
        kr = KnowledgeReasoning()
        kr.get_trading_advice('600519.SH')
        
        # 6. 运维检查
        from auto_ops import AutoOps
        ops = AutoOps()
        ops.get_system_status()
        
        # 清理
        sync.close()
        publisher.close()
        alert.close()
        pm.close()
        kr.close()
        ops.close()
        
        assert True


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
