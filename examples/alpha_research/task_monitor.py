#!/usr/bin/env python3
"""
定时任务监控器
功能：
1. 检查所有 cron 任务状态
2. 检查数据新鲜度
3. 检查账户状态
4. 生成监控报告
5. 发现异常时告警
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from tabulate import tabulate

class TaskMonitor:
    def __init__(self):
        self.cron_file = Path('/Users/rowang/.openclaw/cron/jobs.json')
        self.account_file = Path('./accounts/virtual_2026_account.json')
        self.data_dir = Path('./data/akshare/bars')
        self.report_dir = Path('./reports/monitor')
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def check_cron_tasks(self):
        """检查所有 cron 任务状态"""
        print("\n" + "="*70)
        print("📋 定时任务状态检查")
        print("="*70)
        
        if not self.cron_file.exists():
            print("❌ Cron 配置文件不存在")
            return []
        
        with open(self.cron_file, 'r') as f:
            data = json.load(f)
        
        issues = []
        tasks = []
        
        for job in data.get('jobs', []):
            if not job.get('enabled', True):
                continue
            
            state = job.get('state', {})
            name = job['name']
            status = state.get('lastRunStatus', 'unknown')
            errors = state.get('consecutiveErrors', 0)
            last_run = state.get('lastRunAtMs', 0)
            next_run = state.get('nextRunAtMs', 0)
            
            # 计算上次运行时间
            if last_run > 0:
                last_run_dt = datetime.fromtimestamp(last_run / 1000)
                time_ago = datetime.now() - last_run_dt
            else:
                last_run_dt = None
                time_ago = None
            
            # 计算下次运行时间
            if next_run > 0:
                next_run_dt = datetime.fromtimestamp(next_run / 1000)
            else:
                next_run_dt = None
            
            task_info = {
                'name': name,
                'status': status,
                'errors': errors,
                'last_run': last_run_dt,
                'time_ago': time_ago,
                'next_run': next_run_dt,
                'error_msg': state.get('lastError', None)
            }
            tasks.append(task_info)
            
            # 检查问题
            if status == 'error':
                issues.append(f"❌ {name}: 连续失败 {errors} 次")
                if state.get('lastError'):
                    print(f"   错误：{state['lastError'][:100]}")
            elif time_ago and time_ago > timedelta(hours=24):
                issues.append(f"⚠️ {name}: 超过 24 小时未运行")
            elif errors > 0:
                issues.append(f"⚠️ {name}: 有 {errors} 次错误记录")
        
        # 打印表格
        table_data = []
        for t in sorted(tasks, key=lambda x: x['name']):
            status_icon = "✅" if t['status'] == 'ok' else "❌" if t['status'] == 'error' else "⚠️"
            if t['time_ago']:
                total_seconds = int(t['time_ago'].total_seconds())
                if total_seconds < 60:
                    last_run_str = f"{total_seconds}秒前"
                elif total_seconds < 3600:
                    last_run_str = f"{total_seconds // 60}分钟前"
                else:
                    last_run_str = f"{total_seconds // 3600}小时前"
            else:
                last_run_str = "从未"
            
            table_data.append([
                status_icon,
                t['name'][:25],
                t['status'],
                last_run_str,
                t['errors']
            ])
        
        print(tabulate(table_data, headers=['状态', '任务', '状态', '上次运行', '错误数'], tablefmt='grid'))
        
        return issues
    
    def check_data_freshness(self):
        """检查数据新鲜度"""
        print("\n" + "="*70)
        print("📊 数据新鲜度检查")
        print("="*70)
        
        issues = []
        
        if not self.data_dir.exists():
            print("❌ 数据目录不存在")
            return [f"数据目录不存在：{self.data_dir}"]
        
        # 检查最新数据文件
        csv_files = list(self.data_dir.glob('*.csv'))
        if not csv_files:
            print("❌ 没有找到数据文件")
            return ["没有数据文件"]
        
        # 找到最新的文件时间
        latest_time = max(f.stat().st_mtime for f in csv_files)
        latest_dt = datetime.fromtimestamp(latest_time)
        time_ago = datetime.now() - latest_dt
        
        print(f"最新数据时间：{latest_dt.strftime('%Y-%m-%d %H:%M')}")
        total_seconds = int(time_ago.total_seconds())
        if total_seconds < 3600:
            print(f"距今：{total_seconds // 60}分钟前")
        else:
            print(f"距今：{total_seconds // 3600}小时前")
        
        if time_ago > timedelta(hours=24):
            issues.append(f"⚠️ 数据滞后：最新数据是{total_seconds // 3600}小时前的")
        else:
            print("✅ 数据新鲜")
        
        return issues
    
    def check_account_status(self):
        """检查账户状态"""
        print("\n" + "="*70)
        print("💰 账户状态检查")
        print("="*70)
        
        issues = []
        
        if not self.account_file.exists():
            print("❌ 账户文件不存在")
            return ["账户文件不存在"]
        
        with open(self.account_file, 'r') as f:
            account = json.load(f)
        
        cash = account.get('cash', 0)
        positions = account.get('positions', [])
        total_value = cash + sum(p.get('market_value', 0) for p in positions)
        last_update = account.get('last_update', 'Unknown')
        
        print(f"现金：¥{cash:,.2f}")
        print(f"持仓：{len(positions)}只")
        print(f"总资产：¥{total_value:,.2f}")
        print(f"最后更新：{last_update}")
        
        # 检查现金比例
        cash_ratio = cash / total_value * 100 if total_value > 0 else 0
        if cash_ratio < 5:
            issues.append(f"⚠️ 现金比例过低：{cash_ratio:.1f}% (建议保持 5-10%)")
        elif cash_ratio > 30:
            issues.append(f"⚠️ 现金比例过高：{cash_ratio:.1f}% (资金利用率低)")
        else:
            print("✅ 现金比例合理")
        
        return issues
    
    def generate_report(self, issues):
        """生成监控报告"""
        report_file = self.report_dir / f"task_check_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        report = {
            'check_time': datetime.now().isoformat(),
            'total_issues': len(issues),
            'issues': issues,
            'status': 'error' if issues else 'ok'
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*70)
        print("📝 监控报告")
        print("="*70)
        
        if issues:
            print(f"❌ 发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ 所有任务运行正常，没有发现问题")
        
        print(f"\n报告已保存：{report_file}")
        
        return report
    
    def run(self):
        """运行完整检查"""
        print("\n" + "="*70)
        print(f"🔍 任务监控系统 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        all_issues = []
        
        # 检查 cron 任务
        all_issues.extend(self.check_cron_tasks())
        
        # 检查数据新鲜度
        all_issues.extend(self.check_data_freshness())
        
        # 检查账户状态
        all_issues.extend(self.check_account_status())
        
        # 生成报告
        report = self.generate_report(all_issues)
        
        return report

if __name__ == '__main__':
    monitor = TaskMonitor()
    monitor.run()
