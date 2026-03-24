#!/usr/bin/env python3
"""
交易事件监听器

功能:
- 监听 Redis Streams 事件
- 调用注册的处理器
- 事件溯源和日志

用法:
    listener = EventListener()
    listener.register_handler('TradeExecutedEvent', on_trade)
    listener.start()
"""

import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis 模块不可用")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventListener:
    """事件监听器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        if not REDIS_AVAILABLE:
            raise Exception("Redis 模块不可用")
        
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.redis.ping()
        
        # 事件处理器注册表
        self.handlers: Dict[str, List[Callable]] = {}
        
        # 运行状态
        self.running = False
        
        # 事件统计
        self.stats = {
            'total_received': 0,
            'total_processed': 0,
            'errors': 0
        }
        
        logger.info("✅ 事件监听器初始化完成")
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"📝 已注册处理器：{event_type} -> {handler.__name__}")
    
    def process_event(self, event_data: dict):
        """
        处理单个事件
        
        Args:
            event_data: 事件数据
        """
        event_type = event_data.get('event_type')
        event_id = event_data.get('event_id')
        
        logger.info(f"🔄 处理事件：{event_type} (ID: {event_id})")
        
        # 查找注册的处理器
        handlers = self.handlers.get(event_type, [])
        
        if not handlers:
            logger.warning(f"⚠️ 未找到 {event_type} 的处理器")
            return
        
        # 调用所有处理器
        for handler in handlers:
            try:
                handler(event_data)
                logger.info(f"✅ 处理器执行成功：{handler.__name__}")
            except Exception as e:
                logger.error(f"❌ 处理器执行失败 {handler.__name__}: {e}")
                self.stats['errors'] += 1
        
        self.stats['total_processed'] += 1
    
    def start_listening(self, event_types: List[str] = None, block_ms: int = 1000):
        """
        开始监听事件
        
        Args:
            event_types: 监听的事件类型列表，None 表示监听所有
            block_ms: 阻塞等待时间（毫秒）
        """
        if not event_types:
            event_types = list(self.handlers.keys())
        
        logger.info(f"👂 开始监听事件：{event_types}")
        self.running = True
        
        while self.running:
            try:
                # 构建 Stream 键列表
                stream_keys = {f"events:{et}": "0" for et in event_types}
                
                # 读取事件
                events = self.redis.xread(stream_keys, count=10, block=block_ms)
                
                if events:
                    for stream_name, messages in events:
                        event_type = stream_name.replace("events:", "")
                        
                        for msg_id, msg_data in messages:
                            # 解析事件数据
                            event = {
                                'message_id': msg_id,
                                'event_id': msg_data.get('event_id'),
                                'event_type': msg_data.get('event_type'),
                                'timestamp': msg_data.get('timestamp'),
                                'source': msg_data.get('source'),
                                'severity': msg_data.get('severity'),
                                'payload': json.loads(msg_data.get('payload', '{}'))
                            }
                            
                            self.stats['total_received'] += 1
                            self.process_event(event)
                
            except KeyboardInterrupt:
                logger.info("⚠️ 用户中断")
                self.running = False
            except Exception as e:
                logger.error(f"❌ 监听错误：{e}")
                self.stats['errors'] += 1
                time.sleep(1)
        
        logger.info("🛑 事件监听已停止")
    
    def stop(self):
        """停止监听"""
        self.running = False
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()


# 默认事件处理器示例
def on_trade_executed(event):
    """交易执行处理器"""
    payload = event.get('payload', {})
    logger.info(f"  📊 交易执行：{payload.get('symbol')} {payload.get('side')} "
                f"@ {payload.get('price')} x {payload.get('volume')}")


def on_order_placed(event):
    """订单提交处理器"""
    payload = event.get('payload', {})
    logger.info(f"  📝 订单提交：{payload.get('symbol')} {payload.get('side')} "
                f"@ {payload.get('price')} x {payload.get('volume')}")


def on_position_changed(event):
    """持仓变动处理器"""
    payload = event.get('payload', {})
    logger.info(f"  💼 持仓变动：{payload.get('symbol')} "
                f"变动 {payload.get('change_volume')} -> {payload.get('new_volume')}")


if __name__ == "__main__":
    print("=" * 60)
    print("测试事件监听器")
    print("=" * 60)
    
    listener = EventListener()
    
    # 注册处理器
    listener.register_handler('TradeExecutedEvent', on_trade_executed)
    listener.register_handler('OrderPlacedEvent', on_order_placed)
    listener.register_handler('PositionChangedEvent', on_position_changed)
    
    print("\n开始监听事件（Ctrl+C 停止）...")
    print("监听事件类型：TradeExecutedEvent, OrderPlacedEvent, PositionChangedEvent")
    
    try:
        listener.start_listening(block_ms=5000)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n统计信息：{listener.get_stats()}")
        listener.stop()
