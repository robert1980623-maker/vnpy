#!/usr/bin/env python3
"""
自动更新日期下载范围到最新交易日
"""

from datetime import datetime, timedelta
import re

script_path = "/Users/rowang/projects/vnpy/examples/alpha_research/download_data_akshare.py"

# 计算最近 365 天的日期
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

with open(script_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换开始日期
content = re.sub(r'start_date: str = "\d{8}"', f'start_date: str = "{start_str}"', content)
content = re.sub(r'end_date: str = "\d{8}"', f'end_date: str = "{end_str}"', content)
content = re.sub(r'default="\d{8}"\s*,\s*help="开始日期', f'default="{start_str}", help="开始日期', content)
content = re.sub(r'default="\d{8}"\s*,\s*help="结束日期', f'default="{end_str}", help="结束日期', content)

with open(script_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ 已更新日期下载范围:")
print(f"  开始日期：{start_str} ({start_date.strftime('%Y-%m-%d')})")
print(f"  结束日期：{end_str} ({end_date.strftime('%Y-%m-%d')})")
print(f"  数据范围：最近 365 天")
