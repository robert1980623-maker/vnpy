#!/usr/bin/env python3
"""数据新鲜度快速检查"""

from pathlib import Path
from datetime import datetime
import json

data_dir = Path('./data/akshare/bars')
check_time = datetime.now()
today = check_time.strftime('%Y-%m-%d')

print(f"检查时间：{check_time.strftime('%Y-%m-%d %H:%M')}")
print(f"期望日期：{today}")
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
            last_line = lines[-1].strip().split(',')
            if len(last_line) >= 2:
                data_date = last_line[1]
                is_fresh = data_date == today
                if is_fresh:
                    fresh += 1
                else:
                    stale += 1
                    print(f"❌ {csv_file.stem}: {data_date}")

print()
print(f"新鲜：{fresh}/{len(sample_files)}")
print(f"滞后：{stale}/{len(sample_files)}")

if fresh >= len(sample_files) * 0.9:
    print("✅ 数据新鲜")
else:
    print("⚠️ 数据滞后，需要更新")
