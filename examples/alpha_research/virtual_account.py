#!/usr/bin/env python3
"""
虚拟账户管理模块

功能：
1. 管理虚拟账户资金和持仓
2. 记录交易流水
3. 同步到飞书多维表格
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 配置
ACCOUNT_FILE = Path(__file__).parent / "data" / "virtual_account.json"
TRADE_LOG_FILE = Path(__file__).parent / "data" / "trade_log.json"

# 飞书多维表格配置
FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
FEISHU_ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
FEISHU_TRADE_TABLE = "tbl4n14ZYANQtI26"  # 交易日志表


class VirtualAccount:
    """虚拟账户管理类"""
    
    def __init__(self):
        self.account_data = self._load_account()
        self.trade_log = self._load_trade_log()
    
    def _load_account(self):
        """加载账户数据"""
        if ACCOUNT_FILE.exists():
            with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 默认账户
            return {
                "account_id": "ACC001",
                "account_name": "王雅轩主账户",
                "initial_capital": 1000000,
                "current_cash": 1000000,
                "currency": "CNY",
                "status": "active",
                "created_at": "2026-03-24",
                "updated_at": datetime.now().isoformat()
            }
    
    def _load_trade_log(self):
        """加载交易流水"""
        if TRADE_LOG_FILE.exists():
            with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"trades": []}
    
    def get_available_cash(self):
        """获取可用资金"""
        return self.account_data.get("current_cash", 0)
    
    def get_positions(self):
        """获取持仓列表"""
        positions = {}
        for trade in self.trade_log.get("trades", []):
            if trade.get("status") == "filled" and trade.get("direction") == "买":
                symbol = trade.get("symbol")
                if symbol not in positions:
                    positions[symbol] = {
                        "symbol": symbol,
                        "name": trade.get("name", ""),
                        "quantity": 0,
                        "avg_price": 0,
                        "cost": 0
                    }
                positions[symbol]["quantity"] += trade.get("quantity", 0)
                positions[symbol]["cost"] += trade.get("quantity", 0) * trade.get("price", 0)
        
        # 计算平均价格
        for symbol in positions:
            if positions[symbol]["quantity"] > 0:
                positions[symbol]["avg_price"] = positions[symbol]["cost"] / positions[symbol]["quantity"]
        
        return list(positions.values())
    
    def get_position_value(self):
        """获取持仓总市值"""
        total = 0
        for pos in self.get_positions():
            total += pos["cost"]
        return total
    
    def get_total_asset(self):
        """获取总资产"""
        return self.get_available_cash() + self.get_position_value()
    
    def get_position_ratio(self):
        """获取仓位比例"""
        total = self.get_total_asset()
        if total == 0:
            return 0
        return self.get_position_value() / total * 100
    
    def buy(self, symbol, name, price, quantity, reason=""):
        """
        买入操作
        
        Args:
            symbol: 股票代码
            name: 股票名称
            price: 买入价格
            quantity: 买入数量
            reason: 买入理由
        
        Returns:
            dict: 交易记录
        """
        cost = price * quantity
        available = self.get_available_cash()
        
        if cost > available:
            raise ValueError(f"资金不足！需要 {cost:.2f} 元，可用 {available:.2f} 元")
        
        # 扣减资金
        self.account_data["current_cash"] -= cost
        
        # 生成交易 ID
        trade_id = f"{datetime.now().strftime('%Y%m%d')}-{len(self.trade_log['trades']) + 1:03d}"
        
        # 创建交易记录
        trade_record = {
            "trade_id": trade_id,
            "symbol": symbol,
            "name": name,
            "direction": "买",
            "price": price,
            "quantity": quantity,
            "cost": cost,
            "reason": reason,
            "status": "filled",
            "timestamp": datetime.now().isoformat(),
            "agent_id": "Q-Trade"
        }
        
        self.trade_log["trades"].append(trade_record)
        self.account_data["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self._save()
        
        print(f"✅ 买入成功：{symbol} {name} @ {price:.2f} x {quantity} = {cost:.2f} 元")
        return trade_record
    
    def sell(self, symbol, price, quantity, reason=""):
        """
        卖出操作
        
        Args:
            symbol: 股票代码
            price: 卖出价格
            quantity: 卖出数量
            reason: 卖出理由
        
        Returns:
            dict: 交易记录
        """
        # 检查持仓
        positions = self.get_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)
        
        if not position:
            raise ValueError(f"没有 {symbol} 的持仓！")
        
        if quantity > position["quantity"]:
            raise ValueError(f"持仓不足！持有 {position['quantity']}，要卖 {quantity}")
        
        # 计算收益
        proceeds = price * quantity
        cost_basis = position["avg_price"] * quantity
        profit = proceeds - cost_basis
        
        # 增加资金
        self.account_data["current_cash"] += proceeds
        
        # 生成交易 ID
        trade_id = f"{datetime.now().strftime('%Y%m%d')}-{len(self.trade_log['trades']) + 1:03d}"
        
        # 创建交易记录
        trade_record = {
            "trade_id": trade_id,
            "symbol": symbol,
            "name": position["name"],
            "direction": "卖",
            "price": price,
            "quantity": quantity,
            "proceeds": proceeds,
            "profit": profit,
            "reason": reason,
            "status": "filled",
            "timestamp": datetime.now().isoformat(),
            "agent_id": "Q-Trade"
        }
        
        self.trade_log["trades"].append(trade_record)
        self.account_data["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self._save()
        
        print(f"✅ 卖出成功：{symbol} {position['name']} @ {price:.2f} x {quantity} = {proceeds:.2f} 元 (盈亏：{profit:.2f} 元)")
        return trade_record
    
    def _save(self):
        """保存账户数据和交易流水"""
        # 确保目录存在
        ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存账户数据
        with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.account_data, f, ensure_ascii=False, indent=2)
        
        # 保存交易流水
        with open(TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.trade_log, f, ensure_ascii=False, indent=2)
    
    def sync_to_feishu(self, trade_records):
        """
        同步交易记录到飞书多维表格
        
        Args:
            trade_records: 交易记录列表
        """
        try:
            from openclaw_lark import feishu_bitable_app_table_record
            
            for trade in trade_records:
                fields = {
                    "Agent ID": trade.get("agent_id", "Q-Trade"),
                    "Trade ID": trade.get("trade_id"),
                    "Symbol": trade.get("symbol"),
                    "方向": trade.get("direction"),
                    "价格": trade.get("price", 0),
                    "数量": trade.get("quantity", 0),
                    "状态": trade.get("status", "filled"),
                    "时间戳": int(datetime.fromisoformat(trade.get("timestamp")).timestamp() * 1000)
                }
                
                # 添加备注
                if trade.get("reason"):
                    fields["备注"] = trade.get("reason")
                
                # 如果是买入，添加建仓时间
                if trade.get("direction") == "买":
                    fields["建仓时间"] = int(datetime.fromisoformat(trade.get("timestamp")).timestamp() * 1000)
                
                result = feishu_bitable_app_table_record(
                    action='create',
                    app_token=FEISHU_APP_TOKEN,
                    table_id=FEISHU_TRADE_TABLE,
                    fields=fields
                )
                print(f"📱 已同步到飞书：{trade.get('trade_id')}")
                
        except Exception as e:
            print(f"⚠️ 飞书同步失败：{e}")
    
    def print_summary(self):
        """打印账户摘要"""
        print("\n" + "=" * 60)
        print(" " * 20 + "虚拟账户摘要")
        print("=" * 60)
        print(f"账户：{self.account_data.get('account_name', 'N/A')}")
        print(f"初始资金：{self.account_data.get('initial_capital', 0):,.2f} 元")
        print(f"当前现金：{self.get_available_cash():,.2f} 元")
        print(f"持仓市值：{self.get_position_value():,.2f} 元")
        print(f"总资产：{self.get_total_asset():,.2f} 元")
        print(f"仓位：{self.get_position_ratio():.1f}%")
        
        # 计算总盈亏
        initial = self.account_data.get("initial_capital", 0)
        total = self.get_total_asset()
        profit = total - initial
        profit_pct = profit / initial * 100 if initial > 0 else 0
        print(f"总盈亏：{profit:+,.2f} 元 ({profit_pct:+.2f}%)")
        
        # 持仓明细
        positions = self.get_positions()
        if positions:
            print("\n持仓明细:")
            for pos in positions:
                print(f"  - {pos['symbol']} {pos['name']}: {pos['quantity']} 股 @ {pos['avg_price']:.2f} 元")
        
        print("=" * 60)


def main():
    """主函数 - 测试用"""
    account = VirtualAccount()
    account.print_summary()


if __name__ == "__main__":
    main()
