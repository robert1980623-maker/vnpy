"""
测试单只股票下载
"""

import akshare as ak
import pandas as pd
from datetime import datetime

# 测试平安银行
symbol = "000001"
print(f"测试下载 {symbol}...")

try:
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date="20250101",
        end_date="20260228",
        adjust=""
    )
    
    print(f"✅ 下载成功！")
    print(f"数据形状：{df.shape}")
    print(f"\n列名：{df.columns.tolist()}")
    print(f"\n前 5 行:")
    print(df.head())
    print(f"\n后 5 行:")
    print(df.tail())
    
except Exception as e:
    print(f"❌ 下载失败：{e}")
