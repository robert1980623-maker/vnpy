"""
持仓价格自动更新模块

Phase 6: 从本地 CSV 读取最新收盘价，批量更新 positions 表

功能:
- get_latest_price(): 读取单只股票最新收盘价
- get_latest_prices(): 批量读取最新收盘价
- refresh_positions(): 更新指定账户的所有持仓价格
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from accounts.account_db import get_connection

logger = logging.getLogger(__name__)

# 默认bars目录
DEFAULT_BARS_DIR = Path(__file__).parent.parent / "data" / "akshare" / "bars"

# 交易所代码映射
EXCHANGE_MAP = {
    "SZSE": "sz",
    "SHSE": "sh",
    "BJSE": "bj",
}


def _symbol_to_filename(symbol: str) -> str:
    """将 tushare 格式的 symbol 转换为 CSV 文件名

    Args:
        symbol: tushare 格式，如 000001.SZSE

    Returns:
        CSV 文件名，如 000001_sz.csv
    """
    if "." not in symbol:
        logger.warning(f"Invalid symbol format: {symbol}")
        return None

    code, exchange = symbol.split(".", 1)
    ext = EXCHANGE_MAP.get(exchange, exchange.lower())
    return f"{code}_{ext}.csv"


class PriceUpdater:
    """从本地 CSV 读取最新收盘价，批量更新 positions 表"""

    def __init__(self, bars_dir: Path = None):
        """初始化价格更新器

        Args:
            bars_dir: CSV 文件目录，默认为 data/akshare/bars
        """
        self.bars_dir = bars_dir or DEFAULT_BARS_DIR
        if not self.bars_dir.exists():
            logger.warning(f"Bars directory not found: {self.bars_dir}")

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """读取单只股票最新收盘价

        Args:
            symbol: 股票代码，如 000001.SZSE

        Returns:
            最新收盘价，读取失败返回 None
        """
        filename = _symbol_to_filename(symbol)
        filepath = self.bars_dir / filename

        if not filepath.exists():
            logger.warning(f"CSV file not found: {filepath}")
            return None

        try:
            df = pd.read_csv(filepath)
            if df.empty:
                logger.warning(f"CSV file is empty: {filepath}")
                return None

            # 取最后一行（最新数据）
            latest_row = df.iloc[-1]
            close_price = float(latest_row["close"])

            # 验证价格合理性
            if close_price <= 0 or close_price > 10000:
                logger.warning(f"Invalid price {close_price} for {symbol}, skipping")
                return None

            return close_price
        except Exception as e:
            logger.error(f"Failed to read price for {symbol}: {e}")
            return None

    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """批量读取最新收盘价

        Args:
            symbols: 股票代码列表

        Returns:
            {symbol: price} 字典，找不到价格的 symbol 不会出现在结果中
        """
        prices = {}
        for symbol in symbols:
            price = self.get_latest_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices

    def refresh_positions(self, account_id: str) -> int:
        """更新指定账户的所有持仓价格

        在单个事务内完成所有更新，保证原子性。

        Args:
            account_id: 账户ID

        Returns:
            更新的持仓数量（成功找到价格的）
        """
        conn = get_connection()
        try:
            # 1. 查询该账户所有持仓
            rows = conn.execute(
                "SELECT symbol, quantity, avg_cost FROM positions WHERE account_id = ? AND quantity > 0",
                (account_id,),
            ).fetchall()

            if not rows:
                logger.info(f"No positions to refresh for {account_id}")
                return 0

            # 2. 批量获取最新价格
            symbols = [r[0] for r in rows]
            prices = self.get_latest_prices(symbols)

            if not prices:
                logger.warning(f"No prices found for any positions of {account_id}")
                return 0

            # 3. 在事务内更新
            updated = 0
            import datetime
            now = datetime.datetime.now().isoformat()

            for symbol, quantity, avg_cost in rows:
                if symbol not in prices:
                    logger.warning(f"Price not found for {symbol}, skipping")
                    continue

                current_price = prices[symbol]
                market_value = quantity * current_price
                unrealized_pnl = quantity * (current_price - avg_cost)

                conn.execute(
                    """UPDATE positions 
                       SET current_price = ?, market_value = ?, unrealized_pnl = ?, updated_at = ?
                       WHERE account_id = ? AND symbol = ?""",
                    (current_price, market_value, unrealized_pnl, now, account_id, symbol),
                )
                updated += 1

            conn.commit()
            logger.info(f"Updated {updated} positions for account {account_id}")
            return updated

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to refresh positions: {e}")
            raise
        finally:
            conn.close()


def refresh_prices(account_id: str) -> int:
    """便捷函数：刷新指定账户的持仓价格

    Args:
        account_id: 账户ID

    Returns:
        更新的持仓数量
    """
    updater = PriceUpdater()
    return updater.refresh_positions(account_id)
