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
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    import redis
    from event_schema import create_trade_event, create_order_event, create_position_event, EventType
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis 模块不可用")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventPublisher:
    """事件发布器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        if not REDIS_AVAILABLE:
            raise Exception("Redis 模块不可用")
        
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        self.redis.ping()
        logger.info("✅ Redis 连接成功")
        
        # 事件计数器
        self.event_count = 0
    
    def publish(self, event: dict) -> str:
        """
        发布事件到 Redis Streams
        
        Args:
            event: 事件 dict
        
        Returns:
            str: 消息 ID
        """
        event_type = event.get('event_type', 'UnknownEvent')
        stream_key = f"events:{event_type}"
        
        # 将事件数据转换为 Redis Stream 格式
        stream_data = {
            'event_id': event.get('event_id'),
            'event_type': event_type,
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'severity': event.get('severity'),
            'payload': json.dumps(event.get('payload', {})),
            'published_at': datetime.now().isoformat()
        }
        
        # 发布到 Stream
        message_id = self.redis.xadd(stream_key, stream_data)
        
        # 同时发布到 Pub/Sub（实时通知）
        pubsub_channel = f"channel:{event_type}"
        self.redis.publish(pubsub_channel, json.dumps(event))
        
        self.event_count += 1
        logger.info(f"📤 事件已发布：{event_type} (ID: {message_id})")
        
        return message_id
    
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
        event = create_trade_event(symbol, side, price, volume, account, **kwargs)
        return self.publish(event)
    
    def publish_order_event(self, symbol: str, side: str, price: float,
                           volume: float, account: str, **kwargs) -> str:
        """发布订单提交事件"""
        event = create_order_event(symbol, side, price, volume, account, **kwargs)
        return self.publish(event)
    
    def publish_position_event(self, symbol: str, account: str,
                              change_volume: float, new_volume: float, **kwargs) -> str:
        """发布持仓变动事件"""
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
        messages = self.redis.xrevrange(stream_key, count=count)
        
        events = []
        for msg_id, msg_data in messages:
            event = {
                'message_id': msg_id,
                'event_id': msg_data.get('event_id'),
                'event_type': msg_data.get('event_type'),
                'timestamp': msg_data.get('timestamp'),
                'payload': json.loads(msg_data.get('payload', '{}'))
            }
            events.append(event)
        
        return events
    
    def get_stats(self) -> dict:
        """获取事件统计"""
        stats = {
            'total_published': self.event_count,
            'streams': {}
        }
        
        # 查询各事件类型的数量
        for event_type in EventType:
            stream_key = f"events:{event_type.value}"
            try:
                info = self.redis.xinfo_stream(stream_key)
                stats['streams'][event_type.value] = {
                    'count': info.get('length', 0),
                    'first_entry': info.get('first-entry'),
                    'last_entry': info.get('last-entry')
                }
            except:
                stats['streams'][event_type.value] = {'count': 0}
        
        return stats
    
    def close(self):
        """关闭连接"""
        if self.redis:
            self.redis.close()
            logger.info("Redis 连接已关闭")


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("测试事件发布模块")
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
