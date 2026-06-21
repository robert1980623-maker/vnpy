#!/usr/bin/env python3
"""单元测试 - 虚拟账户模块

覆盖：
- test_account_initialization: 账户初始化（飞书缓存 → SQLite → JSON → 默认）
- test_position_tracking: 持仓跟踪（飞书缓存优先，交易流水回退）
- test_trade_execution: 交易执行（买入 / 卖出 / 资金校验 / 持仓校验）
- test_pnl_calculation: 盈亏计算（总资产 / 持仓市值 / 仓位比例）

所有外部依赖（SQLite、文件系统、飞书 SDK）均通过 mock 隔离。
"""

import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 确保能导入 virtual_account
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock(account=None):
    """构造一个 AccountDB mock，get_account 返回指定账户或 None"""
    db = MagicMock()
    db.get_account.return_value = account
    db.create_account.return_value = True
    db.update_cash.return_value = True
    return db


def _default_account_data(cash: float = 1_000_000) -> dict:
    return {
        "account_id": "virtual_2026",
        "account_name": "王雅轩主账户",
        "initial_capital": 1_000_000,
        "current_cash": cash,
        "currency": "CNY",
        "status": "active",
        "created_at": "2026-03-24",
        "updated_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAccountInitialization:
    """账户初始化测试"""

    @patch("virtual_account.get_db")
    @patch("virtual_account.ACCOUNT_FILE")
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_trade_log", return_value={"trades": []})
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_account_from_feishu", return_value=None)
    def test_default_account_when_no_source(self, _feishu, _trade_log, mock_acc_file, mock_get_db):
        """所有数据源均不可用时，创建默认账户（100 万初始资金）"""
        mock_acc_file.exists.return_value = False
        mock_get_db.return_value = _make_db_mock(account=None)

        from virtual_account import VirtualAccount
        account = VirtualAccount()

        assert account.account_data["account_id"] == "virtual_2026"
        assert account.account_data["initial_capital"] == 1_000_000
        assert account.account_data["current_cash"] == 1_000_000
        assert account.trade_log == {"trades": []}

    @patch("virtual_account.get_db")
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_trade_log", return_value={"trades": []})
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_account_from_feishu")
    def test_feishu_cache_takes_priority(self, mock_feishu, _trade_log, mock_get_db):
        """飞书缓存优先级最高，命中后同步到 SQLite"""
        feishu_data = _default_account_data(cash=500_000)
        mock_feishu.return_value = feishu_data
        db = _make_db_mock()
        mock_get_db.return_value = db

        from virtual_account import VirtualAccount
        account = VirtualAccount()

        assert account.account_data["current_cash"] == 500_000
        # 应调用 _sync_account_to_sqlite
        db.create_account.assert_called_once()

    @patch("virtual_account.get_db")
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_trade_log", return_value={"trades": []})
    @patch.object(__import__("virtual_account").VirtualAccount, "_load_account_from_feishu", return_value=None)
    def test_sqlite_fallback(self, _feishu, _trade_log, mock_get_db):
        """飞书缓存不可用时，从 SQLite 读取"""
        sqlite_account = MagicMock()
        sqlite_account.account_id = "virtual_2026"
        sqlite_account.account_name = "SQLite 账户"
        sqlite_account.initial_capital = 800_000
        sqlite_account.cash = 600_000
        sqlite_account.currency = "CNY"
        sqlite_account.status = "active"
        sqlite_account.created_at = "2026-01-01"
        sqlite_account.updated_at = "2026-06-01"

        mock_get_db.return_value = _make_db_mock(account=sqlite_account)

        from virtual_account import VirtualAccount
        account = VirtualAccount()

        assert account.account_data["current_cash"] == 600_000
        assert account.account_data["account_name"] == "SQLite 账户"


class TestPositionTracking:
    """持仓跟踪测试"""

    def _make_account(self, cash=1_000_000, trades=None):
        """构造一个绕过 __init__ 的 VirtualAccount 实例"""
        from virtual_account import VirtualAccount
        with patch("virtual_account.get_db") as mock_get_db, \
             patch.object(VirtualAccount, "_load_account_from_feishu", return_value=None):
            mock_get_db.return_value = _make_db_mock()
            account = VirtualAccount.__new__(VirtualAccount)
            account.db = mock_get_db.return_value
            account.account_data = _default_account_data(cash=cash)
            account.trade_log = {"trades": trades or []}
        return account

    def test_positions_from_trade_log_fallback(self):
        """飞书缓存不可用时，从交易流水计算持仓"""
        trades = [
            {"symbol": "000001.SZ", "name": "平安银行", "direction": "买",
             "price": 10.0, "quantity": 1000, "status": "filled"},
            {"symbol": "600519.SH", "name": "贵州茅台", "direction": "买",
             "price": 1800.0, "quantity": 100, "status": "filled"},
        ]
        account = self._make_account(trades=trades)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            positions = account.get_positions()

        symbols = {p["symbol"] for p in positions}
        assert "000001.SZ" in symbols
        assert "600519.SH" in symbols

        pingan = next(p for p in positions if p["symbol"] == "000001.SZ")
        assert pingan["quantity"] == 1000
        assert pingan["avg_price"] == 10.0

    def test_positions_from_feishu_cache(self):
        """飞书缓存可用时，直接使用缓存数据"""
        feishu_positions = [
            {"symbol": "000001.SZ", "name": "平安银行", "quantity": 2000,
             "avg_price": 11.0, "cost": 22000},
        ]
        account = self._make_account()

        with patch.object(account, "_load_positions_from_feishu", return_value=feishu_positions):
            positions = account.get_positions()

        assert len(positions) == 1
        assert positions[0]["symbol"] == "000001.SZ"
        assert positions[0]["quantity"] == 2000

    def test_empty_positions(self):
        """无持仓时返回空列表"""
        account = self._make_account(trades=[])

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            positions = account.get_positions()

        assert positions == []

    def test_unfilled_trades_ignored(self):
        """非 filled 状态的交易不计入持仓"""
        trades = [
            {"symbol": "000001.SZ", "name": "平安银行", "direction": "买",
             "price": 10.0, "quantity": 1000, "status": "pending"},
        ]
        account = self._make_account(trades=trades)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            positions = account.get_positions()

        assert positions == []


class TestTradeExecution:
    """交易执行测试"""

    def _make_account(self, cash=1_000_000, trades=None):
        from virtual_account import VirtualAccount
        with patch("virtual_account.get_db") as mock_get_db, \
             patch.object(VirtualAccount, "_load_account_from_feishu", return_value=None):
            mock_get_db.return_value = _make_db_mock()
            account = VirtualAccount.__new__(VirtualAccount)
            account.db = mock_get_db.return_value
            account.account_data = _default_account_data(cash=cash)
            account.trade_log = {"trades": trades or []}
        return account

    @patch.object(__import__("virtual_account").VirtualAccount, "_save")
    def test_buy_success(self, mock_save):
        """正常买入：资金扣减、交易记录写入"""
        account = self._make_account(cash=100_000)

        trade = account.buy("000001.SZ", "平安银行", 10.0, 1000, reason="测试")

        assert trade["direction"] == "买"
        assert trade["cost"] == 10_000
        assert trade["status"] == "filled"
        assert account.account_data["current_cash"] == 90_000
        assert len(account.trade_log["trades"]) == 1
        mock_save.assert_called_once()

    @patch.object(__import__("virtual_account").VirtualAccount, "_save")
    def test_buy_insufficient_cash(self, mock_save):
        """资金不足时抛出 ValueError"""
        account = self._make_account(cash=100)

        with pytest.raises(ValueError, match="资金不足"):
            account.buy("000001.SZ", "平安银行", 10.0, 1000)

        # 资金不变、无交易记录
        assert account.account_data["current_cash"] == 100
        assert len(account.trade_log["trades"]) == 0
        mock_save.assert_not_called()

    @patch.object(__import__("virtual_account").VirtualAccount, "_save")
    def test_sell_success(self, mock_save):
        """正常卖出：资金增加、持仓扣减"""
        existing_trades = [
            {"symbol": "000001.SZ", "name": "平安银行", "direction": "买",
             "price": 10.0, "quantity": 1000, "status": "filled"},
        ]
        account = self._make_account(cash=50_000, trades=existing_trades)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            trade = account.sell("000001.SZ", 12.0, 500, reason="止盈")

        assert trade["direction"] == "卖"
        assert trade["proceeds"] == 6_000
        assert account.account_data["current_cash"] == 56_000
        mock_save.assert_called_once()

    @patch.object(__import__("virtual_account").VirtualAccount, "_save")
    def test_sell_insufficient_position(self, mock_save):
        """持仓不足时抛出 ValueError"""
        account = self._make_account(cash=50_000, trades=[])

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            with pytest.raises(ValueError, match="持仓不足"):
                account.sell("000001.SZ", 12.0, 500)

        mock_save.assert_not_called()

    @patch.object(__import__("virtual_account").VirtualAccount, "_save")
    def test_sell_nonexistent_symbol(self, mock_save):
        """卖出不存在的股票时抛出 ValueError"""
        account = self._make_account(cash=50_000, trades=[])

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            with pytest.raises(ValueError, match="持仓不足"):
                account.sell("999999.SZ", 10.0, 100)

        mock_save.assert_not_called()


class TestPnLCalculation:
    """盈亏计算测试"""

    def _make_account(self, cash=1_000_000, trades=None):
        from virtual_account import VirtualAccount
        with patch("virtual_account.get_db") as mock_get_db, \
             patch.object(VirtualAccount, "_load_account_from_feishu", return_value=None):
            mock_get_db.return_value = _make_db_mock()
            account = VirtualAccount.__new__(VirtualAccount)
            account.db = mock_get_db.return_value
            account.account_data = _default_account_data(cash=cash)
            account.trade_log = {"trades": trades or []}
        return account

    def test_total_asset_no_positions(self):
        """无持仓时，总资产 = 现金"""
        account = self._make_account(cash=500_000)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            assert account.get_total_asset() == 500_000
            assert account.get_position_value() == 0
            assert account.get_position_ratio() == 0

    def test_total_asset_with_positions(self):
        """有持仓时，总资产 = 现金 + 持仓成本"""
        trades = [
            {"symbol": "000001.SZ", "name": "平安银行", "direction": "买",
             "price": 10.0, "quantity": 1000, "status": "filled"},
        ]
        account = self._make_account(cash=90_000, trades=trades)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            # 持仓成本 = 10 * 1000 = 10000
            assert account.get_position_value() == 10_000
            # 总资产 = 90000 + 10000 = 100000
            assert account.get_total_asset() == 100_000

    def test_position_ratio(self):
        """仓位比例计算"""
        trades = [
            {"symbol": "000001.SZ", "name": "平安银行", "direction": "买",
             "price": 10.0, "quantity": 5000, "status": "filled"},
        ]
        account = self._make_account(cash=50_000, trades=trades)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            # 持仓成本 = 10 * 5000 = 50000
            # 总资产 = 50000 + 50000 = 100000
            # 仓位 = 50000 / 100000 * 100 = 50%
            assert account.get_position_ratio() == pytest.approx(50.0)

    def test_position_value_feishu_format(self):
        """飞书格式持仓（含 market_value 字段）的市值计算"""
        feishu_positions = [
            {"symbol": "000001.SZ", "name": "平安银行", "quantity": 1000,
             "avg_price": 10.0, "cost": 10_000, "market_value": 12_000},
        ]
        account = self._make_account(cash=88_000)

        with patch.object(account, "_load_positions_from_feishu", return_value=feishu_positions):
            # 优先使用 market_value
            assert account.get_position_value() == 12_000
            assert account.get_total_asset() == 100_000

    def test_position_value_volume_cost_price_format(self):
        """飞书格式变体（volume + cost_price）的市值计算"""
        positions = [
            {"symbol": "000001.SZ", "name": "平安银行",
             "volume": 1000, "cost_price": 10.0},
        ]
        account = self._make_account(cash=90_000)

        with patch.object(account, "_load_positions_from_feishu", return_value=positions):
            # volume * cost_price = 1000 * 10 = 10000
            assert account.get_position_value() == 10_000

    def test_zero_total_asset_position_ratio(self):
        """总资产为零时仓位比例返回 0（避免除零）"""
        account = self._make_account(cash=0)

        with patch.object(account, "_load_positions_from_feishu", return_value=None):
            assert account.get_total_asset() == 0
            assert account.get_position_ratio() == 0


if __name__ == "__main__":
    unittest.main()
