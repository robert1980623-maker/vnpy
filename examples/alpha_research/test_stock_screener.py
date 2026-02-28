"""
选股策略综合测试

测试完整的选股回测流程
"""

from datetime import datetime
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    create_preset_strategy,
)
from vnpy.alpha.dataset import FinancialIndicator


def test_value_strategy():
    """测试价值股策略"""
    print("=" * 60)
    print("测试价值股策略")
    print("=" * 60)
    
    # 创建价值股策略
    strategy = ValueStockStrategy(
        max_pe=20,
        max_pb=3,
        min_dividend_yield=2,
        min_roe=10,
        max_positions=30
    )
    
    print("策略参数:")
    print(f"  最大 PE: {strategy.max_pe}")
    print(f"  最大 PB: {strategy.max_pb}")
    print(f"  最小股息率：{strategy.min_dividend_yield}%")
    print(f"  最小 ROE: {strategy.min_roe}%")
    print(f"  最大持仓：{strategy.max_positions}")
    print()
    
    # 模拟筛选
    stock_pool = ["000001.SZ", "600036.SH", "600519.SH", "000858.SZ", "300750.SZ"]
    
    fundamental_data = {
        "000001.SZ": FinancialIndicator(
            vt_symbol="000001.SZ",
            report_date="2024-03-31",
            pe_ratio=5.2,
            pb_ratio=0.6,
            dividend_yield=4.5,
            roe=8.5
        ),
        "600036.SH": FinancialIndicator(
            vt_symbol="600036.SH",
            report_date="2024-03-31",
            pe_ratio=6.8,
            pb_ratio=0.7,
            dividend_yield=5.2,
            roe=11.2
        ),
        "600519.SH": FinancialIndicator(
            vt_symbol="600519.SH",
            report_date="2024-03-31",
            pe_ratio=28.5,
            pb_ratio=8.2,
            dividend_yield=1.5,
            roe=32.5
        )
    }
    
    selected = strategy.screen_stocks(
        stock_pool=stock_pool,
        fundamental_data=fundamental_data,
        current_date=datetime(2024, 6, 1)
    )
    
    print(f"筛选结果：{selected}")
    print("✓ 价值股策略测试完成")
    print()


def test_growth_strategy():
    """测试成长股策略"""
    print("=" * 60)
    print("测试成长股策略")
    print("=" * 60)
    
    # 创建成长股策略
    strategy = GrowthStockStrategy(
        min_revenue_growth=25,
        min_profit_growth=30,
        min_roe=15,
        max_pe=40,
        max_positions=20
    )
    
    print("策略参数:")
    print(f"  最小营收增长：{strategy.min_revenue_growth}%")
    print(f"  最小利润增长：{strategy.min_profit_growth}%")
    print(f"  最小 ROE: {strategy.min_roe}%")
    print(f"  最大 PE: {strategy.max_pe}")
    print(f"  最大持仓：{strategy.max_positions}")
    print()
    
    # 模拟筛选
    stock_pool = ["000001.SZ", "600036.SH", "600519.SH", "000858.SZ", "300750.SZ"]
    
    fundamental_data = {
        "000001.SZ": FinancialIndicator(
            vt_symbol="000001.SZ",
            report_date="2024-03-31",
            pe_ratio=5.2,
            revenue_growth=3.2,
            net_profit_growth=5.1,
            roe=8.5
        ),
        "300750.SZ": FinancialIndicator(
            vt_symbol="300750.SZ",
            report_date="2024-03-31",
            pe_ratio=35.2,
            revenue_growth=35.8,
            net_profit_growth=42.5,
            roe=22.5
        )
    }
    
    selected = strategy.screen_stocks(
        stock_pool=stock_pool,
        fundamental_data=fundamental_data,
        current_date=datetime(2024, 6, 1)
    )
    
    print(f"筛选结果：{selected}")
    print("✓ 成长股策略测试完成")
    print()


def test_preset_strategies():
    """测试预设策略"""
    print("=" * 60)
    print("测试预设策略")
    print("=" * 60)
    
    from vnpy.alpha.strategy.preset_strategies import get_strategy_names
    
    strategy_names = get_strategy_names()
    print(f"可用策略：{strategy_names}")
    print()
    
    for name in strategy_names:
        strategy = create_preset_strategy(name)
        params = strategy.get_parameters()
        
        print(f"{name}:")
        print(f"  最大持仓：{params['max_positions']}")
        print(f"  调仓周期：{params['rebalance_days']} 天")
        print()


def test_stock_pool_integration():
    """测试股票池集成"""
    print("=" * 60)
    print("测试股票池集成")
    print("=" * 60)
    
    from vnpy.alpha.dataset import IndexStockPool
    from vnpy.alpha.dataset.fundamental import FundamentalData
    
    # 创建股票池
    pool = IndexStockPool("000300.SH")
    components = ["000001.SZ", "600036.SH", "600519.SH", "000858.SZ", "300750.SZ"]
    pool.update_components(components)
    
    print(f"股票池：{pool.name}")
    print(f"成分股：{pool.get_stocks()}")
    print()
    
    # 创建财务数据
    fd = FundamentalData()
    
    for symbol in components:
        indicator = FinancialIndicator(
            vt_symbol=symbol,
            report_date="2024-03-31",
            pe_ratio=15.0,
            pb_ratio=2.0,
            roe=15.0,
            dividend_yield=2.5
        )
        fd.add(indicator)
    
    print(f"财务数据覆盖：{fd.get_stock_count()} 只股票")
    print("✓ 股票池和财务数据集成完成")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("选股策略综合测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_value_strategy()
    test_growth_strategy()
    test_preset_strategies()
    test_stock_pool_integration()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
    print("\n提示：实际回测需要真实的市场数据和财务数据")
    print("请使用数据下载脚本下载数据后再运行回测")
    print()
