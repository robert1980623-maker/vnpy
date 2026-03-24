#!/usr/bin/env python3
"""
事件溯源查询模块

功能:
- 查询事件历史
- 事件聚合分析
- 事件导出

用法:
    from event溯源 import EventSourcing
    
    sourcing = EventSourcing()
    events = sourcing.query_events('TradeExecutedEvent', limit=10)
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventSourcing:
    """事件溯源查询"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        if not REDIS_AVAILABLE:
            raise Exception("Redis 模块不可用")
        
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.redis.ping()
        logger.info("✅ 事件溯源查询初始化完成")
    
    def query_events(self, event_type: str, 
                     start_time: str = None,
                     end_time: str = None,
                     limit: int = 100) -> List[Dict]:
        """
        查询事件历史
        
        Args:
            event_type: 事件类型
            start_time: 开始时间 (ISO 格式)
            end_time: 结束时间 (ISO 格式)
            limit: 数量限制
        
        Returns:
            list: 事件列表
        """
        stream_key = f"events:{event_type}"
        
        # 查询所有事件
        messages = self.redis.xrevrange(stream_key, max='+', min='-', count=limit)
        
        events = []
        for msg_id, msg_data in messages:
            event = {
                'message_id': msg_id,
                'event_id': msg_data.get('event_id'),
                'event_type': msg_data.get('event_type'),
                'timestamp': msg_data.get('timestamp'),
                'source': msg_data.get('source'),
                'severity': msg_data.get('severity'),
                'payload': json.loads(msg_data.get('payload', '{}'))
            }
            
            # 时间过滤
            if start_time and event['timestamp'] < start_time:
                continue
            if end_time and event['timestamp'] > end_time:
                continue
            
            events.append(event)
        
        return events
    
    def query_by_symbol(self, symbol: str, event_type: str = None) -> List[Dict]:
        """
        按股票代码查询事件
        
        Args:
            symbol: 股票代码
            event_type: 事件类型（可选）
        
        Returns:
            list: 事件列表
        """
        if event_type:
            event_types = [event_type]
        else:
            event_types = ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']
        
        all_events = []
        for et in event_types:
            events = self.query_events(et, limit=1000)
            
            # 过滤股票代码
            for event in events:
                if event['payload'].get('symbol') == symbol:
                    all_events.append(event)
        
        # 按时间排序
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_events
    
    def query_by_account(self, account: str, event_type: str = None) -> List[Dict]:
        """
        按账户查询事件
        
        Args:
            account: 账户 ID
            event_type: 事件类型（可选）
        
        Returns:
            list: 事件列表
        """
        if event_type:
            event_types = [event_type]
        else:
            event_types = ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']
        
        all_events = []
        for et in event_types:
            events = self.query_events(et, limit=1000)
            
            # 过滤账户
            for event in events:
                if event['payload'].get('account') == account:
                    all_events.append(event)
        
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_events
    
    def aggregate_trades(self, symbol: str = None, 
                        account: str = None) -> Dict:
        """
        聚合交易统计
        
        Args:
            symbol: 股票代码（可选）
            account: 账户 ID（可选）
        
        Returns:
            dict: 统计信息
        """
        events = self.query_events('TradeExecutedEvent', limit=10000)
        
        # 过滤
        if symbol:
            events = [e for e in events if e['payload'].get('symbol') == symbol]
        if account:
            events = [e for e in events if e['payload'].get('account') == account]
        
        # 聚合统计
        stats = {
            'total_trades': len(events),
            'buy_count': 0,
            'sell_count': 0,
            'buy_volume': 0.0,
            'sell_volume': 0.0,
            'total_commission': 0.0,
            'symbols': set()
        }
        
        for event in events:
            payload = event['payload']
            side = payload.get('side', '')
            volume = float(payload.get('volume', 0))
            commission = float(payload.get('commission', 0))
            
            stats['symbols'].add(payload.get('symbol'))
            stats['total_commission'] += commission
            
            if side == 'buy':
                stats['buy_count'] += 1
                stats['buy_volume'] += volume
            elif side == 'sell':
                stats['sell_count'] += 1
                stats['sell_volume'] += volume
        
        stats['symbols'] = list(stats['symbols'])
        
        return stats
    
    def export_events(self, event_type: str, output_file: str, format: str = 'json'):
        """
        导出事件
        
        Args:
            event_type: 事件类型
            output_file: 输出文件
            format: 格式 (json/csv)
        """
        events = self.query_events(event_type, limit=10000)
        
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
        elif format == 'csv':
            import csv
            if events:
                keys = events[0].keys()
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(events)
        
        logger.info(f"✅ 已导出 {len(events)} 个事件到 {output_file}")
    
    def get_stats(self) -> Dict:
        """获取事件统计"""
        from event_schema import EventType
        
        stats = {
            'total_streams': 0,
            'streams': {}
        }
        
        for event_type in EventType:
            stream_key = f"events:{event_type.value}"
            try:
                info = self.redis.xinfo_stream(stream_key)
                stats['streams'][event_type.value] = {
                    'count': info.get('length', 0),
                    'consumers': info.get('groups', 0),
                    'first_entry': info.get('first-entry'),
                    'last_entry': info.get('last-entry')
                }
                stats['total_streams'] += info.get('length', 0)
            except:
                stats['streams'][event_type.value] = {'count': 0}
        
        return stats


if __name__ == "__main__":
    print("=" * 60)
    print("测试事件溯源查询")
    print("=" * 60)
    
    sourcing = EventSourcing()
    
    # 查询交易事件
    print("\n1. 查询交易事件...")
    events = sourcing.query_events('TradeExecutedEvent', limit=5)
    print(f"   查询到 {len(events)} 个事件")
    for event in events[:3]:
        print(f"   - {event['payload'].get('symbol')}: "
              f"{event['payload'].get('side')} @ {event['payload'].get('price')}")
    
    # 按股票查询
    print("\n2. 按股票查询 (600519.SH)...")
    events = sourcing.query_by_symbol('600519.SH')
    print(f"   查询到 {len(events)} 个事件")
    
    # 聚合统计
    print("\n3. 交易统计...")
    stats = sourcing.aggregate_trades()
    print(f"   总交易数：{stats['total_trades']}")
    print(f"   买入：{stats['buy_count']} | 卖出：{stats['sell_count']}")
    print(f"   总手续费：{stats['total_commission']:.2f}")
    
    # 事件统计
    print("\n4. 事件统计...")
    event_stats = sourcing.get_stats()
    print(f"   总事件数：{event_stats['total_streams']}")
    for event_type, data in event_stats['streams'].items():
        print(f"   - {event_type}: {data['count']} 个")
    
    print("\n✅ 测试完成")
