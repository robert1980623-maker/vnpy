"""
财务数据使用示例

演示如何使用财务数据模块
"""

from datetime import datetime
from vnpy.alpha.dataset import FundamentalData, FinancialIndicator
from vnpy.alpha.dataset.fundamental import create_fundamental_data, create_indicator


def example_basic_fundamental():
    """基础财务数据示例"""
    print("=" * 60)
    print("基础财务数据示例")
    print("=" * 60)
    
    # 创建财务指标
    indicator = FinancialIndicator(
        vt_symbol="000001.SZ",
        report_date="2024-03-31",
        pe_ratio=5.2,
        pb_ratio=0.6,
        dividend_yield=4.5,
        roe=8.5,
        revenue_growth=3.2,
        net_profit_growth=5.1,
        gross_margin=25.3,
        net_margin=18.7,
        debt_to_asset=65.2
    )
    
    print(f"股票代码：{indicator.vt_symbol}")
    print(f"报告期：{indicator.report_date}")
    print(f"市盈率 (PE): {indicator.pe_ratio}")
    print(f"市净率 (PB): {indicator.pb_ratio}")
    print(f"股息率：{indicator.dividend_yield}%")
    print(f"净资产收益率 (ROE): {indicator.roe}%")
    print()


def example_fundamental_data_manager():
    """财务数据管理器示例"""
    print("=" * 60)
    print("财务数据管理器示例")
    print("=" * 60)
    
    # 创建财务数据管理器
    fd = create_fundamental_data()
    
    # 添加多只股票的财务数据
    stocks_data = [
        {
            "vt_symbol": "000001.SZ",
            "report_date": "2024-03-31",
            "pe_ratio": 5.2,
            "pb_ratio": 0.6,
            "dividend_yield": 4.5,
            "roe": 8.5,
            "revenue_growth": 3.2,
            "net_profit_growth": 5.1
        },
        {
            "vt_symbol": "600036.SH",
            "report_date": "2024-03-31",
            "pe_ratio": 6.8,
            "pb_ratio": 0.7,
            "dividend_yield": 5.2,
            "roe": 11.2,
            "revenue_growth": 5.5,
            "net_profit_growth": 8.3
        },
        {
            "vt_symbol": "600519.SH",
            "report_date": "2024-03-31",
            "pe_ratio": 28.5,
            "pb_ratio": 8.2,
            "dividend_yield": 1.5,
            "roe": 32.5,
            "revenue_growth": 18.5,
            "net_profit_growth": 22.3
        },
        {
            "vt_symbol": "000858.SZ",
            "report_date": "2024-03-31",
            "pe_ratio": 15.3,
            "pb_ratio": 3.5,
            "dividend_yield": 2.8,
            "roe": 25.8,
            "revenue_growth": 12.5,
            "net_profit_growth": 15.8
        },
        {
            "vt_symbol": "300750.SZ",
            "report_date": "2024-03-31",
            "pe_ratio": 35.2,
            "pb_ratio": 6.8,
            "dividend_yield": 0.8,
            "roe": 22.5,
            "revenue_growth": 35.8,
            "net_profit_growth": 42.5
        }
    ]
    
    # 批量添加数据
    for data in stocks_data:
        indicator = create_indicator(**data)
        fd.add(indicator)
    
    print(f"股票数量：{fd.get_stock_count()}")
    print(f"股票代码：{fd.get_symbols()}")
    print()
    
    # 获取单只股票的最新数据
    indicator = fd.get_latest("600519.SH")
    if indicator:
        print(f"贵州茅台最新数据:")
        print(f"  PE: {indicator.pe_ratio}")
        print(f"  ROE: {indicator.roe}%")
        print(f"  营收增长：{indicator.revenue_growth}%")
        print()


def example_filter_stocks():
    """筛选股票示例"""
    print("=" * 60)
    print("筛选股票示例")
    print("=" * 60)
    
    # 使用上面的数据
    fd = create_fundamental_data()
    
    stocks_data = [
        {"vt_symbol": "000001.SZ", "report_date": "2024-03-31", "pe_ratio": 5.2, "pb_ratio": 0.6, "dividend_yield": 4.5, "roe": 8.5},
        {"vt_symbol": "600036.SH", "report_date": "2024-03-31", "pe_ratio": 6.8, "pb_ratio": 0.7, "dividend_yield": 5.2, "roe": 11.2},
        {"vt_symbol": "600519.SH", "report_date": "2024-03-31", "pe_ratio": 28.5, "pb_ratio": 8.2, "dividend_yield": 1.5, "roe": 32.5},
        {"vt_symbol": "000858.SZ", "report_date": "2024-03-31", "pe_ratio": 15.3, "pb_ratio": 3.5, "dividend_yield": 2.8, "roe": 25.8},
        {"vt_symbol": "300750.SZ", "report_date": "2024-03-31", "pe_ratio": 35.2, "pb_ratio": 6.8, "dividend_yield": 0.8, "roe": 22.5}
    ]
    
    for data in stocks_data:
        fd.add(create_indicator(**data))
    
    # 筛选低估值股票（PE < 10）
    low_pe = fd.filter_by_field("pe_ratio", max_value=10)
    print(f"低估值股票 (PE<10): {low_pe}")
    
    # 筛选高 ROE 股票（ROE > 20%）
    high_roe = fd.filter_by_field("roe", min_value=20)
    print(f"高 ROE 股票 (ROE>20%): {high_roe}")
    
    # 筛选高分红股票（股息率 > 3%）
    high_dividend = fd.filter_by_field("dividend_yield", min_value=3)
    print(f"高分红股票 (股息率>3%): {high_dividend}")
    print()
    
    # 多条件筛选
    conditions = {
        "pe_ratio": {"max": 20},
        "pb_ratio": {"max": 5},
        "roe": {"min": 15}
    }
    
    selected = fd.filter_by_multiple(conditions)
    print(f"多条件筛选 (PE<20, PB<5, ROE>15%): {selected}")
    print()


def example_statistics():
    """统计信息示例"""
    print("=" * 60)
    print("统计信息示例")
    print("=" * 60)
    
    # 使用上面的数据
    fd = create_fundamental_data()
    
    stocks_data = [
        {"vt_symbol": "000001.SZ", "report_date": "2024-03-31", "pe_ratio": 5.2, "roe": 8.5},
        {"vt_symbol": "600036.SH", "report_date": "2024-03-31", "pe_ratio": 6.8, "roe": 11.2},
        {"vt_symbol": "600519.SH", "report_date": "2024-03-31", "pe_ratio": 28.5, "roe": 32.5},
        {"vt_symbol": "000858.SZ", "report_date": "2024-03-31", "pe_ratio": 15.3, "roe": 25.8},
        {"vt_symbol": "300750.SZ", "report_date": "2024-03-31", "pe_ratio": 35.2, "roe": 22.5}
    ]
    
    for data in stocks_data:
        fd.add(create_indicator(**data))
    
    # 计算 PE 统计
    pe_stats = fd.get_statistics("pe_ratio")
    print("PE 统计信息:")
    print(f"  数量：{pe_stats.get('count', 0)}")
    print(f"  最小值：{pe_stats.get('min', 0):.2f}")
    print(f"  最大值：{pe_stats.get('max', 0):.2f}")
    print(f"  平均值：{pe_stats.get('mean', 0):.2f}")
    print(f"  中位数：{pe_stats.get('median', 0):.2f}")
    print()
    
    # 计算 ROE 统计
    roe_stats = fd.get_statistics("roe")
    print("ROE 统计信息:")
    print(f"  最小值：{roe_stats.get('min', 0):.2f}%")
    print(f"  最大值：{roe_stats.get('max', 0):.2f}%")
    print(f"  平均值：{roe_stats.get('mean', 0):.2f}%")
    print()


def example_save_and_load():
    """保存和加载示例"""
    print("=" * 60)
    print("保存和加载示例")
    print("=" * 60)
    
    # 创建并保存数据
    fd = create_fundamental_data()
    
    stocks_data = [
        {"vt_symbol": "000001.SZ", "report_date": "2024-03-31", "pe_ratio": 5.2, "roe": 8.5},
        {"vt_symbol": "600036.SH", "report_date": "2024-03-31", "pe_ratio": 6.8, "roe": 11.2}
    ]
    
    for data in stocks_data:
        fd.add(create_indicator(**data))
    
    # 保存到文件
    fd.save("./lab/data/fundamental.json")
    print("数据已保存到 ./lab/data/fundamental.json")
    
    # 从文件加载
    fd_loaded = FundamentalData.load("./lab/data/fundamental.json")
    print(f"加载的股票数量：{fd_loaded.get_stock_count()}")
    print(f"股票代码：{fd_loaded.get_symbols()}")
    print()


if __name__ == "__main__":
    # 运行所有示例
    example_basic_fundamental()
    example_fundamental_data_manager()
    example_filter_stocks()
    example_statistics()
    example_save_and_load()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
