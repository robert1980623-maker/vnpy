#!/usr/bin/env python3
"""数据新鲜度快速检查（修复版）"""

from pathlib import Path
from datetime import datetime, timedelta
import json

data_dir = Path('./data/akshare/bars')
check_time = datetime.now()
today = check_time.strftime('%Y%m%d')

# 获取最近交易日（排除周末）
last_trading = check_time
while last_trading.weekday() >= 5:
    last_trading -= timedelta(days=1)
last_trading_str = last_trading.strftime('%Y%m%d')

print(f"检查时间：{check_time.strftime('%Y-%m-%d %H:%M')}")
print(f"最近交易日：{last_trading_str}")
print()

# 随机检查 10 只股票
import random
csv_files = list(data_dir.glob('*.csv'))
sample_files = random.sample(csv_files, min(10, len(csv_files)))

fresh = 0
stale = 0

for csv_file in sample_files:
    with open(csv_file, 'r') as f:
        lines = f.readlines()
        if len(lines) >= 2:
            # 数据按日期倒序排列，第一行是最新日期
            first_data = lines[1].strip().split(',')
            if len(first_data) >= 1:
                data_date = first_data[0]  # 第0列是日期
                is_fresh = data_date >= last_trading_str
                if is_fresh:
                    fresh += 1
                else:
                    stale += 1
                    print(f"❌ {csv_file.stem}: 最新={data_date}, 期望>={last_trading_str}")

print()
print(f"新鲜：{fresh}/{len(sample_files)}")
print(f"滞后：{stale}/{len(sample_files)}")

if fresh >= len(sample_files) * 0.9:
    print("✅ 数据新鲜")
else:
    print("⚠️ 数据滞后，需要更新")
