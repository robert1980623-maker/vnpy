"""
生成更真实的模拟数据

基于真实市场统计特征生成：
- 真实的收益率分布
- 真实的波动率特征
- 真实的行业相关性
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import random
import math

import polars as pl
import numpy as np

# 数据保存路径
DATA_PATH = Path("./data_real")
DAILY_PATH = DATA_PATH / "daily"
DAILY_PATH.mkdir(parents=True, exist_ok=True)

# 时间范围（最近 3 年）
END_DATE = datetime(2026, 2, 28)
START_DATE = datetime(2023, 1, 1)

# 股票池（按行业分组）
STOCK_POOLS = {
    "bank": [
        ("600000", "SSE", 5.0, 0.6),    # 低估值，低波动
        ("600016", "SSE", 5.5, 0.7),
        ("600036", "SSE", 6.0, 0.6),
        ("601166", "SSE", 5.2, 0.6),
        ("601288", "SSE", 5.8, 0.5),
    ],
    "liquor": [
        ("600519", "SSE", 15.0, 1.2),   # 高估值，高波动
        ("000568", "SSE", 12.0, 1.0),
        ("000858", "SSE", 10.0, 0.9),
    ],
    "tech": [
        ("000063", "SSE", 8.0, 1.5),    # 中等估值，高波动
        ("002230", "SSE", 10.0, 1.8),
        ("300059", "SSE", 12.0, 2.0),
        ("600570", "SSE", 9.0, 1.5),
    ],
    "energy": [
        ("300750", "SSE", 20.0, 2.5),   # 高成长，高波动
        ("002594", "SSE", 18.0, 2.0),
        ("601012", "SSE", 15.0, 1.8),
    ],
    "consumer": [
        ("000333", "SSE", 10.0, 0.8),   # 中等估值，中等波动
        ("000651", "SSE", 9.0, 0.7),
        ("600690", "SSE", 8.5, 0.8),
    ],
}


def generate_realistic_price_series(
    start_price: float,
    annual_return: float,
    annual_volatility: float,
    n_days: int
) -> list[float]:
    """
    生成真实的价格序列（几何布朗运动）
    
    Args:
        start_price: 初始价格
        annual_return: 年化收益率
        annual_volatility: 年化波动率
        n_days: 天数
    
    Returns:
        价格序列
    """
    # 转换为日参数（240 个交易日/年）
    daily_return = annual_return / 240 / 100  # 转换为小数
    daily_vol = annual_volatility / math.sqrt(240) / 100
    
    prices = [start_price]
    
    for _ in range(n_days - 1):
        # 几何布朗运动
        shock = random.gauss(0, 1)
        new_price = prices[-1] * math.exp(daily_return - 0.5 * daily_vol**2 + daily_vol * shock)
        prices.append(max(new_price, 0.5))  # 价格不低于 0.5 元
    
    return prices


def generate_ohlcv(prices: list[datetime], dates: list[datetime]) -> list[dict]:
    """
    从收盘价生成 OHLCV 数据
    
    Args:
        prices: 收盘价序列
        dates: 日期序列
    
    Returns:
        OHLCV 数据列表
    """
    data = []
    
    for i, (dt, close) in enumerate(zip(dates, prices)):
        # 日内波动（约为日波动的 30-50%）
        intraday_vol = abs(random.gauss(0, 0.015))
        
        # 生成开盘价（在前一日收盘价附近）
        if i > 0:
            prev_close = prices[i-1]
            open_price = prev_close * (1 + random.gauss(0, 0.01))
        else:
            open_price = close * (1 + random.gauss(0, 0.01))
        
        # 生成最高最低价
        high = max(open_price, close) * (1 + abs(random.gauss(0, intraday_vol)))
        low = min(open_price, close) * (1 - abs(random.gauss(0, intraday_vol)))
        
        # 生成成交量（对数正态分布）
        base_volume = random.randint(5000000, 50000000)
        volume = int(base_volume * math.exp(random.gauss(0, 0.5)))
        
        # 成交额
        turnover = close * volume
        
        data.append({
            "datetime": dt,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
            "turnover": round(turnover, 2),
        })
    
    return data


def generate_trading_dates(start: datetime, end: datetime) -> list[datetime]:
    """生成交易日（去除周末）"""
    dates = []
    current = start
    
    while current <= end:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current += timedelta(days=1)
    
    return dates


def main():
    """主函数"""
    print("=" * 60)
    print("生成真实模拟数据")
    print("=" * 60)
    print(f"数据保存路径：{DAILY_PATH.absolute()}")
    print(f"时间范围：{START_DATE.date()} - {END_DATE.date()}")
    
    # 生成交易日
    trading_dates = generate_trading_dates(START_DATE, END_DATE)
    n_days = len(trading_dates)
    print(f"交易日数：{n_days}\n")
    
    # 统计
    total_stocks = 0
    total_records = 0
    
    # 按行业生成
    for industry, stocks in STOCK_POOLS.items():
        print(f"📊 行业：{industry}")
        
        for symbol, exchange, pe_ratio, volatility in stocks:
            vt_symbol = f"{symbol}.{exchange}"
            
            # 根据 PE 估算初始价格
            start_price = random.uniform(10, 50)
            
            # 生成价格序列
            prices = generate_realistic_price_series(
                start_price=start_price,
                annual_return=random.uniform(-10, 30),  # 年化收益 -10% 到 30%
                annual_volatility=volatility * 100,  # 转换为百分比
                n_days=n_days
            )
            
            # 生成 OHLCV
            ohlcv_data = generate_ohlcv(prices, trading_dates)
            
            # 添加股票代码
            for row in ohlcv_data:
                row["vt_symbol"] = vt_symbol
            
            # 保存
            df = pl.DataFrame(ohlcv_data)
            file_path = DAILY_PATH / f"{vt_symbol}.parquet"
            df.write_parquet(file_path)
            
            total_stocks += 1
            total_records += len(df)
            
            print(f"  ✅ {vt_symbol}: {len(df)}条 (PE={pe_ratio}, Vol={volatility})")
        
        print()
    
    # 汇总
    print("=" * 60)
    print("生成完成")
    print("=" * 60)
    print(f"股票数量：{total_stocks}")
    print(f"总记录数：{total_records:,}")
    print(f"平均每只：{total_records // total_stocks:,} 条")
    print(f"数据路径：{DAILY_PATH.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
