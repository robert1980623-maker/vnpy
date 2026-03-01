"""
数据质量检查工具

检查已下载数据的完整性和质量：
- 数据连续性
- 缺失值检查
- 异常值检测
- 统计汇总
"""

import sys
from datetime import datetime
from pathlib import Path

import polars as pl

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.lab import AlphaLab
from vnpy.trader.constant import Interval


# ========== 配置 ==========

LAB_PATH = Path("./lab/test_strategy")


def check_data_completeness(lab: AlphaLab) -> dict:
    """
    检查数据完整性
    
    Returns:
        检查结果字典
    """
    print("\n" + "=" * 60)
    print("数据完整性检查")
    print("=" * 60)
    
    # 获取所有股票
    daily_files = list(lab.daily_path.glob("*.parquet"))
    
    if not daily_files:
        print("❌ 未找到任何数据文件")
        return {}
    
    print(f"📊 找到 {len(daily_files)} 只股票的数据\n")
    
    results = {
        "total_symbols": len(daily_files),
        "symbols": []
    }
    
    # 检查每只股票
    for file_path in daily_files:
        vt_symbol = file_path.stem
        
        try:
            df = pl.read_parquet(file_path)
            
            # 基本统计
            record_count = len(df)
            start_date = df["datetime"].min()
            end_date = df["datetime"].max()
            
            # 缺失值检查
            missing_cols = {}
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    null_count = df[col].null_count()
                    if null_count > 0:
                        missing_cols[col] = null_count
            
            # 零值检查（停牌）
            zero_volume_days = df.filter(pl.col("volume") == 0).height
            
            # 异常值检查
            if "close" in df.columns and record_count > 1:
                # 计算日收益率
                returns = df["close"].pct_change()
                
                # 极端涨跌幅（>20%）
                extreme_days = returns.filter(
                    (returns.abs() > 0.20) & (returns.is_not_null())
                ).height
            else:
                extreme_days = 0
            
            symbol_info = {
                "vt_symbol": vt_symbol,
                "record_count": record_count,
                "start_date": start_date,
                "end_date": end_date,
                "missing_values": missing_cols,
                "zero_volume_days": zero_volume_days,
                "extreme_days": extreme_days,
            }
                
            results["symbols"].append(symbol_info)
            
            # 输出摘要
            print(f"{vt_symbol}:")
            print(f"  记录数：{record_count:,}")
            print(f"  时间范围：{start_date} - {end_date}")
            if missing_cols:
                print(f"  缺失值：{missing_cols}")
            if zero_volume_days > 0:
                print(f"  零成交天数：{zero_volume_days}")
            if extreme_days > 0:
                print(f"  极端涨跌幅天数：{extreme_days}")
            print()
        
        except Exception as e:
            print(f"❌ {vt_symbol} 检查失败：{e}")
    
    return results


def check_trading_dates(lab: AlphaLab) -> None:
    """检查交易日连续性"""
    print("\n" + "=" * 60)
    print("交易日连续性检查")
    print("=" * 60)
    
    # 收集所有日期
    all_dates = set()
    
    for file_path in lab.daily_path.glob("*.parquet"):
        try:
            df = pl.read_parquet(file_path)
            dates = df["datetime"].to_list()
            all_dates.update(dates)
        except Exception:
            continue
    
    if not all_dates:
        print("❌ 无数据")
        return
    
    # 排序
    sorted_dates = sorted(all_dates)
    
    print(f"\n📊 总交易日数：{len(sorted_dates)}")
    print(f"时间范围：{sorted_dates[0]} - {sorted_dates[-1]}")
    
    # 检查间隔
    gaps = []
    for i in range(1, len(sorted_dates)):
        prev_date = sorted_dates[i-1]
        curr_date = sorted_dates[i]
        
        # 计算天数差
        days_diff = (curr_date - prev_date).days
        
        # 如果间隔超过 7 天，记录为缺口
        if days_diff > 7:
            gaps.append({
                "start": prev_date,
                "end": curr_date,
                "days": days_diff
            })
    
    if gaps:
        print(f"\n⚠️  发现 {len(gaps)} 个数据缺口（>7 天）:")
        for gap in gaps[:10]:  # 只显示前 10 个
            print(f"  {gap['start'].date()} - {gap['end'].date()} ({gap['days']} 天)")
        if len(gaps) > 10:
            print(f"  ... 还有 {len(gaps) - 10} 个缺口")
    else:
        print("\n✅ 数据连续性良好")


def check_signal_data(lab: AlphaLab) -> None:
    """检查信号数据"""
    print("\n" + "=" * 60)
    print("信号数据检查")
    print("=" * 60)
    
    if not lab.signal_path.exists():
        print("❌ 信号文件夹不存在")
        return
    
    # 收集所有信号文件
    signal_files = list(lab.signal_path.glob("signals_*.parquet"))
    
    if not signal_files:
        print("❌ 未找到信号文件")
        return
    
    print(f"📊 找到 {len(signal_files)} 个交易日的信号\n")
    
    all_signals = []
    
    for file_path in signal_files:
        try:
            df = pl.read_parquet(file_path)
            
            # 基本统计
            record_count = len(df)
            
            # 检查必需列
            required_cols = ["datetime", "vt_symbol"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            # 检查信号列
            has_signal = "signal" in df.columns
            
            if has_signal:
                signal_mean = df["signal"].mean()
                signal_std = df["signal"].std()
                signal_min = df["signal"].min()
                signal_max = df["signal"].max()
            else:
                signal_mean = signal_std = signal_min = signal_max = None
            
            file_info = {
                "date": file_path.stem.replace("signals_", ""),
                "record_count": record_count,
                "missing_cols": missing_cols,
                "has_signal": has_signal,
                "signal_mean": signal_mean,
                "signal_std": signal_std,
            }
            
            all_signals.append(file_info)
            
            # 输出
            print(f"{file_info['date']}:")
            print(f"  股票数：{record_count}")
            if missing_cols:
                print(f"  缺少列：{missing_cols}")
            if has_signal:
                print(f"  信号统计：均值={signal_mean:.3f}, 标准差={signal_std:.3f}, 范围=[{signal_min:.3f}, {signal_max:.3f}]")
            print()
        
        except Exception as e:
            print(f"❌ {file_path.name} 检查失败：{e}")
    
    # 汇总
    total_records = sum(info["record_count"] for info in all_signals)
    print("=" * 60)
    print(f"总计：{len(all_signals)} 个交易日，{total_records:,} 条信号记录")


def check_contract_settings(lab: AlphaLab) -> None:
    """检查合约配置"""
    print("\n" + "=" * 60)
    print("合约配置检查")
    print("=" * 60)
    
    if not lab.contract_path.exists():
        print("⚠️  合约配置文件不存在")
        return
    
    try:
        import json
        with open(lab.contract_path, "r", encoding="utf-8") as f:
            contracts = json.load(f)
        
        print(f"📊 配置了 {len(contracts)} 只合约\n")
        
        # 检查配置完整性
        for vt_symbol, setting in list(contracts.items())[:10]:  # 只显示前 10 个
            print(f"{vt_symbol}:")
            print(f"  买入费率：{setting.get('long_rate', 'N/A')}")
            print(f"  卖出费率：{setting.get('short_rate', 'N/A')}")
            print(f"  合约乘数：{setting.get('size', 'N/A')}")
            print(f"  价格跳动：{setting.get('pricetick', 'N/A')}")
            print()
        
        if len(contracts) > 10:
            print(f"... 还有 {len(contracts) - 10} 只合约")
    
    except Exception as e:
        print(f"❌ 读取失败：{e}")


def generate_summary_report(lab: AlphaLab) -> None:
    """生成数据摘要报告"""
    print("\n" + "=" * 60)
    print("数据摘要报告")
    print("=" * 60)
    
    # 统计数据
    daily_files = list(lab.daily_path.glob("*.parquet"))
    signal_files = list(lab.signal_path.glob("signals_*.parquet")) if lab.signal_path.exists() else []
    
    # 计算总记录数
    total_bars = 0
    for file_path in daily_files:
        try:
            df = pl.read_parquet(file_path)
            total_bars += len(df)
        except Exception:
            continue
    
    total_signals = 0
    for file_path in signal_files:
        try:
            df = pl.read_parquet(file_path)
            total_signals += len(df)
        except Exception:
            continue
    
    # 输出报告
    print(f"""
📊 数据摘要
{'=' * 60}

📁 股票数据:
   - 股票数量：{len(daily_files)}
   - 总记录数：{total_bars:,}
   - 平均每只股票：{total_bars // len(daily_files) if daily_files else 0:,} 条

📁 信号数据:
   - 交易日数：{len(signal_files)}
   - 总记录数：{total_signals:,}
   - 平均每日信号：{total_signals // len(signal_files) if signal_files else 0:,} 条

📁 合约配置:
   - 配置数量：{len(lab.contract_path.exists() and lab.contract_path.read_text() or {})}

{'=' * 60}
""")


def main():
    """主函数"""
    print("=" * 60)
    print("数据质量检查工具")
    print("=" * 60)
    print(f"实验室路径：{LAB_PATH.absolute()}\n")
    
    # 创建实验室实例
    lab = AlphaLab(str(LAB_PATH))
    
    # 1. 检查数据完整性
    results = check_data_completeness(lab)
    
    # 2. 检查交易日连续性
    check_trading_dates(lab)
    
    # 3. 检查信号数据
    check_signal_data(lab)
    
    # 4. 检查合约配置
    check_contract_settings(lab)
    
    # 5. 生成摘要报告
    generate_summary_report(lab)
    
    print("\n✅ 数据检查完成！")


if __name__ == "__main__":
    main()
