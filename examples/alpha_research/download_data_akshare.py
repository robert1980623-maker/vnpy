"""
使用 AKShare 下载股票数据

用于选股策略回测的数据准备
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json


def get_stock_list():
    """
    获取 A 股股票列表
    
    Returns:
        pd.DataFrame: 股票列表
    """
    print("获取 A 股股票列表...")
    try:
        # 获取沪深 A 股列表
        df = ak.stock_info_a_code_name()
        print(f"获取到 {len(df)} 只股票")
        return df
    except Exception as e:
        print(f"获取股票列表失败：{e}")
        return None


def get_stock_bars(vt_symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取股票 K 线数据
    
    Args:
        vt_symbol: 股票代码 (如 "000001.SZ")
        start_date: 开始日期 (如 "20240101")
        end_date: 结束日期 (如 "20241231")
        
    Returns:
        pd.DataFrame: K 线数据
    """
    # 转换代码格式
    code = vt_symbol.split(".")[0]
    exchange = "sz" if vt_symbol.endswith(".SZ") else "sh"
    
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df is None or df.empty:
            return None
        
        # 转换格式
        df["vt_symbol"] = vt_symbol
        df["datetime"] = pd.to_datetime(df["日期"])
        df["open_price"] = df["开盘"].astype(float)
        df["high_price"] = df["最高"].astype(float)
        df["low_price"] = df["最低"].astype(float)
        df["close_price"] = df["收盘"].astype(float)
        df["volume"] = df["成交量"].astype(float) * 100  # 手转股
        df["turnover"] = df["成交额"].astype(float)
        
        return df[["vt_symbol", "datetime", "open_price", "high_price", "low_price", 
                   "close_price", "volume", "turnover"]]
    
    except Exception as e:
        print(f"获取 {vt_symbol} 数据失败：{e}")
        return None


def get_fundamental_data(vt_symbol: str) -> dict:
    """
    获取股票财务数据
    
    Args:
        vt_symbol: 股票代码
        
    Returns:
        dict: 财务指标
    """
    code = vt_symbol.split(".")[0]
    
    try:
        # 获取估值指标
        df = ak.stock_value_manager(symbol=code)
        if df is None or df.empty:
            return None
        
        # 取最新数据
        latest = df.iloc[-1] if len(df) > 0 else None
        if latest is None:
            return None
        
        return {
            "vt_symbol": vt_symbol,
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "pe_ratio": float(latest.get("市盈率", 0)) if "市盈率" in latest else None,
            "pb_ratio": float(latest.get("市净率", 0)) if "市净率" in latest else None,
            "dividend_yield": float(latest.get("股息率", 0)) if "股息率" in latest else None,
        }
    
    except Exception as e:
        # print(f"获取 {vt_symbol} 财务数据失败：{e}")
        return None


def download_index_components(index_code: str = "000300") -> list:
    """
    下载指数成分股
    
    Args:
        index_code: 指数代码 (默认沪深 300)
        
    Returns:
        list: 成分股列表
    """
    print(f"获取 {index_code} 成分股...")
    
    try:
        if index_code == "000300":
            # 沪深 300 成分股
            df = ak.index_stock_cons(symbol=index_code)
        elif index_code == "000016":
            # 上证 50
            df = ak.index_stock_cons(symbol=index_code)
        else:
            df = ak.index_stock_cons(symbol=index_code)
        
        if df is not None and not df.empty:
            # 转换代码格式
            components = []
            for _, row in df.iterrows():
                code = row.get("品种代码", row.get("股票代码", ""))
                if code:
                    exchange = "SZ" if str(code).startswith(("0", "3")) else "SH"
                    components.append(f"{code}.{exchange}")
            
            print(f"获取到 {len(components)} 只成分股")
            return components
    except Exception as e:
        print(f"获取成分股失败：{e}")
    
    return []


def save_data(data_dir: str, bars_dict: dict, fundamental_dict: dict) -> None:
    """
    保存数据到文件
    
    Args:
        data_dir: 数据目录
        bars_dict: K 线数据字典 {vt_symbol: DataFrame}
        fundamental_dict: 财务数据字典 {vt_symbol: dict}
    """
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    
    # 保存 K 线数据
    bars_path = data_path / "bars"
    bars_path.mkdir(exist_ok=True)
    
    for vt_symbol, df in bars_dict.items():
        if df is not None and not df.empty:
            filepath = bars_path / f"{vt_symbol.replace('.', '_')}.csv"
            df.to_csv(filepath, index=False)
    
    # 保存财务数据
    fundamental_path = data_path / "fundamental.json"
    with open(fundamental_path, 'w', encoding='utf-8') as f:
        json.dump(fundamental_dict, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到 {data_dir}")


def main():
    """主函数"""
    print("=" * 60)
    print("下载股票数据")
    print("=" * 60)
    
    # 设置参数
    index_code = "000300"  # 沪深 300
    start_date = "20240101"
    end_date = "20241231"
    data_dir = "./data/akshare"
    max_stocks = 10  # 限制下载数量，测试用
    
    # 1. 获取成分股
    components = download_index_components(index_code)
    if not components:
        print("获取成分股失败，使用示例股票")
        components = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "600519.SH"]
    
    # 限制数量
    components = components[:max_stocks]
    print(f"准备下载 {len(components)} 只股票数据")
    
    # 2. 下载数据
    bars_dict = {}
    fundamental_dict = {}
    
    for i, vt_symbol in enumerate(components, 1):
        print(f"\n[{i}/{len(components)}] 下载 {vt_symbol}...")
        
        # 下载 K 线数据
        bars = get_stock_bars(vt_symbol, start_date, end_date)
        if bars is not None and not bars.empty:
            bars_dict[vt_symbol] = bars
            print(f"  ✓ K 线数据：{len(bars)} 条")
        else:
            print(f"  ✗ K 线数据：失败")
        
        # 下载财务数据
        fundamental = get_fundamental_data(vt_symbol)
        if fundamental:
            fundamental_dict[vt_symbol] = {fundamental["report_date"]: fundamental}
            print(f"  ✓ 财务数据：PE={fundamental.get('pe_ratio', 'N/A')}")
        else:
            print(f"  ✗ 财务数据：失败")
        
        # 避免请求过快
        if i % 5 == 0:
            print("休息 2 秒...")
            import time
            time.sleep(2)
    
    # 3. 保存数据
    if bars_dict:
        save_data(data_dir, bars_dict, fundamental_dict)
        
        print("\n" + "=" * 60)
        print("下载完成！")
        print(f"  - K 线数据：{len(bars_dict)} 只股票")
        print(f"  - 财务数据：{len(fundamental_dict)} 只股票")
        print(f"  - 数据目录：{data_dir}")
        print("=" * 60)
    else:
        print("\n没有成功下载任何数据")


if __name__ == "__main__":
    main()
