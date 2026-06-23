"""账户系统统一异常"""


class AccountError(Exception):
    """账户系统基础异常"""
    pass


class InsufficientCashError(AccountError):
    """现金不足"""
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(
            f"现金不足: 需要 {required:.2f}, 可用 {available:.2f}"
        )


class InsufficientPositionError(AccountError):
    """持仓不足"""
    def __init__(self, symbol: str, required: int, available: int):
        self.symbol = symbol
        self.required = required
        self.available = available
        super().__init__(
            f"持仓不足 [{symbol}]: 需要 {required}, 可用 {available}"
        )


class AccountNotFoundError(AccountError):
    """账户不存在"""
    def __init__(self, account_id: str):
        self.account_id = account_id
        super().__init__(f"账户不存在: {account_id}")


class DuplicateTradeError(AccountError):
    """重复交易 ID"""
    pass


class TransactionError(AccountError):
    """事务执行失败（自动回滚）"""
    pass