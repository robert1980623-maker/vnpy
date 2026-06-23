"""账户交易功能测试"""
import pytest
from accounts.account_db import TradingAccount, AccountDB, get_connection, Account as AccountModel


class TestTradingAccount:
    """测试交易账户功能"""

    def setup_method(self):
        """测试前设置"""
        self.db = AccountDB()
        self.test_account_id = "test_trading_account"
        self._cleanup_test_data()

    def teardown_method(self):
        """测试后清理"""
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """清理测试数据"""
        try:
            conn = get_connection()
            conn.execute("DELETE FROM trades WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM positions WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM accounts WHERE account_id = ?", (self.test_account_id,))
            conn.execute("DELETE FROM daily_snapshots WHERE account_id = ?", (self.test_account_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass  # 忽略清理错误

    def test_trading_account_creation(self):
        """测试交易账户创建"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=100000.0
        )
        self.db.create_account(base_account)

        # 创建交易账户
        trading_account = TradingAccount(self.test_account_id)

        assert trading_account.account_id == self.test_account_id
        assert trading_account.cash == 100000.0
        assert len(trading_account.positions) == 0

    def test_trading_account_creation_nonexistent_account(self):
        """测试创建不存在的交易账户"""
        with pytest.raises(ValueError, match=f"账户 nonexistent_account 不存在"):
            TradingAccount("nonexistent_account")

    def test_trading_account_properties(self):
        """测试交易账户属性"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=80000.0
        )
        self.db.create_account(base_account)

        # 添加一些持仓
        self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.0,
            current_price=16.0
        )

        # 创建交易账户
        trading_account = TradingAccount(self.test_account_id)

        assert trading_account.cash == 80000.0
        assert len(trading_account.positions) == 1
        assert trading_account.positions[0].symbol == "000001.SZSE"

    def test_can_buy_sufficient_funds(self):
        """测试资金充足时的买入判断"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 应该能够买入 1000 股 @ 15.0 价格 (包含手续费)
        can_buy = trading_account.can_buy("000001.SZSE", 1000, 15.0, 0.0003)
        assert can_buy is True  # 1000 * 15.0 * 1.0003 ≈ 15004.5 < 50000

    def test_can_buy_insufficient_funds(self):
        """测试资金不足时的买入判断"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=10000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 应该无法买入 1000 股 @ 15.0 价格 (包含手续费)
        can_buy = trading_account.can_buy("000001.SZSE", 1000, 15.0, 0.0003)
        assert can_buy is False  # 1000 * 15.0 * 1.0003 ≈ 15004.5 > 10000

    def test_buy_success(self):
        """测试买入成功"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 买入
        result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)

        assert result['success'] is True
        assert result['trade_id'] is not None
        assert '买入 000001.SZSE 1000股 @ ¥15.00' in result['message']
        assert result['cost'] == 15000.0 + (15000.0 * 0.0003)  # 15004.5
        assert result['remaining_cash'] == 50000.0 - 15004.5  # 34995.5

        # 验证现金减少
        assert trading_account.cash == 34995.5

        # 验证持仓增加
        position = trading_account.get_position("000001.SZSE")
        assert position is not None
        assert position.quantity == 1000
        assert position.avg_cost == 15.0
        assert position.current_price == 15.0

    def test_buy_insufficient_funds(self):
        """测试买入资金不足"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=5000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 买入 - 应该失败
        result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)

        assert result['success'] is False
        assert '现金不足' in result['message']
        assert result['trade_id'] is None

        # 验证现金没有变化
        assert trading_account.cash == 5000.0

        # 验证没有持仓
        position = trading_account.get_position("000001.SZSE")
        assert position is None

    def test_sell_success(self):
        """测试卖出成功"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 先买入一些股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 然后卖出
        sell_result = trading_account.sell("000001.SZSE", 500, 16.0, 0.0003)

        assert sell_result['success'] is True
        assert sell_result['trade_id'] is not None
        assert '卖出 000001.SZSE 500股 @ ¥16.00' in sell_result['message']

        expected_proceeds = 500 * 16.0 * (1 - 0.0003)  # 7997.6
        assert abs(sell_result['proceeds'] - expected_proceeds) < 0.01
        assert abs(sell_result['remaining_cash'] - (50000.0 - 15004.5 + expected_proceeds)) < 0.01

        # 验证现金增加
        expected_cash = 50000.0 - 15004.5 + expected_proceeds  # 42993.1
        assert abs(trading_account.cash - expected_cash) < 0.01

        # 验证持仓减少
        position = trading_account.get_position("000001.SZSE")
        assert position is not None
        assert position.quantity == 500  # 从1000股减到500股

    def test_sell_insufficient_position(self):
        """测试卖出持仓不足"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 尝试卖出不存在的股票 - 应该失败
        sell_result = trading_account.sell("000001.SZSE", 1000, 15.0, 0.0003)

        assert sell_result['success'] is False
        assert '持仓不足' in sell_result['message']
        assert sell_result['trade_id'] is None

        # 验证现金没有变化
        assert trading_account.cash == 50000.0

    def test_sell_partial_position(self):
        """测试卖出部分持仓"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 买入一些股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 卖出部分持仓
        sell_result = trading_account.sell("000001.SZSE", 300, 16.0, 0.0003)

        assert sell_result['success'] is True
        assert sell_result['trade_id'] is not None

        # 验证剩余持仓
        position = trading_account.get_position("000001.SZSE")
        assert position is not None
        assert position.quantity == 700  # 1000 - 300

    def test_sell_all_position(self):
        """测试清仓"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 买入一些股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 卖出全部持仓
        sell_result = trading_account.sell("000001.SZSE", 1000, 16.0, 0.0003)

        assert sell_result['success'] is True
        assert sell_result['trade_id'] is not None

        # 验证持仓被清除
        position = trading_account.get_position("000001.SZSE")
        assert position is None

    def test_get_total_assets(self):
        """测试获取总资产"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=80000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 初始总资产 = 现金 + 持仓市值
        initial_assets = trading_account.get_total_assets()
        assert initial_assets == 80000.0  # 只有现金，没有持仓

        # 买入股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 更新股价影响市值
        self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.0,
            current_price=16.0  # 股价上涨到16.0
        )

        # 重新创建交易账户以获取最新持仓
        trading_account = TradingAccount(self.test_account_id)

        # 总资产 = 现金 + 持仓市值 = (80000-15004.5) + (1000 * 16.0)
        expected_assets = (80000.0 - 15004.5) + (1000 * 16.0)
        actual_assets = trading_account.get_total_assets()
        assert abs(actual_assets - expected_assets) < 0.01

    def test_get_pnl(self):
        """测试获取盈亏"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=100000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 初始盈亏
        pnl = trading_account.get_pnl()
        assert pnl['unrealized_pnl'] == 0
        assert pnl['realized_pnl'] == 0
        assert pnl['total_pnl'] == 0
        assert pnl['return_pct'] == 0

        # 买入股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 更新股价产生浮动盈亏
        self.db.update_position(
            account_id=self.test_account_id,
            symbol="000001.SZSE",
            quantity=1000,
            avg_cost=15.0,
            current_price=16.0  # 股价上涨到16.0
        )

        # 重新创建交易账户
        trading_account = TradingAccount(self.test_account_id)

        # 验证浮动盈亏
        pnl = trading_account.get_pnl()
        assert pnl['unrealized_pnl'] == 1000.0  # (16.0 - 15.0) * 1000
        # 实现盈亏需要实际的买卖交易记录
        assert pnl['total_pnl'] == pnl['unrealized_pnl'] + pnl['realized_pnl']

    def test_get_position(self):
        """测试获取单个持仓"""
        # 创建基础账户
        base_account = AccountModel(
            account_id=self.test_account_id,
            account_name="Test Trading Account",
            initial_capital=100000.0,
            cash=50000.0
        )
        self.db.create_account(base_account)

        trading_account = TradingAccount(self.test_account_id)

        # 初始时没有持仓
        position = trading_account.get_position("000001.SZSE")
        assert position is None

        # 买入股票
        buy_result = trading_account.buy("000001.SZSE", 1000, 15.0, "平安银行", 0.0003)
        assert buy_result['success'] is True

        # 获取持仓
        position = trading_account.get_position("000001.SZSE")
        assert position is not None
        assert position.symbol == "000001.SZSE"
        assert position.quantity == 1000
        assert position.avg_cost == 15.0