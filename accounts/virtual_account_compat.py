"""
VirtualAccount 向后兼容层

@deprecated 请直接使用 AccountService。
    本模块仅保留供旧调用方过渡，内部将所有操作转发到 AccountService。
    新代码请改用：
        from accounts.account_service import AccountService
        account = AccountService("virtual_2026")
"""

import warnings
import logging
from typing import List, Dict, Optional

from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account
from accounts.event_bus import EventBus

logger = logging.getLogger(__name__)


class _CompatPosition:
    """兼容旧 VirtualAccount 的 Position 对象

    旧代码使用 pos.avg_price / pos.volume / pos.cost 等字段，
    AccountService 的 Position 使用 avg_cost / quantity / cost_basis。
    本类做字段名映射，让旧代码无需改动。
    """

    def __init__(self, pos):
        self.symbol = pos.symbol
        self.name = pos.name
        self.quantity = pos.quantity
        self.volume = pos.quantity              # 旧字段名
        self.avg_cost = pos.avg_cost
        self.avg_price = pos.avg_cost           # 旧字段名
        self.current_price = pos.current_price
        self.market_value = pos.market_value
        self.unrealized_pnl = pos.unrealized_pnl
        self.cost = pos.avg_cost * pos.quantity  # 旧字段名

    def __repr__(self):
        return f"Position({self.symbol}, qty={self.quantity}, avg={self.avg_cost:.2f})"


class _CompatSnapshot:
    """兼容旧 VirtualAccount 的 Snapshot 对象"""

    def __init__(self, snap, positions_list):
        self.date = snap.trade_date
        self.total_value = snap.total_assets
        self.daily_return = 0.0
        self.daily_return_rate = 0.0
        self.positions_count = snap.positions_count
        self.buy_count = 0
        self.sell_count = 0
        self.positions = positions_list


class _CompatTrade:
    """兼容旧 VirtualAccount 的 Trade 对象"""

    def __init__(self, trade):
        self.trade_id = trade.trade_id
        self.symbol = trade.symbol
        self.name = trade.name
        self.direction = "buy" if trade.direction.value == "BUY" else "sell"
        self.quantity = trade.quantity
        self.volume = trade.quantity
        self.price = trade.price
        self.amount = trade.amount
        self.fee = trade.commission
        self.datetime = trade.trade_date
        self.status = trade.status
        self.reason = trade.reason


class VirtualAccount:
    """向后兼容层 — 内部转发到 AccountService

    @deprecated 使用 AccountService 代替

    迁移路径：
        旧: from virtual_account import VirtualAccount
            account = VirtualAccount()
        新: from accounts.account_service import AccountService
            account = AccountService("virtual_2026")
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        account_id: str = "virtual_2026",
    ):
        warnings.warn(
            "VirtualAccount is deprecated, use AccountService instead. "
            "See design/account-system/PHASE-3-ARCHITECTURE.md",
            DeprecationWarning,
            stacklevel=2,
        )
        self.account_id = account_id
        self.initial_capital = initial_capital

        # 确保 SQLite 中存在该账户
        self.db = AccountDB()
        existing = self.db.get_account(account_id)
        if not existing:
            acct = Account(
                account_id=account_id,
                account_name="虚拟账户",
                account_type="virtual",
                initial_capital=initial_capital,
                cash=initial_capital,
                currency="CNY",
                status="active",
                risk_level="moderate",
            )
            if not self.db.create_account(acct):
                # 并发创建，忽略
                pass
            logger.info(f"创建账户 {account_id} (初始资金: {initial_capital:,.0f})")

        self._service = AccountService(account_id)

        # 兼容旧属性
        self._balance_cache = None
        self._positions_cache = None

    def _refresh_cache(self):
        """刷新缓存"""
        self._balance_cache = self._service.get_balance()
        self._positions_cache = [
            _CompatPosition(p) for p in self._service.get_positions()
        ]

    # ── 旧属性兼容 ──────────────────────────────────────────

    @property
    def cash(self) -> float:
        """当前现金（每次读取都从 DB 获取最新值）"""
        return self._service.get_balance().cash

    @property
    def positions(self) -> Dict[str, _CompatPosition]:
        """持仓字典 {symbol: Position}"""
        self._refresh_cache()
        return {p.symbol: p for p in self._positions_cache}

    @property
    def trades(self) -> list:
        """交易记录列表"""
        raw = self._service.get_trade_history(limit=1000)
        return [_CompatTrade(t) for t in raw]

    @property
    def account_data(self) -> dict:
        """兼容 account_data 字典"""
        balance = self._service.get_balance()
        return {
            "account_id": self.account_id,
            "account_name": "虚拟账户",
            "initial_capital": self.initial_capital,
            "current_cash": balance.cash,
            "currency": "CNY",
            "status": "active",
        }

    @property
    def trade_log(self) -> dict:
        """兼容 trade_log 字典"""
        raw = self._service.get_trade_history(limit=1000)
        trades = []
        for t in raw:
            trades.append({
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "name": t.name,
                "direction": "买" if t.direction.value == "BUY" else "卖",
                "price": t.price,
                "quantity": t.quantity,
                "amount": t.amount,
                "reason": t.reason,
                "status": "filled",
                "timestamp": t.created_at,
                "agent_id": t.agent_id,
            })
        return {"trades": trades}

    @property
    def daily_snapshots(self) -> list:
        """兼容 daily_snapshots 列表"""
        return []  # 快照需要单独查询

    # ── 旧方法兼容 ──────────────────────────────────────────

    def get_available_cash(self) -> float:
        """获取可用资金"""
        return self._service.get_balance().cash

    def get_positions(self) -> list:
        """获取持仓列表（返回列表格式，兼容旧调用方）"""
        positions = self._service.get_positions()
        result = []
        for p in positions:
            result.append({
                "symbol": p.symbol,
                "name": p.name,
                "quantity": p.quantity,
                "volume": p.quantity,
                "avg_price": p.avg_cost,
                "avg_cost": p.avg_cost,
                "current_price": p.current_price,
                "market_value": p.market_value,
                "cost": p.avg_cost * p.quantity,
                "unrealized_pnl": p.unrealized_pnl,
            })
        return result

    def get_position_value(self) -> float:
        """获取持仓总市值"""
        return self._service.get_balance().market_value

    def get_total_asset(self) -> float:
        """获取总资产"""
        return self._service.get_balance().total_assets

    def get_total_value(self) -> float:
        """获取总价值（同 get_total_asset）"""
        return self._service.get_balance().total_assets

    def get_position_ratio(self) -> float:
        """获取仓位比例"""
        balance = self._service.get_balance()
        if balance.total_assets == 0:
            return 0.0
        return balance.market_value / balance.total_assets * 100

    def get_performance(self) -> dict:
        """获取绩效统计"""
        balance = self._service.get_balance()
        total_return = balance.total_assets - self.initial_capital
        total_return_rate = (
            total_return / self.initial_capital * 100
            if self.initial_capital > 0
            else 0
        )
        return {
            "initial_capital": self.initial_capital,
            "current_value": balance.total_assets,
            "total_return": total_return,
            "total_return_rate": total_return_rate,
            "trading_days": 0,
            "total_trades": len(self._service.get_trade_history(limit=10000)),
            "max_drawdown": 0.0,
            "avg_daily_return": 0.0,
            "max_daily_return": 0.0,
            "min_daily_return": 0.0,
        }

    def buy(
        self,
        symbol: str,
        name_or_price=None,
        price_or_volume=None,
        volume_or_date=None,
        date_or_reason=None,
        reason=None,
        *,
        price: float = None,
        volume: int = None,
        quantity: int = None,
        name: str = "",
        source_module: str = "",
        **kwargs,
    ):
        """买入 — 兼容多种旧签名

        旧签名 1: buy(symbol, price, volume, date, reason)
        旧签名 2: buy(symbol, name, price, volume, date, reason)
        新签名:   buy(symbol, name, price, quantity, source_module=...)
        """
        # 参数解析：支持多种旧调用方式
        if reason is not None:
            # 所有参数都已通过关键字传入
            actual_price = price
            actual_quantity = quantity or volume or 0
            actual_name = name or ""
        elif date_or_reason is not None and reason is None:
            # buy(symbol, name, price, volume, date, reason) 全位置参数
            actual_name = name_or_price or ""
            actual_price = price_or_volume
            actual_quantity = volume_or_date
        elif volume_or_date is not None:
            # buy(symbol, price, volume, date, reason)
            actual_price = name_or_price
            actual_quantity = price_or_volume
            actual_name = name or ""
        elif price_or_volume is not None:
            # buy(symbol, price, volume)
            actual_price = name_or_price
            actual_quantity = price_or_volume
            actual_name = name or ""
        else:
            actual_price = price or name_or_price
            actual_quantity = quantity or volume or price_or_volume or 0
            actual_name = name or ""

        if actual_price is None or actual_quantity is None:
            raise ValueError(
                f"buy() 参数无法解析: symbol={symbol}, "
                f"name_or_price={name_or_price}, price_or_volume={price_or_volume}"
            )

        result = self._service.buy(
            symbol=symbol,
            name=actual_name or "",
            price=float(actual_price),
            quantity=int(actual_quantity),
            reason=reason or kwargs.get("reason", ""),
            source_module=source_module or kwargs.get("source_module", ""),
        )

        if not result.success:
            logger.warning(f"买入失败: {result.message}")
            return None

        # 返回兼容对象
        return _CompatBuyResult(result, symbol, actual_name or "", actual_price, actual_quantity)

    def sell(
        self,
        symbol: str,
        price_or_price=None,
        volume_or_quantity=None,
        date=None,
        reason: str = "",
        *,
        price: float = None,
        volume: int = None,
        quantity: int = None,
        source_module: str = "",
        **kwargs,
    ):
        """卖出 — 兼容多种旧签名

        旧签名: sell(symbol, price, volume, date, reason)
        新签名: sell(symbol, price, quantity, source_module=...)
        """
        if price is not None:
            actual_price = price
            actual_quantity = quantity or volume or 0
        elif price_or_price is not None:
            actual_price = price_or_price
            actual_quantity = volume_or_quantity or volume or quantity or 0
        else:
            raise ValueError(f"sell() 参数无法解析: symbol={symbol}")

        result = self._service.sell(
            symbol=symbol,
            price=float(actual_price),
            quantity=int(actual_quantity),
            reason=reason or kwargs.get("reason", ""),
            source_module=source_module or kwargs.get("source_module", ""),
        )

        if not result.success:
            logger.warning(f"卖出失败: {result.message}")
            return None

        return _CompatSellResult(result, symbol, actual_price, actual_quantity)

    def update_positions(self, prices: dict = None) -> dict:
        """更新持仓价格（兼容旧接口，实际不操作，因为 AccountService 自动维护）"""
        return {}

    def create_snapshot(
        self,
        date: str = None,
        buy_count: int = 0,
        sell_count: int = 0,
    ) -> _CompatSnapshot:
        """创建每日快照"""
        from datetime import datetime
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        snap = self._service.snapshot(trade_date=date)
        positions = self.get_positions()
        return _CompatSnapshot(snap, positions)

    def _save_account(self):
        """保存账户（兼容旧接口，AccountService 自动持久化，无需手动保存）"""
        pass

    def sync_to_feishu(self, trade_records=None):
        """同步到飞书（兼容旧接口）"""
        # TODO: 集成 FeishuSyncService
        logger.info("sync_to_feishu() 已弃用，请使用 FeishuSyncService")
        return True


class _CompatBuyResult:
    """兼容买入结果"""

    def __init__(self, result, symbol, name, price, quantity):
        self.success = result.success
        self.trade_id = result.trade_id
        self.message = result.message
        self.symbol = symbol
        self.name = name
        self.price = price
        self.quantity = quantity
        self.amount = price * quantity
        self.cost = price * quantity


class _CompatSellResult:
    """兼容卖出结果"""

    def __init__(self, result, symbol, price, quantity):
        self.success = result.success
        self.trade_id = result.trade_id
        self.message = result.message
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.amount = price * quantity
        self.proceeds = price * quantity


# 兼容导出：旧代码可能 from virtual_account import Position
class Position(_CompatPosition):
    """兼容 Position 类 — 从 AccountService Position 包装"""
    pass
