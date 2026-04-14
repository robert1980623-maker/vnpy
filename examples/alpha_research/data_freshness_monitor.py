#!/usr/bin/env python3
# 通知工具
from notification_utils import notify_task_start, notify_task_complete, notify_task_error

"""数据新鲜度监控 Agent - 修复版"""

import json
import subprocess
import os
import sys
from pathlib import Path
from agent_report import create_report
from report_templates import create_monitoring_report
from datetime import datetime, timedelta

class DataFreshnessMonitor:
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path('./cache/freshness_monitor')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_hours = 24
        self.check_time = datetime.now()
        self.today = self.check_time.strftime('%Y-%m-%d')
        
        self.report = {
            'check_time': self.check_time.isoformat(),
            'expected_date': self.today,
            'status': 'unknown',
            'fresh_count': 0,
            'stale_count': 0,
            'stale_stocks': [],
            'actions_taken': [],
            'alerts': []
        }
    
    def check_data_freshness(self):
        print("=" * 70)
        print(f"数据新鲜度检查 - {self.check_time.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        print(f"期望日期：{self.today}")
        print(f"允许滞后：{self.max_age_hours} 小时\n")
        
        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在：{self.data_dir}")
            return False
        
        csv_files = list(self.data_dir.glob('*.csv'))
        if not csv_files:
            print(f"❌ 数据目录为空")
            return False
        
        print(f"检查 {len(csv_files)} 个文件...\n")
        
        fresh_count = 0
        stale_count = 0
        stale_stocks = []
        
        for csv_file in csv_files:
            symbol = csv_file.stem.replace('_', '.')
            
            try:
                result = subprocess.run(
                    ['tail', '-1', str(csv_file)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0 or not result.stdout.strip():
                    continue
                
                last_line = result.stdout.strip().split(',')
                
                if len(last_line) < 2:
                    continue
                
                data_date = last_line[1]
                # 支持两种日期格式：2026-04-08 (ISO) 和 20260408 (Tushare)
                try:
                    data_datetime = datetime.strptime(data_date, '%Y-%m-%d')
                except ValueError:
                    try:
                        data_datetime = datetime.strptime(data_date, '%Y%m%d')
                    except ValueError:
                        # 无法解析日期格式，跳过该文件
                        continue
                age_hours = (self.check_time - data_datetime).total_seconds() / 3600
                
                # 市场数据允许48小时滞后（覆盖周末和节假日）
                effective_max_age = max(self.max_age_hours, 48)
                if age_hours <= effective_max_age:
                    fresh_count += 1
                else:
                    stale_count += 1
                    stale_stocks.append({
                        'symbol': symbol,
                        'data_date': data_date,
                        'age_hours': round(age_hours, 1)
                    })
                    
            except Exception as e:
                stale_count += 1
        
        self.report['fresh_count'] = fresh_count
        self.report['stale_count'] = stale_count
        self.report['stale_stocks'] = sorted(stale_stocks, key=lambda x: x['age_hours'], reverse=True)[:20]
        
        total = fresh_count + stale_count
        fresh_ratio = fresh_count / total if total > 0 else 0
        
        print(f"📊 统计:")
        print(f"  新鲜数据：{fresh_count} 只")
        print(f"  滞后数据：{stale_count} 只")
        
        if fresh_ratio >= 0.95:
            self.report['status'] = 'fresh'
            print(f"\n✅ 数据新鲜：{fresh_count}/{total} ({fresh_ratio*100:.1f}%)")
        elif fresh_ratio >= 0.80:
            self.report['status'] = 'partial_stale'
            print(f"\n⚠️ 部分滞后：{stale_count}/{total} ({(1-fresh_ratio)*100:.1f}%)")
        else:
            self.report['status'] = 'stale'
            print(f"\n❌ 数据滞后：{stale_count}/{total} ({(1-fresh_ratio)*100:.1f}%)")
        
        if stale_stocks:
            print(f"\n📉 滞后股票 Top 5:")
            for stock in sorted(stale_stocks, key=lambda x: x['age_hours'], reverse=True)[:5]:
                print(f"  - {stock['symbol']}: {stock['data_date']} ({stock['age_hours']} 小时前)")
        
        return fresh_ratio >= 0.95
    
    def save_report(self):
        report_file = Path('./reports/data_freshness_report.json')
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 报告已保存：{report_file}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='数据新鲜度监控')
    parser.add_argument('--once', action='store_true', help='只执行一次')
    parser.add_argument('--no-auto-fix', action='store_true', help='禁用自动修复')
    parser.add_argument('--no-notify', action='store_true', help='禁用通知')
    args = parser.parse_args()
    
    monitor = DataFreshnessMonitor()
    monitor.check_data_freshness()
    monitor.save_report()

if __name__ == '__main__':
    # 发送开始通知
    notify_task_start("数据新鲜度监控", {
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    try:
        main()
        
        # 发送完成通知
        notify_task_complete("数据新鲜度监控", {
            "状态": "完成"
        })
    except Exception as e:
        notify_task_error("数据新鲜度监控", str(e))
        raise
