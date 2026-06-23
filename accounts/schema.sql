-- 账户系统 SQLite Schema
-- 设计目标：支持多账户、交易记录、持仓管理

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    account_type TEXT DEFAULT 'virtual',  -- virtual/real
    initial_capital REAL NOT NULL,
    cash REAL NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'CNY',
    status TEXT DEFAULT 'active',  -- active/suspended/closed
    risk_level TEXT DEFAULT 'moderate',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    symbol_name TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    avg_cost REAL NOT NULL DEFAULT 0,
    current_price REAL DEFAULT 0,
    market_value REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, symbol),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    symbol_name TEXT,
    trade_type TEXT NOT NULL,  -- BUY/SELL
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    commission REAL DEFAULT 0,
    trade_date TEXT NOT NULL,
    trade_time TEXT NOT NULL,
    order_id TEXT,
    status TEXT DEFAULT 'filled',  -- pending/filled/cancelled
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 每日快照（用于复盘）
CREATE TABLE IF NOT EXISTS daily_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    cash REAL NOT NULL,
    total_market_value REAL NOT NULL,
    total_assets REAL NOT NULL,
    realized_pnl REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    positions_count INTEGER DEFAULT 0,
    trades_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(account_id, trade_date),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_account_date ON daily_snapshots(account_id, trade_date);

-- 🆕 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    operation       TEXT NOT NULL,  -- BUY, SELL, SYNC, SNAPSHOT, ADJUST, MANUAL
    symbol          TEXT,
    quantity        REAL,
    price           REAL,
    amount          REAL,
    cash_before     REAL,
    cash_after      REAL,
    agent_id        TEXT DEFAULT 'system',
    source_module   TEXT,           -- 调用方模块名 (e.g. "daily_trading.py")
    details         TEXT,           -- JSON 扩展字段
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_account_date
    ON audit_log(account_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_operation
    ON audit_log(account_id, operation);