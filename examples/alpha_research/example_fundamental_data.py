"""
财务数据模块使用示例

演示如何使用 FundamentalData 类管理财务指标和筛选股票
"""

from datetime import datetime
import polars as pl
from vnpy.alpha.dataset import FundamentalData, create_fundamental_data


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("财务数据基础示例")
    print("=" * 60)
    
    # 创建财务数据实例
    fd = create_fundamental_data("./data/fundamental")
    
    print("\n📊 可用的财务指标分类:")
    print(f"  估值指标：{fd.VALUATION_METRICS}")
    print(f"  盈利能力：{fd.PROFITABILITY_METRICS}")
    print(f"  成长能力：{fd.GROWTH_METRICS}")
    print(f"  杠杆水平：{fd.LEVERAGE_METRICS}")
    print(f"  运营效率：{fd.EFFICIENCY_METRICS}")


def example_calculate_metrics():
    """计算财务指标示例"""
    print("\n" + "=" * 60)
    print("财务指标计算示例")
    print("=" * 60)
    
    fd = FundamentalData()
    
    # 计算市盈率
    pe = fd.calculate_pe_ratio(price=25.5, eps_ttm=2.1)
    print(f"\n💰 市盈率计算:")
    print(f"  股价：25.5 元，EPS(TTM): 2.1 元")
    print(f"  PE = {pe}")
    
    # 计算市净率
    pb = fd.calculate_pb_ratio(price=25.5, bvps=15.3)
    print(f"\n📈 市净率计算:")
    print(f"  股价：25.5 元，每股净资产：15.3 元")
    print(f"  PB = {pb}")
    
    # 计算 ROE
    roe = fd.calculate_roe(net_profit=500000000, equity=3000000000)
    print(f"\n📊 ROE 计算:")
    print(f"  净利润：5 亿元，净资产：30 亿元")
    print(f"  ROE = {roe}%")
    
    # 计算增长率
    growth = fd.calculate_growth_rate(current_value=1200000000, previous_value=1000000000, periods=1)
    print(f"\n📈 增长率计算:")
    print(f"  本期：12 亿元，上期：10 亿元")
    print(f"  增长率 = {growth}%")


def example_filter_by_metrics():
    """财务指标过滤示例"""
    print("\n" + "=" * 60)
    print("财务指标过滤示例")
    print("=" * 60)
    
    fd = create_fundamental_data()
    
    # 创建模拟数据
    print("\n📊 创建模拟全市场财务数据...")
    data = {
        "symbol": [f"00000{i}.SZSE" for i in range(1, 21)],
        "date": ["2024-12-31"] * 20,
        "pe_ratio": [5, 8, 12, 15, 18, 22, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, -5, 10],
        "pb_ratio": [0.8, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 1.0, 1.5, 2.0, 2.5, 3.0, 0.5, 1.0, 1.5, 2.0, 2.5],
        "roe": [5, 8, 12, 15, 18, 20, 22, 25, 28, 30, 10, 12, 15, 18, 20, 5, 8, 12, 15, 18],
        "revenue_growth": [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 5, 10, 15, 20, 25, -5, 0, 5, 10, 15],
        "net_profit_growth": [-15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 8, 12, 16, 20, 24, -10, -5, 0, 5, 10],
        "debt_to_asset": [80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 50, 55, 60, 65, 70, 85, 90, 60, 55, 50],
        "dividend_yield": [5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5, 3, 2.5, 2, 1.5, 1, 6, 7, 3, 2.5, 2],
        "net_margin": [2, 5, 8, 10, 12, 15, 18, 20, 22, 25, 10, 12, 15, 18, 20, 3, 5, 8, 10, 12],
    }
    
    df = pl.DataFrame(data)
    print(f"原始数据：{len(df)} 只股票")
    print(df.select(["symbol", "pe_ratio", "pb_ratio", "roe", "revenue_growth"]))
    
    # 价值股筛选
    print("\n🔍 筛选价值股（低估值、高股息）...")
    value_stocks = fd.get_value_stocks(df, max_pe=20, max_pb=3, min_dividend_yield=2)
    print(f"✅ 价值股：{len(value_stocks)} 只")
    if not value_stocks.is_empty():
        print(value_stocks.select(["symbol", "pe_ratio", "pb_ratio", "dividend_yield"]))
    
    # 成长股筛选
    print("\n🚀 筛选成长股（高增长）...")
    growth_stocks = fd.get_growth_stocks(df, min_revenue_growth=20, min_net_profit_growth=25, min_roe=20)
    print(f"✅ 成长股：{len(growth_stocks)} 只")
    if not growth_stocks.is_empty():
        print(growth_stocks.select(["symbol", "revenue_growth", "net_profit_growth", "roe"]))
    
    # 优质股筛选
    print("\n⭐ 筛选优质股（高 ROE、稳定增长）...")
    quality_stocks = fd.get_quality_stocks(df, min_roe=15, min_revenue_growth=10, max_debt_to_asset=60, min_net_margin=10)
    print(f"✅ 优质股：{len(quality_stocks)} 只")
    if not quality_stocks.is_empty():
        print(quality_stocks.select(["symbol", "roe", "revenue_growth", "debt_to_asset", "net_margin"]))


def example_composite_score():
    """综合得分计算示例"""
    print("\n" + "=" * 60)
    print("综合得分计算示例")
    print("=" * 60)
    
    fd = create_fundamental_data()
    
    # 创建模拟数据
    data = {
        "symbol": [f"00000{i}.SZSE" for i in range(1, 11)],
        "date": ["2024-12-31"] * 10,
        "pe_ratio": [10, 15, 20, 25, 30, 12, 18, 22, 28, 35],
        "roe": [20, 18, 15, 12, 10, 22, 19, 16, 13, 11],
        "revenue_growth": [25, 20, 15, 10, 5, 30, 25, 20, 15, 10],
        "debt_to_asset": [40, 50, 60, 70, 80, 35, 45, 55, 65, 75],
    }
    
    df = pl.DataFrame(data)
    print("\n📊 原始数据:")
    print(df)
    
    # 定义因子权重和方向
    factors = {
        "pe_ratio": 0.3,        # 估值权重 30%
        "roe": 0.3,             # 盈利能力 30%
        "revenue_growth": 0.25, # 成长能力 25%
        "debt_to_asset": 0.15,  # 财务健康 15%
    }
    
    # 因子方向：1 表示越大越好，-1 表示越小越好
    direction = {
        "pe_ratio": -1,         # PE 越低越好
        "roe": 1,               # ROE 越高越好
        "revenue_growth": 1,    # 增长越高越好
        "debt_to_asset": -1,    # 负债率越低越好
    }
    
    # 计算综合得分
    print("\n🎯 计算综合得分...")
    scored_df = fd.calculate_composite_score(df, factors, direction)
    
    # 按得分排序
    ranked = scored_df.sort("composite_score", descending=True)
    print("\n📈 股票排名:")
    print(ranked.select(["symbol", "composite_score"]))
    
    # 选出前 3 名
    top3 = ranked.limit(3)
    print(f"\n🏆 推荐 TOP3: {top3['symbol'].to_list()}")


def example_custom_filter():
    """自定义条件过滤示例"""
    print("\n" + "=" * 60)
    print("自定义条件过滤示例")
    print("=" * 60)
    
    fd = create_fundamental_data()
    
    # 创建模拟数据
    data = {
        "symbol": [f"00000{i}.SZSE" for i in range(1, 21)],
        "date": ["2024-12-31"] * 20,
        "pe_ratio": [i * 3 for i in range(1, 21)],
        "pb_ratio": [i * 0.3 for i in range(1, 21)],
        "roe": [i * 1.5 for i in range(1, 21)],
        "revenue_growth": [(i - 10) * 2 for i in range(1, 21)],
        "net_profit_growth": [(i - 10) * 2.5 for i in range(1, 21)],
        "debt_to_asset": [80 - i * 2 for i in range(1, 21)],
        "dividend_yield": [i * 0.3 for i in range(1, 21)],
    }
    
    df = pl.DataFrame(data)
    
    # 自定义筛选条件：PEG 策略
    print("\n🔍 自定义筛选条件:")
    print("  - PE < 30")
    print("  - ROE > 15%")
    print("  - 净利润增长率 > 20%")
    print("  - 资产负债率 < 60%")
    
    filtered = fd.filter_by_metrics(
        df=df,
        max_pe=30,
        min_roe=15,
        min_net_profit_growth=20,
        max_debt_to_asset=60
    )
    
    print(f"\n✅ 筛选结果：{len(filtered)} 只股票")
    if not filtered.is_empty():
        print(filtered.select(["symbol", "pe_ratio", "roe", "net_profit_growth", "debt_to_asset"]))


def example_data_download():
    """数据下载示例"""
    print("\n" + "=" * 60)
    print("财务数据下载示例")
    print("=" * 60)
    
    print("""
    要下载真实的财务数据，可以使用以下代码：
    
    ### 使用 RQData 下载
    
    ```python
    import rqdatac as rq
    from vnpy.alpha.dataset import FundamentalData
    
    # 初始化
    rq.init(user="your_username", pwd="your_password")
    fd = FundamentalData("./data/fundamental")
    
    # 获取全市场财务指标
    date = "2024-12-31"
    
    # 下载估值指标
    valuation_data = rq.get_valuation(
        order_book_ids=None,  # 全市场
        start_date=date,
        end_date=date,
        fields=['pe_ratio', 'pb_ratio', 'ps_ratio', 'dividend_yield']
    )
    
    # 下载盈利能力
    profitability_data = rq.financial_indicator(
        order_book_ids=None,
        report_date=date,
        fields=['roe', 'roa', 'gross_margin', 'net_margin']
    )
    
    # 下载成长能力
    growth_data = rq.financial_indicator(
        order_book_ids=None,
        report_date=date,
        fields=['revenue_growth', 'net_profit_growth', 'eps_growth']
    )
    
    # 合并数据并保存
    # ... 数据合并逻辑 ...
    fd.save_data(merged_df, data_type="daily")
    ```
    
    ### 使用 Tushare 下载
    
    ```python
    import tushare as ts
    from vnpy.alpha.dataset import FundamentalData
    
    # 初始化
    ts.set_token("your_token")
    pro = ts.pro_api()
    fd = FundamentalData("./data/fundamental")
    
    # 获取每日估值
    daily_basic = pro.daily_basic(
        ts_code='',
        trade_date='20241231',
        fields='ts_code,pe,pb,ps,dv_ratio'
    )
    
    # 获取财务指标
    finance_data = pro.fina_indicator(
        ts_code='',
        start_date='20240101',
        end_date='20241231'
    )
    
    # 转换格式并保存
    # ... 数据转换逻辑 ...
    fd.save_data(converted_df, data_type="daily")
    ```
    """)


def example_combined_screening():
    """结合股票池和财务数据筛选"""
    print("\n" + "=" * 60)
    print("股票池 + 财务数据联合筛选")
    print("=" * 60)
    
    from vnpy.alpha.dataset import StockPool
    
    # 创建股票池和财务数据实例
    pool = StockPool("./data/pool")
    fd = FundamentalData("./data/fundamental")
    
    print("\n🎯 筛选策略：沪深 300 成分股中的优质成长股")
    print("  1. 从沪深 300 成分股开始")
    print("  2. 排除 ST、停牌股票")
    print("  3. 要求 ROE > 15%")
    print("  4. 要求营收增长 > 20%")
    print("  5. 要求 PE < 40")
    
    # 模拟成分股数据
    csi300 = [f"00000{i}.SZSE" for i in range(1, 51)]  # 模拟 50 只成分股
    
    # 模拟财务数据
    import random
    financial_data = {
        "symbol": csi300,
        "date": ["2024-12-31"] * len(csi300),
        "pe_ratio": [random.uniform(10, 60) for _ in csi300],
        "roe": [random.uniform(5, 30) for _ in csi300],
        "revenue_growth": [random.uniform(-10, 50) for _ in csi300],
    }
    df = pl.DataFrame(financial_data)
    
    # 过滤股票池
    print("\n📊 过滤股票池...")
    filtered_symbols = pool.filter_stocks(
        symbols=csi300,
        df=df,
        exclude_st=True,
        exclude_suspended=True
    )
    df_filtered = df.filter(pl.col("symbol").is_in(filtered_symbols))
    
    # 财务指标过滤
    print("📈 财务指标过滤...")
    final_stocks = fd.filter_by_metrics(
        df=df_filtered,
        min_roe=15,
        min_revenue_growth=20,
        max_pe=40
    )
    
    print(f"\n✅ 最终筛选结果：{len(final_stocks)} 只股票")
    if not final_stocks.is_empty():
        print(final_stocks.select(["symbol", "pe_ratio", "roe", "revenue_growth"]).sort("roe", descending=True))


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_calculate_metrics()
    example_filter_by_metrics()
    example_composite_score()
    example_custom_filter()
    example_data_download()
    example_combined_screening()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)
