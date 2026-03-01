"""
RQData 数据下载脚本

用于从 RQData 下载：
- 指数成分股数据
- 股票财务数据
- 股票日频数据
- 信号数据生成
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.dataset import StockPool, FundamentalData, create_pool, create_fundamental_data
from vnpy.trader.constant import Interval

try:
    import rqdatac as rq
except ImportError:
    print("错误：请先安装 rqdatac")
    print("pip install rqdatac")
    sys.exit(1)


# ========== 配置 ==========

# RQData 登录信息（请替换为你的账号）
RQ_USER = "your_username"
RQ_PASSWORD = "your_password"

# 数据保存路径
DATA_PATH = Path("./data")
LAB_PATH = Path("./lab/my_strategy")

# 下载时间范围
START_DATE = "2020-01-01"
END_DATE = "2024-12-31"

# 要下载的指数列表
INDICES = {
    "csi300": "000300.XSHG",    # 沪深 300
    "csi500": "000905.XSHG",    # 中证 500
    "csi1000": "000852.XSHG",   # 中证 1000
    "csi_all": "000985.XSHG",   # 中证全指
    "a800": "000906.XSHG",      # 中证 800
    "chiext": "399102.XSHE",    # 创业板指
    "star50": "000688.XSHG",    # 科创 50
    "csi100": "000903.XSHG",    # 中证 100
}


def login_rqdata() -> bool:
    """登录 RQData"""
    try:
        rq.init(user=RQ_USER, pwd=RQ_PASSWORD)
        print("✅ RQData 登录成功")
        return True
    except Exception as e:
        print(f"❌ RQData 登录失败：{e}")
        return False


def download_index_components() -> None:
    """下载指数成分股数据"""
    print("\n" + "=" * 60)
    print("开始下载指数成分股数据")
    print("=" * 60)
    
    pool = create_pool(str(DATA_PATH / "pool"))
    
    for index_name, index_code in INDICES.items():
        print(f"\n📊 下载 {index_name} ({index_code}) 成分股...")
        
        try:
            # 获取成分股历史数据
            data = rq.index_components(
                order_book_ids=index_code,
                start_date=START_DATE,
                end_date=END_DATE
            )
            
            # 转换为字典格式
            components = {}
            for dt, symbols in data.items():
                date_str = dt.strftime("%Y-%m-%d")
                # 转换代码格式（XSHG->SSE, XSHE->SZSE）
                vt_symbols = [
                    s.replace(".XSHG", ".SSE").replace(".XSHE", ".SZSE")
                    for s in symbols
                ]
                components[date_str] = vt_symbols
            
            # 保存成分股数据
            pool.save_index_components(index_name, components)
            
            print(f"  ✅ 已保存 {len(components)} 个交易日的成分股数据")
            
            # 统计最新成分股数量
            if components:
                latest_date = max(components.keys())
                latest_count = len(components[latest_date])
                print(f"  📈 最新成分股数量 ({latest_date}): {latest_count} 只")
        
        except Exception as e:
            print(f"  ❌ 下载失败：{e}")


def download_daily_data(vt_symbols: list[str]) -> None:
    """
    下载股票日频数据
    
    Args:
        vt_symbols: 股票代码列表
    """
    print("\n" + "=" * 60)
    print("开始下载股票日频数据")
    print("=" * 60)
    
    lab = AlphaLab(str(LAB_PATH))
    
    # 分批下载，避免单次请求过大
    batch_size = 50
    total = len(vt_symbols)
    
    for i in range(0, total, batch_size):
        batch_symbols = vt_symbols[i:i+batch_size]
        print(f"\n📊 批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
        
        for vt_symbol in batch_symbols:
            try:
                # 转换代码格式
                symbol = vt_symbol.split(".")[0]
                exchange = vt_symbol.split(".")[1]
                
                if exchange == "SSE":
                    rq_symbol = f"{symbol}.XSHG"
                elif exchange == "SZSE":
                    rq_symbol = f"{symbol}.XSHE"
                else:
                    continue
                
                # 下载日频数据
                df = rq.get_price(
                    order_book_ids=rq_symbol,
                    start_date=START_DATE,
                    end_date=END_DATE,
                    frequency="1d",
                    adjust_type="none",  # 不复权
                    expect_df=True
                )
                
                if df is None or df.empty:
                    print(f"  ⚠️  {vt_symbol}: 无数据")
                    continue
                
                # 转换为 BarData 格式
                bars = []
                for idx, row in df.iterrows():
                    from vnpy.trader.object import BarData
                    from vnpy.trader.constant import Exchange
                    
                    exchange_obj = Exchange.SSE if exchange == "SSE" else Exchange.SZSE
                    
                    bar = BarData(
                        symbol=symbol,
                        exchange=exchange_obj,
                        datetime=idx.to_pydatetime(),
                        interval=Interval.DAILY,
                        open_price=row["open"],
                        high_price=row["high"],
                        low_price=row["low"],
                        close_price=row["close"],
                        volume=row["volume"],
                        turnover=row["total_turnover"],
                        open_interest=0,
                        gateway_name="RQDATA"
                    )
                    bars.append(bar)
                
                # 保存数据
                if bars:
                    lab.save_bar_data(bars)
                    print(f"  ✅ {vt_symbol}: {len(bars)} 条记录")
            
            except Exception as e:
                print(f"  ❌ {vt_symbol} 下载失败：{e}")


def download_fundamental_data() -> None:
    """下载财务数据"""
    print("\n" + "=" * 60)
    print("开始下载财务数据")
    print("=" * 60)
    
    fd = create_fundamental_data(str(DATA_PATH / "fundamental"))
    
    # 获取全市场股票列表
    all_stocks = rq.all_instruments(type="CS", market="cn")
    stock_symbols = all_stocks["order_book_id"].tolist()
    
    print(f"📊 全市场股票数量：{len(stock_symbols)}")
    
    # 下载每日估值数据
    print("\n📈 下载每日估值数据...")
    
    # 按日期下载
    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        print(f"\n  日期：{date_str}")
        
        try:
            # 下载估值数据
            valuation_data = rq.get_valuation(
                order_book_ids=None,  # 全市场
                start_date=date_str,
                end_date=date_str,
                fields=[
                    "pe_ratio", "pb_ratio", "ps_ratio", "pcf_ratio",
                    "dividend_yield", "ev_ebitda"
                ]
            )
            
            if valuation_data is None or valuation_data.empty:
                current_dt += timedelta(days=1)
                continue
            
            # 转换格式
            result_data = []
            for idx, row in valuation_data.iterrows():
                symbol = idx[0] if isinstance(idx, tuple) else idx
                
                # 转换代码格式
                if ".XSHG" in symbol:
                    vt_symbol = symbol.replace(".XSHG", ".SSE")
                elif ".XSHE" in symbol:
                    vt_symbol = symbol.replace(".XSHE", ".SZSE")
                else:
                    continue
                
                result_data.append({
                    "symbol": vt_symbol,
                    "date": date_str,
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "ps_ratio": row["ps_ratio"],
                    "pcf_ratio": row["pcf_ratio"],
                    "dividend_yield": row["dividend_yield"],
                    "ev_ebitda": row["ev_ebitda"],
                })
            
            if result_data:
                df = pl.DataFrame(result_data)
                fd.save_data(df, data_type="daily")
                print(f"    ✅ 已保存 {len(df)} 条记录")
        
        except Exception as e:
            print(f"    ❌ 下载失败：{e}")
        
        current_dt += timedelta(days=1)
    
    # 下载财务指标数据（季度）
    print("\n📊 下载财务指标数据...")
    
    try:
        # 下载最近几年的财务指标
        financial_data = rq.financial_indicator(
            order_book_ids=None,  # 全市场
            report_date=None,  # 最新报告期
            fields=[
                "roe", "roa", "roic",
                "gross_margin", "net_margin", "operating_margin",
                "revenue_growth", "net_profit_growth", "eps_growth",
                "debt_to_asset", "debt_to_equity",
                "current_ratio", "quick_ratio",
                "asset_turnover", "inventory_turnover"
            ]
        )
        
        if financial_data is not None and not financial_data.empty:
            # 转换格式
            result_data = []
            for idx, row in financial_data.iterrows():
                symbol = idx[0] if isinstance(idx, tuple) else idx
                
                if ".XSHG" in symbol:
                    vt_symbol = symbol.replace(".XSHG", ".SSE")
                elif ".XSHE" in symbol:
                    vt_symbol = symbol.replace(".XSHE", ".SZSE")
                else:
                    continue
                
                # 获取报告日期
                report_date = row.get("report_date", None)
                if report_date is None:
                    continue
                
                result_data.append({
                    "symbol": vt_symbol,
                    "date": report_date.strftime("%Y-%m-%d") if isinstance(report_date, datetime) else str(report_date),
                    "roe": row["roe"],
                    "roa": row["roa"],
                    "roic": row["roic"],
                    "gross_margin": row["gross_margin"],
                    "net_margin": row["net_margin"],
                    "operating_margin": row["operating_margin"],
                    "revenue_growth": row["revenue_growth"],
                    "net_profit_growth": row["net_profit_growth"],
                    "eps_growth": row["eps_growth"],
                    "debt_to_asset": row["debt_to_asset"],
                    "debt_to_equity": row["debt_to_equity"],
                    "current_ratio": row["current_ratio"],
                    "quick_ratio": row["quick_ratio"],
                    "asset_turnover": row["asset_turnover"],
                    "inventory_turnover": row["inventory_turnover"],
                })
            
            if result_data:
                df = pl.DataFrame(result_data)
                fd.save_data(df, data_type="quarterly")
                print(f"  ✅ 已保存 {len(df)} 条季度财务数据")
    
    except Exception as e:
        print(f"  ❌ 下载失败：{e}")


def generate_signals() -> None:
    """生成选股信号"""
    print("\n" + "=" * 60)
    print("生成选股信号")
    print("=" * 60)
    
    fd = create_fundamental_data(str(DATA_PATH / "fundamental"))
    lab = AlphaLab(str(LAB_PATH))
    
    # 加载财务数据
    print("\n📊 加载财务数据...")
    
    # 读取所有每日估值数据
    daily_path = DATA_PATH / "fundamental" / "daily"
    if not daily_path.exists():
        print("  ❌ 财务数据文件夹不存在")
        return
    
    all_signals = []
    
    for file_path in daily_path.glob("*.parquet"):
        try:
            df = pl.read_parquet(file_path)
            
            # 计算综合得分
            # 价值得分 = ROE 排名 * 0.5 + (1/PE) 排名 * 0.5
            if "roe" in df.columns and "pe_ratio" in df.columns:
                # 过滤有效数据
                df = df.filter(
                    (pl.col("pe_ratio") > 0) &
                    (pl.col("roe") > 0)
                )
                
                # 计算排名得分
                df = df.with_columns([
                    pl.col("roe").rank().alias("roe_rank"),
                    (1.0 / pl.col("pe_ratio")).rank().alias("value_rank")
                ])
                
                # 综合得分
                df = df.with_columns(
                    (pl.col("roe_rank") * 0.5 + pl.col("value_rank") * 0.5).alias("signal")
                )
                
                # 添加 datetime 列
                if "date" in df.columns:
                    df = df.with_columns(pl.col("date").alias("datetime"))
                
                # 选择需要的列
                signal_df = df.select(["datetime", "symbol", "signal", "pe_ratio", "roe"])
                
                all_signals.append(signal_df)
                print(f"  ✅ {file_path.name}: {len(signal_df)} 只股票")
        
        except Exception as e:
            print(f"  ❌ {file_path.name} 处理失败：{e}")
    
    if all_signals:
        # 合并所有信号
        merged_signals = pl.concat(all_signals)
        
        # 保存信号
        lab.save_signals(merged_signals)
        
        print(f"\n📈 总计生成 {len(merged_signals)} 条信号记录")
    else:
        print("\n⚠️  未生成有效信号")


def get_all_symbols() -> list[str]:
    """获取全市场股票代码"""
    print("\n📊 获取全市场股票代码...")
    
    all_stocks = rq.all_instruments(type="CS", market="cn")
    
    symbols = []
    for _, row in all_stocks.iterrows():
        symbol = row["order_book_id"]
        
        # 转换代码格式
        if ".XSHG" in symbol:
            vt_symbol = symbol.replace(".XSHG", ".SSE")
        elif ".XSHE" in symbol:
            vt_symbol = symbol.replace(".XSHE", ".SZSE")
        else:
            continue
        
        # 过滤掉 ST、*ST 股票
        name = row.get("symbol", "")
        if "ST" in name:
            continue
        
        symbols.append(vt_symbol)
    
    print(f"  ✅ 获取到 {len(symbols)} 只股票")
    return symbols


def main():
    """主函数"""
    print("=" * 60)
    print("RQData 数据下载脚本")
    print("=" * 60)
    print(f"数据保存路径：{DATA_PATH.absolute()}")
    print(f"实验室路径：{LAB_PATH.absolute()}")
    print(f"时间范围：{START_DATE} - {END_DATE}")
    
    # 登录 RQData
    if not login_rqdata():
        return
    
    # 1. 下载指数成分股
    download_index_components()
    
    # 2. 获取全市场股票代码
    all_symbols = get_all_symbols()
    
    # 3. 下载财务数据
    download_fundamental_data()
    
    # 4. 下载日频数据（可选，数据量大）
    # download_daily_data(all_symbols)
    
    # 5. 生成选股信号
    generate_signals()
    
    print("\n" + "=" * 60)
    print("✅ 数据下载完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 检查数据质量")
    print("2. 运行回测验证")
    print("3. 开发和测试策略")


if __name__ == "__main__":
    main()
