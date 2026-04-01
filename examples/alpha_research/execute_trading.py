#!/usr/bin/env python3
"""
交易执行脚本 - 飞书多维表格版

功能：
1. 直接读写飞书多维表格作为虚拟账户数据源
2. 执行虚拟账户买入/卖出
3. 同步交易记录、账户资金、持仓到飞书多维表格
4. 生成交易执行报告

用法：
    python3 execute_trading.py [--date 2026-03-27] [--dry-run]
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

# 配置
REPORTS_DIR = Path(__file__).parent / "reports"
EXECUTION_LOG_DIR = Path(__file__).parent / "logs"

# 飞书多维表格
FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
FEISHU_ACCOUNT_TABLE = "tblMqYRdqBjhMnik"      # 虚拟账户表
FEISHU_TRADE_TABLE = "tbl4n14ZYANQtI26"        # 交易日志表
FEISHU_POSITION_TABLE = "tblLHrg7fFOcN0to"     # 持仓记录表

# 账户记录 ID（从虚拟账户表读取，主账户固定）
ACCOUNT_RECORD_ID = "recveSFVVfD6EJ"


# ─────────────────────────────────────────────
#  飞书多维表格 API 封装
# ─────────────────────────────────────────────

# 飞书应用凭证（从 openclaw.json trading account 获取）
FEISHU_APP_ID = "cli_a930169999f9dbc8"
FEISHU_APP_SECRET = "SFVUIUlYtTTb0o6xK1qiYbwwCxgBKdh2"


def _get_client():
    """获取飞书客户端"""
    return lark.Client.builder() \
        .app_id(FEISHU_APP_ID) \
        .app_secret(FEISHU_APP_SECRET) \
        .build()


def _extract_text_field(value) -> str:
    """从文本字段提取字符串"""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
        return str(value[0]) if value else ""
    return str(value) if value else ""


def _extract_number_field(value) -> float:
    """从数字字段提取数值"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except:
            return 0.0
    return 0.0


def _text_field(value: str) -> dict:
    """构造文本字段"""
    return [{"type": "text", "text": str(value)}]


def get_account_from_feishu() -> dict:
    """从飞书读取账户数据"""
    client = _get_client()
    resp = client.bitable.v1.app_table_record.list(
        lark.CreateNodeReq.builder()
        .app_token(FEISHU_APP_TOKEN)
        .table_id(FEISHU_ACCOUNT_TABLE)
        .page_size(10)
        .build()
    )

    # 直接用 HTTP client 更简单
    import lark_oapi as lark
    resp = lark.WSClient("", lark.Logger.NO_LEVEL, lark.Logger.NO_LEVEL)._sync("/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records".format(
        app_token=FEISHU_APP_TOKEN,
        table_id=FEISHU_ACCOUNT_TABLE
    ), {"method": "GET", "params": {}})

    # 使用简易 HTTP 调用
    try:
        import urllib.request
        import os

        # 从环境变量获取 tenant_access_token（简化版，直接用已知的 app_token）
        # 这里我们用同步的 request 包
        pass
    except:
        pass

    return None


class FeishuVirtualAccount:
    """
    虚拟账户（飞书多维表格版）
    数据直接读写飞书多维表格
    """

    def __init__(self):
        self.app_token = FEISHU_APP_TOKEN
        self.client = lark.Client.builder() \
            .app_id(FEISHU_APP_ID) \
            .app_secret(FEISHU_APP_SECRET) \
            .build()
        self.account_record_id = ACCOUNT_RECORD_ID

    # ── 读取 ─────────────────────────────────

    def _list_records(self, table_id: str, filter_data: dict = None) -> list:
        """读取数据表记录"""
        try:
            req = CreateAppTableRecordListReq.builder() \
                .page_size(500) \
                .build()
            # 用原生方法
            resp = self.client.bitable.v1.app_table_record.select(
                lark.CreateIDESelectReq.builder()
                .app_token(self.app_token)
                .table_id(table_id)
                .build()
            )
        except Exception as e:
            # 降级：用 base HTTP
            pass

        # 直接调用 list
        try:
            from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest
            req = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .page_size(500) \
                .build()
            resp = self.client.bitable.v1.app_table_record.list(req)
            if resp.code == 0:
                return resp.data.items if resp.data else []
        except Exception as e:
            print(f"   ⚠️ 读取表 {table_id} 失败: {e}")
        return []

    def get_account(self) -> dict:
        """读取账户信息"""
        try:
            from lark_oapi.api.bitable.v1 import GetAppTableRecordRequest
            req = GetAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_ACCOUNT_TABLE) \
                .record_id(self.account_record_id) \
                .build()
            resp = self.client.bitable.v1.app_table_record.get(req)
            if resp.code == 0 and resp.data and resp.data.record:
                f = resp.data.record.fields
                return {
                    "account_id": _extract_text_field(f.get("账户ID", "")),
                    "account_name": _extract_text_field(f.get("账户名称", "")),
                    "initial_capital": _extract_number_field(f.get("初始资金", 0)),
                    "current_cash": _extract_number_field(f.get("当前资金", 0)),
                    "position_value": _extract_number_field(f.get("持仓市值", 0)),
                    "total_asset": _extract_number_field(f.get("当前资金", 0)) + _extract_number_field(f.get("持仓市值", 0)),
                }
        except Exception as e:
            print(f"   ⚠️ 读取账户失败: {e}")
        return None

    def get_positions(self) -> list:
        """读取当前持仓列表"""
        positions = []
        try:
            from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest
            req = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_POSITION_TABLE) \
                .page_size(500) \
                .build()
            resp = self.client.bitable.v1.app_table_record.list(req)
            if resp.code == 0 and resp.data:
                for record in resp.data.items:
                    f = record.fields
                    symbol = _extract_text_field(f.get("股票代码", ""))
                    if symbol and f.get("状态") == "持仓中":
                        positions.append({
                            "record_id": record.record_id,
                            "symbol": symbol,
                            "name": _extract_text_field(f.get("股票名称", "")),
                            "quantity": int(_extract_number_field(f.get("持仓数量", 0))),
                            "avg_price": _extract_number_field(f.get("平均成本", 0)),
                            "cost": _extract_number_field(f.get("持仓成本", 0)),
                            "market_value": _extract_number_field(f.get("持仓市值", 0)),
                        })
        except Exception as e:
            print(f"   ⚠️ 读取持仓失败: {e}")
        return positions

    def get_trade_log(self) -> list:
        """读取交易日志"""
        trades = []
        try:
            from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest
            req = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_TRADE_TABLE) \
                .page_size(500) \
                .build()
            resp = self.client.bitable.v1.app_table_record.list(req)
            if resp.code == 0 and resp.data:
                for record in resp.data.items:
                    f = record.fields
                    trades.append({
                        "trade_id": _extract_text_field(f.get("Trade ID", "")),
                        "symbol": _extract_text_field(f.get("股票代码", "")),
                        "direction": f.get("方向", ""),
                        "price": _extract_number_field(f.get("价格", 0)),
                        "quantity": int(_extract_number_field(f.get("数量", 0))),
                    })
        except Exception as e:
            print(f"   ⚠️ 读取交易日志失败: {e}")
        return trades

    def get_available_cash(self) -> float:
        """获取可用资金"""
        acct = self.get_account()
        return acct.get("current_cash", 0) if acct else 0

    def get_position_value(self) -> float:
        """获取持仓总市值"""
        acct = self.get_account()
        return acct.get("position_value", 0) if acct else 0

    def get_total_asset(self) -> float:
        """获取总资产"""
        acct = self.get_account()
        return acct.get("total_asset", 0) if acct else 0

    def get_position_ratio(self) -> float:
        """获取仓位比例"""
        total = self.get_total_asset()
        if total == 0:
            return 0
        return self.get_position_value() / total * 100

    # ── 写入 ─────────────────────────────────

    def _update_account_fields(self, fields: dict):
        """更新账户表字段"""
        try:
            from lark_oapi.api.bitable.v1.model import AppTableRecord
            record = AppTableRecord.builder().fields(fields).build()
            req = UpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_ACCOUNT_TABLE) \
                .record_id(self.account_record_id) \
                .request_body(record) \
                .build()
            resp = self.client.bitable.v1.app_table_record.update(req)
            if resp.code != 0:
                print(f"   ⚠️ 更新账户失败: {resp.msg}")
                return False
            return True
        except Exception as e:
            print(f"   ⚠️ 更新账户异常: {e}")
            return False

    def _update_position_fields(self, record_id: str, fields: dict):
        """更新持仓表字段"""
        try:
            from lark_oapi.api.bitable.v1.model import AppTableRecord
            record = AppTableRecord.builder().fields(fields).build()
            req = UpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_POSITION_TABLE) \
                .record_id(record_id) \
                .request_body(record) \
                .build()
            resp = self.client.bitable.v1.app_table_record.update(req)
            if resp.code != 0:
                print(f"   ⚠️ 更新持仓失败: {resp.msg}")
                return False
            return True
        except Exception as e:
            print(f"   ⚠️ 更新持仓异常: {e}")
            return False

    def _create_trade_record(self, fields: dict) -> str:
        """创建交易记录"""
        try:
            from lark_oapi.api.bitable.v1.model import AppTableRecord
            # 转换字段格式：文本字段用 _text_field 包裹
            converted = {}
            for k, v in fields.items():
                if k in ("多行文本", "股票代码", "股票名称", "Trade ID", "Agent ID", "备注"):
                    if isinstance(v, str):
                        v = _text_field(v)
                converted[k] = v
            record = AppTableRecord.builder().fields(converted).build()
            req = CreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_TRADE_TABLE) \
                .request_body(record) \
                .build()
            resp = self.client.bitable.v1.app_table_record.create(req)
            if resp.code == 0:
                return resp.data.record.record_id
            else:
                print(f"   ⚠️ 创建交易记录失败: {resp.msg}")
                return None
        except Exception as e:
            print(f"   ⚠️ 创建交易记录异常: {e}")
            return None

    def _create_position_record(self, fields: dict) -> str:
        """创建持仓记录"""
        try:
            from lark_oapi.api.bitable.v1.model import AppTableRecord
            # 转换字段格式：文本字段用 _text_field 包裹
            converted = {}
            for k, v in fields.items():
                if k in ("股票代码", "股票名称", "Agent ID"):
                    if isinstance(v, str):
                        v = _text_field(v)
                converted[k] = v
            record = AppTableRecord.builder().fields(converted).build()
            req = CreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(FEISHU_POSITION_TABLE) \
                .request_body(record) \
                .build()
            resp = self.client.bitable.v1.app_table_record.create(req)
            if resp.code == 0:
                return resp.data.record.record_id
            else:
                print(f"   ⚠️ 创建持仓记录失败: {resp.msg}")
                return None
        except Exception as e:
            print(f"   ⚠️ 创建持仓记录异常: {e}")
            return None

    # ── 交易操作 ─────────────────────────────────

    def buy(self, symbol: str, name: str, price: float, quantity: int, reason: str = "") -> dict:
        """买入"""
        cost = price * quantity
        available = self.get_available_cash()

        if cost > available + 0.01:
            raise ValueError(f"资金不足！需要 {cost:.2f} 元，可用 {available:.2f} 元")

        timestamp = int(datetime.now().timestamp() * 1000)
        trade_id = f"{datetime.now().strftime('%Y%m%d')}-{symbol}"

        # 1. 更新账户资金
        acct = self.get_account()
        new_cash = acct["current_cash"] - cost
        new_pos_value = acct["position_value"] + cost
        self._update_account_fields({
            "当前资金": new_cash,
            "持仓市值": new_pos_value,
            "更新时间": timestamp,
        })

        # 2. 更新或创建持仓
        positions = self.get_positions()
        existing = next((p for p in positions if p["symbol"] == symbol), None)

        if existing:
            # 加仓：重新计算平均成本
            old_qty = existing["quantity"]
            old_cost = existing["cost"]
            new_qty = old_qty + quantity
            new_avg = (old_cost + cost) / new_qty
            new_total_cost = new_avg * new_qty
            self._update_position_fields(existing["record_id"], {
                "持仓数量": new_qty,
                "平均成本": round(new_avg, 3),
                "持仓成本": round(new_total_cost, 2),
                "持仓市值": round(new_total_cost, 2),
                "当前价": price,
                "更新时间": timestamp,
            })
        else:
            # 新建持仓
            self._create_position_record({
                "股票代码": _text_field(symbol),
                "股票名称": _text_field(name),
                "持仓数量": quantity,
                "持仓成本": round(cost, 2),
                "平均成本": round(price, 3),
                "当前价": round(price, 2),
                "持仓市值": round(cost, 2),
                "浮盈": 0,
                "收益率": 0,
                "建仓日期": timestamp,
                "更新时间": timestamp,
                "状态": "持仓中",
                "Agent ID": _text_field("Q-Trade"),
            })

        # 3. 记录交易
        self._create_trade_record({
            "多行文本": _text_field(f"{symbol} - 买"),
            "股票代码": _text_field(symbol),
            "股票名称": _text_field(name),
            "Trade ID": _text_field(trade_id),
            "方向": "买",
            "价格": price,
            "数量": quantity,
            "状态": "filled",
            "建仓时间": timestamp,
            "Agent ID": _text_field("Q-Trade"),
            "备注": _text_field(reason),
        })

        print(f"   ✅ 买入成功：{symbol} {name} @ {price:.2f} x {quantity} = {cost:,.2f} 元")
        return {
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

    def sell(self, symbol: str, price: float, quantity: int, reason: str = "") -> dict:
        """卖出"""
        positions = self.get_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)

        if not position:
            raise ValueError(f"没有 {symbol} 的持仓！")

        if quantity > position["quantity"]:
            raise ValueError(f"持仓不足！持有 {position['quantity']}，要卖 {quantity}")

        proceeds = price * quantity
        cost_basis = position["avg_price"] * quantity
        profit = proceeds - cost_basis
        timestamp = int(datetime.now().timestamp() * 1000)
        trade_id = f"{datetime.now().strftime('%Y%m%d')}-{symbol}-sell"

        # 1. 更新账户资金
        acct = self.get_account()
        new_cash = acct["current_cash"] + proceeds
        remaining_cost = (position["quantity"] - quantity) / position["quantity"] * position["cost"] if position["quantity"] > quantity else 0
        new_pos_value = acct["position_value"] - position["cost"] + remaining_cost

        self._update_account_fields({
            "当前资金": new_cash,
            "持仓市值": max(0, new_pos_value),
            "更新时间": timestamp,
        })

        # 2. 更新或删除持仓
        if position["quantity"] == quantity:
            # 全部卖出，更新为已平仓
            self._update_position_fields(position["record_id"], {
                "状态": "已平仓",
                "更新时间": timestamp,
            })
        else:
            # 部分卖出
            new_qty = position["quantity"] - quantity
            new_avg = position["avg_price"]
            new_cost = new_avg * new_qty
            self._update_position_fields(position["record_id"], {
                "持仓数量": new_qty,
                "持仓成本": round(new_cost, 2),
                "持仓市值": round(new_cost, 2),
                "当前价": price,
                "浮盈": round(profit, 2),
                "收益率": round((price - position["avg_price"]) / position["avg_price"] * 100, 2),
                "更新时间": timestamp,
            })

        # 3. 记录交易
        self._create_trade_record({
            "多行文本": _text_field(f"{symbol} - 卖"),
            "股票代码": _text_field(symbol),
            "股票名称": _text_field(position["name"]),
            "Trade ID": _text_field(trade_id),
            "方向": "卖",
            "价格": price,
            "数量": quantity,
            "状态": "filled",
            "平仓时间": timestamp,
            "Agent ID": _text_field("Q-Trade"),
            "备注": _text_field(f"{reason} | 盈亏: {profit:.2f}"),
        })

        print(f"   ✅ 卖出成功：{symbol} {position['name']} @ {price:.2f} x {quantity} = {proceeds:,.2f} 元 (盈亏：{profit:.2f} 元)")
        return {
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

    # ── 展示 ─────────────────────────────────

    def print_summary(self):
        """打印账户摘要"""
        acct = self.get_account() or {}
        positions = self.get_positions()

        print("\n" + "=" * 60)
        print(" " * 20 + "虚拟账户摘要")
        print("=" * 60)
        print(f"账户：{acct.get('account_name', 'N/A')}")
        print(f"初始资金：{acct.get('initial_capital', 0):,.2f} 元")
        print(f"当前现金：{acct.get('current_cash', 0):,.2f} 元")
        print(f"持仓市值：{acct.get('position_value', 0):,.2f} 元")
        print(f"总资产：{acct.get('total_asset', 0):,.2f} 元")
        print(f"仓位：{self.get_position_ratio():.1f}%")

        initial = acct.get('initial_capital', 0)
        total = acct.get('total_asset', 0)
        profit = total - initial
        profit_pct = profit / initial * 100 if initial > 0 else 0
        print(f"总盈亏：{profit:+,.2f} 元 ({profit_pct:+.2f}%)")

        if positions:
            print("\n持仓明细:")
            for pos in positions:
                print(f"  - {pos['symbol']} {pos['name']}: {pos['quantity']} 股 @ {pos['avg_price']:.2f} 元")

        print("=" * 60)


# ─────────────────────────────────────────────
#  交易计划
# ─────────────────────────────────────────────

def load_trading_plan(date=None):
    """加载交易计划"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    plan_file = REPORTS_DIR / f"trading_plan_{date}.json"

    if not plan_file.exists():
        print(f"❌ 交易计划文件不存在：{plan_file}")
        return None

    with open(plan_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_current_price(symbol, date=None):
    """获取当前价格（从选股报告估算）"""
    selection_date = datetime.now().strftime("%Y-%m-%d") if date is None else date
    selection_file = REPORTS_DIR / f"stock_selection_{selection_date}.json"

    if selection_file.exists():
        with open(selection_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for stock in data.get("stocks", []):
                stock_symbol = str(stock.get("symbol", ""))
                target_symbol = str(symbol)

                if (stock_symbol == target_symbol or
                        stock_symbol.replace('.', '') == target_symbol.replace('.', '')):
                    pe = stock.get("pe", 20)
                    estimated_price = pe * 0.8
                    print(f"   参考价格：{estimated_price:.2f} 元 (PE={pe})")
                    return estimated_price

    print(f"   ⚠️ 使用默认价格：10.00 元")
    return 10.0


def calculate_buy_quantity(account: FeishuVirtualAccount, symbol: str, price: float, max_position_ratio=0.3):
    """计算买入数量"""
    available_cash = account.get_available_cash()
    total_asset = account.get_total_asset()

    max_amount_by_cash = available_cash * 0.95
    max_amount_by_position = total_asset * max_position_ratio

    buy_amount = min(max_amount_by_cash, max_amount_by_position)

    if buy_amount <= 0:
        return 0

    quantity = int(buy_amount / price / 100) * 100

    if quantity < 100:
        quantity = 100

    return quantity


# ─────────────────────────────────────────────
#  主执行
# ─────────────────────────────────────────────

def execute_trading(date=None, dry_run=False):
    """执行交易"""
    print("=" * 70)
    print(" " * 25 + "交易执行")
    print("=" * 70)
    print(f"日期：{date or datetime.now().strftime('%Y-%m-%d')}")
    print(f"时间：{datetime.now().strftime('%H:%M:%S')}")
    print(f"模式：{'模拟' if dry_run else '实盘（飞书多维表格）'}")
    print("=" * 70)

    # 加载交易计划
    plan = load_trading_plan(date)
    if plan is None:
        return {"success": False, "error": "交易计划加载失败"}

    print(f"\n📊 交易计划:")
    print(f"  买入：{len(plan.get('buy', []))} 只")
    print(f"  卖出：{len(plan.get('sell', []))} 只")

    # 初始化飞书虚拟账户
    account = FeishuVirtualAccount()
    account.print_summary()

    executed_trades = []
    failed_trades = []

    # 执行买入
    print("\n" + "=" * 70)
    print(" " * 25 + "执行买入")
    print("=" * 70)

    for stock in plan.get("buy", []):
        symbol = stock.get("symbol")
        name = stock.get("name", "")
        reason = stock.get("reason", "")
        score = stock.get("score", 0)

        print(f"\n【买入】{symbol} {name} (评分：{score}, 理由：{reason})")

        try:
            price = get_current_price(symbol)
            quantity = calculate_buy_quantity(account, symbol, price)

            if quantity <= 0:
                raise ValueError("计算买入数量失败")

            cost = price * quantity
            print(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{cost:,.2f} 元")

            if dry_run:
                print(f"   [模拟] 买入成功")
                trade_record = {
                    "trade_id": f"DRY_{datetime.now().strftime('%Y%m%d')}_{len(executed_trades)+1:03d}",
                    "symbol": symbol,
                    "name": name,
                    "direction": "买",
                    "price": price,
                    "quantity": quantity,
                    "cost": cost,
                    "reason": reason,
                    "status": "dry_run",
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": "Q-Trade"
                }
                executed_trades.append(trade_record)
            else:
                trade_record = account.buy(
                    symbol=symbol,
                    name=name,
                    price=price,
                    quantity=quantity,
                    reason=reason
                )
                executed_trades.append(trade_record)

        except Exception as e:
            print(f"   ❌ 买入失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })

    # 执行卖出
    print("\n" + "=" * 70)
    print(" " * 25 + "执行卖出")
    print("=" * 70)

    for stock in plan.get("sell", []):
        symbol = stock.get("symbol")
        name = stock.get("name", "")
        reason = stock.get("reason", "")

        print(f"\n【卖出】{symbol} {name} (理由：{reason})")

        try:
            price = get_current_price(symbol)
            positions = account.get_positions()
            position = next((p for p in positions if p["symbol"] == symbol), None)

            if not position:
                raise ValueError("没有持仓")

            quantity = position["quantity"]
            proceeds = price * quantity

            print(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{proceeds:,.2f} 元")

            if dry_run:
                print(f"   [模拟] 卖出成功")
            else:
                account.sell(symbol=symbol, price=price, quantity=quantity, reason=reason)

        except Exception as e:
            print(f"   ❌ 卖出失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })

    # 打印执行后摘要
    if not dry_run:
        account.print_summary()

    # 生成执行报告
    report = {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "summary": {
            "total_buy": len(plan.get("buy", [])),
            "total_sell": len(plan.get("sell", [])),
            "executed_buy": len([t for t in executed_trades if t.get("direction") == "买"]),
            "executed_sell": len([t for t in executed_trades if t.get("direction") == "卖"]),
            "failed": len(failed_trades)
        },
        "executed_trades": executed_trades,
        "failed_trades": failed_trades,
        "account_summary": {
            "cash": account.get_available_cash(),
            "position_value": account.get_position_value(),
            "total_asset": account.get_total_asset(),
            "position_ratio": account.get_position_ratio()
        } if not dry_run else None
    }

    # 保存执行报告
    EXECUTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_file = EXECUTION_LOG_DIR / f"execution_{date or datetime.now().strftime('%Y-%m-%d')}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 执行报告已保存：{report_file}")

    # 打印总结
    print("\n" + "=" * 70)
    print(" " * 25 + "执行总结")
    print("=" * 70)
    print(f"计划买入：{report['summary']['total_buy']} 只")
    print(f"实际买入：{report['summary']['executed_buy']} 只")
    print(f"失败：{report['summary']['failed']} 只")

    if executed_trades:
        print("\n执行成功的交易:")
        for trade in executed_trades:
            direction = "买入" if trade.get("direction") == "买" else "卖出"
            print(f"  ✅ {trade.get('symbol')} {direction} {trade.get('quantity')} 股 @ {trade.get('price'):.2f} 元")

    print("=" * 70)

    return report


def main():
    parser = argparse.ArgumentParser(description='交易执行脚本（飞书多维表格版）')
    parser.add_argument('--date', type=str, help='交易日期 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行')

    args = parser.parse_args()

    report = execute_trading(date=args.date, dry_run=args.dry_run)
    sys.exit(0 if report.get("summary", {}).get("failed", 0) == 0 else 1)


if __name__ == "__main__":
    main()
