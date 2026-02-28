"""
Alpha 策略模块
"""

from .stock_screener_strategy import (
    StockScreenerStrategy,
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy,
    create_strategy,
)

from .preset_strategies import (
    get_value_strategy,
    get_growth_strategy,
    get_quality_strategy,
    get_dividend_strategy,
    get_balanced_strategy,
    create_preset_strategy,
    PRESET_STRATEGIES,
    get_strategy_names,
)

from .cross_sectional_engine import (
    CrossSectionalEngine,
    create_cross_sectional_engine,
)

# IndustryRotationStrategy 需要 vnpy 完整安装
# from .industry_rotation import (
#     IndustryRotationStrategy,
# )

__all__ = [
    # Base Strategy
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
    "get_strategy_names",
    
    # Backtesting
    "CrossSectionalEngine",
    "create_cross_sectional_engine",
    
    # Industry Rotation (需要 vnpy 完整安装)
    # "IndustryRotationStrategy",
]
