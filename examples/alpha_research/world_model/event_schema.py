#!/usr/bin/env python3
"""
交易事件 Schema 定义

定义 vnpy 交易相关的事件类型和结构
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class EventType(Enum):
    """事件类型枚举"""
    TRADE_EXECUTED = "TradeExecutedEvent"      # 交易执行
    ORDER_PLACED = "OrderPlacedEvent"          # 订单提交
    ORDER_CANCELLED = "OrderCancelledEvent"    # 订单撤销
    POSITION_CHANGED = "PositionChangedEvent"  # 持仓变动
    PORTFOLIO_UPDATED = "PortfolioUpdatedEvent" # 组合更新


class EventSchema:
    """事件 Schema 基类"""
    
    @staticmethod
    def create_event_id(event_type: str) -> str:
        """生成事件 ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"event_{event_type}_{timestamp}"
    
    @staticmethod
    def validate(event_type: str, payload: Dict[str, Any]) -> bool:
        """验证事件数据"""
        required_fields = EVENT_SCHEMAS.get(event_type, {}).get('required', [])
        for field in required_fields:
            if field not in payload:
                return False
        return True


# 事件 Schema 定义
EVENT_SCHEMAS = {
    EventType.TRADE_EXECUTED.value: {
        'required': ['symbol', 'side', 'price', 'volume', 'account'],
        'optional': ['commission', 'tax', 'trade_time', 'order_id'],
        'description': '交易执行事件'
    },
    EventType.ORDER_PLACED.value: {
        'required': ['symbol', 'side', 'price', 'volume', 'account'],
        'optional': ['order_time', 'status'],
        'description': '订单提交事件'
    },
    EventType.ORDER_CANCELLED.value: {
        'required': ['order_id', 'account'],
        'optional': ['cancel_time', 'reason'],
        'description': '订单撤销事件'
    },
    EventType.POSITION_CHANGED.value: {
        'required': ['symbol', 'account', 'change_volume', 'new_volume'],
        'optional': ['avg_price', 'change_reason'],
        'description': '持仓变动事件'
    },
    EventType.PORTFOLIO_UPDATED.value: {
        'required': ['account', 'total_value', 'cash'],
        'optional': ['positions', 'pnl', 'update_time'],
        'description': '组合更新事件'
    }
}


def create_trade_event(symbol: str, side: str, price: float, 
                       volume: float, account: str, **kwargs) -> Dict[str, Any]:
    """
    创建交易执行事件
    
    Args:
        symbol: 股票代码
        side: 买卖方向 (buy/sell)
        price: 成交价格
        volume: 成交数量
        account: 账户 ID
        **kwargs: 可选字段 (commission, tax, trade_time, order_id)
    
    Returns:
        dict: 事件数据
    """
    payload = {
        'symbol': symbol,
        'side': side,
        'price': price,
        'volume': volume,
        'account': account,
        'trade_time': kwargs.get('trade_time', datetime.now().isoformat()),
        'order_id': kwargs.get('order_id'),
        'commission': kwargs.get('commission', 0.0),
        'tax': kwargs.get('tax', 0.0)
    }
    
    return {
        'event_id': EventSchema.create_event_id(EventType.TRADE_EXECUTED.value),
        'event_type': EventType.TRADE_EXECUTED.value,
        'timestamp': datetime.now().isoformat(),
        'source': 'vnpy_trading',
        'severity': 'medium',
        'payload': payload
    }


def create_order_event(symbol: str, side: str, price: float,
                       volume: float, account: str, **kwargs) -> Dict[str, Any]:
    """
    创建订单提交事件
    
    Args:
        symbol: 股票代码
        side: 买卖方向
        price: 委托价格
        volume: 委托数量
        account: 账户 ID
        **kwargs: 可选字段 (order_time, status)
    
    Returns:
        dict: 事件数据
    """
    payload = {
        'symbol': symbol,
        'side': side,
        'price': price,
        'volume': volume,
        'account': account,
        'order_time': kwargs.get('order_time', datetime.now().isoformat()),
        'status': kwargs.get('status', 'submitted')
    }
    
    return {
        'event_id': EventSchema.create_event_id(EventType.ORDER_PLACED.value),
        'event_type': EventType.ORDER_PLACED.value,
        'timestamp': datetime.now().isoformat(),
        'source': 'vnpy_trading',
        'severity': 'low',
        'payload': payload
    }


def create_position_event(symbol: str, account: str,
                          change_volume: float, new_volume: float, **kwargs) -> Dict[str, Any]:
    """
    创建持仓变动事件
    
    Args:
        symbol: 股票代码
        account: 账户 ID
        change_volume: 变动数量（正数买入，负数卖出）
        new_volume: 新的持仓数量
        **kwargs: 可选字段 (avg_price, change_reason)
    
    Returns:
        dict: 事件数据
    """
    payload = {
        'symbol': symbol,
        'account': account,
        'change_volume': change_volume,
        'new_volume': new_volume,
        'avg_price': kwargs.get('avg_price'),
        'change_reason': kwargs.get('change_reason', 'trade')
    }
    
    return {
        'event_id': EventSchema.create_event_id(EventType.POSITION_CHANGED.value),
        'event_type': EventType.POSITION_CHANGED.value,
        'timestamp': datetime.now().isoformat(),
        'source': 'vnpy_trading',
        'severity': 'medium',
        'payload': payload
    }


if __name__ == "__main__":
    # 测试
    print("测试交易事件 Schema")
    print("=" * 60)
    
    # 创建交易事件
    trade_event = create_trade_event(
        symbol='600519.SH',
        side='buy',
        price=1440.11,
        volume=200,
        account='virtual_2026',
        commission=5.0
    )
    print(f"交易事件：{trade_event['event_type']}")
    print(f"事件 ID: {trade_event['event_id']}")
    print(f"数据源：{trade_event['source']}")
    print(f"股票代码：{trade_event['payload']['symbol']}")
    print(f"买卖方向：{trade_event['payload']['side']}")
    print(f"成交价格：{trade_event['payload']['price']}")
    print(f"成交数量：{trade_event['payload']['volume']}")
    
    print("\n✅ Schema 测试完成")
