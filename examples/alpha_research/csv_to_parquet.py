#!/usr/bin/env python3
"""
将 AKShare CSV 日线数据转换为 AlphaLab Parquet 格式

支持两种 CSV 格式:
1. AKShare: symbol,date,open,high,low,close,volume
2. Tushare: ts_code,open,high,low,close,vol,amount,pct_chg,date
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import polars as pl
from vnpy.alpha.lab import AlphaLab
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange


def parse_csv_line(parts: list) -> dict | None:
    """解析 CSV 行，返回标准化数据"""
    if len(parts) < 6:
        return None
    
    # 尝试 Tushare 格式：ts_code,open,high,low,close,vol,amount,pct_chg,date (9 列)
    if len(parts) >= 9:
        try:
            date_str = parts[-1].strip()
            # Tushare 格式：最后一列是 8 位日期
            if len(date_str) == 8 and date_str.isdigit():
                symbol = parts[0].strip()
                open_p = float(parts[1])
                high = float(parts[2])
                low = float(parts[3])
                close = float(parts[4])
                volume = float(parts[5])
                if open_p > 0 and close > 0:
                    return {
                        'symbol': symbol,
                        'date': date_str,
                        'open': open_p,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    }
        except (ValueError, IndexError):
            pass
    
    # 尝试 AKShare 格式：symbol,date,open,high,low,close,volume (7 列)
    if len(parts) >= 7:
        try:
            date_str = parts[1].strip()
            # AKShare 格式：第二列是日期（可能是 YYYYMMDD 或 YYYYMMDD.0）
            if date_str and (date_str.isdigit() or (date_str.split('.')[0].isdigit() and len(date_str.split('.')[0]) == 8)):
                symbol = parts[0].strip()
                date_str = date_str.split('.')[0]  # 去除 .0
                open_p = float(parts[2])
                high = float(parts[3])
                low = float(parts[4])
                close = float(parts[5])
                volume = float(parts[6])
                if open_p > 0 and close > 0:
                    return {
                        'symbol': symbol,
                        'date': date_str,
                        'open': open_p,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    }
        except (ValueError, IndexError):
            pass
    
    return None


def csv_to_bars(csv_path: Path) -> list[BarData]:
    """读取 CSV 文件并返回 BarData 列表"""
    bars = []
    with open(csv_path, 'r') as f:
        header = f.readline()  # 跳过 header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            data = parse_csv_line(parts)
            if not data:
                continue
            
            try:
                dt = datetime.strptime(data['date'], '%Y%m%d')
                symbol = data['symbol']
                
                # Parse symbol
                if '.' in symbol:
                    code, market = symbol.split('.')
                    if market.upper() in ('SH', 'SSE'):
                        exchange = Exchange.SSE
                    else:
                        exchange = Exchange.SZSE
                else:
                    code = symbol
                    exchange = Exchange.SSE if code.startswith(('6', '9')) else Exchange.SZSE
                
                vt_symbol = f"{code}.{exchange.value}"
                
                bars.append(BarData(
                    symbol=code,
                    exchange=exchange,
                    datetime=dt,
                    interval=Interval.DAILY,
                    open_price=data['open'],
                    high_price=data['high'],
                    low_price=data['low'],
                    close_price=data['close'],
                    volume=data['volume'],
                    turnover=0,
                    open_interest=0,
                    gateway_name="AKShare"
                ))
            except (ValueError, IndexError) as e:
                continue
    
    return bars


def convert_all(csv_dir: str, lab_dir: str, start_date: str = None, end_date: str = None):
    csv_path = Path(csv_dir)
    if not csv_path.exists():
        print(f"❌ CSV 目录不存在: {csv_path}")
        return

    lab = AlphaLab(lab_dir)
    csv_files = list(csv_path.glob('*.csv'))
    print(f"📊 找到 {len(csv_files)} 个 CSV 文件")

    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_dt = None
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_dt = None

    total_bars = 0
    for i, f in enumerate(csv_files, 1):
        bars = csv_to_bars(f)
        if start_dt or end_dt:
            bars = [b for b in bars if
                    (not start_dt or b.datetime >= start_dt) and
                    (not end_dt or b.datetime <= end_dt)]
        if bars:
            lab.save_bar_data(bars)
            total_bars += len(bars)

        if i % 500 == 0 or i == len(csv_files):
            print(f"  [{i}/{len(csv_files)}] 已转换 {total_bars} 条数据")

    print(f"\n✅ 转换完成：{total_bars} 条日线数据")
    print(f"   输出目录：{lab.daily_path}")
    print(f"   Parquet 文件数：{len(list(lab.daily_path.glob('*.parquet')))}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-dir', default='./data/akshare/bars')
    parser.add_argument('--lab-dir', default='./lab/test')
    parser.add_argument('--start', default=None)
    parser.add_argument('--end', default=None)
    args = parser.parse_args()
    convert_all(args.csv_dir, args.lab_dir, args.start, args.end)
