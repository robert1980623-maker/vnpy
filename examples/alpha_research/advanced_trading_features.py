#!/usr/bin/env python3
"""
高级交易功能

功能：
- 止损单 (Stop-Loss)
- 止盈单 (Take-Profit)
- 条件单 (Conditional Order)
- 追踪止损 (Trailing Stop)
"""

import logging
logger = logging.getLogger(__name__)

import tushare as ts
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from paper_trading_system import PaperTradingAccount, Trade

# 初始化 Tushare
ts.set_token('612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5')
pro = ts.pro_api()


class OrderType(Enum):
    """订单类型"""
    STOP_LOSS = "止损单"
    TAKE_PROFIT = "止盈单"
    CONDITIONAL = "条件单"
    TRAILING_STOP = "追踪止损"


@dataclass
class Order:
    """订单"""
    order_id: str
    ts_code: str
    stock_name: str
    order_type: OrderType
    trigger_price: float  # 触发价格
    target_price: float   # 目标价格（卖出价）
    volume: int
    status: str  # active/triggered/cancelled
    created_at: str
    triggered_at: Optional[str] = None
    
    def check_trigger(self, current_price: float) -> bool:
        """检查是否触发"""
        if self.status != 'active':
            return False
        
        if self.order_type == OrderType.STOP_LOSS:
            # 止损：当前价 <= 触发价
            return current_price <= self.trigger_price
        elif self.order_type == OrderType.TAKE_PROFIT:
            # 止盈：当前价 >= 触发价
            return current_price >= self.trigger_price
        elif self.order_type == OrderType.TRAILING_STOP:
            # 追踪止损：从最高点回撤超过阈值
            return current_price <= self.trigger_price
        
        return False


class AdvancedTradingAccount(PaperTradingAccount):
    """高级交易账户"""
    
    def __init__(self, initial_cash: float = 1000000.0):
        super().__init__(initial_cash)
        self.orders: List[Order] = []
        self.order_counter = 0
        self.load_orders()
    
    def load_orders(self):
        """加载订单"""
        orders_file = Path('paper_trading_demo/active_orders.json')
        if orders_file.exists():
            with open(orders_file, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
            self.orders = []
            for o in orders_data:
                order_type = OrderType(o['order_type'])
                order = Order(
                    order_id=o['order_id'],
                    ts_code=o['ts_code'],
                    stock_name=o['stock_name'],
                    order_type=order_type,
                    trigger_price=o['trigger_price'],
                    target_price=o['target_price'],
                    volume=o['volume'],
                    status=o['status'],
                    created_at=o['created_at'],
                    triggered_at=o.get('triggered_at')
                )
                self.orders.append(order)
    
    def save_orders(self):
        """保存订单"""
        orders_file = Path('paper_trading_demo/active_orders.json')
        orders_file.parent.mkdir(exist_ok=True)
        
        orders_data = []
        for o in self.orders:
            if o.status == 'active':  # 只保存活跃订单
                orders_data.append({
                    'order_id': o.order_id,
                    'ts_code': o.ts_code,
                    'stock_name': o.stock_name,
                    'order_type': o.order_type.value,
                    'trigger_price': o.trigger_price,
                    'target_price': o.target_price,
                    'volume': o.volume,
                    'status': o.status,
                    'created_at': o.created_at,
                    'triggered_at': o.triggered_at
                })
        
        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump(orders_data, f, indent=2, ensure_ascii=False)
    
    def set_stop_loss(self, ts_code: str, stop_price: float, 
                      volume: Optional[int] = None) -> Optional[Order]:
        """设置止损单"""
        if ts_code not in self.positions:
            logger.info(f"❌ 不持有 {ts_code}")
            return None
        
        pos = self.positions[ts_code]
        current_price, _ = self.get_latest_price(ts_code)
        
        if current_price is None:
            return None
        
        if volume is None:
            volume = pos['volume']  # 默认全部持仓
        
        if volume > pos['volume']:
            logger.info(f"❌ 持仓不足：持有{pos['volume']}股，设置{volume}股止损")
            return None
        
        # 检查止损价是否合理
        if stop_price >= current_price:
            logger.error(f"⚠️  止损价¥{stop_price:.2f} >= 现价¥{current_price:.2f}，可能设置错误")
        
        self.order_counter += 1
        
        try:
            basic = pro.stock_basic(ts_code=ts_code, fields='ts_code,name')
            stock_name = basic.iloc[0]['name'] if not basic.empty else ts_code
        except:
            stock_name = ts_code
        
        order = Order(
            order_id=f"SL{self.order_counter:04d}",
            ts_code=ts_code,
            stock_name=stock_name,
            order_type=OrderType.STOP_LOSS,
            trigger_price=stop_price,
            target_price=stop_price,  # 止损单触发后按触发价卖出
            volume=volume,
            status='active',
            created_at=datetime.now().isoformat()
        )
        
        self.orders.append(order)
        self.save_orders()
        
        logger.info(f"✅ 止损单已设置：{stock_name} ({ts_code})")
        logger.info(f"   止损价：¥{stop_price:.2f}")
        logger.info(f"   数量：{volume}股")
        logger.info(f"   当前价：¥{current_price:.2f}")
        logger.info(f"   止损幅度：{(current_price - stop_price)/current_price*100:.2f}%")
        
        return order
    
    def set_take_profit(self, ts_code: str, target_price: float,
                        volume: Optional[int] = None) -> Optional[Order]:
        """设置止盈单"""
        if ts_code not in self.positions:
            logger.info(f"❌ 不持有 {ts_code}")
            return None
        
        pos = self.positions[ts_code]
        current_price, _ = self.get_latest_price(ts_code)
        
        if current_price is None:
            return None
        
        if volume is None:
            volume = pos['volume']
        
        if volume > pos['volume']:
            logger.info(f"❌ 持仓不足")
            return None
        
        if target_price <= current_price:
            logger.error(f"⚠️  止盈价¥{target_price:.2f} <= 现价¥{current_price:.2f}，可能设置错误")
        
        self.order_counter += 1
        
        try:
            basic = pro.stock_basic(ts_code=ts_code, fields='ts_code,name')
            stock_name = basic.iloc[0]['name'] if not basic.empty else ts_code
        except:
            stock_name = ts_code
        
        order = Order(
            order_id=f"TP{self.order_counter:04d}",
            ts_code=ts_code,
            stock_name=stock_name,
            order_type=OrderType.TAKE_PROFIT,
            trigger_price=target_price,
            target_price=target_price,
            volume=volume,
            status='active',
            created_at=datetime.now().isoformat()
        )
        
        self.orders.append(order)
        self.save_orders()
        
        logger.info(f"✅ 止盈单已设置：{stock_name} ({ts_code})")
        logger.info(f"   止盈价：¥{target_price:.2f}")
        logger.info(f"   数量：{volume}股")
        logger.info(f"   当前价：¥{current_price:.2f}")
        logger.info(f"   预期收益：{(target_price - current_price)/current_price*100:.2f}%")
        
        return order
    
    def set_trailing_stop(self, ts_code: str, trail_percent: float = 5.0,
                          volume: Optional[int] = None) -> Optional[Order]:
        """设置追踪止损单
        
        Args:
            ts_code: 股票代码
            trail_percent: 从最高点回撤百分比
            volume: 卖出数量
        """
        if ts_code not in self.positions:
            logger.info(f"❌ 不持有 {ts_code}")
            return None
        
        pos = self.positions[ts_code]
        current_price, _ = self.get_latest_price(ts_code)
        
        if current_price is None:
            return None
        
        if volume is None:
            volume = pos['volume']
        
        # 追踪止损触发价 = 当前价 * (1 - 回撤百分比)
        trigger_price = current_price * (1 - trail_percent / 100)
        
        self.order_counter += 1
        
        try:
            basic = pro.stock_basic(ts_code=ts_code, fields='ts_code,name')
            stock_name = basic.iloc[0]['name'] if not basic.empty else ts_code
        except:
            stock_name = ts_code
        
        order = Order(
            order_id=f"TS{self.order_counter:04d}",
            ts_code=ts_code,
            stock_name=stock_name,
            order_type=OrderType.TRAILING_STOP,
            trigger_price=trigger_price,
            target_price=trigger_price,
            volume=volume,
            status='active',
            created_at=datetime.now().isoformat()
        )
        
        self.orders.append(order)
        self.save_orders()
        
        logger.info(f"✅ 追踪止损单已设置：{stock_name} ({ts_code})")
        logger.info(f"   回撤阈值：{trail_percent}%")
        logger.info(f"   触发价：¥{trigger_price:.2f}")
        logger.info(f"   数量：{volume}股")
        logger.info(f"   当前价：¥{current_price:.2f}")
        
        return order
    
    def check_orders(self) -> List[Order]:
        """检查并执行触发的订单"""
        triggered_orders = []
        
        logger.info("【检查订单触发】")
        logger.info("-" * 80)
        
        for order in self.orders:
            if order.status != 'active':
                continue
            
            current_price, _ = self.get_latest_price(order.ts_code)
            if current_price is None:
                continue
            
            if order.check_trigger(current_price):
                # 订单触发，执行卖出
                logger.info(f"  🚨 订单触发：{order.stock_name} {order.order_type.value}")
                logger.info(f"     触发价：¥{current_price:.2f}")
                logger.info(f"     数量：{order.volume}股")
                
                # 执行卖出
                trade = self.sell(order.ts_code, order.volume, price=current_price)
                
                if trade:
                    order.status = 'triggered'
                    order.triggered_at = datetime.now().isoformat()
                    triggered_orders.append(order)
                    logger.info(f"     ✅ 已执行卖出")
                else:
                    logger.error(f"     ❌ 执行失败")
        
        if triggered_orders:
            self.save_orders()
            logger.info()
            logger.info(f"  共触发 {len(triggered_orders)} 个订单")
        else:
            logger.info("  无触发订单")
        
        logger.info()
        return triggered_orders
    
    def list_orders(self):
        """列出所有活跃订单"""
        logger.info("【活跃订单】")
        logger.info("-" * 80)
        
        active_orders = [o for o in self.orders if o.status == 'active']
        
        if not active_orders:
            logger.info("  无活跃订单")
            return
        
        for order in active_orders:
            current_price, _ = self.get_latest_price(order.ts_code)
            
            logger.info(f"\n  {order.order_id}: {order.stock_name} ({order.ts_code})")
            logger.info(f"    类型：{order.order_type.value}")
            logger.info(f"    触发价：¥{order.trigger_price:.2f}")
            logger.info(f"    数量：{order.volume}股")
            logger.info(f"    创建时间：{order.created_at[:10]}")
            
            if current_price:
                if order.order_type == OrderType.STOP_LOSS:
                    distance = (current_price - order.trigger_price) / current_price * 100
                    logger.info(f"    当前价：¥{current_price:.2f} (距止损 {distance:.2f}%)")
                elif order.order_type == OrderType.TAKE_PROFIT:
                    distance = (order.trigger_price - current_price) / current_price * 100
                    logger.info(f"    当前价：¥{current_price:.2f} (距止盈 {distance:.2f}%)")
        
        logger.info()
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id:
                if order.status != 'active':
                    logger.info(f"❌ 订单 {order_id} 已不是活跃状态")
                    return False
                
                order.status = 'cancelled'
                self.save_orders()
                logger.info(f"✅ 订单 {order_id} 已取消")
                return True
        
        logger.info(f"❌ 未找到订单 {order_id}")
        return False


def main():
    """演示高级交易功能"""
    logger.info("=" * 80)
    logger.info(" " * 25 + "📊 高级交易功能演示")
    logger.info("=" * 80)
    logger.info()
    
    # 创建账户
    account = AdvancedTradingAccount()
    
    # 打印持仓
    account.print_report()
    
    # 设置止损单
    logger.info("\n" + "=" * 80)
    logger.info("【设置止损单】")
    logger.info("=" * 80)
    
    # 平安银行 -3% 止损
    current_price, _ = account.get_latest_price('000001.SZ')
    if current_price:
        stop_price = current_price * 0.97  # -3%
        account.set_stop_loss('000001.SZ', stop_price)
    
    # 招商银行 -3% 止损
    current_price, _ = account.get_latest_price('600036.SH')
    if current_price:
        stop_price = current_price * 0.97
        account.set_stop_loss('600036.SH', stop_price)
    
    # 贵州茅台 -3% 止损
    current_price, _ = account.get_latest_price('600519.SH')
    if current_price:
        stop_price = current_price * 0.97
        account.set_stop_loss('600519.SH', stop_price)
    
    # 列出订单
    logger.info("\n" + "=" * 80)
    account.list_orders()
    
    # 检查触发
    logger.info("=" * 80)
    account.check_orders()
    
    logger.info("=" * 80)
    logger.info("✅ 高级交易功能演示完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
