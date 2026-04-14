#!/usr/bin/env python3
"""
CSV → Parquet ETL（健壮版）
把 akshare/bars/*.csv 转换到 lab/data/daily/*.parquet
自动跳过格式错误的行
"""
import pandas as pd
from pathlib import Path
import sys

SOURCE_DIR = Path("/Users/rowang/projects/vnpy/examples/alpha_research/data/akshare/bars")
TARGET_DIR = Path("/Users/rowang/projects/vnpy/lab/test_engine/daily")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# 预期的标准列
EXPECTED_COLS = ["symbol", "date", "open", "high", "low", "close", "volume"]

def convert_csv_to_parquet(csv_path: Path) -> bool:
    """转换单个 CSV → Parquet，跳过格式错误的行"""
    try:
        # 读取时跳过格式错误的行
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        
        if df.empty:
            return False
        
        # 标准化列名（统一小写）
        df.columns = [c.lower().strip() for c in df.columns]
        
        # 只保留有 symbol+date+close 的行
        symbol_col = None
        for col in df.columns:
            if 'symbol' in col or col in ['code', 'ts_code']:
                symbol_col = col
                break
        
        if symbol_col and symbol_col != 'symbol':
            df = df.rename(columns={symbol_col: 'symbol'})
        
        # 只保留有用列
        valid_cols = [c for c in df.columns if c in EXPECTED_COLS]
        if len(valid_cols) < 4:
            return False
        df = df[valid_cols].dropna(subset=['symbol', 'close'])
        
        # 生成输出文件名
        symbol = df['symbol'].iloc[0].replace('.', '_').replace('/', '_') if len(df) > 0 else csv_path.stem
        parquet_path = TARGET_DIR / f"{symbol}.parquet"
        
        df.to_parquet(parquet_path, index=False)
        return True
    except Exception as e:
        return False

def main():
    csv_files = list(SOURCE_DIR.glob("*.csv"))
    print(f"发现 {len(csv_files)} 个 CSV 文件")
    print(f"目标目录: {TARGET_DIR}")
    
    success = 0
    failed = 0
    
    for csv_file in csv_files:
        if convert_csv_to_parquet(csv_file):
            success += 1
        else:
            failed += 1
        
        if (success + failed) % 500 == 0:
            print(f"  进度: {success + failed}/{len(csv_files)}")
    
    print(f"\n✅ 完成: {success} 成功, {failed} 失败")
    
    # 验证
    parquet_files = list(TARGET_DIR.glob("*.parquet"))
    print(f"📁 Parquet 文件数: {len(parquet_files)}")
    
    if parquet_files:
        import os
        total_size = sum(os.path.getsize(p) for p in parquet_files)
        print(f"💾 总大小: {total_size / 1024 / 1024:.1f} MB")
    
    return 0 if failed < success else 1

if __name__ == "__main__":
    sys.exit(main())
