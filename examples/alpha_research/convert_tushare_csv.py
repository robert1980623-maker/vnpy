#!/usr/bin/env python3
"""Convert Tushare-format CSVs (8-column with vt_symbol) to Parquet"""
import pandas as pd
import glob
import os

csv_dir = './data/akshare/bars/'
lab_dir = '/Users/rowang/projects/vnpy/lab/data/daily/'

csv_files = glob.glob(os.path.join(csv_dir, '*.csv'))
tushare_files = [f for f in csv_files if 'vt_symbol' in open(f).readline()]
print(f'Tushare CSVs: {len(tushare_files)}')

converted = 0
errors = 0
for f in tushare_files:
    try:
        df = pd.read_csv(f)
        if len(df) == 0:
            continue

        # Get symbol
        raw = str(df['vt_symbol'].iloc[0])
        code = raw.split('.')[0] if '.' in raw else raw
        exchange = raw.split('.')[1] if '.' in raw else 'SZ'

        if exchange.upper() in ('SH', 'SSE'):
            parquet_name = f'{code}.SSE.parquet'
        elif exchange.upper() in ('SZ', 'SZSE'):
            parquet_name = f'{code}.SZSE.parquet'
        else:
            parquet_name = f'{code}.parquet'

        parquet_path = os.path.join(lab_dir, parquet_name)

        # Select and rename columns
        df = df.rename(columns={
            'datetime': 'datetime',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume'
        })
        cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df = df[cols]

        # Normalize datetime: '2026-04-30' -> '20260430'
        df['datetime'] = df['datetime'].str.replace('-', '').str[:8]

        # Merge with existing
        if os.path.exists(parquet_path):
            existing = pd.read_parquet(parquet_path)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['datetime'], keep='last')
            df = combined

        df.to_parquet(parquet_path, index=False)
        converted += 1
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f'Error {os.path.basename(f)}: {e}')

print(f'Converted: {converted}, Errors: {errors}')
print(f'Parquet total: {len(glob.glob(os.path.join(lab_dir, \"*.parquet\")))}')
