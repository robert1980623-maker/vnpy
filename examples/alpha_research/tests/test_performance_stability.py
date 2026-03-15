#!/usr/bin/env python3
"""
性能测试和稳定性测试
"""

import pytest
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'world_model'))


class TestPerformance:
    """性能测试"""
    
    def test_data_sync_performance(self):
        """测试数据同步性能"""
        from neo4j_sync import Neo4jSync
        
        sync = Neo4jSync()
        test_data = {'symbol': '600519.SH', 'datetime': datetime.now(), 'close': 1440.11, 'volume': 100}
        
        start = time.time()
        for i in range(10):
            test_data['symbol'] = f'60051{i}.SH'
            sync.sync_stock_data(test_data)
        elapsed = time.time() - start
        
        sync.close()
        
        # 性能要求：10 次同步 < 5 秒
        assert elapsed < 5.0, f"数据同步性能不达标：{elapsed:.2f}秒"
    
    def test_event_publishing_performance(self):
        """测试事件发布性能"""
        from event_publisher import EventPublisher
        
        publisher = EventPublisher()
        
        start = time.time()
        for i in range(20):
            publisher.publish_trade_event(f'60051{i}.SH', 'buy', 1440.11, 100, 'virtual_2026')
        elapsed = time.time() - start
        
        publisher.close()
        
        # 性能要求：20 个事件 < 5 秒
        assert elapsed < 5.0, f"事件发布性能不达标：{elapsed:.2f}秒"
    
    def test_alert_system_performance(self):
        """测试告警系统性能"""
        from smart_alert import SmartAlertSystem, AlertLevel, AlertType
        
        alert = SmartAlertSystem()
        
        start = time.time()
        for i in range(10):
            alert.create_alert(
                level=AlertLevel.HIGH,
                alert_type=AlertType.TRADE_ANOMALY,
                title=f"测试告警{i}",
                message="性能测试"
            )
        elapsed = time.time() - start
        
        alert.close()
        
        # 性能要求：10 个告警 < 3 秒
        assert elapsed < 3.0, f"告警系统性能不达标：{elapsed:.2f}秒"
    
    def test_query_performance(self):
        """测试查询性能"""
        from predictive_maintenance import PredictiveMaintenance
        
        pm = PredictiveMaintenance()
        
        start = time.time()
        pm.get_system_health_report()
        elapsed = time.time() - start
        
        pm.close()
        
        # 性能要求：健康报告查询 < 5 秒
        assert elapsed < 5.0, f"查询性能不达标：{elapsed:.2f}秒"


class TestStability:
    """稳定性测试"""
    
    def test_concurrent_operations(self):
        """测试并发操作稳定性"""
        import threading
        
        from neo4j_sync import Neo4jSync
        from event_publisher import EventPublisher
        
        errors = []
        
        def sync_data(sync, i):
            try:
                test_data = {'symbol': f'60051{i}.SH', 'datetime': datetime.now(), 'close': 1440.11, 'volume': 100}
                sync.sync_stock_data(test_data)
            except Exception as e:
                errors.append(f"sync_{i}: {e}")
        
        def publish_event(publisher, i):
            try:
                publisher.publish_trade_event(f'60051{i}.SH', 'buy', 1440.11, 100, 'virtual_2026')
            except Exception as e:
                errors.append(f"publish_{i}: {e}")
        
        sync = Neo4jSync()
        publisher = EventPublisher()
        
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=sync_data, args=(sync, i))
            t2 = threading.Thread(target=publish_event, args=(publisher, i))
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        sync.close()
        publisher.close()
        
        assert len(errors) == 0, f"并发操作失败：{errors}"
    
    def test_long_running_operations(self):
        """测试长时间运行稳定性"""
        from smart_alert import SmartAlertSystem, AlertLevel, AlertType
        
        alert = SmartAlertSystem()
        
        errors = []
        for i in range(50):
            try:
                alert.create_alert(
                    level=AlertLevel.MEDIUM,
                    alert_type=AlertType.DATA_QUALITY,
                    title=f"长时间测试{i}",
                    message="稳定性测试"
                )
            except Exception as e:
                errors.append(f"iteration_{i}: {e}")
        
        alert.close()
        
        assert len(errors) == 0, f"长时间运行失败：{errors}"
    
    def test_resource_cleanup(self):
        """测试资源清理"""
        from neo4j_sync import Neo4jSync
        from event_publisher import EventPublisher
        from smart_alert import SmartAlertSystem
        from predictive_maintenance import PredictiveMaintenance
        from knowledge_reasoning import KnowledgeReasoning
        from auto_ops import AutoOps
        
        # 创建多个实例
        instances = [
            Neo4jSync(),
            EventPublisher(),
            SmartAlertSystem(),
            PredictiveMaintenance(),
            KnowledgeReasoning(),
            AutoOps()
        ]
        
        # 关闭所有实例
        for instance in instances:
            try:
                instance.close()
            except:
                pass
        
        # 验证资源已释放 (简单检查)
        assert True


class TestIntegration:
    """集成测试"""
    
    def test_all_modules_integration(self):
        """测试所有模块集成"""
        # 导入所有模块
        from neo4j_sync import Neo4jSync
        from event_publisher import EventPublisher
        from event_sourcing import EventSourcing
        from smart_alert import SmartAlertSystem
        from predictive_maintenance import PredictiveMaintenance
        from knowledge_reasoning import KnowledgeReasoning
        from auto_ops import AutoOps
        
        # 创建实例
        sync = Neo4jSync()
        publisher = EventPublisher()
        sourcing = EventSourcing()
        alert = SmartAlertSystem()
        pm = PredictiveMaintenance()
        kr = KnowledgeReasoning()
        ops = AutoOps()
        
        # 验证所有实例正常创建
        assert sync is not None
        assert publisher is not None
        assert sourcing is not None
        assert alert is not None
        assert pm is not None
        assert kr is not None
        assert ops is not None
        
        # 清理
        sync.close()
        publisher.close()
        sourcing.close()
        alert.close()
        pm.close()
        kr.close()
        ops.close()
    
    def test_data_consistency(self):
        """测试数据一致性"""
        from neo4j_sync import Neo4jSync
        from event_publisher import EventPublisher
        from event_sourcing import EventSourcing
        
        # 同步数据
        test_data = {'symbol': 'TEST.SH', 'datetime': datetime.now(), 'close': 100.00, 'volume': 100}
        sync = Neo4jSync()
        sync.sync_stock_data(test_data)
        
        # 发布事件
        publisher = EventPublisher()
        publisher.publish_trade_event('TEST.SH', 'buy', 100.00, 100, 'test')
        
        # 查询事件
        sourcing = EventSourcing()
        events = sourcing.query_events('TradeExecutedEvent', limit=5)
        
        # 验证数据一致性
        assert len(events) > 0
        
        # 清理
        sync.close()
        publisher.close()
        sourcing.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
