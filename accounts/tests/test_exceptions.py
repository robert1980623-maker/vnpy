"""账户系统异常测试"""
import pytest
from accounts.exceptions import (
    AccountError,
    InsufficientCashError,
    InsufficientPositionError,
    AccountNotFoundError,
    DuplicateTradeError,
    TransactionError
)


class TestAccountError:
    """测试基础账户异常"""

    def test_account_error_base_class(self):
        """测试基础账户异常类"""
        error = AccountError("Generic account error")
        assert str(error) == "Generic account error"

        # 测试继承关系
        assert issubclass(AccountError, Exception)


class TestInsufficientCashError:
    """测试现金不足异常"""

    def test_insufficient_cash_error_creation(self):
        """测试现金不足异常创建"""
        error = InsufficientCashError(required=1000.0, available=500.0)

        assert error.required == 1000.0
        assert error.available == 500.0
        assert str(error) == "现金不足: 需要 1000.00, 可用 500.00"

    def test_insufficient_cash_error_formatting(self):
        """测试现金不足异常的数字格式"""
        error = InsufficientCashError(required=123.456, available=78.901)

        expected_message = "现金不足: 需要 123.46, 可用 78.90"
        assert str(error) == expected_message


class TestInsufficientPositionError:
    """测试持仓不足异常"""

    def test_insufficient_position_error_creation(self):
        """测试持仓不足异常创建"""
        error = InsufficientPositionError(
            symbol="000001.SZSE",
            required=1000,
            available=500
        )

        assert error.symbol == "000001.SZSE"
        assert error.required == 1000
        assert error.available == 500
        assert str(error) == "持仓不足 [000001.SZSE]: 需要 1000, 可用 500"

    def test_insufficient_position_error_different_values(self):
        """测试不同数值的持仓不足异常"""
        error = InsufficientPositionError(
            symbol="600000.SSE",
            required=100,
            available=0
        )

        expected_message = "持仓不足 [600000.SSE]: 需要 100, 可用 0"
        assert str(error) == expected_message


class TestAccountNotFoundError:
    """测试账户不存在异常"""

    def test_account_not_found_error_creation(self):
        """测试账户不存在异常创建"""
        error = AccountNotFoundError(account_id="nonexistent_account")

        assert error.account_id == "nonexistent_account"
        assert str(error) == "账户不存在: nonexistent_account"

    def test_account_not_found_error_different_ids(self):
        """测试不同账户ID的异常"""
        test_cases = [
            "A001",
            "test_account",
            "long_account_identifier_123"
        ]

        for account_id in test_cases:
            error = AccountNotFoundError(account_id=account_id)
            expected = f"账户不存在: {account_id}"
            assert str(error) == expected


class TestDuplicateTradeError:
    """测试重复交易异常"""

    def test_duplicate_trade_error_creation(self):
        """测试重复交易异常创建"""
        error = DuplicateTradeError("Trade ID T123456 already exists")

        assert str(error) == "Trade ID T123456 already exists"

    def test_duplicate_trade_error_empty_message(self):
        """测试空消息的重复交易异常"""
        error = DuplicateTradeError()

        assert str(error) == ""


class TestTransactionError:
    """测试事务异常"""

    def test_transaction_error_creation(self):
        """测试事务异常创建"""
        error = TransactionError("Database connection lost during transaction")

        assert str(error) == "Database connection lost during transaction"

    def test_transaction_error_without_message(self):
        """测试无消息的事务异常"""
        error = TransactionError()

        assert str(error) == ""