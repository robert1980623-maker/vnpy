"""
AKShare 真实数据下载脚本

优化版：
- 添加重试机制
- 添加请求延时
- 错误处理和日志
- 支持断点续传
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import polars as pl

try:
    import akshare as ak
except ImportError:
    print("❌ 请先安装 akshare: pip install akshare")
    sys.exit(1)


# ========== 配置 ==========

# 数据保存路径
DATA_PATH = Path("./data_real")
DAILY_PATH = DATA_PATH / "daily"
DAILY_PATH.mkdir(parents=True, exist_ok=True)

# 时间范围（最近 2 年）
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=730)

# 股票池（沪深 300 部分活跃股票）
STOCK_POOL = [
    # 银行
    "600000", "600016", "600036", "600104", "601166", "601288", "601328", "601398",
    # 保险
    "601318", "601601", "601628",
    # 证券
    "600030", "601066", "601211", "601688", "601881",
    # 白酒
    "000568", "000725", "000858", "600519", "600702", "600809",
    # 食品
    "000895", "600887", "603288",
    # 家电
    "000333", "000651", "600690",
    # 医药
    "000538", "002007", "300122", "600276", "600436", "600521",
    # 新能源
    "002594", "300014", "300274", "300750", "601012", "601865",
    # 科技
    "000063", "000725", "002230", "002415", "300059", "600570", "600745",
    # 制造
    "000001", "000002", "600031", "600276", "601766",
]

# 下载配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 2  # 重试延时（秒）
REQUEST_DELAY = 0.5  # 请求间隔（秒）


def get_exchange(symbol: str) -> str:
    """判断交易所"""
    if symbol.startswith("6"):
        return "SSE"
    else:
        return "SZSE"


def download_single_stock(symbol: str, skip_if_exists: bool = True) -> Optional[pd.DataFrame]:
    """
    下载单只股票数据（带重试）
    
    Args:
        symbol: 股票代码
        skip_if_exists: 如果已存在是否跳过
    
    Returns:
        DataFrame 或 None
    """
    exchange = get_exchange(symbol)
    vt_symbol = f"{symbol}.{exchange}"
    file_path = DAILY_PATH / f"{vt_symbol}.parquet"
    
    # 检查是否已存在
    if skip_if_exists and file_path.exists():
        try:
            df = pl.read_parquet(file_path)
            if len(df) > 100:  # 数据量足够
                print(f"  ⏭️  已存在：{vt_symbol} ({len(df)}条)")
                return None
        except Exception:
            pass
    
    # 下载
    for attempt in range(MAX_RETRIES):
        try:
            # 延时
            if attempt > 0:
                print(f"  重试 {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY * (attempt + 1))
            
            # 调用 AKShare
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=START_DATE.strftime("%Y%m%d"),
                end_date=END_DATE.strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            
            if df is None or df.empty:
                print(f"  ⚠️  {vt_symbol}: 无数据")
                return None
            
            # 转换列名
            df = df.rename(columns={
                "日期": "datetime",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "turnover",
            })
            
            # 添加股票代码
            df["vt_symbol"] = vt_symbol
            
            # 选择列
            df = df[["datetime", "open", "high", "low", "close", "volume", "turnover", "vt_symbol"]]
            
            # 保存
            pl_df = pl.from_pandas(df)
            pl_df.write_parquet(file_path)
            
            print(f"  ✅ {vt_symbol}: {len(df)}条记录")
            return df
        
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "timeout" in error_msg.lower():
                print(f"  ⚠️  {vt_symbol}: 网络错误 ({attempt + 1}/{MAX_RETRIES})")
                continue
            else:
                print(f"  ❌ {vt_symbol}: {error_msg}")
                break
    
    print(f"  ❌ {vt_symbol}: 下载失败")
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("AKShare 真实数据下载")
    print("=" * 60)
    print(f"数据保存路径：{DAILY_PATH.absolute()}")
    print(f"时间范围：{START_DATE.date()} - {END_DATE.date()}")
    print(f"股票数量：{len(STOCK_POOL)}")
    print(f"配置：重试={MAX_RETRIES}, 延时={REQUEST_DELAY}秒\n")
    
    # 统计
    success_count = 0
    skip_count = 0
    fail_count = 0
    total_records = 0
    
    # 下载
    for i, symbol in enumerate(STOCK_POOL):
        print(f"[{i+1}/{len(STOCK_POOL)}] {symbol}", end="")
        
        # 下载
        df = download_single_stock(symbol)
        
        if df is not None:
            if len(df) > 100:
                success_count += 1
                total_records += len(df)
            else:
                skip_count += 1
        else:
            # 检查是否已存在
            exchange = get_exchange(symbol)
            vt_symbol = f"{symbol}.{exchange}"
            file_path = DAILY_PATH / f"{vt_symbol}.parquet"
            
            if file_path.exists():
                skip_count += 1
            else:
                fail_count += 1
        
        # 请求延时
        time.sleep(REQUEST_DELAY)
    
    # 汇总
    print("\n" + "=" * 60)
    print("下载完成")
    print("=" * 60)
    print(f"成功：{success_count} 只")
    print(f"跳过：{skip_count} 只（已存在）")
    print(f"失败：{fail_count} 只")
    print(f"总记录数：{total_records:,} 条")
    print(f"数据路径：{DAILY_PATH.absolute()}")
    print("=" * 60)
    
    # 验证
    print("\n📊 数据验证...")
    files = list(DAILY_PATH.glob("*.parquet"))
    print(f"  文件数：{len(files)}")
    
    if files:
        total = 0
        for f in files:
            df = pl.read_parquet(f)
            total += len(df)
        print(f"  总记录：{total:,} 条")
        print(f"  平均每只：{total // len(files):,} 条")


if __name__ == "__main__":
    main()
