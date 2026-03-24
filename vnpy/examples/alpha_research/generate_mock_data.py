"""
生成模拟数据进行回测测试

用于验证回测系统功能
"""

import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json


def generate_trading_dates(start: datetime, end: datetime) -> list:
    """生成交易日期（排除周末）"""
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current += timedelta(days=1)
    return dates


def generate_bars(vt_symbol: str, start_price: float, dates: list) -> pd.DataFrame:
    """
    生成模拟 K 线数据
    
    Args:
        vt_symbol: 股票代码
        start_price: 起始价格
        dates: 交易日期列表
        
    Returns:
        pd.DataFrame: K 线数据
    """
    random.seed(hash(vt_symbol) % 10000)  # 固定随机种子
    
    bars = []
    price = start_price
    
    for date in dates:
        # 随机涨跌 (-3% 到 +3%)
        change = random.uniform(-0.03, 0.03)
        close = price * (1 + change)
        
        # 生成 OHLC
        high = max(price, close) * (1 + random.uniform(0, 0.02))
        low = min(price, close) * (1 - random.uniform(0, 0.02))
        open_price = price
        
        # 成交量和成交额
        volume = random.randint(1000000, 50000000)
        turnover = volume * close
        
        bars.append({
            "vt_symbol": vt_symbol,
            "datetime": date,
            "open_price": round(open_price, 2),
            "high_price": round(high, 2),
            "low_price": round(low, 2),
            "close_price": round(close, 2),
            "volume": volume,
            "turnover": round(turnover, 2)
        })
        
        price = close
    
    return pd.DataFrame(bars)


def generate_fundamental(vt_symbol: str) -> dict:
    """
    生成模拟财务数据
    
    Args:
        vt_symbol: 股票代码
        
    Returns:
        dict: 财务指标
    """
    random.seed(hash(vt_symbol + "fundamental") % 10000)
    
    # 根据代码生成不同风格的股票
    is_value = hash(vt_symbol) % 2 == 0
    
    if is_value:
        # 价值股：低 PE，高股息
        pe = random.uniform(5, 15)
        pb = random.uniform(0.5, 2)
        dividend = random.uniform(3, 6)
        roe = random.uniform(8, 15)
    else:
        # 成长股：高 PE，高增长
        pe = random.uniform(20, 50)
        pb = random.uniform(2, 8)
        dividend = random.uniform(0.5, 2)
        roe = random.uniform(15, 30)
    
    return {
        "vt_symbol": vt_symbol,
        "report_date": "2024-03-31",
        "pe_ratio": round(pe, 2),
        "pb_ratio": round(pb, 2),
        "dividend_yield": round(dividend, 2),
        "roe": round(roe, 2),
        "revenue_growth": round(random.uniform(5, 40), 2),
        "net_profit_growth": round(random.uniform(5, 50), 2),
        "gross_margin": round(random.uniform(20, 60), 2),
        "net_margin": round(random.uniform(10, 30), 2),
        "debt_to_asset": round(random.uniform(30, 70), 2)
    }


def save_data(data_dir: str, bars_dict: dict, fundamental_dict: dict) -> None:
    """保存数据到文件"""
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    
    # 保存 K 线数据
    bars_path = data_path / "bars"
    bars_path.mkdir(exist_ok=True)
    
    for vt_symbol, df in bars_dict.items():
        filepath = bars_path / f"{vt_symbol.replace('.', '_')}.csv"
        df.to_csv(filepath, index=False)
    
    # 保存财务数据
    fundamental_path = data_path / "fundamental.json"
    with open(fundamental_path, 'w', encoding='utf-8') as f:
        json.dump(fundamental_dict, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到 {data_dir}")


def main():
    """生成模拟数据"""
    print("=" * 60)
    print("生成模拟数据")
    print("=" * 60)
    
    # 设置参数
    data_dir = "./data/mock"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    # 股票池（10 只股票，5 只价值股 + 5 只成长股）
    stock_pool = [
        # 价值股
        "600000.SH",  # 浦发银行
        "600036.SH",  # 招商银行
        "601398.SH",  # 工商银行
        "600519.SH",  # 贵州茅台
        "000651.SZ",  # 格力电器
        # 成长股
        "300750.SZ",  # 宁德时代
        "002594.SZ",  # 比亚迪
        "000858.SZ",  # 五粮液
        "601888.SH",  # 中国中免
        "300059.SZ",  # 东方财富
    ]
    
    # 生成交易日期
    dates = generate_trading_dates(start_date, end_date)
    print(f"\n交易日期：{len(dates)} 天")
    
    # 生成 K 线数据
    print("\n生成 K 线数据...")
    bars_dict = {}
    
    base_prices = {
        "600000.SH": 15.0,
        "600036.SH": 35.0,
        "601398.SH": 5.0,
        "600519.SH": 1700.0,
        "000651.SZ": 40.0,
        "300750.SZ": 200.0,
        "002594.SZ": 250.0,
        "000858.SZ": 150.0,
        "601888.SH": 100.0,
        "300059.SZ": 15.0,
    }
    
    for vt_symbol in stock_pool:
        start_price = base_prices.get(vt_symbol, 20.0)
        df = generate_bars(vt_symbol, start_price, dates)
        bars_dict[vt_symbol] = df
        print(f"  ✓ {vt_symbol}: {len(df)} 条 K 线，价格区间 [{df['close_price'].min():.2f}, {df['close_price'].max():.2f}]")
    
    # 生成财务数据
    print("\n生成财务数据...")
    fundamental_dict = {}
    
    for vt_symbol in stock_pool:
        fundamental = generate_fundamental(vt_symbol)
        fundamental_dict[vt_symbol] = {fundamental["report_date"]: fundamental}
        
        style = "价值" if fundamental["pe_ratio"] < 20 else "成长"
        print(f"  ✓ {vt_symbol}: PE={fundamental['pe_ratio']:.1f}, ROE={fundamental['roe']:.1f}%, 股息率={fundamental['dividend_yield']:.1f}% [{style}]")
    
    # 保存数据
    print("\n保存数据...")
    save_data(data_dir, bars_dict, fundamental_dict)
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print(f"  - 股票数量：{len(stock_pool)}")
    print(f"  - 交易天数：{len(dates)}")
    print(f"  - 数据目录：{data_dir}")
    print("=" * 60)
    
    print("\n下一步：运行回测")
    print(f"  python run_backtest.py --data {data_dir}")


if __name__ == "__main__":
    main()
