"""
股票池使用示例

演示如何使用股票池管理功能
"""

from datetime import datetime
from vnpy.alpha.dataset import StockPool, IndexStockPool, CustomStockPool
from vnpy.alpha.dataset.pool import create_index_pool, create_custom_pool


def example_basic_stock_pool():
    """基础股票池示例"""
    print("=" * 60)
    print("基础股票池示例")
    print("=" * 60)
    
    # 创建股票池
    pool = StockPool(name="my_portfolio")
    
    # 添加股票
    pool.add("000001.SZ")
    pool.add("000002.SZ")
    pool.add(["600000.SH", "600036.SH", "000858.SZ"])
    
    print(f"股票池：{pool}")
    print(f"股票列表：{pool.get_stocks()}")
    print(f"股票数量：{pool.count()}")
    
    # 检查是否包含某只股票
    print(f"是否包含 000001.SZ: {pool.contains('000001.SZ')}")
    
    # 移除股票
    pool.remove("000002.SZ")
    print(f"移除 000002.SZ 后：{pool.get_stocks()}")
    
    # 保存股票池
    pool.save("./lab/data/my_portfolio.json")
    print("股票池已保存到 ./lab/data/my_portfolio.json")
    
    # 加载股票池
    loaded_pool = StockPool.load("./lab/data/my_portfolio.json")
    print(f"加载的股票池：{loaded_pool}")
    print()


def example_index_stock_pool():
    """指数成分股股票池示例"""
    print("=" * 60)
    print("指数成分股股票池示例")
    print("=" * 60)
    
    # 创建沪深 300 成分股股票池
    pool = IndexStockPool("000300.SH")
    
    print(f"指数信息：{pool.get_index_info()}")
    
    # 模拟更新成分股（实际应该从数据源获取）
    components = [
        "000001.SZ", "000002.SZ", "000063.SZ",
        "600000.SH", "600036.SH", "600519.SH",
        "000858.SZ", "002415.SZ", "300750.SZ"
    ]
    
    pool.update_components(components)
    print(f"成分股数量：{pool.count()}")
    print(f"成分股列表：{pool.get_stocks()}")
    print()


def example_custom_stock_pool():
    """自定义股票池示例"""
    print("=" * 60)
    print("自定义股票池示例")
    print("=" * 60)
    
    # 创建自定义股票池
    custom_pool = create_custom_pool("multi_strategy")
    
    # 创建子股票池
    value_pool = StockPool(name="value_stocks")
    value_pool.add(["600000.SH", "600036.SH", "600519.SH"])
    
    growth_pool = StockPool(name="growth_stocks")
    growth_pool.add(["000858.SZ", "002415.SZ", "300750.SZ"])
    
    # 添加子股票池
    custom_pool.add_sub_pool("value", value_pool)
    custom_pool.add_sub_pool("growth", growth_pool)
    
    print(f"子股票池：{custom_pool.get_sub_pool_names()}")
    
    # 计算并集
    union = custom_pool.union("value", "growth")
    print(f"并集（value + growth）: {union}")
    
    # 计算交集（这里没有交集）
    intersection = custom_pool.intersection("value", "growth")
    print(f"交集（value ∩ growth）: {intersection}")
    
    # 计算差集
    difference = custom_pool.difference("value", "growth")
    print(f"差集（value - growth）: {difference}")
    print()


def example_factory_functions():
    """工厂函数示例"""
    print("=" * 60)
    print("工厂函数示例")
    print("=" * 60)
    
    # 创建指数股票池
    index_pool = create_index_pool(
        "000905.SH",
        components=["000001.SZ", "000002.SZ", "600000.SH"]
    )
    print(f"中证 500 成分股：{index_pool.get_stocks()}")
    
    # 创建自定义股票池
    custom_pool = create_custom_pool("test_pool")
    print(f"自定义股票池：{custom_pool}")
    print()


def example_stock_pool_operations():
    """股票池运算示例"""
    print("=" * 60)
    print("股票池运算示例")
    print("=" * 60)
    
    # 创建两个股票池
    pool1 = StockPool(name="pool1")
    pool1.add(["000001.SZ", "000002.SZ", "000063.SZ", "600000.SH"])
    
    pool2 = StockPool(name="pool2")
    pool2.add(["000002.SZ", "000063.SZ", "600036.SH", "600519.SH"])
    
    print(f"池 1: {pool1.get_stocks()}")
    print(f"池 2: {pool2.get_stocks()}")
    
    # 并集
    union = set(pool1.get_stocks()) | set(pool2.get_stocks())
    print(f"并集：{sorted(list(union))}")
    
    # 交集
    intersection = set(pool1.get_stocks()) & set(pool2.get_stocks())
    print(f"交集：{sorted(list(intersection))}")
    
    # 差集
    difference = set(pool1.get_stocks()) - set(pool2.get_stocks())
    print(f"差集（池 1 - 池 2）: {sorted(list(difference))}")
    print()


if __name__ == "__main__":
    # 运行所有示例
    example_basic_stock_pool()
    example_index_stock_pool()
    example_custom_stock_pool()
    example_factory_functions()
    example_stock_pool_operations()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
