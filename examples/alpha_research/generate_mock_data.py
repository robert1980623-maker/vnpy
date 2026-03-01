"""
生成模拟股票数据用于测试

不需要网络连接，生成符合真实格式的模拟数据
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

import polars as pl
import numpy as np

# 数据保存路径
DATA_PATH = Path("./data")
DAILY_PATH = DATA_PATH / "daily"
DAILY_PATH.mkdir(parents=True, exist_ok=True)

# 测试股票池
TEST_SYMBOLS = [
    ("000001", "SSE"), ("000002", "SSE"), ("000003", "SSE"), ("000004", "SSE"), ("000005", "SSE"),
    ("000006", "SSE"), ("000007", "SSE"), ("000008", "SSE"), ("000009", "SSE"), ("000010", "SSE"),
]

# 时间范围（最近 1 年）
END_DATE = datetime(2026, 2, 28)
START_DATE = datetime(2025, 1, 1)


def generate_stock_data(symbol: str, exchange: str) -> pl.DataFrame:
    """
    生成模拟股票数据
    
    模拟真实股票的价格走势：
    - 随机游走
    - 波动率 2-3%
    - 成交量随机
    """
    # 生成交易日（去除周末）
    dates = []
    current = START_DATE
    while current <= END_DATE:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current += timedelta(days=1)
    
    # 初始价格 10-100 元随机
    initial_price = random.uniform(10, 100)
    
    # 生成价格序列（随机游走）
    prices = [initial_price]
    for _ in range(len(dates) - 1):
        # 日收益率：均值 0，标准差 2%
        ret = random.gauss(0, 0.02)
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 1))  # 价格不低于 1 元
    
    # 生成 OHLCV 数据
    data = []
    for i, dt in enumerate(dates):
        close = prices[i]
        
        # 生成开盘、最高、最低
        daily_volatility = random.uniform(0.01, 0.03)
        open_price = close * (1 + random.gauss(0, daily_volatility * 0.5))
        high = max(open_price, close) * (1 + abs(random.gauss(0, daily_volatility)))
        low = min(open_price, close) * (1 - abs(random.gauss(0, daily_volatility)))
        
        # 生成成交量（100 万 -1 亿随机）
        volume = random.randint(1000000, 100000000)
        
        # 成交额 = 价格 * 成交量
        turnover = close * volume
        
        data.append({
            "datetime": dt,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
            "turnover": round(turnover, 2),
            "vt_symbol": f"{symbol}.{exchange}"
        })
    
    df = pl.DataFrame(data)
    return df


def main():
    """主函数"""
    print("=" * 60)
    print("生成模拟股票数据")
    print("=" * 60)
    print(f"数据保存路径：{DAILY_PATH.absolute()}")
    print(f"时间范围：{START_DATE.date()} - {END_DATE.date()}")
    print(f"股票数量：{len(TEST_SYMBOLS)}\n")
    
    for i, (symbol, exchange) in enumerate(TEST_SYMBOLS):
        vt_symbol = f"{symbol}.{exchange}"
        print(f"[{i+1}/{len(TEST_SYMBOLS)}] 生成 {vt_symbol}...", end="")
        
        # 生成数据
        df = generate_stock_data(symbol, exchange)
        
        # 保存
        file_path = DAILY_PATH / f"{vt_symbol}.parquet"
        df.write_parquet(file_path)
        
        print(f" ✅ {len(df)} 条记录")
    
    print("\n" + "=" * 60)
    print("✅ 数据生成完成！")
    print("=" * 60)
    print(f"总记录数：{len(TEST_SYMBOLS) * len(dates) if (dates := []) else 'N/A'}")
    print(f"数据路径：{DAILY_PATH.absolute()}")
    print("=" * 60)
    
    # 显示示例
    print("\n📊 示例数据（前 5 行）:")
    sample_file = list(DAILY_PATH.glob("*.parquet"))[0]
    df = pl.read_parquet(sample_file)
    print(df.head())


if __name__ == "__main__":
    main()
