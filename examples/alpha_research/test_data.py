"""
数据测试 - 验证生成的模拟数据

不依赖 vnpy 完整环境，只测试数据本身
"""

from pathlib import Path
import polars as pl

# 数据路径
DATA_PATH = Path("./data")
DAILY_PATH = DATA_PATH / "daily"

print("=" * 60)
print("数据验证测试")
print("=" * 60)

# 1. 检查文件
print("\n📊 检查数据文件...")
files = list(DAILY_PATH.glob("*.parquet"))
print(f"  找到 {len(files)} 个文件")

# 2. 读取并验证每个文件
print("\n📊 验证数据质量...")

total_records = 0
symbols = []

for file_path in files:
    try:
        df = pl.read_parquet(file_path)
        vt_symbol = df["vt_symbol"][0]
        symbols.append(vt_symbol)
        total_records += len(df)
        
        # 验证必需列
        required_cols = ["datetime", "open", "high", "low", "close", "volume", "turnover"]
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            print(f"  ❌ {vt_symbol}: 缺少列 {missing}")
        else:
            # 验证数据范围
            start_date = df["datetime"].min()
            end_date = df["datetime"].max()
            
            # 验证价格有效性
            invalid_prices = df.filter(
                (pl.col("open") <= 0) | 
                (pl.col("high") <= 0) | 
                (pl.col("low") <= 0) | 
                (pl.col("close") <= 0)
            ).height
            
            if invalid_prices > 0:
                print(f"  ⚠️  {vt_symbol}: {invalid_prices} 条记录价格无效")
            else:
                print(f"  ✅ {vt_symbol}: {len(df)}条记录 ({start_date.date()} - {end_date.date()})")
    
    except Exception as e:
        print(f"  ❌ {file_path.name}: 读取失败 - {e}")

# 3. 汇总
print("\n" + "=" * 60)
print("数据汇总")
print("=" * 60)
print(f"  股票数量：{len(symbols)}")
print(f"  总记录数：{total_records:,}")
print(f"  平均每只股票：{total_records // len(symbols) if symbols else 0:,} 条")

# 4. 显示示例数据
print("\n📊 示例数据:")
if files:
    df = pl.read_parquet(files[0])
    print(df.head(10))

print("\n✅ 数据验证完成！")
