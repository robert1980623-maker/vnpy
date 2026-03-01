"""
独立数据下载脚本 - 不依赖 vnpy 完整环境

使用 AKShare 下载股票数据并保存为 Parquet 格式
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

import pandas as pd
import polars as pl

try:
    import akshare as ak
except ImportError:
    print("❌ 请先安装 akshare: pip install akshare")
    sys.exit(1)


# ========== 配置 ==========

# 数据保存路径
DATA_PATH = Path("./data")
DAILY_PATH = DATA_PATH / "daily"

# 创建文件夹
DAILY_PATH.mkdir(parents=True, exist_ok=True)

# 测试用股票池（沪深 300 部分成分股）
TEST_SYMBOLS = [
    "000001", "000002", "000063", "000100", "000157",
    "000333", "000538", "000568", "000651", "000725",
    "000858", "002001", "002007", "002027", "002049",
    "002129", "002142", "002230", "002236", "002241",
    "002304", "002352", "002371", "002410", "002415",
    "002459", "002460", "002466", "002475", "002487",
    "002507", "002594", "002601", "002648", "002709",
    "002714", "002812", "002821", "002850", "002920",
    "300014", "300059", "300122", "300124", "300274",
    "300316", "300347", "300413", "300433", "300450",
    "300498", "300601", "300628", "300750", "300759",
    "300760", "300782", "300896",
    "600000", "600009", "600016", "600028", "600030",
    "600031", "600036", "600048", "600050", "600104",
    "600111", "600132", "600141", "600176", "600183",
    "600188", "600219", "600276", "600309", "600346",
    "600352", "600372", "600406", "600426", "600436",
    "600438", "600459", "600460", "600486", "600489",
    "600519", "600522", "600547", "600570", "600584",
    "600585", "600588", "600660", "600690", "600745",
    "600763", "600809", "600803", "600887", "600893",
    "600900", "600905", "600919", "600941", "600989",
    "601012", "601066", "601088", "601117", "601138",
    "601166", "601211", "601225", "601288", "601318",
    "601328", "601336", "601398", "601601", "601628",
    "601633", "601658", "601668", "601669", "601688",
    "601728", "601766", "601788", "601816", "601857",
    "601865", "601872", "601877", "601881", "601888",
    "601899", "601919", "601939", "601985", "601988",
    "601995", "601998", "603019", "603195", "603259",
    "603260", "603288", "603290", "603369", "603392",
    "603486", "603501", "603517", "603596", "603659",
    "603707", "603712", "603799", "603806", "603833",
    "603899", "603986",
]

# 时间范围（最近 1 年）
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)


def download_stock_data(symbol: str, exchange: str) -> pd.DataFrame | None:
    """
    下载单只股票数据
    
    Args:
        symbol: 股票代码（6 位数字）
        exchange: 交易所（SSE/SZSE）
    
    Returns:
        DataFrame 或 None
    """
    try:
        # AKShare 代码格式
        if exchange == "SSE":
            ak_symbol = f"sh{symbol}"
        else:
            ak_symbol = f"sz{symbol}"
        
        # 下载日频数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=START_DATE.strftime("%Y%m%d"),
            end_date=END_DATE.strftime("%Y%m%d"),
            adjust=""  # 不复权
        )
        
        if df is None or df.empty:
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
        
        # 添加股票代码列
        vt_symbol = f"{symbol}.{exchange}"
        df["vt_symbol"] = vt_symbol
        
        # 选择需要的列
        df = df[["datetime", "open", "high", "low", "close", "volume", "turnover", "vt_symbol"]]
        
        return df
    
    except Exception as e:
        print(f"  ❌ {symbol} 下载失败：{e}")
        return None


def save_to_parquet(df: pd.DataFrame, vt_symbol: str) -> None:
    """
    保存数据为 Parquet 格式
    
    Args:
        df: 数据 DataFrame
        vt_symbol: 股票代码
    """
    file_path = DAILY_PATH / f"{vt_symbol}.parquet"
    # 转换为 polars 再保存
    pl_df = pl.from_pandas(df)
    pl_df.write_parquet(file_path)
    print(f"  ✅ 已保存：{file_path.name} ({len(df)} 条记录)")


def main():
    """主函数"""
    print("=" * 60)
    print("独立数据下载脚本（AKShare 免费数据源）")
    print("=" * 60)
    print(f"数据保存路径：{DAILY_PATH.absolute()}")
    print(f"时间范围：{START_DATE.date()} - {END_DATE.date()}")
    print(f"股票数量：{len(TEST_SYMBOLS)}\n")
    
    success_count = 0
    total_records = 0
    
    for i, symbol in enumerate(TEST_SYMBOLS):
        # 判断交易所
        if symbol.startswith("6"):
            exchange = "SSE"
        else:
            exchange = "SZSE"
        
        vt_symbol = f"{symbol}.{exchange}"
        
        # 显示进度
        print(f"[{i+1}/{len(TEST_SYMBOLS)}] {vt_symbol}", end="")
        
        # 下载数据
        df = download_stock_data(symbol, exchange)
        
        if df is not None and not df.is_empty():
            # 保存数据
            save_to_parquet(df, vt_symbol)
            success_count += 1
            total_records += len(df)
        else:
            print(" ❌ 无数据")
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("✅ 数据下载完成！")
    print("=" * 60)
    print(f"成功：{success_count}/{len(TEST_SYMBOLS)}")
    print(f"总记录数：{total_records:,}")
    print(f"数据路径：{DAILY_PATH.absolute()}")
    print("=" * 60)
    
    # 生成简单统计
    print("\n📊 数据摘要:")
    print(f"  - 股票数量：{success_count}")
    print(f"  - 总记录数：{total_records:,}")
    print(f"  - 平均每只股票：{total_records // success_count if success_count > 0 else 0:,} 条")
    print(f"  - 时间范围：{START_DATE.date()} - {END_DATE.date()}")


if __name__ == "__main__":
    main()
