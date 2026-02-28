"""
选股策略基类

提供选股策略的统一接口和基础功能：
- 定期调仓
- 仓位管理
- 股票筛选
- 绩效跟踪
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json


class StockScreenerStrategy(ABC):
    """
    选股策略基类
    
    所有选股策略应继承此类并实现筛选逻辑
    """
    
    def __init__(
        self,
        name: str = "stock_screener",
        max_positions: int = 30,
        position_size: float = 0.03,
        rebalance_days: int = 20
    ):
        """
        初始化选股策略
        
        Args:
            name: 策略名称
            max_positions: 最大持仓数量
            position_size: 单只股票仓位比例（默认 3%）
            rebalance_days: 调仓周期（交易日）
        """
        self.name = name
        self.max_positions = max_positions
        self.position_size = position_size
        self.rebalance_days = rebalance_days
        
        # 状态跟踪
        self._current_positions: List[str] = []  # 当前持仓
        self._target_positions: List[str] = []  # 目标持仓
        self._last_rebalance_date: Optional[datetime] = None
        self._days_since_rebalance: int = 0
        
        # 参数（子类可覆盖）
        self.parameters: Dict[str, Any] = {}
    
    @abstractmethod
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选股票（子类必须实现）
        
        Args:
            stock_pool: 可选股票池
            fundamental_data: 财务数据字典 {vt_symbol: FinancialIndicator}
            current_date: 当前日期
            
        Returns:
            List[str]: 筛选出的股票代码列表
        """
        pass
    
    def should_rebalance(self, current_date: datetime) -> bool:
        """
        判断是否需要调仓
        
        Args:
            current_date: 当前日期
            
        Returns:
            bool: 是否需要调仓
        """
        if self._last_rebalance_date is None:
            return True
        
        days_diff = (current_date - self._last_rebalance_date).days
        return days_diff >= self.rebalance_days
    
    def update_positions(
        self,
        new_positions: List[str],
        current_date: datetime
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        更新持仓
        
        Args:
            new_positions: 新的目标持仓
            current_date: 当前日期
            
        Returns:
            Tuple[List[str], List[str], List[str]]: (买入列表，卖出列表，保持列表)
        """
        old_positions = set(self._current_positions)
        new_positions_set = set(new_positions[:self.max_positions])
        
        # 计算交易列表
        to_buy = list(new_positions_set - old_positions)
        to_sell = list(old_positions - new_positions_set)
        to_keep = list(old_positions & new_positions_set)
        
        # 更新状态
        self._target_positions = list(new_positions_set)
        self._current_positions = list(new_positions_set)
        self._last_rebalance_date = current_date
        self._days_since_rebalance = 0
        
        return to_buy, to_sell, to_keep
    
    def increment_days(self, days: int = 1) -> None:
        """
        增加交易日计数
        
        Args:
            days: 增加的交易日数
        """
        self._days_since_rebalance += days
    
    def get_position_info(self) -> Dict:
        """
        获取持仓信息
        
        Returns:
            Dict: 持仓信息字典
        """
        return {
            "current_positions": self._current_positions,
            "target_positions": self._target_positions,
            "position_count": len(self._current_positions),
            "max_positions": self.max_positions,
            "last_rebalance": self._last_rebalance_date.isoformat() if self._last_rebalance_date else None,
            "days_since_rebalance": self._days_since_rebalance
        }
    
    def set_parameters(self, **kwargs) -> None:
        """
        设置策略参数
        
        Args:
            **kwargs: 参数键值对
        """
        self.parameters.update(kwargs)
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        获取策略参数
        
        Returns:
            Dict[str, Any]: 参数字典
        """
        return {
            "name": self.name,
            "max_positions": self.max_positions,
            "position_size": self.position_size,
            "rebalance_days": self.rebalance_days,
            **self.parameters
        }
    
    def to_dict(self) -> Dict:
        """
        转换为字典
        
        Returns:
            Dict: 策略字典表示
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "parameters": self.get_parameters(),
            "positions": self.get_position_info()
        }


class ValueStockStrategy(StockScreenerStrategy):
    """
    价值股选股策略
    
    基于估值指标筛选低估值、高分红的股票
    """
    
    def __init__(
        self,
        max_pe: float = 20,
        max_pb: float = 3,
        min_dividend_yield: float = 2,
        min_roe: float = 10,
        name: str = "value_stock",
        **kwargs
    ):
        """
        初始化价值股策略
        
        Args:
            max_pe: 最大市盈率
            max_pb: 最大市净率
            min_dividend_yield: 最小股息率 (%)
            min_roe: 最小 ROE (%)
            name: 策略名称
            **kwargs: 其他基类参数
        """
        super().__init__(name=name, **kwargs)
        
        self.max_pe = max_pe
        self.max_pb = max_pb
        self.min_dividend_yield = min_dividend_yield
        self.min_roe = min_roe
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选价值股
        
        筛选条件：
        - PE <= max_pe
        - PB <= max_pb
        - 股息率 >= min_dividend_yield
        - ROE >= min_roe
        """
        selected = []
        
        for vt_symbol in stock_pool:
            if vt_symbol not in fundamental_data:
                continue
            
            indicator = fundamental_data[vt_symbol]
            
            # 检查估值指标
            pe = getattr(indicator, 'pe_ratio', None)
            pb = getattr(indicator, 'pb_ratio', None)
            dividend = getattr(indicator, 'dividend_yield', None)
            roe = getattr(indicator, 'roe', None)
            
            if pe is None or pb is None or dividend is None or roe is None:
                continue
            
            # 应用筛选条件
            if pe <= 0 or pe > self.max_pe:
                continue
            if pb <= 0 or pb > self.max_pb:
                continue
            if dividend < self.min_dividend_yield:
                continue
            if roe < self.min_roe:
                continue
            
            selected.append(vt_symbol)
        
        # 按 PE 排序，选择最低的一批
        selected_with_pe = [
            (sym, fundamental_data[sym].pe_ratio)
            for sym in selected
        ]
        selected_with_pe.sort(key=lambda x: x[1])
        
        return [sym for sym, _ in selected_with_pe[:self.max_positions]]


class GrowthStockStrategy(StockScreenerStrategy):
    """
    成长股选股策略
    
    基于成长指标筛选高增长的股票
    """
    
    def __init__(
        self,
        min_revenue_growth: float = 20,
        min_profit_growth: float = 25,
        min_roe: float = 15,
        max_pe: float = 50,
        name: str = "growth_stock",
        **kwargs
    ):
        """
        初始化成长股策略
        
        Args:
            min_revenue_growth: 最小营收增长率 (%)
            min_profit_growth: 最小净利润增长率 (%)
            min_roe: 最小 ROE (%)
            max_pe: 最大市盈率
            name: 策略名称
            **kwargs: 其他基类参数
        """
        super().__init__(name=name, **kwargs)
        
        self.min_revenue_growth = min_revenue_growth
        self.min_profit_growth = min_profit_growth
        self.min_roe = min_roe
        self.max_pe = max_pe
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选成长股
        
        筛选条件：
        - 营收增长率 >= min_revenue_growth
        - 净利润增长率 >= min_profit_growth
        - ROE >= min_roe
        - PE <= max_pe
        """
        selected = []
        
        for vt_symbol in stock_pool:
            if vt_symbol not in fundamental_data:
                continue
            
            indicator = fundamental_data[vt_symbol]
            
            rev_growth = getattr(indicator, 'revenue_growth', None)
            profit_growth = getattr(indicator, 'net_profit_growth', None)
            roe = getattr(indicator, 'roe', None)
            pe = getattr(indicator, 'pe_ratio', None)
            
            if any(x is None for x in [rev_growth, profit_growth, roe, pe]):
                continue
            
            if rev_growth < self.min_revenue_growth:
                continue
            if profit_growth < self.min_profit_growth:
                continue
            if roe < self.min_roe:
                continue
            if pe <= 0 or pe > self.max_pe:
                continue
            
            selected.append(vt_symbol)
        
        # 按净利润增长率排序
        selected_with_growth = [
            (sym, fundamental_data[sym].net_profit_growth)
            for sym in selected
        ]
        selected_with_growth.sort(key=lambda x: x[1], reverse=True)
        
        return [sym for sym, _ in selected_with_growth[:self.max_positions]]


class QualityStockStrategy(StockScreenerStrategy):
    """
    质量股选股策略
    
    基于盈利能力筛选高质量股票
    """
    
    def __init__(
        self,
        min_roe: float = 15,
        min_gross_margin: float = 30,
        min_net_margin: float = 10,
        max_debt_ratio: float = 50,
        name: str = "quality_stock",
        **kwargs
    ):
        """
        初始化质量股策略
        
        Args:
            min_roe: 最小 ROE (%)
            min_gross_margin: 最小毛利率 (%)
            min_net_margin: 最小净利率 (%)
            max_debt_ratio: 最大资产负债率 (%)
            name: 策略名称
            **kwargs: 其他基类参数
        """
        super().__init__(name=name, **kwargs)
        
        self.min_roe = min_roe
        self.min_gross_margin = min_gross_margin
        self.min_net_margin = min_net_margin
        self.max_debt_ratio = max_debt_ratio
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选质量股
        
        筛选条件：
        - ROE >= min_roe
        - 毛利率 >= min_gross_margin
        - 净利率 >= min_net_margin
        - 资产负债率 <= max_debt_ratio
        """
        selected = []
        
        for vt_symbol in stock_pool:
            if vt_symbol not in fundamental_data:
                continue
            
            indicator = fundamental_data[vt_symbol]
            
            roe = getattr(indicator, 'roe', None)
            gross_margin = getattr(indicator, 'gross_margin', None)
            net_margin = getattr(indicator, 'net_margin', None)
            debt_ratio = getattr(indicator, 'debt_to_asset', None)
            
            if any(x is None for x in [roe, gross_margin, net_margin, debt_ratio]):
                continue
            
            if roe < self.min_roe:
                continue
            if gross_margin < self.min_gross_margin:
                continue
            if net_margin < self.min_net_margin:
                continue
            if debt_ratio > self.max_debt_ratio:
                continue
            
            selected.append(vt_symbol)
        
        # 按 ROE 排序
        selected_with_roe = [
            (sym, fundamental_data[sym].roe)
            for sym in selected
        ]
        selected_with_roe.sort(key=lambda x: x[1], reverse=True)
        
        return [sym for sym, _ in selected_with_roe[:self.max_positions]]


class DividendStockStrategy(StockScreenerStrategy):
    """
    高股息选股策略
    
    基于股息率筛选高分红股票
    """
    
    def __init__(
        self,
        min_dividend_yield: float = 4,
        min_payout_years: int = 3,
        max_payout_ratio: float = 80,
        min_roe: float = 8,
        name: str = "dividend_stock",
        **kwargs
    ):
        """
        初始化高股息策略
        
        Args:
            min_dividend_yield: 最小股息率 (%)
            min_payout_years: 最小连续分红年数
            max_payout_ratio: 最大分红比例 (%)
            min_roe: 最小 ROE (%)
            name: 策略名称
            **kwargs: 其他基类参数
        """
        super().__init__(name=name, **kwargs)
        
        self.min_dividend_yield = min_dividend_yield
        self.min_payout_years = min_payout_years
        self.max_payout_ratio = max_payout_ratio
        self.min_roe = min_roe
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选高股息股
        
        筛选条件：
        - 股息率 >= min_dividend_yield
        - ROE >= min_roe
        - PE > 0 (排除亏损股)
        """
        selected = []
        
        for vt_symbol in stock_pool:
            if vt_symbol not in fundamental_data:
                continue
            
            indicator = fundamental_data[vt_symbol]
            
            dividend = getattr(indicator, 'dividend_yield', None)
            roe = getattr(indicator, 'roe', None)
            pe = getattr(indicator, 'pe_ratio', None)
            
            if any(x is None for x in [dividend, roe, pe]):
                continue
            
            if dividend < self.min_dividend_yield:
                continue
            if roe < self.min_roe:
                continue
            if pe <= 0:
                continue
            
            selected.append(vt_symbol)
        
        # 按股息率排序
        selected_with_div = [
            (sym, fundamental_data[sym].dividend_yield)
            for sym in selected
        ]
        selected_with_div.sort(key=lambda x: x[1], reverse=True)
        
        return [sym for sym, _ in selected_with_div[:self.max_positions]]


def create_strategy(strategy_type: str, **kwargs) -> StockScreenerStrategy:
    """
    工厂函数：创建选股策略
    
    Args:
        strategy_type: 策略类型 ("value", "growth", "quality", "dividend")
        **kwargs: 策略参数
        
    Returns:
        StockScreenerStrategy: 策略实例
    """
    strategies = {
        "value": ValueStockStrategy,
        "growth": GrowthStockStrategy,
        "quality": QualityStockStrategy,
        "dividend": DividendStockStrategy,
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return strategies[strategy_type](**kwargs)
