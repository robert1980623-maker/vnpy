#!/usr/bin/env python3
"""事件溯源查询模块"""

import sys, json, logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

try:
    import redis
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventSourcing:
    def __init__(self, redis_host='localhost', redis_port=6379):
        if not REDIS_AVAILABLE:
            raise Exception("Redis 不可用")
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.redis.ping()
        logger.info("✅ 事件溯源初始化完成")
    
    def query_events(self, event_type: str, limit: int = 100) -> List[Dict]:
        stream_key = f"events:{event_type}"
        messages = self.redis.xrevrange(stream_key, count=limit)
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
    
    def query_by_symbol(self, symbol: str) -> List[Dict]:
        events = self.query_events('TradeExecutedEvent', limit=1000)
        return [e for e in events if e['payload'].get('symbol') == symbol]
    
    def aggregate_trades(self) -> Dict:
        events = self.query_events('TradeExecutedEvent', limit=10000)
        stats = {'total_trades': len(events), 'buy_count': 0, 'sell_count': 0, 'buy_volume': 0.0, 'sell_volume': 0.0}
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
        stats = {'total_streams': 0, 'streams': {}}
        for et in ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']:
            try:
                info = self.redis.xinfo_stream(f"events:{et}")
                stats['streams'][et] = {'count': info.get('length', 0)}
                stats['total_streams'] += info.get('length', 0)
            except:
                stats['streams'][et] = {'count': 0}
        return stats
    
    def close(self):
        """关闭连接"""
        if self.redis:
            self.redis.close()


if __name__ == "__main__":
    print("=" * 60)
    print("测试事件溯源查询")
    print("=" * 60)
    
    sourcing = EventSourcing()
    
    print("\n1. 查询交易事件...")
    events = sourcing.query_events('TradeExecutedEvent', limit=5)
    print(f"   查询到 {len(events)} 个事件")
    
    print("\n2. 按股票查询...")
    events = sourcing.query_by_symbol('600519.SH')
    print(f"   查询到 {len(events)} 个事件")
    
    print("\n3. 交易统计...")
    stats = sourcing.aggregate_trades()
    print(f"   总交易：{stats['total_trades']}, 买入：{stats['buy_count']}, 卖出：{stats['sell_count']}")
    
    print("\n4. 事件统计...")
    event_stats = sourcing.get_stats()
    print(f"   总事件：{event_stats['total_streams']}")
    
    sourcing.close()
    print("\n✅ 测试完成")
