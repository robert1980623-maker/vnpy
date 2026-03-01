"""
股票池管理示例

演示如何使用 StockPool 类管理指数成分股和自定义股票池
"""

from datetime import datetime, timedelta
from vnpy.alpha.dataset import StockPool, create_pool


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("股票池管理基础示例")
    print("=" * 60)
    
    # 创建股票池实例
    pool = create_pool("./data/pool")
    
    # 查看预定义的指数
    print("\n📊 支持的指数成分股:")
    for name, info in StockPool.INDEX_MAP.items():
        print(f"  - {name}: {info['name']} ({info['code']})")
    
    # 创建自定义股票池
    print("\n📁 创建自定义股票池...")
    my_stocks = [
        "000001.SZSE",  # 平安银行
        "000002.SZSE",  # 万科 A
        "600000.SSE",   # 浦发银行
        "600036.SSE",   # 招商银行
        "000858.SZSE",  # 五粮液
    ]
    pool.create_custom_pool("my_bluechip", my_stocks)
    
    # 获取自定义股票池
    stocks = pool.get_custom_pool("my_bluechip")
    print(f"\n✅ 'my_bluechip' 股票池包含 {len(stocks)} 只股票:")
    for s in stocks:
        print(f"  - {s}")
    
    # 添加股票到股票池
    print("\n➕ 添加股票到股票池...")
    pool.add_to_pool("my_bluechip", ["601318.SSE"])  # 中国平安
    stocks = pool.get_custom_pool("my_bluechip")
    print(f"现在包含 {len(stocks)} 只股票")
    
    # 列出所有股票池
    print("\n📋 所有自定义股票池:")
    for name in pool.list_pools():
        print(f"  - {name}")


def example_index_components():
    """指数成分股示例"""
    print("\n" + "=" * 60)
    print("指数成分股示例")
    print("=" * 60)
    
    pool = create_pool("./data/pool")
    
    # 模拟保存成分股数据（实际使用时应该从数据源下载）
    print("\n💾 模拟保存沪深 300 成分股数据...")
    
    # 模拟数据：不同日期的成分股
    components_data = {
        "2024-01-01": [f"00000{i}.SZSE" for i in range(1, 51)] + 
                      [f"60000{i}.SSE" for i in range(1, 51)],
        "2024-06-01": [f"00000{i}.SZSE" for i in range(1, 52)] + 
                      [f"60000{i}.SSE" for i in range(1, 50)],
        "2024-12-01": [f"00000{i}.SZSE" for i in range(1, 53)] + 
                      [f"60000{i}.SSE" for i in range(1, 49)],
    }
    
    pool.save_index_components("csi300", components_data)
    
    # 获取指定日期的成分股
    print("\n📅 获取 2024-06-01 的沪深 300 成分股...")
    components = pool.get_index_components("csi300", datetime(2024, 6, 1))
    print(f"包含 {len(components)} 只股票")
    print(f"前 10 只：{components[:10]}")


def example_filter():
    """股票过滤示例"""
    print("\n" + "=" * 60)
    print("股票过滤示例")
    print("=" * 60)
    
    import polars as pl
    
    pool = create_pool("./data/pool")
    
    # 创建模拟数据
    print("\n📊 创建模拟行情数据...")
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    
    data = {
        "symbol": [
            "000001.SZSE",  # 正常股票
            "000002.SZSE",  # 正常股票
            "ST0003.SZSE",  # ST 股票
            "600001.SSE",   # 停牌股票（成交量为 0）
            "600002.SSE",   # 低流动性股票
        ],
        "date": [date_str] * 5,
        "close": [10.5, 20.3, 5.2, 15.8, 8.9],
        "volume": [1000000, 500000, 200000, 0, 10000],  # 600001 停牌
        "turnover": [10500000, 10150000, 1040000, 0, 89000],  # 600002 低流动性
    }
    
    df = pl.DataFrame(data)
    print(f"原始数据:\n{df}")
    
    # 测试股票池
    test_pool = ["000001.SZSE", "000002.SZSE", "ST0003.SZSE", "600001.SSE", "600002.SSE"]
    
    # 过滤股票
    print("\n🔍 应用过滤条件...")
    filtered = pool.filter_stocks(
        symbols=test_pool,
        df=df,
        exclude_st=True,           # 排除 ST
        exclude_suspended=True,    # 排除停牌
        min_turnover=100000        # 最小成交额 10 万
    )
    
    print(f"\n✅ 过滤后剩余 {len(filtered)} 只股票:")
    for s in filtered:
        print(f"  - {s}")


def example_universe():
    """多股票池合并示例"""
    print("\n" + "=" * 60)
    print("多股票池合并示例")
    print("=" * 60)
    
    pool = create_pool("./data/pool")
    
    # 创建多个自定义股票池
    pool.create_custom_pool("tech", ["000001.SZSE", "000002.SZSE", "600001.SSE"])
    pool.create_custom_pool("finance", ["600001.SSE", "600002.SSE", "000003.SZSE"])
    
    # 获取并集
    print("\n🔗 获取 'tech' 和 'finance' 的并集...")
    universe = pool.get_universe(["tech", "finance"])
    print(f"并集包含 {len(universe)} 只股票：{universe}")
    
    # 获取交集
    print("\n🔀 获取 'tech' 和 'finance' 的交集...")
    intersection = pool.get_intersection(["tech", "finance"])
    print(f"交集包含 {len(intersection)} 只股票：{intersection}")


def example_download_components():
    """下载指数成分股示例（需要 RQData）"""
    print("\n" + "=" * 60)
    print("下载指数成分股示例")
    print("=" * 60)
    
    print("""
    要下载真实的指数成分股数据，可以使用以下代码：
    
    ```python
    from datetime import datetime
    import rqdatac as rq
    from vnpy.alpha.dataset import StockPool
    
    # 初始化股票池
    pool = StockPool("./data/pool")
    
    # 配置 RQData
    rq.init(user="your_username", pwd="your_password")
    
    # 下载沪深 300 成分股历史数据
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    data = rq.index_components("000300.XSHG", start_date=start_date, end_date=end_date)
    
    # 转换格式
    components = {}
    for dt, symbols in data.items():
        date_str = dt.strftime("%Y-%m-%d")
        # 转换代码格式：XSHG -> SSE, XSHE -> SZSE
        vt_symbols = [
            s.replace("XSHG", "SSE").replace("XSHE", "SZSE")
            for s in symbols
        ]
        components[date_str] = vt_symbols
    
    # 保存到股票池
    pool.save_index_components("csi300", components)
    ```
    """)


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_index_components()
    example_filter()
    example_universe()
    example_download_components()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)
