#!/usr/bin/env python3
"""事件溯源查询模块"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

# 导入基础设施配置（降级方案）
sys.path.insert(0, '/Users/rowang/projects/vnpy')
try:
    from infrastructure_config import cache_instance, CacheFactory
    CACHE_FACTORY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ infrastructure_config 不可用: {e}")
    cache_instance = None
    CacheFactory = None
    CACHE_FACTORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入 EventPublisher 的共享内存存储
from event_publisher import _SHARED_MEMORY_STORE

# 共享内存存储（与 EventPublisher 共用）



class EventSourcing:
    """事件溯源查询器（支持缓存降级）"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        # 使用 CacheFactory 创建缓存实例
        if CACHE_FACTORY_AVAILABLE:
            self.cache = CacheFactory.create_cache('auto')
        else:
            self.cache = None
        
        # 如果缓存无效，使用内存 fallback
        if self.cache is None or (hasattr(self.cache, 'available') and not self.cache.available):
            self.cache = None  # 我们主要使用内存存储
        
        # 初始化内存存储
        self._memory_store = _SHARED_MEMORY_STORE
        
        logger.info("✅ 事件溯源初始化完成（降级模式）")
    
    def publish_event(self, event_type: str, event_data: dict):
        """内部方法：发布事件到内存存储"""
        stream_key = f"events:{event_type}"
        if stream_key not in self._memory_store:
            self._memory_store[stream_key] = []
        msg_id = f"{stream_key}-{len(self._memory_store[stream_key])}"
        self._memory_store[stream_key].append({
            'message_id': msg_id,
            'event_id': event_data.get('event_id'),
            'event_type': event_type,
            'timestamp': event_data.get('timestamp'),
            'payload': json.dumps(event_data.get('payload', {}))
        })
        return msg_id
    
    def query_events(self, event_type: str, limit: int = 100) -> List[Dict]:
        """查询事件"""
        stream_key = f"events:{event_type}"
        
        if stream_key in self._memory_store:
            messages = self._memory_store[stream_key][-limit:]
            events = []
            for msg_data in messages:
                event = {
                    'message_id': msg_data.get('message_id'),
                    'event_id': msg_data.get('event_id'),
                    'event_type': msg_data.get('event_type'),
                    'timestamp': msg_data.get('timestamp'),
                    'payload': json.loads(msg_data.get('payload', '{}'))
                }
                events.append(event)
            return events
        return []
    
    def query_by_symbol(self, symbol: str) -> List[Dict]:
        """按股票代码查询"""
        events = self.query_events('TradeExecutedEvent', limit=1000)
        return [e for e in events if e['payload'].get('symbol') == symbol]
    
    def aggregate_trades(self) -> Dict:
        """交易聚合统计"""
        events = self.query_events('TradeExecutedEvent', limit=10000)
        stats = {
            'total_trades': len(events), 
            'buy_count': 0, 
            'sell_count': 0, 
            'buy_volume': 0.0, 
            'sell_volume': 0.0
        }
        for e in events:
            p = e['payload']
            if p.get('side') == 'buy':
                stats['buy_count'] += 1
                stats['buy_volume'] += float(p.get('volume', 0))
            else:
                stats['sell_count'] += 1
                stats['sell_volume'] += float(p.get('volume', 0))
        return stats
    
    def get_stats(self) -> Dict:
        """获取统计"""
        stats = {'total_streams': 0, 'streams': {}}
        for et in ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']:
            stream_key = f"events:{et}"
            if stream_key in self._memory_store:
                count = len(self._memory_store[stream_key])
                stats['streams'][et] = {'count': count}
                stats['total_streams'] += count
            else:
                stats['streams'][et] = {'count': 0}
        return stats
    
    def close(self):
        """关闭连接"""
        if self.cache and hasattr(self.cache, 'close'):
            self.cache.close()
        logger.info("事件溯源已关闭")


if __name__ == "__main__":
    print("=" * 60)
    print("测试事件溯源查询（降级模式）")
    print("=" * 60)
    
    sourcing = EventSourcing()
    
    # 添加一些测试数据
    print("\n1. 添加测试事件...")
    test_event = {
        'event_id': 'test-001',
        'event_type': 'TradeExecutedEvent',
        'timestamp': datetime.now().isoformat(),
        'payload': {
            'symbol': '600519.SH',
            'side': 'buy',
            'price': 1440.11,
            'volume': 100
        }
    }
    msg_id = sourcing.publish_event('TradeExecutedEvent', test_event)
    print(f"   事件 ID: {msg_id}")
    
    print("\n2. 查询交易事件...")
    events = sourcing.query_events('TradeExecutedEvent', limit=5)
    print(f"   查询到 {len(events)} 个事件")
    
    print("\n3. 按股票查询...")
    events = sourcing.query_by_symbol('600519.SH')
    print(f"   查询到 {len(events)} 个事件")
    
    print("\n4. 交易统计...")
    stats = sourcing.aggregate_trades()
    print(f"   总交易：{stats['total_trades']}, 买入：{stats['buy_count']}, 卖出：{stats['sell_count']}")
    
    print("\n5. 事件统计...")
    event_stats = sourcing.get_stats()
    print(f"   总事件：{event_stats['total_streams']}")
    
    sourcing.close()
    print("\n✅ 测试完成")
