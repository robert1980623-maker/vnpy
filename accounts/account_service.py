"""
账户系统统一入口

Phase 2: AccountService
- SQLite 唯一数据源 (Single Source of Truth)
- 所有 buy/sell 操作在事务内完成 (Atomic)
- 每次交易发布事件，解耦通知 (Event-Driven)
- 所有操作记录审计日志 (Auditable)
"""
import json
import logging
import random
import time
from datetime import datetime
from typing import List, Optional

from accounts.account_db import AccountDB, get_connection
from accounts.event_bus import EventBus, EventType, AccountEvent, trade_event
from accounts.exceptions import (
    InsufficientCashError,
    InsufficientPositionError,
    AccountNotFoundError,
)
from accounts.models import Balance, Position, Trade, Snapshot, TradeResult, Direction

logger = logging.getLogger(__name__)


class AccountService:
    """账户系统统一入口

    设计原则:
    1. SQLite 唯一数据源 (Single Source of Truth)
    2. 所有 buy/sell 操作在事务内完成 (Atomic)
    3. 每次交易发布事件，解耦通知 (Event-Driven)
    4. 所有操作记录审计日志 (Auditable)
    """

    def __init__(self, account_id: str, event_bus: EventBus = None):
        self.db = AccountDB()
        self.account_id = account_id
        self.event_bus = event_bus or EventBus()

    # ── 交易操作 (事务保证) ─────────────────────────────

    def buy(
        self,
        symbol: str,
        name: str,
        price: float,
        quantity: int,
        reason: str = "",
        agent_id: str = "system",
        source_module: str = "",
    ) -> TradeResult:
        """买入 — cash 扣减 + position 更新 + trade 记录 原子完成

        事务流程:
        1. BEGIN TRANSACTION
        2. SELECT cash FROM accounts WHERE account_id = ?
        3. 检查 cash >= price * quantity
        4. UPDATE accounts SET cash = cash - amount
        5. UPDATE/INSERT positions (quantity += N, avg_cost 重算)
        6. INSERT trades (trade_id, symbol, BUY, ...)
        7. INSERT audit_log (op=BUY, cash_before, cash_after, ...)
        8. COMMIT
        9. event_bus.emit(TradeEvent(...))

        Raises:
            InsufficientCashError: 现金不足
            AccountNotFoundError: 账户不存在
        """
        amount = price * quantity
        trade_id = self._generate_trade_id()

        def do_buy(conn):
            # 1. 读取当前 cash
            row = conn.execute(
                "SELECT cash FROM accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            if not row:
                raise AccountNotFoundError(self.account_id)
            cash_before = row[0]

            # 2. 检查现金
            if cash_before < amount:
                raise InsufficientCashError(amount, cash_before)

            cash_after = cash_before - amount

            # 3. 更新 cash
            conn.execute(
                "UPDATE accounts SET cash = ?, updated_at = ? WHERE account_id = ?",
                (cash_after, datetime.now().isoformat(), self.account_id),
            )

            # 4. 更新 position (upsert)
            pos_row = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE account_id = ? AND symbol = ?",
                (self.account_id, symbol),
            ).fetchone()

            if pos_row:
                old_qty, old_avg = pos_row[0], pos_row[1]
                new_qty = old_qty + quantity
                new_avg = (old_qty * old_avg + quantity * price) / new_qty
                conn.execute(
                    """UPDATE positions
                       SET quantity = ?, avg_cost = ?, market_value = ?,
                           current_price = ?,
                           unrealized_pnl = ?,
                           updated_at = ?
                       WHERE account_id = ? AND symbol = ?""",
                    (
                        new_qty, new_avg, new_qty * price, price,
                        new_qty * (price - new_avg),
                        datetime.now().isoformat(),
                        self.account_id, symbol,
                    ),
                )
                position_quantity = new_qty
            else:
                conn.execute(
                    """INSERT INTO positions
                       (account_id, symbol, symbol_name, quantity, avg_cost,
                        current_price, market_value, unrealized_pnl, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self.account_id, symbol, name, quantity, price,
                        price, quantity * price, 0.0,
                        datetime.now().isoformat(),
                    ),
                )
                position_quantity = quantity

            # 5. 记录 trade
            now = datetime.now()
            conn.execute(
                """INSERT INTO trades
                   (account_id, symbol, symbol_name, trade_type, quantity, price,
                    amount, commission, trade_date, trade_time, order_id, status,
                    created_at, reason, agent_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.account_id, symbol, name, "BUY", quantity, price,
                    amount, 0.0,
                    now.strftime("%Y%m%d"), now.strftime("%H:%M:%S"),
                    trade_id, "filled", now.isoformat(),
                    reason, agent_id,
                ),
            )

            # 6. 记录审计日志
            conn.execute(
                """INSERT INTO audit_log
                   (account_id, operation, symbol, quantity, price, amount,
                    cash_before, cash_after, agent_id, source_module, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.account_id, "BUY", symbol, quantity, price, amount,
                    cash_before, cash_after, agent_id, source_module,
                    json.dumps({"reason": reason, "trade_id": trade_id}),
                ),
            )

            return cash_after, position_quantity

        # 执行事务
        try:
            cash_after, position_quantity = self.db.execute_in_transaction([do_buy])

            # 发布事件 (事务外)
            self.event_bus.emit(trade_event(
                account_id=self.account_id,
                symbol=symbol,
                direction="BUY",
                quantity=quantity,
                price=price,
                amount=amount,
                agent_id=agent_id,
            ))

            return TradeResult(
                success=True,
                trade_id=trade_id,
                message=f"买入成功: {symbol} {quantity}@{price}",
                cash_after=cash_after,
                position_quantity=position_quantity,
            )
        except (InsufficientCashError, AccountNotFoundError) as e:
            return TradeResult(success=False, message=str(e))
        except Exception as e:
            logger.error(f"Buy failed: {e}")
            return TradeResult(success=False, message=f"交易失败: {e}")

    def sell(
        self,
        symbol: str,
        price: float,
        quantity: int,
        reason: str = "",
        agent_id: str = "system",
        source_module: str = "",
    ) -> TradeResult:
        """卖出 — cash 增加 + position 扣减 + trade 记录 原子完成

        事务流程:
        1. BEGIN TRANSACTION
        2. SELECT quantity, avg_cost FROM positions WHERE symbol = ?
        3. 检查 quantity >= sell_quantity
        4. 计算 realized_pnl = (price - avg_cost) * quantity
        5. UPDATE accounts SET cash = cash + amount
        6. UPDATE/DELETE positions (quantity -= N, 或 0 时删除)
        7. INSERT trades (trade_id, symbol, SELL, ...)
        8. INSERT audit_log (op=SELL, cash_before, cash_after, realized_pnl)
        9. COMMIT
        10. event_bus.emit(TradeEvent(...))

        Raises:
            InsufficientPositionError: 持仓不足
        """
        amount = price * quantity
        trade_id = self._generate_trade_id()

        def do_sell(conn):
            # 1. 读取持仓
            pos_row = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE account_id = ? AND symbol = ?",
                (self.account_id, symbol),
            ).fetchone()
            if not pos_row:
                raise InsufficientPositionError(symbol, quantity, 0)

            pos_qty, avg_cost = pos_row[0], pos_row[1]
            if pos_qty < quantity:
                raise InsufficientPositionError(symbol, quantity, pos_qty)

            # 2. 计算 realized_pnl
            realized_pnl = (price - avg_cost) * quantity

            # 3. 读取当前 cash
            cash_row = conn.execute(
                "SELECT cash FROM accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            cash_before = cash_row[0]
            cash_after = cash_before + amount

            # 4. 更新 cash
            conn.execute(
                "UPDATE accounts SET cash = ?, updated_at = ? WHERE account_id = ?",
                (cash_after, datetime.now().isoformat(), self.account_id),
            )

            # 5. 更新 position
            new_qty = pos_qty - quantity
            if new_qty == 0:
                conn.execute(
                    "DELETE FROM positions WHERE account_id = ? AND symbol = ?",
                    (self.account_id, symbol),
                )
                position_quantity = 0
            else:
                conn.execute(
                    """UPDATE positions
                       SET quantity = ?, market_value = ?, current_price = ?,
                           unrealized_pnl = ?,
                           updated_at = ?
                       WHERE account_id = ? AND symbol = ?""",
                    (
                        new_qty, new_qty * price, price,
                        new_qty * (price - avg_cost),
                        datetime.now().isoformat(),
                        self.account_id, symbol,
                    ),
                )
                position_quantity = new_qty

            # 6. 记录 trade
            now = datetime.now()
            conn.execute(
                """INSERT INTO trades
                   (account_id, symbol, trade_type, quantity, price,
                    amount, commission, trade_date, trade_time,
                    order_id, status, created_at, reason, agent_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.account_id, symbol, "SELL", quantity, price,
                    amount, 0.0,
                    now.strftime("%Y%m%d"), now.strftime("%H:%M:%S"),
                    trade_id, "filled", now.isoformat(),
                    reason, agent_id,
                ),
            )

            # 7. 记录审计日志
            conn.execute(
                """INSERT INTO audit_log
                   (account_id, operation, symbol, quantity, price, amount,
                    cash_before, cash_after, agent_id, source_module, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.account_id, "SELL", symbol, quantity, price, amount,
                    cash_before, cash_after, agent_id, source_module,
                    json.dumps({
                        "reason": reason,
                        "trade_id": trade_id,
                        "realized_pnl": realized_pnl,
                    }),
                ),
            )

            return cash_after, position_quantity, realized_pnl

        # 执行事务
        try:
            cash_after, position_quantity, realized_pnl = self.db.execute_in_transaction([do_sell])

            # 发布事件
            self.event_bus.emit(trade_event(
                account_id=self.account_id,
                symbol=symbol,
                direction="SELL",
                quantity=quantity,
                price=price,
                amount=amount,
                agent_id=agent_id,
            ))

            return TradeResult(
                success=True,
                trade_id=trade_id,
                message=f"卖出成功: {symbol} {quantity}@{price}, 盈亏: {realized_pnl:.2f}",
                cash_after=cash_after,
                position_quantity=position_quantity,
            )
        except InsufficientPositionError as e:
            return TradeResult(success=False, message=str(e))
        except Exception as e:
            logger.error(f"Sell failed: {e}")
            return TradeResult(success=False, message=f"交易失败: {e}")

    # ── 查询操作 (只读) ─────────────────────────────────

    def get_balance(self) -> Balance:
        """统一余额计算: cash + sum(quantity * current_price)

        current_price 从持仓的 current_price 字段获取；如果为 0 则 fallback 到 avg_cost
        """
        account = self.db.get_account(self.account_id)
        if not account:
            raise AccountNotFoundError(self.account_id)

        positions = self.get_positions()
        market_value = sum(p.market_value for p in positions)
        unrealized_pnl = sum(p.unrealized_pnl for p in positions)

        # 已实现盈亏: 从审计日志中累计 SELL 的 realized_pnl
        realized_pnl = self._compute_realized_pnl()

        return Balance(
            cash=account.cash,
            market_value=market_value,
            total_assets=account.cash + market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            updated_at=datetime.now().isoformat(),
        )

    def get_positions(self) -> List[Position]:
        """从 SQLite 读取持仓，无 fallback 链"""
        db_positions = self.db.get_positions(self.account_id)
        result = []
        for p in db_positions:
            current_price = p.current_price if p.current_price > 0 else p.avg_cost
            result.append(Position(
                symbol=p.symbol,
                name=p.symbol_name or "",
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                current_price=current_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
            ))
        return result

    def get_trade_history(
        self,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100,
    ) -> List[Trade]:
        """从 trades 表读取交易记录

        Args:
            start_date: 起始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end_date: 截止日期 (YYYY-MM-DD 或 YYYYMMDD)
            limit: 返回条数上限
        """
        conn = get_connection()
        try:
            query = "SELECT * FROM trades WHERE account_id = ?"
            params = [self.account_id]

            if start_date:
                normalized = start_date.replace("-", "")
                query += " AND trade_date >= ?"
                params.append(normalized)
            if end_date:
                normalized = end_date.replace("-", "")
                query += " AND trade_date <= ?"
                params.append(normalized)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_trade(row) for row in rows]
        finally:
            conn.close()

    def get_audit_log(
        self,
        operation: str = None,
        limit: int = 100,
    ) -> List[dict]:
        """从 audit_log 表读取操作记录"""
        conn = get_connection()
        try:
            query = "SELECT * FROM audit_log WHERE account_id = ?"
            params = [self.account_id]

            if operation:
                query += " AND operation = ?"
                params.append(operation.upper())

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ── 快照操作 ─────────────────────────────────────────

    def snapshot(self, trade_date: str = None) -> Snapshot:
        """生成并保存每日快照

        1. 计算当前 balance
        2. 统计 positions_count, trades_count
        3. INSERT INTO daily_snapshots
        4. event_bus.emit(SNAPSHOT_CREATED)
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")

        balance = self.get_balance()

        conn = get_connection()
        try:
            positions_count = conn.execute(
                "SELECT COUNT(*) FROM positions WHERE account_id = ? AND quantity > 0",
                (self.account_id,),
            ).fetchone()[0]

            # 今日交易数
            trades_count = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE account_id = ? AND trade_date = ?",
                (self.account_id, trade_date),
            ).fetchone()[0]
        finally:
            conn.close()

        snap = Snapshot(
            account_id=self.account_id,
            trade_date=trade_date,
            cash=balance.cash,
            market_value=balance.market_value,
            total_assets=balance.total_assets,
            realized_pnl=balance.realized_pnl,
            unrealized_pnl=balance.unrealized_pnl,
            positions_count=positions_count,
            trades_count=trades_count,
        )

        # 保存到数据库
        self.db.save_snapshot(
            account_id=self.account_id,
            trade_date=trade_date,
            cash=snap.cash,
            market_value=snap.market_value,
            realized_pnl=snap.realized_pnl,
            unrealized_pnl=snap.unrealized_pnl,
        )
        # 更新 positions_count / trades_count（save_snapshot 默认写 0）
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE daily_snapshots
                   SET positions_count = ?, trades_count = ?
                   WHERE account_id = ? AND trade_date = ?""",
                (positions_count, trades_count, self.account_id, trade_date),
            )
            conn.commit()
        finally:
            conn.close()

        # 发布事件
        self.event_bus.emit(AccountEvent(
            type=EventType.SNAPSHOT_CREATED,
            account_id=self.account_id,
            data={
                "trade_date": trade_date,
                "total_assets": snap.total_assets,
                "cash": snap.cash,
                "positions_count": positions_count,
            },
        ))

        return snap

    # ── 辅助方法 ─────────────────────────────────────────

    def _generate_trade_id(self) -> str:
        """生成唯一 trade_id: T-{timestamp}-{random4}"""
        ts = int(time.time() * 1000)
        rand = random.randint(1000, 9999)
        return f"T-{ts}-{rand}"

    def _compute_realized_pnl(self) -> float:
        """从审计日志中累计已实现盈亏"""
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT details FROM audit_log
                   WHERE account_id = ? AND operation = 'SELL'""",
                (self.account_id,),
            ).fetchall()
            total = 0.0
            for row in rows:
                try:
                    details = json.loads(row[0]) if row[0] else {}
                    total += details.get("realized_pnl", 0.0)
                except (json.JSONDecodeError, TypeError):
                    pass
            return total
        finally:
            conn.close()

    def _row_to_trade(self, row) -> Trade:
        """将 SQLite 行转换为 Trade 对象"""
        d = dict(row)
        direction_str = d.get("trade_type", "BUY")
        try:
            direction = Direction(direction_str)
        except ValueError:
            direction = Direction.BUY

        return Trade(
            trade_id=d.get("order_id", "") or "",
            account_id=d["account_id"],
            symbol=d["symbol"],
            name=d.get("symbol_name", "") or "",
            direction=direction,
            quantity=d["quantity"],
            price=d["price"],
            amount=d["amount"],
            commission=d.get("commission", 0.0),
            trade_date=d.get("trade_date", ""),
            trade_time=d.get("trade_time", ""),
            order_id=d.get("order_id", "") or "",
            status=d.get("status", "filled"),
            agent_id=d.get("agent_id", "system") or "system",
            reason=d.get("reason", "") or "",
            created_at=d.get("created_at", ""),
        )
