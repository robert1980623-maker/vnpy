"""
Alpha 研究模块

提供股票量化研究的全套工具：
- 数据集管理（股票池、财务数据）
- 策略开发（选股策略、预设策略）
- 回测引擎（截面回测）
"""

from .dataset import (
    StockPool,
    IndexStockPool,
    CustomStockPool,
    FundamentalData,
    FinancialIndicator,
)

from .strategy import (
    StockScreenerStrategy,
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy,
    create_strategy,
)

from .strategy.preset_strategies import (
    get_value_strategy,
    get_growth_strategy,
    get_quality_strategy,
    get_dividend_strategy,
    get_balanced_strategy,
    create_preset_strategy,
    PRESET_STRATEGIES,
)

from .strategy.cross_sectional_engine import (
    CrossSectionalEngine,
    create_cross_sectional_engine,
)

__all__ = [
    # Dataset
    "StockPool",
    "IndexStockPool",
    "CustomStockPool",
    "FundamentalData",
    "FinancialIndicator",
    
    # Strategy
    "StockScreenerStrategy",
    "ValueStockStrategy",
    "GrowthStockStrategy",
    "QualityStockStrategy",
    "DividendStockStrategy",
    "create_strategy",
    
    # Preset Strategies
    "get_value_strategy",
    "get_growth_strategy",
    "get_quality_strategy",
    "get_dividend_strategy",
    "get_balanced_strategy",
    "create_preset_strategy",
    "PRESET_STRATEGIES",
    
    # Backtesting
    "CrossSectionalEngine",
    "create_cross_sectional_engine",
]
