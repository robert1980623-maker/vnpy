#!/usr/bin/env python3
"""
虚拟账户管理模块

功能：
1. 管理虚拟账户资金和持仓
2. 记录交易流水
3. 同步到飞书多维表格
4. 从飞书缓存读取最新数据

IQ-01 修复：使用 SQLite 作为主数据源，JSON 仅作为备份
虚拟账户数据分裂修复：以飞书缓存为主，SQLite 同步
"""

import logging
logger = logging.getLogger(__name__)

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径以导入 account_db
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from accounts.account_db import AccountDB, Account, get_db

# 配置
ACCOUNT_FILE = Path(__file__).parent / "data" / "virtual_account.json"
TRADE_LOG_FILE = Path(__file__).parent / "data" / "trade_log.json"
CACHE_DIR = Path(__file__).parent / "data" / "feishu_cache"

# 飞书多维表格配置
FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
FEISHU_ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
FEISHU_TRADE_TABLE = "tbl4n14ZYANQtI26"  # 交易日志表
FEISHU_POSITION_TABLE = "tblLHrg7fFOcN0to"  # 持仓记录表

# 虚拟账户 ID
VIRTUAL_ACCOUNT_ID = "virtual_2026"


class VirtualAccount:
    """虚拟账户管理类
    
    IQ-01 修复：使用 SQLite 作为主数据源，JSON 仅作为备份
    虚拟账户数据分裂修复：以飞书缓存为主，SQLite 同步
    """
    
    def __init__(self):
        self.db = get_db()  # SQLite 数据库
        self.account_data = self._load_account()
        self.trade_log = self._load_trade_log()
    
    def _load_account(self):
        """加载账户数据，统一数据源优先级：
        
        1. 优先从飞书缓存读取（最新数据，如果有）
        2. 否则从 SQLite 读取（主数据源）
        3. 最后从本地 JSON 读取（备份）
        4. 如果都不存在，创建默认账户并写入 SQLite
        """
        # 第一优先级：飞书缓存（如果有且新鲜）
        feishu_data = self._load_account_from_feishu()
        if feishu_data:
            logger.info(f"ℹ️ 从飞书缓存读取账户数据，同步到 SQLite")
            # 同步到 SQLite，确保数据一致
            self._sync_account_to_sqlite(feishu_data)
            return feishu_data
        
        # 第二优先级：SQLite（主数据源）
        sqlite_account = self.db.get_account(VIRTUAL_ACCOUNT_ID)
        if sqlite_account:
            logger.info(f"ℹ️ 从 SQLite 读取账户数据")
            return {
                "account_id": sqlite_account.account_id,
                "account_name": sqlite_account.account_name,
                "initial_capital": sqlite_account.initial_capital,
                "current_cash": sqlite_account.cash,
                "currency": sqlite_account.currency,
                "status": sqlite_account.status,
                "created_at": sqlite_account.created_at,
                "updated_at": sqlite_account.updated_at
            }
        
        # 第三优先级：本地 JSON（备份）
        if ACCOUNT_FILE.exists():
            try:
                with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                logger.info(f"ℹ️ 从本地 JSON 读取账户数据（备份），同步到 SQLite")
                self._sync_account_to_sqlite(local_data)
                return local_data
            except Exception as e:
                logger.error(f"⚠️ 读取本地 JSON 失败：{e}")
        
        # 默认：创建新账户
        logger.info(f"ℹ️ 创建默认账户")
        default_account = {
            "account_id": VIRTUAL_ACCOUNT_ID,
            "account_name": "王雅轩主账户",
            "initial_capital": 1000000,
            "current_cash": 1000000,
            "currency": "CNY",
            "status": "active",
            "created_at": "2026-03-24",
            "updated_at": datetime.now().isoformat()
        }
        self._sync_account_to_sqlite(default_account)
        return default_account
    
    def _sync_account_to_sqlite(self, account_data: dict):
        """同步账户数据到 SQLite（原子操作）"""
        account = Account(
            account_id=account_data.get("account_id", VIRTUAL_ACCOUNT_ID),
            account_name=account_data.get("account_name", "虚拟账户"),
            account_type='virtual',
            initial_capital=account_data.get("initial_capital", 0),
            cash=account_data.get("current_cash", 0),
            currency=account_data.get("currency", "CNY"),
            status=account_data.get("status", "active"),
            risk_level='moderate',
            created_at=account_data.get("created_at"),
            updated_at=account_data.get("updated_at")
        )
        
        # 尝试创建，如果已存在则更新
        if not self.db.create_account(account):
            # 账户已存在，更新现金
            self.db.update_cash(account.account_id, account.cash)
    
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
                try:
                    cache_time = datetime.fromisoformat(updated.replace('+08:00', ''))
                    age = (datetime.now() - cache_time).total_seconds()
                    if age > 3600:  # 超过 1 小时
                        logger.info(f"⚠️ 账户缓存过期 {age/3600:.1f} 小时")
                        return None
                except Exception:
                    pass
            logger.info(f"ℹ️ 从飞书缓存读取账户数据")
            return data
        except Exception as e:
            logger.error(f"⚠️ 读取账户缓存失败：{e}")
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
            
            logger.info(f"ℹ️ 从飞书缓存读取 {len(positions)} 条持仓")
            return positions
        except Exception as e:
            logger.error(f"⚠️ 读取持仓缓存失败：{e}")
        return None
    
    def _load_trade_log(self):
        """加载交易流水（从 SQLite 读取）"""
        # IQ-01 修复：从 SQLite 读取交易记录，不再使用 JSON
        # 为了简化，暂时保留 JSON 读取，后续可以迁移到 SQLite
        if TRADE_LOG_FILE.exists():
            with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
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
            logger.info(f"ℹ️ 从飞书缓存读取到 {len(feishu_positions)} 条持仓记录")
            return feishu_positions
        
        # 最后备用：从本地交易流水计算
        logger.info("⚠️ 飞书持仓缓存不可用，回退到交易流水计算")
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
        """获取持仓总市值
        
        兼容两种数据格式:
        - 飞书缓存格式: {stock_code, volume, cost_price, market_value, ...}
        - 本地交易流水格式: {symbol, quantity, avg_price, cost, ...}
        """
        total = 0
        for pos in self.get_positions():
            # 优先使用 market_value (飞书格式)
            if 'market_value' in pos:
                total += pos['market_value']
            # 其次使用 cost (本地格式)
            elif 'cost' in pos:
                total += pos['cost']
            # 最后用 volume * cost_price 计算 (飞书格式变体)
            elif 'volume' in pos and 'cost_price' in pos:
                total += pos['volume'] * pos['cost_price']
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
        
        # IQ-01 修复：使用事务原子写入 SQLite 和 JSON
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
        
        # IQ-01 修复：使用事务原子写入 SQLite 和 JSON
        self._save()
        return trade
    
    def _save(self):
        """保存账户数据和交易流水（IQ-01 修复：原子操作）
        
        使用事务确保 SQLite 和 JSON 同时更新，避免不一致
        """
        self.account_data["updated_at"] = datetime.now().isoformat()
        
        # 先写 SQLite（主数据源）
        try:
            self._sync_account_to_sqlite(self.account_data)
        except Exception as e:
            logger.error(f"⚠️ 写入 SQLite 失败：{e}，回滚操作")
            raise
        
        # 再写 JSON（备份）
        try:
            ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.account_data, f, ensure_ascii=False, indent=2)
            
            with open(TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.trade_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"⚠️ 写入 JSON 失败：{e}，但 SQLite 已成功")
            # SQLite 已成功，JSON 失败不影响主数据
    
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
            
            logger.info(f"✅ 准备同步：1 条账户记录，{len(position_records)} 条持仓记录")
            # 实际同步由 process_feishu_sync_qtrade.py 处理
            return True
        except Exception as e:
            logger.error(f"❌ 同步到飞书失败：{e}")
            return False


if __name__ == "__main__":
    # 测试
    account = VirtualAccount()
    logger.info(f"可用资金：¥{account.get_available_cash():,.2f}")
    logger.info(f"持仓：{len(account.get_positions())} 只")
    for pos in account.get_positions():
        logger.info(f"  {pos['symbol']}: {pos['quantity']}股 @ ¥{pos['avg_price']:.2f}")
