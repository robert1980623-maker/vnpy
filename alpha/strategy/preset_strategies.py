"""
预设选股策略

提供常用的选股策略配置，开箱即用
"""

from .stock_screener_strategy import (
    StockScreenerStrategy,
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy,
)
from typing import Dict, List, Any


def get_value_strategy(
    max_pe: float = 15,
    max_pb: float = 2,
    min_dividend_yield: float = 3,
    min_roe: float = 12,
    max_positions: int = 30,
    rebalance_days: int = 20,
    **kwargs
) -> ValueStockStrategy:
    """
    深度价值策略
    
    特点：
    - 低估值（PE<15, PB<2）
    - 高分红（股息率>3%）
    - 盈利能力尚可（ROE>12%）
    - 适合保守型投资者
    
    Args:
        max_pe: 最大市盈率
        max_pb: 最大市净率
        min_dividend_yield: 最小股息率
        min_roe: 最小 ROE
        max_positions: 最大持仓数
        rebalance_days: 调仓周期
        
    Returns:
        ValueStockStrategy: 策略实例
    """
    return ValueStockStrategy(
        max_pe=max_pe,
        max_pb=max_pb,
        min_dividend_yield=min_dividend_yield,
        min_roe=min_roe,
        max_positions=max_positions,
        rebalance_days=rebalance_days,
        name=kwargs.pop('name', 'deep_value'),
        **kwargs
    )


def get_growth_strategy(
    min_revenue_growth: float = 25,
    min_profit_growth: float = 30,
    min_roe: float = 15,
    max_pe: float = 40,
    max_positions: int = 20,
    rebalance_days: int = 20,
    **kwargs
) -> GrowthStockStrategy:
    """
    高成长策略
    
    特点：
    - 高增长（营收增长>25%, 利润增长>30%）
    - 盈利能力强（ROE>15%）
    - 估值容忍度较高（PE<40）
    - 适合进取型投资者
    
    Args:
        min_revenue_growth: 最小营收增长率
        min_profit_growth: 最小净利润增长率
        min_roe: 最小 ROE
        max_pe: 最大市盈率
        max_positions: 最大持仓数
        rebalance_days: 调仓周期
        
    Returns:
        GrowthStockStrategy: 策略实例
    """
    return GrowthStockStrategy(
        min_revenue_growth=min_revenue_growth,
        min_profit_growth=min_profit_growth,
        min_roe=min_roe,
        max_pe=max_pe,
        max_positions=max_positions,
        rebalance_days=rebalance_days,
        name=kwargs.pop('name', 'high_growth'),
        **kwargs
    )


def get_quality_strategy(
    min_roe: float = 20,
    min_gross_margin: float = 40,
    min_net_margin: float = 15,
    max_debt_ratio: float = 40,
    max_positions: int = 25,
    rebalance_days: int = 30,
    **kwargs
) -> QualityStockStrategy:
    """
    高质量策略
    
    特点：
    - 超高盈利能力（ROE>20%, 毛利率>40%）
    - 财务稳健（负债率<40%）
    - 长期持有导向（调仓周期 30 天）
    - 适合稳健型投资者
    
    Args:
        min_roe: 最小 ROE
        min_gross_margin: 最小毛利率
        min_net_margin: 最小净利率
        max_debt_ratio: 最大资产负债率
        max_positions: 最大持仓数
        rebalance_days: 调仓周期
        
    Returns:
        QualityStockStrategy: 策略实例
    """
    return QualityStockStrategy(
        min_roe=min_roe,
        min_gross_margin=min_gross_margin,
        min_net_margin=min_net_margin,
        max_debt_ratio=max_debt_ratio,
        max_positions=max_positions,
        rebalance_days=rebalance_days,
        name=kwargs.pop('name', 'high_quality'),
        **kwargs
    )


def get_dividend_strategy(
    min_dividend_yield: float = 5,
    min_roe: float = 10,
    max_positions: int = 30,
    rebalance_days: int = 60,
    **kwargs
) -> DividendStockStrategy:
    """
    高股息策略
    
    特点：
    - 超高分红（股息率>5%）
    - 盈利稳定（ROE>10%）
    - 低频调仓（60 天）
    - 适合收益型投资者
    
    Args:
        min_dividend_yield: 最小股息率
        min_roe: 最小 ROE
        max_positions: 最大持仓数
        rebalance_days: 调仓周期
        
    Returns:
        DividendStockStrategy: 策略实例
    """
    return DividendStockStrategy(
        min_dividend_yield=min_dividend_yield,
        min_roe=min_roe,
        max_positions=max_positions,
        rebalance_days=rebalance_days,
        name=kwargs.pop('name', 'high_dividend'),
        **kwargs
    )


def get_balanced_strategy(
    max_pe: float = 20,
    min_roe: float = 15,
    min_revenue_growth: float = 15,
    max_positions: int = 30,
    rebalance_days: int = 20,
    **kwargs
) -> StockScreenerStrategy:
    """
    均衡策略
    
    特点：
    - 估值合理（PE<20）
    - 盈利良好（ROE>15%）
    - 适度增长（营收增长>15%）
    - 风险收益平衡
    - 适合大多数投资者
    
    Args:
        max_pe: 最大市盈率
        min_roe: 最小 ROE
        min_revenue_growth: 最小营收增长率
        max_positions: 最大持仓数
        rebalance_days: 调仓周期
        
    Returns:
        ValueStockStrategy: 策略实例（基于价值策略）
    """
    # 使用价值策略作为基础，平衡估值和成长
    return ValueStockStrategy(
        max_pe=max_pe,
        max_pb=3,
        min_dividend_yield=1.5,
        min_roe=min_roe,
        max_positions=max_positions,
        rebalance_days=rebalance_days,
        name=kwargs.pop('name', 'balanced'),
        **kwargs
    )


# 策略配置字典
PRESET_STRATEGIES: Dict[str, callable] = {
    "value": get_value_strategy,
    "growth": get_growth_strategy,
    "quality": get_quality_strategy,
    "dividend": get_dividend_strategy,
    "balanced": get_balanced_strategy,
}


def get_strategy_names() -> List[str]:
    """
    获取所有预设策略名称
    
    Returns:
        List[str]: 策略名称列表
    """
    return list(PRESET_STRATEGIES.keys())


def create_preset_strategy(
    name: str,
    **kwargs
) -> StockScreenerStrategy:
    """
    创建预设策略
    
    Args:
        name: 策略名称
        **kwargs: 策略参数（覆盖默认值）
        
    Returns:
        StockScreenerStrategy: 策略实例
        
    Raises:
        ValueError: 策略名称不存在
    """
    if name not in PRESET_STRATEGIES:
        raise ValueError(
            f"Unknown strategy: {name}. "
            f"Available: {get_strategy_names()}"
        )
    
    return PRESET_STRATEGIES[name](**kwargs)


def compare_strategies(
    stock_pool: List[str],
    fundamental_data: Dict[str, Any],
    current_date: Any = None
) -> Dict[str, List[str]]:
    """
    比较所有预设策略的选股结果
    
    Args:
        stock_pool: 股票池
        fundamental_data: 财务数据
        current_date: 当前日期
        
    Returns:
        Dict[str, List[str]]: {策略名：选中的股票列表}
    """
    from datetime import datetime
    
    if current_date is None:
        current_date = datetime.now()
    
    results = {}
    
    for name in PRESET_STRATEGIES:
        strategy = create_preset_strategy(name)
        selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
        results[name] = selected
    
    return results


def get_strategy_info(name: str) -> Dict[str, Any]:
    """
    获取策略详细信息
    
    Args:
        name: 策略名称
        
    Returns:
        Dict[str, Any]: 策略信息
    """
    strategy = create_preset_strategy(name)
    return strategy.get_parameters()


def list_strategies() -> None:
    """打印所有策略信息"""
    print("可用预设策略:\n")
    
    for name in PRESET_STRATEGIES:
        info = get_strategy_info(name)
        print(f"  {name}:")
        print(f"    - 最大持仓：{info['max_positions']}")
        print(f"    - 调仓周期：{info['rebalance_days']} 天")
        print(f"    - 单票仓位：{info['position_size']*100:.1f}%")
        print()
