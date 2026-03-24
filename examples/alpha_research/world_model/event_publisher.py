#!/usr/bin/env python3
"""
交易事件发布模块

功能:
- 发布交易事件到 Redis Streams
- 事件持久化
- 事件溯源查询

用法:
    from event_publisher import EventPublisher
    
    publisher = EventPublisher()
    publisher.publish_trade_event(...)

降级方案:
- 优先使用 Redis（通过 CacheFactory）
- Redis 不可用时自动降级到 MemoryCache
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from event_schema import create_trade_event, create_order_event, create_position_event, EventType
    EVENT_SCHEMA_AVAILABLE = True
except ImportError:
    EVENT_SCHEMA_AVAILABLE = False
    print("⚠️ EventSchema 模块不可用")

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

# 共享内存存储（所有实例共用，用于 fallback 模式下的事件共享）
_SHARED_MEMORY_STORE = {}



class MemoryCacheFallback:
    """内存缓存降级实现（当 Redis 不可用时）"""
    
    def __init__(self):
        self._data = {}
        self._pubsub = {}
        self.available = True
    
    def get(self, key: str):
        return self._data.get(key)
    
    def set(self, key: str, value, expire: int = None) -> bool:
        self._data[key] = value
        return True
    
    def publish(self, channel: str, message: str) -> int:
        """发布消息到内存中的频道"""
        if channel not in self._pubsub:
            self._pubsub[channel] = []
        self._pubsub[channel].append(message)
        return 1
    
    def xadd(self, stream_key: str, data: dict):
        """模拟 xadd（实际存储到内存）"""
        if not hasattr(self, '_streams'):
            self._streams = {}
        if stream_key not in self._streams:
            self._streams[stream_key] = []
        msg_id = f"{stream_key}-{len(self._streams[stream_key])}"
        self._streams[stream_key].append((msg_id, data))
        return msg_id
    
    def xrevrange(self, stream_key: str, count: int = 10):
        """模拟 xrevrange"""
        if not hasattr(self, '_streams') or stream_key not in self._streams:
            return []
        messages = self._streams[stream_key][-count:]
        return messages[::-1]  # 逆序返回
    
    def xinfo_stream(self, stream_key: str):
        """模拟 xinfo_stream"""
        if not hasattr(self, '_streams') or stream_key not in self._streams:
            return {'length': 0}
        return {'length': len(self._streams[stream_key])}
    
    def close(self):
        pass


class EventPublisher:
    """事件发布器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        self.redis_db = redis_db
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        # 使用 CacheFactory 创建缓存实例（自动降级）
        if CACHE_FACTORY_AVAILABLE:
            self.cache = CacheFactory.create_cache('auto')
        else:
            self.cache = None
        
        # 如果缓存无效，使用内存 fallback
        if self.cache is None or (hasattr(self.cache, 'available') and not self.cache.available):
            self.cache = MemoryCacheFallback()
        
        # 事件计数器
        self.event_count = 0
        
        # 初始化内存存储
        self._memory_store = _SHARED_MEMORY_STORE
        
        logger.info("✅ 事件发布器初始化成功（降级模式）")
    
    def publish(self, event: dict) -> str:
        """
        发布事件到缓存（Redis Streams 或 Memory）
        
        Args:
            event: 事件 dict
        
        Returns:
            str: 消息 ID
        """
        event_type = event.get('event_type', 'UnknownEvent')
        stream_key = f"events:{event_type}"
        
        # 将事件数据转换为存储格式
        stream_data = {
            'event_id': event.get('event_id'),
            'event_type': event_type,
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'severity': event.get('severity'),
            'payload': json.dumps(event.get('payload', {})),
            'published_at': datetime.now().isoformat()
        }
        
        # 发布到 Pub/Sub（实时通知）
        pubsub_channel = f"channel:{event_type}"
        if self.cache:
            self.cache.publish(pubsub_channel, json.dumps(event))
        
        # 存储到内存
        if stream_key not in self._memory_store:
            self._memory_store[stream_key] = []
        mock_id = f"{stream_key}-{len(self._memory_store[stream_key])}"
        self._memory_store[stream_key].append({
            'message_id': mock_id,
            **stream_data
        })
        
        self.event_count += 1
        logger.info(f"📤 事件已发布：{event_type}")
        
        return mock_id
    
    def publish_trade_event(self, symbol: str, side: str, price: float,
                           volume: float, account: str, **kwargs) -> str:
        """
        发布交易执行事件
        
        Args:
            symbol: 股票代码
            side: 买卖方向
            price: 成交价格
            volume: 成交数量
            account: 账户 ID
            **kwargs: 其他字段
        
        Returns:
            str: 消息 ID
        """
        if not EVENT_SCHEMA_AVAILABLE:
            logger.error("EventSchema 不可用，无法创建交易事件")
            return ""
        event = create_trade_event(symbol, side, price, volume, account, **kwargs)
        return self.publish(event)
    
    def publish_order_event(self, symbol: str, side: str, price: float,
                           volume: float, account: str, **kwargs) -> str:
        """发布订单提交事件"""
        if not EVENT_SCHEMA_AVAILABLE:
            logger.error("EventSchema 不可用，无法创建订单事件")
            return ""
        event = create_order_event(symbol, side, price, volume, account, **kwargs)
        return self.publish(event)
    
    def publish_position_event(self, symbol: str, account: str,
                              change_volume: float, new_volume: float, **kwargs) -> str:
        """发布持仓变动事件"""
        if not EVENT_SCHEMA_AVAILABLE:
            logger.error("EventSchema 不可用，无法创建持仓事件")
            return ""
        event = create_position_event(symbol, account, change_volume, new_volume, **kwargs)
        return self.publish(event)
    
    def get_events(self, event_type: str, count: int = 10) -> list:
        """
        查询事件历史
        
        Args:
            event_type: 事件类型
            count: 数量
        
        Returns:
            list: 事件列表
        """
        stream_key = f"events:{event_type}"
        
        if stream_key in self._memory_store:
            messages = self._memory_store[stream_key][-count:]
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
    
    def get_stats(self) -> dict:
        """获取事件统计"""
        stats = {
            'total_published': self.event_count,
            'streams': {}
        }
        
        event_types = ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']
        if EVENT_SCHEMA_AVAILABLE:
            event_types = [e.value for e in EventType]
        
        for event_type in event_types:
            stream_key = f"events:{event_type}"
            if stream_key in self._memory_store:
                stats['streams'][event_type] = {
                    'count': len(self._memory_store[stream_key]),
                    'first_entry': self._memory_store[stream_key][0] if self._memory_store[stream_key] else None,
                    'last_entry': self._memory_store[stream_key][-1] if self._memory_store[stream_key] else None
                }
            else:
                stats['streams'][event_type] = {'count': 0}
        
        return stats
    
    def close(self):
        """关闭连接"""
        if self.cache and hasattr(self.cache, 'close'):
            self.cache.close()
        logger.info("事件发布器已关闭")


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("测试事件发布模块（降级模式）")
    print("=" * 60)
    
    publisher = EventPublisher()
    
    # 发布交易事件
    print("\n1. 发布交易执行事件...")
    msg_id = publisher.publish_trade_event(
        symbol='600519.SH',
        side='buy',
        price=1440.11,
        volume=200,
        account='virtual_2026',
        commission=5.0
    )
    print(f"   消息 ID: {msg_id}")
    
    # 发布订单事件
    print("\n2. 发布订单提交事件...")
    msg_id = publisher.publish_order_event(
        symbol='000858.SZ',
        side='sell',
        price=103.22,
        volume=100,
        account='virtual_2026'
    )
    print(f"   消息 ID: {msg_id}")
    
    # 发布持仓事件
    print("\n3. 发布持仓变动事件...")
    msg_id = publisher.publish_position_event(
        symbol='600519.SH',
        account='virtual_2026',
        change_volume=200,
        new_volume=400
    )
    print(f"   消息 ID: {msg_id}")
    
    # 查询事件
    print("\n4. 查询交易事件历史...")
    events = publisher.get_events('TradeExecutedEvent', count=5)
    print(f"   查询到 {len(events)} 个事件")
    for event in events:
        print(f"   - {event['event_id']}: {event['payload'].get('symbol')}")
    
    # 统计
    print("\n5. 事件统计...")
    stats = publisher.get_stats()
    print(f"   总发布数：{stats['total_published']}")
    for event_type, data in stats['streams'].items():
        print(f"   - {event_type}: {data['count']} 个")
    
    publisher.close()
    print("\n✅ 测试完成")
