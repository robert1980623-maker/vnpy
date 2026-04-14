#!/usr/bin/env python3
"""
数据新鲜度检查 + 自动诊断

检查项:
1. Parquet 数量（应 > 4000）
2. Parquet 最新日期（应为最近交易日）
3. AlphaLab 加载验证
4. 财务缓存
5. 持仓状态
6. Tushare 连通性

返回: 诊断报告 + 修复建议
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import polars as pl
from vnpy.alpha.lab import AlphaLab
from vnpy.trader.constant import Interval


def check_freshness(lab_dir: str = '/Users/rowang/projects/vnpy/lab/data', account_file: str = None):
    report = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "status": "OK",
        "checks": {},
        "issues": [],
        "suggestions": [],
    }
    
    lab_path = Path(lab_dir)
    daily_path = lab_path / 'daily'
    
    # 1. Parquet 数量
    pq_files = list(daily_path.glob('*.parquet')) if daily_path.exists() else []
    pq_count = len(pq_files)
    report["checks"]["parquet_count"] = pq_count
    
    if pq_count < 100:
        report["status"] = "ERROR"
        report["issues"].append(f"Parquet 仅 {pq_count} 只（应 > 4000）")
        report["suggestions"].append("运行: python3 csv_to_parquet.py --lab-dir " + lab_dir)
    elif pq_count < 4000:
        report["status"] = "WARNING"
        report["issues"].append(f"Parquet {pq_count} 只（目标 > 4000）")
    
    # 2. Parquet 最新日期（抽样检查）
    if pq_count > 0:
        # 动态抽样：至少 10 只，最多 50 只，或总数的 1%
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
            min_date = min(latest_dates)
            report["checks"]["parquet_date_range"] = f"{min_date} ~ {max_date}"
            report["checks"]["parquet_sample_size"] = sample_size
            
            days_ago = (datetime.now().date() - max_date).days
            if days_ago > 5:
                report["status"] = "ERROR" if report["status"] != "ERROR" else report["status"]
                report["issues"].append(f"数据仅到 {max_date}，距今 {days_ago} 天")
                # 检查 CSV 源数据是否也过期
                csv_dir = Path('./data/akshare/bars')
                if csv_dir.exists():
                    csv_files_list = list(csv_dir.glob('*.csv'))
                    if csv_files_list:
                        # 检查一个代表性股票的 CSV 最新日期
                        sample_csv = csv_files_list[0]
                        with open(sample_csv, 'r') as fh:
                            lines = fh.readlines()
                            if len(lines) > 1:
                                last_line = lines[-1].strip().split(',')
                                csv_date_str = last_line[1] if len(last_line) > 1 else ''
                                if '.' in csv_date_str:
                                    csv_date_str = csv_date_str.split('.')[0]
                                if csv_date_str and len(csv_date_str) == 8:
                                    csv_date = datetime.strptime(csv_date_str, '%Y%m%d').date()
                                    csv_days_ago = (datetime.now().date() - csv_date).days
                                    if csv_days_ago > 5:
                                        report["issues"].append(f"CSV 源数据也过期了（最新 {csv_date}，距今 {csv_days_ago} 天）")
                                        report["suggestions"].append("先运行 tushare_pro_downloader.py 补 CSV")
                                        report["suggestions"].append("再运行 python3 csv_to_parquet.py 转 Parquet")
                                    else:
                                        report["suggestions"].append("CSV 有数据 → 运行: python3 csv_to_parquet.py --lab-dir " + lab_dir)
    
    # 3. AlphaLab 加载验证
    try:
        lab = AlphaLab(str(lab_path))
        bars = lab.load_bar_data('000001.SZSE', Interval.DAILY,
            datetime.now() - timedelta(days=14), datetime.now())
        report["checks"]["alphalab_load"] = len(bars)
        if len(bars) == 0:
            report["issues"].append("AlphaLab 无法加载近期数据")
            if report["status"] == "OK":
                report["status"] = "ERROR"
    except Exception as e:
        report["checks"]["alphalab_load"] = f"失败: {e}"
        if report["status"] == "OK":
            report["status"] = "ERROR"
    
    # 4. 财务缓存
    cache_dir = Path('/Users/rowang/projects/vnpy/examples/alpha_research/cache/fundamental')
    if cache_dir.exists():
        fc_count = len(list(cache_dir.glob('*.json')))
        report["checks"]["fundamental_cache"] = fc_count
        if fc_count < 1000:
            report["suggestions"].append("财务缓存不足，运行: python3 build_fina_cache.py")
    
    # 5. 持仓状态
    acc_path = Path(account_file or './accounts/virtual_2026_account.json')
    if acc_path.exists():
        with open(acc_path) as f:
            account = json.load(f)
        pos_count = len(account.get('positions', []))
        trade_count = len(account.get('trades', []))
        report["checks"]["positions"] = pos_count
        report["checks"]["trades"] = trade_count
        
        if pos_count == 0 and trade_count > 0:
            report["issues"].append(f"持仓为空但有 {trade_count} 笔交易，需重建")
            report["suggestions"].append("运行: python3 rebuild_positions.py")
    else:
        report["checks"]["positions"] = "文件不存在"
    
    # 6. Tushare 连通性
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        report["checks"]["tushare"] = "Token 未设置"
        report["suggestions"].append("export TUSHARE_TOKEN=xxx")
    else:
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            df = pro.daily_basic(trade_date=datetime.now().strftime('%Y%m%d'),
                                fields='ts_code', limit=1)
            if df is not None and len(df) > 0:
                report["checks"]["tushare"] = "✅ 连通"
            else:
                report["checks"]["tushare"] = "今日无数据（可能非交易日）"
        except Exception as e:
            report["checks"]["tushare"] = f"❌ {str(e)[:50]}"
    
    return report


def print_report(report: dict):
    print(f"\n{'='*60}")
    print(f"  VNPY 数据新鲜度报告 ({report['timestamp']})")
    print(f"  状态: {report['status']}")
    print(f"{'='*60}")
    
    print("\n📊 检查项:")
    for key, val in report['checks'].items():
        print(f"  {key}: {val}")
    
    if report['issues']:
        print(f"\n⚠️  问题 ({len(report['issues'])} 项):")
        for i, issue in enumerate(report['issues'], 1):
            print(f"  {i}. {issue}")
    
    if report['suggestions']:
        print(f"\n🔧 建议:")
        for s in report['suggestions']:
            print(f"  → {s}")
    
    print(f"\n{'='*60}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--lab-dir', default='/Users/rowang/projects/vnpy/lab/data')
    parser.add_argument('--account', default=None)
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    args = parser.parse_args()
    
    report = check_freshness(args.lab_dir, args.account)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
