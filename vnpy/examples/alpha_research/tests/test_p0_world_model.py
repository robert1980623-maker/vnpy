#!/usr/bin/env python3
"""
P0 任务回归测试用例 - vnpy 世界模型集成

测试范围:
- P0-1: 数据同步管道
- P0-2: 交易事件总线
- P0-3: Agent 注册同步

用法:
    python3 -m pytest tests/test_p0_world_model.py -v
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加 world_model 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'world_model'))


class TestP0_1_DataSync:
    """P0-1: 数据同步管道测试"""
    
    def test_neo4j_sync_module_import(self):
        """测试 Neo4j 同步模块导入"""
        try:
            from neo4j_sync import Neo4jSync
            assert True
        except ImportError:
            pytest.fail("Neo4jSync 模块导入失败")
    
    def test_neo4j_connection(self):
        """测试 Neo4j 连接"""
        from neo4j_sync import Neo4jSync
        sync = Neo4jSync()
        assert sync.driver is not None
        sync.close()
    
    def test_sync_stock_data(self):
        """测试股票数据同步"""
        from neo4j_sync import Neo4jSync
        sync = Neo4jSync()
        
        test_data = {
            'symbol': '600519.SH',
            'datetime': datetime.now(),
            'close': 1440.11,
            'volume': 100
        }
        
        try:
            sync.sync_stock_data(test_data)
            assert True
        except Exception as e:
            pytest.fail(f"数据同步失败：{e}")
        finally:
            sync.close()
    
    def test_batch_download_enhanced_exists(self):
        """测试增强版下载脚本存在"""
        script_path = Path(__file__).parent.parent / 'batch_download_enhanced.py'
        assert script_path.exists(), "batch_download_enhanced.py 不存在"
    
    def test_tushare_primary_config(self):
        """测试 Tushare 主数据源配置"""
        script_path = Path(__file__).parent.parent / 'batch_download_enhanced.py'
        content = script_path.read_text()
        
        assert 'DATA_SOURCE_PRIMARY = "tushare"' in content
        assert 'DATA_SOURCE_BACKUP = "akshare"' in content


class TestP0_2_EventBus:
    """P0-2: 交易事件总线测试"""
    
    def test_event_schema_import(self):
        """测试事件 Schema 导入"""
        try:
            from event_schema import EventType, EventSchema
            assert len(EventType) == 5
        except ImportError:
            pytest.fail("event_schema 模块导入失败")
    
    def test_event_types_defined(self):
        """测试事件类型定义"""
        from event_schema import EventType
        
        expected_types = [
            'TradeExecutedEvent',
            'OrderPlacedEvent',
            'OrderCancelledEvent',
            'PositionChangedEvent',
            'PortfolioUpdatedEvent'
        ]
        
        for et in expected_types:
            assert et in [e.value for e in EventType]
    
    def test_create_trade_event(self):
        """测试创建交易事件"""
        from event_schema import create_trade_event
        
        event = create_trade_event(
            symbol='600519.SH',
            side='buy',
            price=1440.11,
            volume=200,
            account='virtual_2026'
        )
        
        assert event['event_type'] == 'TradeExecutedEvent'
        assert event['payload']['symbol'] == '600519.SH'
        assert event['payload']['side'] == 'buy'
    
    def test_event_publisher_import(self):
        """测试事件发布模块导入"""
        try:
            from event_publisher import EventPublisher
            assert True
        except ImportError:
            pytest.fail("event_publisher 模块导入失败")
    
    def test_event_publisher_publish(self):
        """测试事件发布"""
        from event_publisher import EventPublisher
        
        publisher = EventPublisher()
        msg_id = publisher.publish_trade_event(
            symbol='600519.SH',
            side='buy',
            price=1440.11,
            volume=200,
            account='virtual_2026'
        )
        
        assert msg_id is not None
        publisher.close()
    
    def test_event_query(self):
        """测试事件查询"""
        from event_publisher import EventPublisher
        
        publisher = EventPublisher()
        events = publisher.get_events('TradeExecutedEvent', count=5)
        
        assert isinstance(events, list)
        publisher.close()
    
    def test_event_listener_import(self):
        """测试事件监听器导入"""
        try:
            from event_listener import EventListener
            assert True
        except ImportError:
            pytest.fail("event_listener 模块导入失败")
    
    def test_event_sourcing_import(self):
        """测试事件溯源导入"""
        try:
            from event_sourcing import EventSourcing
            assert True
        except ImportError:
            pytest.fail("event_sourcing 模块导入失败")
    
    def test_event_aggregate(self):
        """测试事件聚合统计"""
        from event_sourcing import EventSourcing
        
        sourcing = EventSourcing()
        stats = sourcing.aggregate_trades()
        
        assert 'total_trades' in stats
        assert 'buy_count' in stats
        assert 'sell_count' in stats
        sourcing.close()


class TestP0_3_AgentRegistry:
    """P0-3: Agent 注册同步测试"""
    
    def test_agent_registry_import(self):
        """测试 Agent 注册模块导入"""
        try:
            from agent_registry import AgentRegistry
            assert True
        except ImportError:
            pytest.fail("agent_registry 模块导入失败")
    
    def test_agent_scan(self):
        """测试 Agent 扫描"""
        from agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        project_dir = Path(__file__).parent.parent
        agents = registry.scan_agents(str(project_dir))
        
        assert len(agents) > 0
        registry.close()
    
    def test_agent_types_mapped(self):
        """测试 Agent 类型映射"""
        from agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        expected_types = [
            'monitoring', 'data', 'trading',
            'risk', 'coordinator', 'reporting'
        ]
        
        for atype in expected_types:
            assert atype in registry.agent_type_map.values()
        
        registry.close()
    
    def test_agent_stats(self):
        """测试 Agent 统计"""
        from agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        stats = registry.get_agent_stats()
        
        assert 'total' in stats
        assert 'by_type' in stats
        assert stats['total'] > 0
        registry.close()
    
    def test_agent_files_exist(self):
        """测试 Agent 文件存在"""
        project_dir = Path(__file__).parent.parent
        
        expected_agents = [
            'agent_health_check.py',
            'agent_error_handler.py',
            'chief_risk_officer.py',
            'compliance_agent.py',
            'data_agent.py',
            'quant_agent.py',
            'report_agent.py'
        ]
        
        for agent_file in expected_agents:
            agent_path = project_dir / agent_file
            assert agent_path.exists(), f"{agent_file} 不存在"


class TestP0_Integration:
    """P0 集成测试"""
    
    def test_world_model_directory_exists(self):
        """测试 world_model 目录存在"""
        world_model_dir = Path(__file__).parent.parent / 'world_model'
        assert world_model_dir.exists()
        assert world_model_dir.is_dir()
    
    def test_world_model_init_exists(self):
        """测试 __init__.py 存在"""
        init_file = Path(__file__).parent.parent / 'world_model' / '__init__.py'
        assert init_file.exists()
    
    def test_all_p0_modules_importable(self):
        """测试所有 P0 模块可导入"""
        modules = [
            'neo4j_sync',
            'event_schema',
            'event_publisher',
            'event_listener',
            'event_sourcing',
            'agent_registry'
        ]
        
        for module_name in modules:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{module_name} 模块导入失败")
    
    def test_requirements_file_exists(self):
        """测试 requirements.txt 存在"""
        req_file = Path(__file__).parent.parent / 'world_model' / 'requirements.txt'
        assert req_file.exists()
    
    def test_documentation_complete(self):
        """测试文档完整性"""
        world_model_dir = Path(__file__).parent.parent / 'world_model'
        
        expected_docs = [
            'P0_1_COMPLETE.md',
            'P0_2_FINAL.md',
            'P0_3_COMPLETE.md',
            'P0_QA_REPORT.md'
        ]
        
        for doc in expected_docs:
            doc_path = world_model_dir / doc
            assert doc_path.exists(), f"{doc} 不存在"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
