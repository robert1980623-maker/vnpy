#!/usr/bin/env python3
"""
虚拟账户管理模块

功能：
1. 管理虚拟账户资金和持仓
2. 记录交易流水
3. 同步到飞书多维表格
4. 从飞书缓存读取最新数据
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 配置
ACCOUNT_FILE = Path(__file__).parent / "data" / "virtual_account.json"
TRADE_LOG_FILE = Path(__file__).parent / "data" / "trade_log.json"
CACHE_DIR = Path(__file__).parent / "data" / "feishu_cache"

# 飞书多维表格配置
FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
FEISHU_ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
FEISHU_TRADE_TABLE = "tbl4n14ZYANQtI26"  # 交易日志表
FEISHU_POSITION_TABLE = "tblLHrg7fFOcN0to"  # 持仓记录表


class VirtualAccount:
    """虚拟账户管理类"""
    
    def __init__(self):
        self.account_data = self._load_account()
        self.trade_log = self._load_trade_log()
    
    def _load_account(self):
        """加载账户数据，统一数据源：飞书缓存为主，本地 JSON 为备份
        
        修复：虚拟账户数据分裂问题
        1. 优先从飞书缓存读取（最新数据）
        2. 如果飞书缓存新鲜（< 1小时），同步到本地 JSON
        3. 如果飞书缓存过期或不存在，使用本地 JSON
        4. 如果本地 JSON 也不存在，创建默认账户
        """
        # 优先从飞书缓存读取
        feishu_data = self._load_account_from_feishu()
        if feishu_data:
            # 检查缓存是否新鲜
            updated = feishu_data.get("updated_at", "")
            if updated:
                try:
                    cache_time = datetime.fromisoformat(updated.replace('+08:00', ''))
                    age = (datetime.now() - cache_time).total_seconds()
                    if age <= 3600:  # 1 小时内，认为是新鲜数据
                        print(f"ℹ️ 飞书缓存新鲜 ({age/60:.0f} 分钟前)，同步到本地")
                        # 同步到本地 JSON，确保数据一致
                        self._save_account_to_local(feishu_data)
                        return feishu_data
                except Exception:
                    pass
            
            # 缓存过期或读取失败，尝试本地 JSON
            print(f"⚠️ 飞书缓存不可用，检查本地 JSON")
        
        # 备用：从本地文件读取
        if ACCOUNT_FILE.exists():
            try:
                with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                print(f"ℹ️ 从本地 JSON 读取账户数据")
                return local_data
            except Exception as e:
                print(f"⚠️ 读取本地 JSON 失败：{e}")
        
        # 默认账户
        print(f"ℹ️ 创建默认账户")
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
    
    def _save_account_to_local(self, account_data: dict):
        """保存账户数据到本地 JSON（同步飞书缓存）"""
        try:
            ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump(account_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 同步到本地 JSON 失败：{e}")
    
    def _load_account_from_feishu(self):
        """从飞书缓存文件读取账户数据"""
        cache_file = CACHE_DIR / "account.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 检查缓存是否新鲜（1 小时内）
            updated = data.get("updated_at", "")
            if updated:
                cache_time = datetime.fromisoformat(updated)
                age = (datetime.now() - cache_time).total_seconds()
                if age > 3600:  # 超过 1 小时
                    print(f"⚠️ 账户缓存过期 {age/3600:.1f} 小时")
                    return None
            print(f"ℹ️ 从飞书缓存读取账户数据")
            return data
        except Exception as e:
            print(f"⚠️ 读取账户缓存失败：{e}")
        return None
    
    def _load_positions_from_feishu(self):
        """从飞书缓存文件读取持仓数据"""
        cache_file = CACHE_DIR / "positions.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_records = data.get("records", [])
            
            # 字段名标准化映射
            positions = []
            for rec in raw_records:
                stock_code = rec.get("stock_code", "")
                # 添加交易所后缀
                if stock_code.startswith('6'):
                    symbol = f"{stock_code}.SH"
                else:
                    symbol = f"{stock_code}.SZ"
                
                positions.append({
                    "symbol": symbol,
                    "name": rec.get("stock_name", ""),
                    "quantity": rec.get("quantity", 0),
                    "avg_price": rec.get("avg_cost", 0),
                    "cost": rec.get("cost_basis", 0)
                })
            
            print(f"ℹ️ 从飞书缓存读取 {len(positions)} 条持仓")
            return positions
        except Exception as e:
            print(f"⚠️ 读取持仓缓存失败：{e}")
        return None
    
    def _save_positions_to_local(self, positions: list):
        """保存持仓数据到本地文件（同步飞书缓存）"""
        POSITIONS_FILE = Path(__file__).parent / "data" / "positions.json"
        try:
            POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "positions": positions,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 同步持仓到本地失败：{e}")
    
    def _load_positions_from_local(self) -> list:
        """从本地持仓文件读取"""
        POSITIONS_FILE = Path(__file__).parent / "data" / "positions.json"
        if not POSITIONS_FILE.exists():
            return None
        try:
            with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("positions", [])
        except Exception as e:
            print(f"⚠️ 读取本地持仓文件失败：{e}")
            return None
    
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
        """获取持仓列表，统一数据源：飞书缓存为主，本地交易流水为备份
        
        修复：虚拟账户数据分裂问题
        1. 优先从飞书缓存读取（最新数据）
        2. 如果飞书缓存新鲜，同步到本地持仓文件
        3. 如果飞书缓存不可用，使用本地交易流水计算
        """
        # 优先从飞书缓存读取
        feishu_positions = self._load_positions_from_feishu()
        if feishu_positions is not None and len(feishu_positions) > 0:
            print(f"ℹ️ 从飞书缓存读取到 {len(feishu_positions)} 条持仓记录")
            # 同步到本地持仓文件
            self._save_positions_to_local(feishu_positions)
            return feishu_positions
        
        # 备用：检查本地持仓文件
        local_positions = self._load_positions_from_local()
        if local_positions is not None and len(local_positions) > 0:
            print(f"ℹ️ 从本地持仓文件读取 {len(local_positions)} 条记录")
            return local_positions
        
        # 最后备用：从本地交易流水计算
        print("⚠️ 飞书持仓缓存和本地持仓文件都不可用，回退到交易流水计算")
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
        """买入操作"""
        cost = price * quantity
        if cost > self.get_available_cash():
            raise ValueError(f"资金不足：需要¥{cost:,.2f}，可用¥{self.get_available_cash():,.2f}")
        
        trade = {
            "trade_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
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
        
        self.trade_log["trades"].append(trade)
        self.account_data["current_cash"] -= cost
        self._save()
        return trade
    
    def sell(self, symbol, price, quantity, reason=""):
        """卖出操作"""
        # 检查持仓
        positions = self.get_positions()
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        if not pos or pos["quantity"] < quantity:
            raise ValueError(f"持仓不足：{symbol} 当前持仓{pos['quantity'] if pos else 0}股")
        
        proceeds = price * quantity
        trade = {
            "trade_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
            "symbol": symbol,
            "name": pos["name"],
            "direction": "卖",
            "price": price,
            "quantity": quantity,
            "proceeds": proceeds,
            "reason": reason,
            "status": "filled",
            "timestamp": datetime.now().isoformat(),
            "agent_id": "Q-Trade"
        }
        
        self.trade_log["trades"].append(trade)
        self.account_data["current_cash"] += proceeds
        self._save()
        return trade
    
    def _save(self):
        """保存账户数据和交易流水"""
        self.account_data["updated_at"] = datetime.now().isoformat()
        
        with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.account_data, f, ensure_ascii=False, indent=2)
        
        with open(TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.trade_log, f, ensure_ascii=False, indent=2)
    
    def sync_to_feishu(self, trade_records=None):
        """同步到飞书多维表格"""
        try:
            import sys
            sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')
            from openclaw_lark import feishu_bitable_app_table_record
            
            # 同步账户数据
            account_record = {
                "fields": {
                    "账户 ID": self.account_data.get("account_id"),
                    "账户名称": self.account_data.get("account_name"),
                    "初始资金": self.account_data.get("initial_capital"),
                    "现金余额": self.account_data.get("current_cash"),
                    "状态": self.account_data.get("status"),
                    "最后更新": self.account_data.get("updated_at")
                }
            }
            
            # 同步持仓数据
            positions = self.get_positions()
            position_records = []
            for pos in positions:
                position_records.append({
                    "fields": {
                        "股票代码": pos["symbol"],
                        "股票名称": pos["name"],
                        "持仓数量": pos["quantity"],
                        "平均成本": pos["avg_price"],
                        "持仓市值": pos["cost"],
                        "状态": "持仓中"
                    }
                })
            
            print(f"✅ 准备同步：1 条账户记录，{len(position_records)} 条持仓记录")
            # 实际同步由 process_feishu_sync_qtrade.py 处理
            return True
        except Exception as e:
            print(f"❌ 同步到飞书失败：{e}")
            return False


if __name__ == "__main__":
    # 测试
    account = VirtualAccount()
    print(f"可用资金：¥{account.get_available_cash():,.2f}")
    print(f"持仓：{len(account.get_positions())} 只")
    for pos in account.get_positions():
        print(f"  {pos['symbol']}: {pos['quantity']}股 @ ¥{pos['avg_price']:.2f}")
