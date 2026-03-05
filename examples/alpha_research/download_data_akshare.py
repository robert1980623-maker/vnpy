"""
使用 AKShare/Tushare 下载股票数据（增强版）

支持：
- 多数据源（Tushare 优先、AKShare、Baostock）
- Tushare token 配置（config/auto_config.yaml）
- 本地缓存
- 自动重试
- akshare-proxy-patch 支持
"""

# 先加载 akshare-proxy-patch（在导入 akshare 之前）
try:
    import akshare_proxy_patch
    akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
    print("✓ akshare-proxy-patch 已加载")
except ImportError:
    print("⚠️ akshare-proxy-patch 未安装，将使用原始 AKShare")
except Exception as e:
    print(f"⚠️ akshare-proxy-patch 加载失败：{e}")

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import random
import yaml
import os
import requests

# ==================== 配置加载 ====================

def load_data_config() -> dict:
    """加载数据源配置"""
    config_file = Path('./config/auto_config.yaml')
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('data', {})
    return {}

# 优先从环境变量读取 TUSHARE_TOKEN，其次从配置文件
ENV_TOKEN = os.environ.get('TUSHARE_TOKEN', '')
CONFIG_TOKEN = load_data_config().get('tushare_token', '')
TUSHARE_TOKEN = ENV_TOKEN if ENV_TOKEN else CONFIG_TOKEN

USE_TUSHARE = bool(TUSHARE_TOKEN and TUSHARE_TOKEN.strip())

if USE_TUSHARE:
    print(f"✓ Tushare 已配置，将优先使用 Tushare 数据源")
    if ENV_TOKEN:
        print("  来源：环境变量 TUSHARE_TOKEN")
    else:
        print("  来源：config/auto_config.yaml")
    # 初始化 Tushare
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
else:
    print("ℹ Tushare 未配置，将使用 AKShare 数据源")
    print("  设置方式:")
    print("  1. 环境变量：export TUSHARE_TOKEN='your_token'")
    print("  2. 配置文件：config/auto_config.yaml 中的 data.tushare_token")
    pro = None


# ==================== 缓存管理 ====================

class DataCache:
    """数据缓存管理"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.cache_dir / "cache_meta.json"
        self.meta = self._load_meta()
    
    def _load_meta(self) -> dict:
        """加载缓存元数据"""
        if self.meta_file.exists():
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_meta(self):
        """保存缓存元数据"""
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def get_bars(self, vt_symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从缓存获取 K 线数据"""
        cache_key = f"{vt_symbol}_{start_date}_{end_date}"
        cache_info = self.meta.get(cache_key)
        
        if not cache_info:
            return None
        
        cache_file = self.cache_dir / cache_info["file"]
        if not cache_file.exists():
            return None
        
        try:
            df = pd.read_csv(cache_file)
            df["datetime"] = pd.to_datetime(df["datetime"])
            print(f"  ✓ 从缓存加载 {vt_symbol}")
            return df
        except Exception as e:
            print(f"  ✗ 缓存读取失败：{e}")
            return None
    
    def save_bars(self, vt_symbol: str, start_date: str, end_date: str, df: pd.DataFrame):
        """保存 K 线数据到缓存"""
        cache_key = f"{vt_symbol}_{start_date}_{end_date}"
        cache_file = self.cache_dir / f"bars_{vt_symbol.replace('.', '_')}.csv"
        
        df.to_csv(cache_file, index=False)
        self.meta[cache_key] = {
            "file": cache_file.name,
            "rows": len(df),
            "created": datetime.now().isoformat()
        }
        self._save_meta()
        print(f"  ✓ 已缓存 {vt_symbol} ({len(df)} 条)")
    
    def get_fundamental(self, vt_symbol: str) -> dict:
        """从缓存获取财务数据"""
        cache_key = f"fundamental_{vt_symbol}"
        cache_info = self.meta.get(cache_key)
        
        if not cache_info:
            return None
        
        cache_file = self.cache_dir / cache_info["file"]
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  ✓ 从缓存加载 {vt_symbol} 财务数据")
            return data
        except Exception as e:
            return None
    
    def save_fundamental(self, vt_symbol: str, data: dict):
        """保存财务数据到缓存"""
        cache_key = f"fundamental_{vt_symbol}"
        cache_file = self.cache_dir / f"fundamental_{vt_symbol.replace('.', '_')}.json"
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.meta[cache_key] = {
            "file": cache_file.name,
            "created": datetime.now().isoformat()
        }
        self._save_meta()


# ==================== 数据下载 ====================

def get_stock_bars_akshare(vt_symbol: str, start_date: str, end_date: str, 
                           max_retries: int = 3) -> pd.DataFrame:
    """
    使用 AKShare 获取 K 线数据（带重试）
    
    Args:
        vt_symbol: 股票代码 (如 "000001.SZ")
        start_date: 开始日期 (如 "20240101")
        end_date: 结束日期 (如 "20241231")
        max_retries: 最大重试次数
        
    Returns:
        pd.DataFrame: K 线数据
    """
    code = vt_symbol.split(".")[0]
    
    for attempt in range(max_retries):
        try:
            # 获取日线数据（前复权）
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
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
            if attempt < max_retries - 1:
                wait_time = random.uniform(3, 6) * (attempt + 1)
                print(f"  重试 {attempt+1}/{max_retries}, 等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)
            else:
                print(f"  ✗ AKShare 失败：{e}")
                return None
    
    return None



def get_stock_bars_tushare(vt_symbol: str, start_date: str, end_date: str, 
                           max_retries: int = 3) -> pd.DataFrame:
    """
    使用 Tushare SDK 获取 K 线数据（带重试）
    
    Args:
        vt_symbol: 股票代码 (如 "000001.SZ")
        start_date: 开始日期 (如 "20240101")
        end_date: 结束日期 (如 "20241231")
        max_retries: 最大重试次数
        
    Returns:
        pd.DataFrame: K 线数据
    """
    if not pro:
        return None
    
    code = vt_symbol.split(".")[0]
    exchange = vt_symbol.split(".")[1] if "." in vt_symbol else "SZ"
    
    # 转换交易所代码为 Tushare 格式
    ts_exchange = "SZ" if exchange == "SZ" else "SH"
    ts_symbol = f"{code}.{ts_exchange}"
    
    for attempt in range(max_retries):
        try:
            # 使用 Tushare Pro SDK API 获取日线数据
            df = pro.daily(
                ts_code=ts_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                return None
            
            # 转换格式
            df["vt_symbol"] = vt_symbol
            df["datetime"] = pd.to_datetime(df["trade_date"])
            df["open_price"] = df["open"].astype(float)
            df["high_price"] = df["high"].astype(float)
            df["low_price"] = df["low"].astype(float)
            df["close_price"] = df["close"].astype(float)
            df["volume"] = df["vol"].astype(float) * 100  # 手转股
            df["turnover"] = df["amount"].astype(float)
            
            print(f"  ✓ Tushare 成功获取 {vt_symbol}")
            
            return df[["vt_symbol", "datetime", "open_price", "high_price", "low_price", 
                       "close_price", "volume", "turnover"]]
        
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 4) * (attempt + 1)
                print(f"  Tushare 重试 {attempt+1}/{max_retries}, 等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)
            else:
                print(f"  ✗ Tushare 失败：{e}")
                return None
    
    return None


def get_stock_bars_baostock(vt_symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 Baostock 获取 K 线数据（备选数据源）
    
    Args:
        vt_symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: K 线数据
    """
    try:
        import baostock as bs
        
        # 登录
        lg = bs.login()
        if lg.error_code != '0':
            print(f"  Baostock 登录失败：{lg.error_msg}")
            return None
        
        # 转换代码格式 (baostock 需要 sh.600000 或 sz.000001 格式)
        code = vt_symbol.lower()
        if "." in code:
            parts = code.split(".")
            if parts[1] == "sh":
                code = f"sh.{parts[0]}"
            elif parts[1] == "sz":
                code = f"sz.{parts[0]}"
        
        # 转换日期格式 (baostock 需要 YYYY-MM-DD)
        start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end_date_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        # 获取日线数据（前复权）
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            frequency="d",
            adjustflag="3"  # 前复权
        )
        
        if rs.error_code != '0':
            print(f"  Baostock 查询失败：{rs.error_msg}")
            bs.logout()
            return None
        
        # 转换为 DataFrame
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
        
        # 登出
        bs.logout()
        
        if not data_list:
            return None
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 转换格式
        df["vt_symbol"] = vt_symbol
        df["datetime"] = pd.to_datetime(df["date"])
        df["open_price"] = df["open"].astype(float)
        df["high_price"] = df["high"].astype(float)
        df["low_price"] = df["low"].astype(float)
        df["close_price"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["turnover"] = df["amount"].astype(float)
        
        return df[["vt_symbol", "datetime", "open_price", "high_price", "low_price", 
                   "close_price", "volume", "turnover"]]
    
    except ImportError:
        print("  Baostock 未安装，跳过")
        return None
    except Exception as e:
        print(f"  ✗ Baostock 失败：{e}")
        return None


def get_fundamental_data(vt_symbol: str, max_retries: int = 2) -> dict:
    """
    获取股票财务数据
    
    使用多个 AKShare 接口获取财务指标
    
    Args:
        vt_symbol: 股票代码
        max_retries: 最大重试次数
        
    Returns:
        dict: 财务指标
    """
    code = vt_symbol.split(".")[0]
    
    for attempt in range(max_retries):
        try:
            # 方法 1: 获取个股估值指标
            try:
                df = ak.stock_value_em(symbol=code)
            except:
                # 备用方法
                df = None
            
            if df is not None and not df.empty:
                latest = df.iloc[-1] if len(df) > 0 else None
                if latest is not None:
                    return {
                        "vt_symbol": vt_symbol,
                        "report_date": datetime.now().strftime("%Y-%m-%d"),
                        "pe_ratio": float(latest.get("市盈率", 0)) if "市盈率" in latest else None,
                        "pb_ratio": float(latest.get("市净率", 0)) if "市净率" in latest else None,
                        "dividend_yield": float(latest.get("股息率", 0)) if "股息率" in latest else None,
                    }
            
            # 方法 2: 获取财务指标
            try:
                df2 = ak.stock_financial_analysis_indicator(symbol=code)
                if df2 is not None and not df2.empty:
                    latest = df2.iloc[0]  # 取最新一期
                    return {
                        "vt_symbol": vt_symbol,
                        "report_date": latest.get("报告期", datetime.now().strftime("%Y-%m-%d")),
                        "pe_ratio": float(latest.get("市盈率", 0)) if "市盈率" in latest else None,
                        "pb_ratio": float(latest.get("市净率", 0)) if "市净率" in latest else None,
                        "roe": float(latest.get("净资产收益率", 0)) if "净资产收益率" in latest else None,
                    }
            except:
                pass
            
            # 如果都失败，返回基础数据
            return {
                "vt_symbol": vt_symbol,
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "pe_ratio": None,
                "pb_ratio": None,
                "dividend_yield": None,
            }
        
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 4)
                print(f"  重试 {attempt+1}/{max_retries}, 等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)
            else:
                print(f"  ✗ 财务数据获取失败：{e}")
                # 返回空数据，不影响 K 线下载
                return {
                    "vt_symbol": vt_symbol,
                    "report_date": datetime.now().strftime("%Y-%m-%d"),
                    "pe_ratio": None,
                    "pb_ratio": None,
                    "dividend_yield": None,
                }
    
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
        df = ak.index_stock_cons(symbol=index_code)
        
        if df is not None and not df.empty:
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


# ==================== 主流程 ====================

def download_all_data(
    components: list,
    start_date: str = "20250304",
    end_date: str = "20260304",
    max_stocks: int = None,
    use_cache: bool = True,
    cache_dir: str = "./cache",
    night_mode: bool = False
):
    """
    批量下载股票数据
    
    Args:
        components: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        max_stocks: 最大下载数量（None 表示全部）
        use_cache: 是否使用缓存
        cache_dir: 缓存目录
    """
    # 初始化缓存
    cache = DataCache(cache_dir) if use_cache else None
    
    # 限制数量
    if max_stocks:
        components = components[:max_stocks]
    
    print(f"\n准备下载 {len(components)} 只股票数据")
    print(f"时间范围：{start_date} - {end_date}")
    if use_cache:
        print(f"缓存目录：{cache_dir}")
    print("=" * 60)
    
    # 下载数据
    bars_dict = {}
    fundamental_dict = {}
    success_count = 0
    cache_hit_count = 0
    
    for i, vt_symbol in enumerate(components, 1):
        print(f"\n[{i}/{len(components)}] 下载 {vt_symbol}...")
        
        # 下载 K 线数据
        bars = None
        if use_cache and cache:
            bars = cache.get_bars(vt_symbol, start_date, end_date)
            if bars is not None:
                cache_hit_count += 1
        
        if bars is None:
            # 数据源优先级：Tushare > AKShare > Baostock
            if USE_TUSHARE:
                print("  使用 Tushare 数据源...")
                bars = get_stock_bars_tushare(vt_symbol, start_date, end_date)
            
            # Tushare 失败或未配置，尝试 AKShare
            if bars is None:
                print("  使用 AKShare 数据源...")
                bars = get_stock_bars_akshare(vt_symbol, start_date, end_date)
            
            # AKShare 失败，尝试 Baostock
            if bars is None:
                print("  尝试 Baostock...")
                bars = get_stock_bars_baostock(vt_symbol, start_date, end_date)
            
            # 保存到缓存
            if bars is not None and use_cache and cache:
                cache.save_bars(vt_symbol, start_date, end_date, bars)
        
        if bars is not None and not bars.empty:
            bars_dict[vt_symbol] = bars
            print(f"  ✓ K 线数据：{len(bars)} 条")
            success_count += 1
        else:
            print(f"  ✗ K 线数据：失败")
        
        # 下载财务数据
        fundamental = None
        if use_cache and cache:
            fundamental = cache.get_fundamental(vt_symbol)
        
        if fundamental is None:
            fundamental = get_fundamental_data(vt_symbol)
            if fundamental and use_cache and cache:
                cache.save_fundamental(vt_symbol, fundamental)
        
        if fundamental:
            fundamental_dict[vt_symbol] = {fundamental["report_date"]: fundamental}
            pe = fundamental.get('pe_ratio', 'N/A')
            print(f"  ✓ 财务数据：PE={pe}")
        else:
            print(f"  ✗ 财务数据：失败")
        
        # 延迟，避免请求过快
        if i < len(components):
            # 夜间模式使用更长延迟
            if night_mode:
                if i % 2 == 0:  # 每 2 只股票休息
                    wait_time = random.uniform(8, 12)
                    print(f"\n休息 {wait_time:.1f}秒 (夜间模式)...")
                    time.sleep(wait_time)
            else:
                if i % 3 == 0:  # 每 3 只股票休息
                    wait_time = random.uniform(3, 5)
                    print(f"\n休息 {wait_time:.1f}秒...")
                    time.sleep(wait_time)
    
    # 统计
    print("\n" + "=" * 60)
    print("下载完成！")
    print(f"  - 成功：{success_count}/{len(components)} 只股票")
    print(f"  - 缓存命中：{cache_hit_count} 次")
    print(f"  - 财务数据：{len(fundamental_dict)} 只股票")
    print("=" * 60)
    
    return bars_dict, fundamental_dict


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="下载股票数据（增强版）")
    parser.add_argument("--index", type=str, default="000300", 
                       help="指数代码 (默认：000300 沪深 300)")
    parser.add_argument("--start", type=str, default=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"), help="开始日期 (默认：30 天前)")
    parser.add_argument("--end", type=str, default=datetime.now().strftime("%Y%m%d"), help="结束日期 (默认：当天)")
    parser.add_argument("--max", type=int, default=5,
                       help="最大下载数量 (默认：5，小批量下载)")
    parser.add_argument("--symbols", type=str, nargs='+',
                       help="指定股票代码列表（覆盖 index 和 max 参数）")
    parser.add_argument("--cache", type=str, default="./cache",
                       help="缓存目录 (默认：./cache)")
    parser.add_argument("--no-cache", action="store_true",
                       help="不使用缓存")
    parser.add_argument("--night-mode", action="store_true",
                       help="夜间下载模式 (更长延迟，避免限流)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("下载股票数据（增强版）")
    print("=" * 60)
    
    # 设置参数
    index_code = args.index
    start_date = args.start
    end_date = args.end
    
    # 支持指定股票代码列表
    if args.symbols:
        symbols = args.symbols
        print(f"指定股票：{len(symbols)} 只")
        print(f"  列表：{', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
        max_stocks = len(symbols)
        components = symbols  # 使用指定的股票列表
    else:
        max_stocks = args.max
    use_cache = not args.no_cache
    cache_dir = args.cache
    night_mode = args.night_mode
    
    if night_mode:
        print("夜间模式：启用（更长延迟）")
    
    # 1. 获取成分股（如果未指定股票列表）
    if not args.symbols:
        components = download_index_components(index_code)
        if not components:
            print("获取成分股失败，使用示例股票")
            components = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "600519.SH"]
    # 如果指定了 symbols，components 已经在上面设置过了
    
    # 2. 下载数据
    bars_dict, fundamental_dict = download_all_data(
        components=components,
        start_date=start_date,
        end_date=end_date,
        max_stocks=max_stocks,
        use_cache=use_cache,
        cache_dir=cache_dir
    )
    
    # 3. 保存数据到输出目录
    if bars_dict:
        from pathlib import Path
        data_dir = Path("./data/akshare")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 K 线数据
        bars_path = data_dir / "bars"
        bars_path.mkdir(exist_ok=True)
        for vt_symbol, df in bars_dict.items():
            filepath = bars_path / f"{vt_symbol.replace('.', '_')}.csv"
            df.to_csv(filepath, index=False)
        
        # 保存财务数据
        fundamental_path = data_dir / "fundamental.json"
        with open(fundamental_path, 'w', encoding='utf-8') as f:
            json.dump(fundamental_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据已保存到 {data_dir}")
        print(f"下一步：python run_backtest.py --data {data_dir}")


if __name__ == "__main__":
    main()

# 添加 --symbols 参数支持（在 main 函数内）
# 找到 args.max 后面添加：
# parser.add_argument("--symbols", type=str, nargs='+', help="指定股票代码列表")
