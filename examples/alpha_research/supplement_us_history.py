#!/usr/bin/env python3
"""
补充美股指数历史数据 - 使用 akshare
下载最近 20 个交易日数据用于计算涨跌
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# 加载 akshare-proxy-patch
try:
    import akshare_proxy_patch
    akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
    print("✓ akshare-proxy-patch 已加载")
except Exception as e:
    print(f"⚠️ patch 加载失败：{e}")

import akshare as ak
import pandas as pd

# 配置
DATA_DIR = Path("/Users/rowang/projects/vnpy/examples/alpha_research/data/akshare/bars")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 美股指数配置（symbol 是 akshare 用的，filename 是本地文件名）
US_INDICES = [
    {"symbol": "DJI", "filename": "US_DJIA", "name": "道琼斯工业平均指数"},
    {"symbol": "SPX", "filename": "US_SPX", "name": "标普 500"},
    {"symbol": "NDX", "filename": "US_NDX", "name": "纳斯达克 100"},
]

def download_index_history(symbol: str, filename: str, name: str, days: int = 20):
    """下载美股指数历史数据"""
    print(f"\n📥 下载 {name} ({symbol}) 最近 {days} 个交易日...")
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days*2)).strftime("%Y%m%d")
    
    try:
        # 使用 index_zh_a_hist 下载（这个接口支持美股指数）
        df = ak.index_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            print(f"  ⚠️ 无数据返回")
            return False
        
        print(f"  ✅ 获取到 {len(df)} 条数据")
        
        # 标准化列名
        rename_map = {}
        if "日期" in df.columns:
            rename_map["日期"] = "date"
        if "开盘" in df.columns:
            rename_map["开盘"] = "open"
        if "最高" in df.columns:
            rename_map["最高"] = "high"
        if "最低" in df.columns:
            rename_map["最低"] = "low"
        if "收盘" in df.columns:
            rename_map["收盘"] = "close"
        if "成交量" in df.columns:
            rename_map["成交量"] = "volume"
        if "成交额" in df.columns:
            rename_map["成交额"] = "amount"
        
        df = df.rename(columns=rename_map)
        
        # 只保留需要的列
        needed_cols = ["date", "open", "high", "low", "close", "volume"]
        available_cols = [c for c in needed_cols if c in df.columns]
        df = df[available_cols]
        
        # 按日期排序
        if "date" in df.columns:
            df = df.sort_values("date")
        
        # 保存到 CSV
        filepath = DATA_DIR / f"{filename}.csv"
        df.to_csv(filepath, index=False)
        print(f"  ✅ 已保存到 {filepath}")
        
        # 显示最新几条
        print(f"  最新数据:")
        print(df.tail(3).to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"  ❌ 下载失败：{type(e).__name__}: {e}")
        return False

def main():
    print("=" * 70)
    print(" " * 20 + "补充美股指数历史数据")
    print("=" * 70)
    print(f"数据目录：{DATA_DIR}")
    print(f"时间范围：最近 20 个交易日")
    print()
    
    results = {}
    for idx in US_INDICES:
        success = download_index_history(
            idx["symbol"], 
            idx["filename"], 
            idx["name"]
        )
        results[idx["filename"]] = success
        time.sleep(3)  # 避免请求过快
    
    print("\n" + "=" * 70)
    print("📊 下载汇总")
    print("=" * 70)
    
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    
    for filename, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {filename}")
    
    print(f"\n总计：{success_count} 成功，{fail_count} 失败")
    
    if success_count > 0:
        print("\n✅ 历史数据补充完成！现在可以准确计算涨跌了")
    else:
        print("\n⚠️ 所有下载都失败了，请检查网络或数据源")

if __name__ == "__main__":
    main()
