#!/usr/bin/env python3
"""
VNPY 每日工作流 - 一键选股

流程：诊断 → 修复 → 验证 → 选股 → 报告

用法：
    cd /Users/rowang/projects/vnpy/examples/alpha_research
    export TUSHARE_TOKEN=xxx
    python3 daily_workflow.py
    
    # 跳过数据检查（数据已确认最新时）
    python3 daily_workflow.py --skip-check
    
    # 只检查不选股
    python3 daily_workflow.py --check-only
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# 设置工作目录
WORK_DIR = Path('/Users/rowang/projects/vnpy/examples/alpha_research')
os.chdir(WORK_DIR)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.lab import AlphaLab
from vnpy.trader.constant import Interval


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_ok(text: str):
    print(f"  ✅ {text}")


def print_warn(text: str):
    print(f"  ⚠️  {text}")


def print_err(text: str):
    print(f"  ❌ {text}")


def step_check_data() -> dict:
    """Step 1: 数据新鲜度检查"""
    print_header("Step 1: 数据新鲜度检查")
    
    report = {
        "status": "OK",
        "issues": [],
        "fixes_needed": [],
    }
    
    lab_path = Path('/Users/rowang/projects/vnpy/lab/data')
    daily_path = lab_path / 'daily'
    
    # 1. Parquet 数量
    pq_files = list(daily_path.glob('*.parquet')) if daily_path.exists() else []
    pq_count = len(pq_files)
    print(f"  Parquet 文件: {pq_count} 只", end="")
    
    if pq_count < 100:
        print_err("严重不足（应 > 4000）")
        report["status"] = "ERROR"
        report["issues"].append(f"Parquet 仅 {pq_count} 只")
        report["fixes_needed"].append("run_csv_to_parquet")
    elif pq_count < 4000:
        print_warn(f"不足（目标 > 4000）")
        report["status"] = "WARNING"
        report["fixes_needed"].append("run_csv_to_parquet")
    else:
        print_ok(f"{pq_count} 只")
    
    # 2. 数据日期
    if pq_count > 0:
        import polars as pl
        sample_size = max(10, min(50, int(pq_count * 0.01)))
        sample_files = pq_files[:sample_size]
        latest_dates = []
        for f in sample_files:
            try:
                df = pl.scan_parquet(str(f)).select('datetime').collect()
                if len(df) > 0:
                    latest_dates.append(df['datetime'].max().date())
            except Exception:
                pass
        
        if latest_dates:
            max_date = max(latest_dates)
            days_ago = (datetime.now().date() - max_date).days
            print(f"  最新数据日期: {max_date}", end="")
            
            if days_ago > 5:
                print_err(f"（距今 {days_ago} 天）")
                report["status"] = "ERROR" if report["status"] != "ERROR" else report["status"]
                report["issues"].append(f"数据仅到 {max_date}，距今 {days_ago} 天")
                
                # 检查 CSV 源数据
                csv_dir = Path('/Users/rowang/projects/vnpy/examples/alpha_research/data/akshare/bars')
                if csv_dir.exists():
                    csv_files = list(csv_dir.glob('*.csv'))
                    if csv_files:
                        with open(csv_files[0], 'r') as fh:
                            lines = fh.readlines()
                            if len(lines) > 1:
                                last = lines[-1].strip().split(',')
                                if len(last) > 1:
                                    csv_date = last[1].split('.')[0]
                                    if csv_date and len(csv_date) == 8:
                                        csv_dt = datetime.strptime(csv_date, '%Y%m%d').date()
                                        csv_days = (datetime.now().date() - csv_dt).days
                                        if csv_days > 5:
                                            report["fixes_needed"].append("run_tushare_download")
                                            report["issues"].append(f"CSV 也过期了（最新 {csv_dt}）")
                                        else:
                                            report["fixes_needed"].append("run_csv_to_parquet")
            else:
                print_ok(f"（距今 {days_ago} 天）")
    
    # 3. AlphaLab 加载验证
    try:
        lab = AlphaLab(str(lab_path))
        bars = lab.load_bar_data('000001.SZSE', Interval.DAILY,
            datetime.now() - timedelta(days=14), datetime.now())
        print(f"  AlphaLab 加载: {len(bars)} 条（近 14 天）", end="")
        if len(bars) == 0:
            print_err("0 条")
            report["status"] = "ERROR" if report["status"] != "ERROR" else report["status"]
            report["issues"].append("AlphaLab 无法加载近期数据")
        else:
            print_ok("OK")
    except Exception as e:
        print_err(str(e)[:50])
        report["status"] = "ERROR" if report["status"] != "ERROR" else report["status"]
    
    # 4. 财务缓存
    cache_dir = Path('/Users/rowang/projects/vnpy/examples/alpha_research/cache/fundamental')
    if cache_dir.exists():
        fc_count = len(list(cache_dir.glob('*.json')))
        print(f"  财务缓存: {fc_count} 个文件", end="")
        if fc_count > 1000:
            print_ok("OK")
        else:
            print_warn("不足，选股时 PE/PB 会实时拉 Tushare")
    else:
        print_warn("财务缓存目录不存在")
    
    # 5. 持仓状态
    acc_file = Path('./accounts/virtual_2026_account.json')
    if acc_file.exists():
        with open(acc_file) as f:
            account = json.load(f)
        pos_count = len(account.get('positions', []))
        trade_count = len(account.get('trades', []))
        print(f"  持仓: {pos_count} 只 / 交易: {trade_count} 笔", end="")
        if pos_count == 0 and trade_count > 0:
            print_warn("positions 为空但 trades 存在")
            report["fixes_needed"].append("rebuild_positions")
        else:
            print_ok("OK")
    else:
        print_warn("账户文件不存在")
    
    # 6. Tushare Token
    token = os.environ.get('TUSHARE_TOKEN', '')
    print(f"  Tushare Token: {'✅ 已设置' if token else '❌ 未设置（export TUSHARE_TOKEN=xxx）'}")
    if not token:
        report["issues"].append("TUSHARE_TOKEN 未设置")
    
    return report


def step_fix_data(fixes: list) -> bool:
    """Step 2: 自动修复"""
    if not fixes:
        print_ok("无需修复")
        return True
    
    print_header("Step 2: 自动修复")
    
    for fix in fixes:
        if fix == "rebuild_positions":
            print("  [持仓重建] ", end="")
            try:
                from scripts.rebuild_positions import rebuild_positions
                rebuild_positions(str(WORK_DIR / 'accounts/virtual_2026_account.json'))
                print_ok("完成")
            except Exception as e:
                print_err(str(e))
        
        elif fix == "run_csv_to_parquet":
            print("  [CSV → Parquet] ", end="")
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(WORK_DIR / 'csv_to_parquet.py'),
                     '--lab-dir', '/Users/rowang/projects/vnpy/lab/data',
                     '--start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                     '--end', datetime.now().strftime('%Y-%m-%d')],
                    capture_output=True, text=True, timeout=180,
                    cwd=str(WORK_DIR)
                )
                if result.returncode == 0:
                    print_ok("完成")
                else:
                    print_err(result.stderr[:100])
            except subprocess.TimeoutExpired:
                print_err("超时")
            except Exception as e:
                print_err(str(e))
        
        elif fix == "run_tushare_download":
            print("  [Tushare 下载] ", end="")
            token = os.environ.get('TUSHARE_TOKEN', '')
            if not token:
                print_err("TUSHARE_TOKEN 未设置，跳过")
                continue
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(WORK_DIR / 'tushare_pro_downloader.py'),
                     '--all', '--start-date', (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                     '--end-date', datetime.now().strftime('%Y%m%d')],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(WORK_DIR),
                    env={**os.environ, 'TUSHARE_TOKEN': token}
                )
                if result.returncode == 0:
                    print_ok("完成")
                else:
                    print_err(result.stderr[:100])
            except subprocess.TimeoutExpired:
                print_err("超时")
            except Exception as e:
                print_err(str(e))
    
    return True


def step_select_stocks() -> dict:
    """Step 3: 运行选股"""
    print_header("Step 3: 运行选股")
    
    try:
        from vnpy.alpha.lab import AlphaLab
        from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
        from alpha.strategy.industry_rotation import IndustryRotationStrategy
        from vnpy.trader.constant import Interval
        
        lab = AlphaLab('/Users/rowang/projects/vnpy/lab/data')
        engine = CrossSectionalBacktestingEngine(lab)
        
        # 获取所有股票列表
        pq_files = list(Path('/Users/rowang/projects/vnpy/lab/data/daily').glob('*.parquet'))
        vt_symbols = [f.stem for f in pq_files[:50]]  # 先用 50 只测试
        
        if len(vt_symbols) == 0:
            print_err("无可用股票数据")
            return {
            "result_df": result_df,"status": "ERROR", "stocks": []}
        
        print(f"  股票池: {len(vt_symbols)} 只")
        
        # 设置参数（用最近 30 天数据）
        engine.set_parameters(
            vt_symbols=vt_symbols,
            interval=Interval.DAILY,
            start=datetime.now() - timedelta(days=30),
            end=datetime.now(),
            capital=1_000_000,
        )
        
        # 添加策略
        engine.add_strategy(IndustryRotationStrategy, setting={
            'name': '行业轮动',
            'max_positions': 10,
            'position_size': 0.1,
            'rebalance_days': 20,
            'max_pe': 20,
            'max_pb': 3,
            'top_industries': 3,
        })
        
        print("  [加载数据] ", end="")
        engine.load_data()
        print_ok("完成")
        
        print("  [运行回测] ", end="")
        engine.run_backtesting()
        print_ok("完成")
        
        # 获取结果
        stats = engine.calculate_statistics()
        result_df = engine.calculate_result()
        
        print(f"\n  📊 回测统计:")
        print(f"    年化收益: {stats.get('annual_return', 0):.2%}")
        print(f"    最大回撤: {stats.get('max_drawdown', 0):.2%}")
        print(f"    Sharpe:   {stats.get('sharpe_ratio', 0):.2f}")
        print(f"    结果记录: {len(result_df) if result_df is not None else 0} 条")
        
        return {
            "status": "OK",
            "stats": stats,
            "result_df": result_df,
        }
        
    except Exception as e:
        print_err(f"选股失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ERROR", "error": str(e)}


def step_generate_report(result: dict, check_report: dict):
    """Step 4: 生成报告"""
    print_header("Step 4: 报告")
    
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  数据状态: {check_report['status']}")
    print(f"  选股状态: {result.get('status', 'N/A')}")
    
    if check_report.get('issues'):
        print(f"\n  ⚠️  问题 ({len(check_report['issues'])} 项):")
        for issue in check_report['issues']:
            print(f"    - {issue}")
    
    if result.get("result_df") is not None:
        df = result["result_df"]
        if df is not None and len(df) > 0:
            print(f"\n  📈 回测结果: {len(df)} 条记录")
            print(f"    {df.head(3)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='VNPY 每日选股工作流')
    parser.add_argument('--skip-check', action='store_true', help='跳过数据检查')
    parser.add_argument('--check-only', action='store_true', help='只检查数据，不选股')
    parser.add_argument('--top', type=int, default=50, help='选股池股票数量（默认 50）')
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║          VNPY 每日选股工作流                               ║
║          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                              ║
╚══════════════════════════════════════════════════════════╝""")
    
    # Step 1: 数据检查
    if not args.skip_check:
        check_report = step_check_data()
        
        # Step 2: 修复（如果需要）
        if check_report.get('fixes_needed'):
            step_fix_data(check_report['fixes_needed'])
            
            # 重新检查
            print("\n  [重新检查] ", end="")
            check_report = step_check_data()
    else:
        check_report = {"status": "OK", "issues": [], "fixes_needed": []}
        print_ok("跳过数据检查")
    
    # Step 3: 选股
    if args.check_only:
        step_generate_report({"status": "N/A", "stocks": []}, check_report)
        return
    
    result = step_select_stocks()
    
    # Step 4: 报告
    step_generate_report(result, check_report)
    
    # 总结
    print(f"\n{'='*60}")
    if check_report['status'] == 'OK' and result.get('status') == 'OK':
        print("  🎉 每日选股完成！")
    else:
        print("  ⚠️  完成但有警告，请检查上方问题列表")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
