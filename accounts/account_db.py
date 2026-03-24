"""
账户数据库访问层
SQLite 持久化封装
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


DB_PATH = Path(__file__).parent / "trading.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        schema = f.read()
    
    conn = get_connection()
    conn.executescript(schema)
    conn.commit()
    conn.close()


@dataclass
class Account:
    account_id: str
    account_name: str
    account_type: str = 'virtual'
    initial_capital: float = 0
    cash: float = 0
    currency: str = 'CNY'
    status: str = 'active'
    risk_level: str = 'moderate'
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


@dataclass
class Position:
    id: Optional[int] = None
    account_id: str = ''
    symbol: str = ''
    symbol_name: str = ''
    quantity: int = 0
    avg_cost: float = 0
    current_price: float = 0
    market_value: float = 0
    unrealized_pnl: float = 0
    updated_at: str = None

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class AccountDB:
    """账户数据库操作类"""
    
    def __init__(self):
        init_db()
    
    # ==================== 账户操作 ====================
    
    def create_account(self, account: Account) -> bool:
        """创建账户"""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO accounts (account_id, account_name, account_type, 
                    initial_capital, cash, currency, status, risk_level, 
                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account.account_id, account.account_name, account.account_type,
                account.initial_capital, account.cash, account.currency,
                account.status, account.risk_level, account.created_at, account.updated_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 账户已存在
        finally:
            conn.close()
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", 
                (account_id,)
            ).fetchone()
            if row:
                return Account(**dict(row))
            return None
        finally:
            conn.close()
    
    def update_cash(self, account_id: str, cash: float) -> bool:
        """更新现金"""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE accounts SET cash = ?, updated_at = ? WHERE account_id = ?",
                (cash, datetime.now().isoformat(), account_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== 持仓操作 ====================
    
    def update_position(
        self, account_id: str, symbol: str, quantity: int, 
        avg_cost: float, current_price: float = 0
    ) -> bool:
        """更新持仓"""
        conn = get_connection()
        market_value = quantity * current_price
        unrealized_pnl = quantity * (current_price - avg_cost)
        
        try:
            conn.execute("""
                INSERT INTO positions (account_id, symbol, quantity, avg_cost, 
                    current_price, market_value, unrealized_pnl, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, symbol) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_cost = excluded.avg_cost,
                    current_price = excluded.current_price,
                    market_value = excluded.market_value,
                    unrealized_pnl = excluded.unrealized_pnl,
                    updated_at = excluded.updated_at
            """, (account_id, symbol, quantity, avg_cost, current_price, 
                  market_value, unrealized_pnl, datetime.now().isoformat()))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_positions(self, account_id: str) -> List[Position]:
        """获取所有持仓"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM positions WHERE account_id = ? AND quantity > 0",
                (account_id,)
            ).fetchall()
            return [Position(**dict(row)) for row in rows]
        finally:
            conn.close()
    
    # ==================== 交易记录 ====================
    
    def add_trade(
        self, account_id: str, symbol: str, trade_type: str,
        quantity: int, price: float, commission: float = 0,
        symbol_name: str = "", order_id: str = None
    ) -> int:
        """添加交易记录"""
        conn = get_connection()
        amount = quantity * price
        now = datetime.now()
        trade_date = now.strftime('%Y%m%d')
        trade_time = now.strftime('%H:%M:%S')
        
        try:
            cursor = conn.execute("""
                INSERT INTO trades (account_id, symbol, symbol_name, trade_type,
                    quantity, price, amount, commission, trade_date, trade_time,
                    order_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_id, symbol, symbol_name, trade_type, quantity,
                  price, amount, commission, trade_date, trade_time,
                  order_id, 'filled', now.isoformat()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_trades(self, account_id: str, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM trades WHERE account_id = ? ORDER BY created_at DESC LIMIT ?",
                (account_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    # ==================== 快照操作 ====================
    
    def save_snapshot(self, account_id: str, trade_date: str, 
                      cash: float, market_value: float, 
                      realized_pnl: float = 0, unrealized_pnl: float = 0) -> bool:
        """保存每日快照"""
        conn = get_connection()
        total_assets = cash + market_value
        
        try:
            conn.execute("""
                INSERT INTO daily_snapshots (account_id, trade_date, cash,
                    total_market_value, total_assets, realized_pnl, unrealized_pnl,
                    positions_count, trades_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, trade_date) DO UPDATE SET
                    cash = excluded.cash,
                    total_market_value = excluded.total_market_value,
                    total_assets = excluded.total_assets,
                    realized_pnl = excluded.realized_pnl,
                    unrealized_pnl = excluded.unrealized_pnl,
                    updated_at = excluded.created_at
            """, (account_id, trade_date, cash, market_value, total_assets,
                  realized_pnl, unrealized_pnl, 0, 0, datetime.now().isoformat()))
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== 工具方法 ====================
    
    def get_account_summary(self, account_id: str) -> Dict:
        """获取账户摘要"""
        conn = get_connection()
        try:
            # 账户信息
            account = conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", 
                (account_id,)
            ).fetchone()
            
            # 持仓统计
            positions = conn.execute(
                "SELECT COUNT(*) as cnt, SUM(market_value) as mv, SUM(unrealized_pnl) as pnl FROM positions WHERE account_id = ?",
                (account_id,)
            ).fetchone()
            
            # 今日交易
            today = datetime.now().strftime('%Y%m%d')
            trades_today = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE account_id = ? AND trade_date = ?",
                (account_id, today)
            ).fetchone()[0]
            
            return {
                'account': dict(account) if account else None,
                'positions_count': positions['cnt'] or 0,
                'total_market_value': positions['mv'] or 0,
                'unrealized_pnl': positions['pnl'] or 0,
                'trades_today': trades_today
            }
        finally:
            conn.close()


# 初始化并导出单例
_db = None

def get_db() -> AccountDB:
    global _db
    if _db is None:
        _db = AccountDB()
    return _db


if __name__ == '__main__':
    # 测试
    db = get_db()
    
    # 创建 robert 账户（如果不存在）
    if not db.get_account('robert'):
        account = Account(
            account_id='robert',
            account_name='Robert',
            initial_capital=1_000_000,
            cash=1_000_000
        )
        db.create_account(account)
        print("✅ 账户 robert 已创建")
    
    # 获取摘要
    summary = db.get_account_summary('robert')
    print(f"\n📊 账户摘要:")
    print(f"  现金: ¥{summary['account']['cash']:,.2f}")
    print(f"  持仓数: {summary['positions_count']}")
    print(f"  持仓市值: ¥{summary['total_market_value']:,.2f}")
    print(f"  浮动盈亏: ¥{summary['unrealized_pnl']:,.2f}")


class TradingAccount(AccountDB):
    """交易账户（支持买卖操作）"""
    
    def __init__(self, account_id: str):
        super().__init__()
        self.account_id = account_id
        self.account = self.get_account(account_id)
        if not self.account:
            raise ValueError(f"账户 {account_id} 不存在")
    
    @property
    def cash(self) -> float:
        """当前现金"""
        return self.account.cash
    
    @property
    def positions(self) -> List[Position]:
        """当前持仓"""
        return self.get_positions(self.account_id)
    
    def can_buy(self, symbol: str, quantity: int, price: float, 
                commission_rate: float = 0.0003) -> bool:
        """检查是否可以买入"""
        required = quantity * price * (1 + commission_rate)
        return self.cash >= required
    
    def buy(self, symbol: str, quantity: int, price: float,
            symbol_name: str = "", commission_rate: float = 0.0003) -> Dict:
        """
        买入股票
        返回: {'success': bool, 'message': str, 'trade_id': int or None}
        """
        commission = quantity * price * commission_rate
        total_cost = quantity * price + commission
        
        if not self.can_buy(symbol, quantity, price, commission_rate):
            return {
                'success': False, 
                'message': f'现金不足，需要 ¥{total_cost:,.2f}，当前可用 ¥{self.cash:,.2f}',
                'trade_id': None
            }
        
        # 记录交易
        trade_id = self.add_trade(
            account_id=self.account_id,
            symbol=symbol,
            trade_type='BUY',
            quantity=quantity,
            price=price,
            commission=commission,
            symbol_name=symbol_name
        )
        
        # 更新现金
        new_cash = self.cash - total_cost
        self.update_cash(self.account_id, new_cash)
        
        # 更新持仓
        current_pos = self.get_position(symbol)
        if current_pos:
            # 加仓
            new_qty = current_pos.quantity + quantity
            new_avg = (current_pos.quantity * current_pos.avg_cost + quantity * price) / new_qty
            self.update_position(self.account_id, symbol, new_qty, new_avg, price)
        else:
            # 新建持仓
            self.update_position(self.account_id, symbol, quantity, price, price)
        
        # 刷新账户
        self.account = self.get_account(self.account_id)
        
        return {
            'success': True,
            'message': f'买入 {symbol} {quantity}股 @ ¥{price:.2f}',
            'trade_id': trade_id,
            'cost': total_cost,
            'remaining_cash': new_cash
        }
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取单只股票持仓"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM positions WHERE account_id = ? AND symbol = ?",
                (self.account_id, symbol)
            ).fetchone()
            return Position(**dict(row)) if row else None
        finally:
            conn.close()
    
    def sell(self, symbol: str, quantity: int, price: float,
             commission_rate: float = 0.0003) -> Dict:
        """
        卖出股票
        """
        pos = self.get_position(symbol)
        if not pos or pos.quantity < quantity:
            return {
                'success': False,
                'message': f'持仓不足，当前 {pos.quantity if pos else 0} 股，需要 {quantity} 股',
                'trade_id': None
            }
        
        commission = quantity * price * commission_rate
        proceeds = quantity * price - commission
        
        # 记录交易
        trade_id = self.add_trade(
            account_id=self.account_id,
            symbol=symbol,
            trade_type='SELL',
            quantity=quantity,
            price=price,
            commission=commission
        )
        
        # 更新现金
        new_cash = self.cash + proceeds
        self.update_cash(self.account_id, new_cash)
        
        # 更新持仓
        remaining = pos.quantity - quantity
        if remaining > 0:
            self.update_position(self.account_id, symbol, remaining, pos.avg_cost, price)
        else:
            # 清仓
            conn = get_connection()
            conn.execute(
                "DELETE FROM positions WHERE account_id = ? AND symbol = ?",
                (self.account_id, symbol)
            )
            conn.commit()
            conn.close()
        
        # 刷新账户
        self.account = self.get_account(self.account_id)
        
        return {
            'success': True,
            'message': f'卖出 {symbol} {quantity}股 @ ¥{price:.2f}',
            'trade_id': trade_id,
            'proceeds': proceeds,
            'remaining_cash': new_cash
        }
    
    def get_total_assets(self) -> float:
        """总资产 = 现金 + 持仓市值"""
        positions = self.positions
        market_value = sum(p.market_value for p in positions)
        return self.cash + market_value
    
    def get_pnl(self) -> Dict:
        """盈亏统计"""
        positions = self.positions
        unrealized = sum(p.unrealized_pnl for p in positions)
        
        # 已实现盈亏（需要从交易记录计算）
        conn = get_connection()
        result = conn.execute("""
            SELECT 
                SUM(CASE WHEN trade_type = 'SELL' THEN amount - commission ELSE 0 END) -
                SUM(CASE WHEN trade_type = 'BUY' THEN amount + commission ELSE 0 END) as realized
            FROM trades WHERE account_id = ?
        """, (self.account_id,)).fetchone()
        realized = result['realized'] or 0
        
        return {
            'unrealized_pnl': unrealized,
            'realized_pnl': realized,
            'total_pnl': unrealized + realized,
            'return_pct': (unrealized + realized) / self.account.initial_capital * 100
        }
