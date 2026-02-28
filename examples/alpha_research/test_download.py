"""
测试数据下载功能

验证缓存和多数据源功能
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from download_data_akshare import DataCache, get_stock_bars_akshare, get_fundamental_data


def test_cache():
    """测试缓存功能"""
    print("=" * 60)
    print("测试数据缓存功能")
    print("=" * 60)
    
    # 创建缓存
    cache = DataCache("./test_cache")
    
    # 测试保存和读取
    import pandas as pd
    from datetime import datetime
    
    df = pd.DataFrame({
        "vt_symbol": ["000001.SZ", "000001.SZ"],
        "datetime": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
        "open_price": [10.0, 10.5],
        "close_price": [10.5, 11.0]
    })
    
    # 保存
    cache.save_bars("000001.SZ", "20240101", "20241231", df)
    
    # 读取
    cached_df = cache.get_bars("000001.SZ", "20240101", "20241231")
    
    if cached_df is not None and len(cached_df) == 2:
        print("\n✓ 缓存测试通过")
    else:
        print("\n✗ 缓存测试失败")
    
    # 清理
    import shutil
    if Path("./test_cache").exists():
        shutil.rmtree("./test_cache")


def test_akshare_single():
    """测试单只股票下载"""
    print("\n" + "=" * 60)
    print("测试 AKShare 单只股票下载")
    print("=" * 60)
    
    vt_symbol = "000001.SZ"
    print(f"\n下载 {vt_symbol}...")
    
    bars = get_stock_bars_akshare(vt_symbol, "20240101", "20240131")
    
    if bars is not None and not bars.empty:
        print(f"✓ 下载成功：{len(bars)} 条 K 线")
        print(f"  价格区间：{bars['close_price'].min():.2f} - {bars['close_price'].max():.2f}")
    else:
        print("✗ 下载失败")
    
    # 测试财务数据
    print(f"\n获取 {vt_symbol} 财务数据...")
    fundamental = get_fundamental_data(vt_symbol)
    
    if fundamental:
        print(f"✓ 财务数据：PE={fundamental.get('pe_ratio', 'N/A')}")
    else:
        print("✗ 财务数据获取失败")


if __name__ == "__main__":
    test_cache()
    test_akshare_single()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
