#!/usr/bin/env python3
"""
单元测试 - DebugVirtualAccount 持仓加载和账户操作

测试目标：
- 验证 DebugVirtualAccount 正确加载 debug_positions.json
- 验证 get_available_cash() / get_positions() / get_position_value() 正确
- 使用临时目录注入测试持仓数据，确保测试隔离
"""

import pytest
import json
import sys
import os
import importlib
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 原始工作目录（项目根目录，有真实的 debug_positions.json）
ORIG_CWD = PROJECT_ROOT


def _make_account(positions_data, cwd=ORIG_CWD):
    """
    创建 DebugVirtualAccount 实例，数据由 positions_data 提供。

    策略：用 tmp_path + chdir 切换工作目录，把 debug_positions.json 写进去，
    让 DebugVirtualAccount.__init__ 读到测试数据。
    """
    # 移除已缓存模块
    if "debug_virtual_account" in sys.modules:
        del sys.modules["debug_virtual_account"]

    # 准备临时目录（每个调用独享）
    tmpdir = ORIG_CWD / f".test_dva_{os.getpid()}_{id(positions_data)}"
    tmpdir.mkdir(exist_ok=True)
    tmp_pos_file = tmpdir / "debug_positions.json"

    with open(tmp_pos_file, "w", encoding="utf-8") as f:
        json.dump(positions_data, f)

    orig_cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        # 清除同一目录下可能缓存的 .pyc
        cache_dir = tmpdir / "__pycache__"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        from debug_virtual_account import DebugVirtualAccount
        return DebugVirtualAccount()
    finally:
        os.chdir(orig_cwd)


class TestDebugVirtualAccountInit:
    """测试 DebugVirtualAccount 初始化"""

    def test_init_account_data_fields(self):
        """初始化后 account_data 包含必要字段"""
        account = _make_account([])
        assert "account_id" in account.account_data
        assert "account_name" in account.account_data
        assert "initial_capital" in account.account_data
        assert "currency" in account.account_data
        assert "status" in account.account_data

    def test_init_account_id_correct(self):
        """账户 ID 正确"""
        account = _make_account([])
        assert account.account_data["account_id"] == "ACC001"

    def test_init_account_name_correct(self):
        """账户名称正确"""
        account = _make_account([])
        assert account.account_data["account_name"] == "王雅轩主账户"

    def test_init_initial_capital_correct(self):
        """初始资金正确"""
        account = _make_account([])
        assert account.account_data["initial_capital"] == 1000000

    def test_init_status_active(self):
        """账户状态为 active"""
        account = _make_account([])
        assert account.account_data["status"] == "active"

    def test_init_trade_log_empty(self):
        """交易日志初始化为空"""
        account = _make_account([])
        assert "trades" in account.trade_log
        assert account.trade_log["trades"] == []

    def test_init_loads_single_position(self):
        """从 JSON 文件加载单条持仓"""
        positions = [
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6}
        ]
        account = _make_account(positions)
        assert len(account.positions) == 1


class TestDebugVirtualAccountGetAvailableCash:
    """
    测试 get_available_cash()

    注意：DebugVirtualAccount.current_cash 是硬编码值 (1000000 - 996546.4 = 3453.6)，
    不随 self.positions 变化。这是该调试类的设计特点。
    因此 get_available_cash() 始终返回 3453.6，与持仓无关。
    """

    def test_available_cash_is_hardcoded_value(self):
        """硬编码：可用资金始终返回 3453.6"""
        account = _make_account([])
        # 硬编码值：1000000 - 996546.4 = 3453.6
        assert abs(account.get_available_cash() - 3453.6) < 0.01

    def test_available_cash_returns_float(self):
        """返回值类型为 float"""
        account = _make_account([])
        assert isinstance(account.get_available_cash(), float)


class TestDebugVirtualAccountGetPositions:
    """测试 get_positions()"""

    def test_empty_returns_empty_list(self):
        """无持仓时返回空列表"""
        account = _make_account([])
        assert account.get_positions() == []

    def test_returns_correct_position_data(self):
        """返回持仓数据正确"""
        positions = [
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6}
        ]
        account = _make_account(positions)
        assert account.get_positions() == positions

    def test_multiple_positions_count(self):
        """多持仓数量正确"""
        positions = [
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6},
            {"symbol": "603893.SH", "name": "瑞芯微", "quantity": 30100, "avg_price": 10.13, "cost": 304920.8},
            {"symbol": "300251.SZ", "name": "光线传媒", "quantity": 30000, "avg_price": 10.0, "cost": 300000.0},
        ]
        account = _make_account(positions)
        assert len(account.get_positions()) == 3


class TestDebugVirtualAccountGetPositionValue:
    """测试 get_position_value()"""

    def test_empty_positions_returns_zero(self):
        """空持仓市值 = 0"""
        account = _make_account([])
        assert account.get_position_value() == 0

    def test_single_position_value(self):
        """单持仓市值 = cost"""
        positions = [
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6}
        ]
        account = _make_account(positions)
        assert abs(account.get_position_value() - 391625.6) < 0.01

    def test_multiple_positions_sum(self):
        """多持仓市值 = 各 cost 之和"""
        positions = [
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6},
            {"symbol": "603893.SH", "name": "瑞芯微", "quantity": 30100, "avg_price": 10.13, "cost": 304920.8},
            {"symbol": "300251.SZ", "name": "光线传媒", "quantity": 30000, "avg_price": 10.0, "cost": 300000.0},
        ]
        account = _make_account(positions)
        expected = 391625.6 + 304920.8 + 300000.0
        assert abs(account.get_position_value() - expected) < 0.01


class TestDebugVirtualAccountCurrentCash:
    """
    测试 current_cash 属性

    注意：current_cash 是 __init__ 中的硬编码值，不随 positions 变化。
    这是 DebugVirtualAccount 的设计特点（调试用固定值）。
    """

    def test_current_cash_is_hardcoded(self):
        """硬编码 current_cash = 3453.6（1000000 - 996546.4）"""
        account = _make_account([])
        assert abs(account.account_data["current_cash"] - 3453.6) < 0.01

    def test_current_cash_independent_of_positions(self):
        """current_cash 与 positions 数据无关（硬编码）"""
        # 用空持仓
        acc_empty = _make_account([])
        # 用3条持仓
        acc_full = _make_account([
            {"symbol": "300476.SZ", "name": "胜宏科技", "quantity": 32200, "avg_price": 12.162, "cost": 391625.6},
        ])
        # 两者 current_cash 应该相同（都是硬编码的 3453.6）
        assert abs(acc_empty.account_data["current_cash"] - acc_full.account_data["current_cash"]) < 0.01


class TestDebugVirtualAccountMainBlock:
    """测试 __main__ 块"""

    def test_instantiation_no_exception(self):
        """直接实例化不抛异常"""
        account = _make_account([])
        assert account is not None

    def test_instantiation_uses_hardcoded_cash(self):
        """实例化后可用资金为硬编码值 3453.6"""
        account = _make_account([])
        assert abs(account.get_available_cash() - 3453.6) < 0.01
