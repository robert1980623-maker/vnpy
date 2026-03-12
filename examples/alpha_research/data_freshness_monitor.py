#!/usr/bin/env python3
"""
数据新鲜度监控 Agent

职责:
1. 每小时检查数据新鲜度
2. 如果数据滞后，自动触发更新
3. 如果更新失败，通知主 Agent
4. 确保持仓价格、财务数据、消息面数据都是最新的
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import subprocess


class DataFreshnessMonitor:
    """数据新鲜度监控 Agent"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path('./cache/freshness_monitor')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = Path('./reports/data_freshness_report.json')
        
        # 配置
        self.max_age_hours = 24  # 数据最大允许滞后时间（小时）
        self.check_time = datetime.now()
        self.today = self.check_time.strftime('%Y-%m-%d')
        self.yesterday = (self.check_time - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 监控结果
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
        """检查数据新鲜度"""
        print("=" * 70)
        print(" " * 18 + f"数据新鲜度检查 - {self.check_time.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        print(f"期望日期：{self.today}")
        print(f"允许滞后：{self.max_age_hours} 小时")
        print()
        
        if not self.data_dir.exists():
            self.report['status'] = 'error'
            self.report['alerts'].append({
                'level': 'critical',
                'message': f'数据目录不存在：{self.data_dir}',
                'action': '需要创建数据目录或重新下载数据'
            })
            print(f"❌ 数据目录不存在：{self.data_dir}")
            return False
        
        csv_files = list(self.data_dir.glob('*.csv'))
        if not csv_files:
            self.report['status'] = 'error'
            self.report['alerts'].append({
                'level': 'critical',
                'message': '数据目录为空，无股票数据',
                'action': '需要运行 download_data_akshare.py 下载数据'
            })
            print(f"❌ 数据目录为空")
            return False
        
        fresh_count = 0
        stale_count = 0
        stale_stocks = []
        
        for csv_file in csv_files:
            symbol = csv_file.stem.replace('_', '.')
            
            # 读取最后一行获取最新日期 (优化：使用 tail 命令)
            import subprocess
            try:
                result = subprocess.run(
                    ['tail', '-1', str(csv_file)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    last_line = result.stdout.strip().split(',')
                else:
                    continue
            except:
                continue
                if len(last_line) >= 2:
                    data_date = last_line[1]  # datetime 列
                    
                    # 计算数据年龄
                    try:
                        data_datetime = datetime.strptime(data_date, '%Y-%m-%d')
                        age_hours = (self.check_time - data_datetime).total_seconds() / 3600
                        
                        if age_hours <= self.max_age_hours:
                            fresh_count += 1
                        else:
                            stale_count += 1
                            stale_stocks.append({
                                'symbol': symbol,
                                'data_date': data_date,
                                'age_hours': round(age_hours, 1),
                                'file': str(csv_file)
                            })
                    except Exception as e:
                        stale_count += 1
                        stale_stocks.append({
                            'symbol': symbol,
                            'data_date': data_date,
                            'age_hours': None,
                            'error': str(e)
                        })
        
        self.report['fresh_count'] = fresh_count
        self.report['stale_count'] = stale_count
        self.report['stale_stocks'] = stale_stocks[:20]  # 最多记录 20 只
        
        # 判断状态
        total = fresh_count + stale_count
        fresh_ratio = fresh_count / total if total > 0 else 0
        
        if fresh_ratio >= 0.95:
            self.report['status'] = 'fresh'
            print(f"✅ 数据新鲜：{fresh_count}/{total} ({fresh_ratio*100:.1f}%)")
        elif fresh_ratio >= 0.80:
            self.report['status'] = 'partial_stale'
            print(f"⚠️ 部分滞后：{stale_count}/{total} ({(1-fresh_ratio)*100:.1f}%)")
        else:
            self.report['status'] = 'stale'
            print(f"❌ 数据滞后：{stale_count}/{total} ({(1-fresh_ratio)*100:.1f}%)")
        
        print()
        print(f"📊 统计:")
        print(f"  新鲜数据：{fresh_count} 只")
        print(f"  滞后数据：{stale_count} 只")
        
        if stale_stocks:
            print(f"\n📉 滞后股票 Top 10:")
            for stock in sorted(stale_stocks, key=lambda x: x.get('age_hours', 0), reverse=True)[:10]:
                print(f"  - {stock['symbol']}: {stock['data_date']} ({stock.get('age_hours', 'N/A')} 小时前)")
        
        return fresh_ratio >= 0.95
    
    def auto_update_data(self):
        """自动触发数据更新"""
        print("\n" + "=" * 70)
        print(" " * 20 + "自动数据更新")
        print("=" * 70)
        
        # 检查是否是交易日的工作时间
        now = datetime.now()
        is_weekday = now.weekday() < 5  # 周一 - 周五
        is_trading_hour = 9 <= now.hour < 15  # 交易时间 9:00-15:00
        is_after_market = now.hour >= 17  # 盘后 17:00 之后
        
        if not is_weekday:
            print("⚠️ 非交易日，跳过自动更新")
            self.report['actions_taken'].append({
                'action': 'skip_weekend',
                'reason': '非交易日',
                'time': now.isoformat()
            })
            return False
        
        print(f"📅 交易日：{is_weekday}")
        print(f"⏰ 交易时间：{is_trading_hour}")
        print(f"🌆 盘后时间：{is_after_market}")
        
        # 确定更新日期
        if is_after_market:
            # 盘后：下载今日数据
            target_date = self.today
            print(f"📥 盘后模式：下载 {self.today} 数据")
        elif is_trading_hour:
            # 交易中：下载昨日数据（今日数据还不完整）
            target_date = self.yesterday
            print(f"📥 交易中模式：下载 {self.yesterday} 数据")
        else:
            # 其他时间：下载最新数据
            target_date = self.today
            print(f"📥 普通模式：下载 {self.today} 数据")
        
        # 执行数据更新
        try:
            print(f"\n🚀 执行数据更新...")
            
            cmd = [
                sys.executable,
                'download_data_akshare.py',
                '--end', target_date,
                '--max', '100'  # 批量下载
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path(__file__).parent)
            )
            
            if result.returncode == 0:
                print("✅ 数据更新成功")
                self.report['actions_taken'].append({
                    'action': 'auto_update_success',
                    'target_date': target_date,
                    'time': now.isoformat(),
                    'output_lines': len(result.stdout.split('\n'))
                })
                return True
            else:
                print(f"❌ 数据更新失败：{result.stderr[:200]}")
                self.report['actions_taken'].append({
                    'action': 'auto_update_failed',
                    'target_date': target_date,
                    'time': now.isoformat(),
                    'error': result.stderr[:500]
                })
                return False
        
        except subprocess.TimeoutExpired:
            print("❌ 数据更新超时（5 分钟）")
            self.report['actions_taken'].append({
                'action': 'auto_update_timeout',
                'target_date': target_date,
                'time': now.isoformat()
            })
            return False
        
        except Exception as e:
            print(f"❌ 数据更新异常：{e}")
            self.report['actions_taken'].append({
                'action': 'auto_update_error',
                'target_date': target_date,
                'time': now.isoformat(),
                'error': str(e)
            })
            return False
    
    def notify_main_agent(self, alert_level: str = 'warning'):
        """通知主 Agent"""
        print("\n" + "=" * 70)
        print(" " * 20 + "通知主 Agent")
        print("=" * 70)
        
        # 构建告警消息
        if alert_level == 'critical':
            emoji = "🚨"
            title = "紧急：数据严重滞后"
        elif alert_level == 'warning':
            emoji = "⚠️"
            title = "警告：数据部分滞后"
        else:
            emoji = "ℹ️"
            title = "提示：数据新鲜度检查"
        
        message = f"""{emoji} {title}

检查时间：{self.check_time.strftime('%Y-%m-%d %H:%M:%S')}
数据状态：{self.report['status']}

📊 统计:
- 新鲜数据：{self.report['fresh_count']} 只
- 滞后数据：{self.report['stale_count']} 只
- 新鲜率：{self.report['fresh_count']/(self.report['fresh_count']+self.report['stale_count'])*100:.1f}% (如果总数>0)

📉 滞后股票:
{chr(10).join([f"  - {s['symbol']}: {s['data_date']} ({s.get('age_hours', 'N/A')} 小时)" for s in self.report['stale_stocks'][:5]])}

🔧 已执行操作:
{chr(10).join([f"  - {a['action']}: {a.get('reason', a.get('target_date', ''))}" for a in self.report['actions_taken']])}

💡 建议操作:
1. 手动触发数据更新：python3 download_data_akshare.py --end $(date +%Y-%m-%d)
2. 检查数据源是否正常
3. 检查网络连接和 API 配额
"""
        
        print(message)
        
        # 保存告警到文件（主 Agent 可以读取）
        alert_file = self.cache_dir / f"alert_{self.check_time.strftime('%Y%m%d_%H%M')}.json"
        alert_data = {
            'timestamp': self.check_time.isoformat(),
            'level': alert_level,
            'title': title,
            'message': message,
            'report': self.report
        }
        
        with open(alert_file, 'w', encoding='utf-8') as f:
            json.dump(alert_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 告警已保存到：{alert_file}")
        
        # 也可以通过 sessions_send 通知主 Agent（如果有 session）
        # 这需要 OpenClaw 的 sessions_send 工具
        
        return alert_file
    
    def save_report(self):
        """保存检查报告"""
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{self.report_file}")
        return self.report_file
    
    def run(self, auto_fix: bool = True, notify: bool = True):
        """执行完整监控流程"""
        # 步骤 1: 检查新鲜度
        is_fresh = self.check_data_freshness()
        
        if is_fresh:
            print("\n✅ 数据新鲜，无需操作")
            self.save_report()
            return True
        
        # 步骤 2: 自动修复（如果启用）
        if auto_fix:
            update_success = self.auto_update_data()
            
            if update_success:
                # 重新检查
                print("\n🔄 重新检查数据新鲜度...")
                is_fresh = self.check_data_freshness()
                
                if is_fresh:
                    print("\n✅ 数据已更新为最新")
                    self.save_report()
                    return True
        
        # 步骤 3: 通知主 Agent（如果启用且仍有问题）
        if notify and not is_fresh:
            # 判断告警级别
            total = self.report['fresh_count'] + self.report['stale_count']
            fresh_ratio = self.report['fresh_count'] / total if total > 0 else 0
            
            if fresh_ratio < 0.50:
                alert_level = 'critical'
            elif fresh_ratio < 0.80:
                alert_level = 'warning'
            else:
                alert_level = 'info'
            
            self.notify_main_agent(alert_level)
        
        # 保存报告
        self.save_report()
        
        return is_fresh


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据新鲜度监控 Agent')
    parser.add_argument('--once', action='store_true', help='只执行一次检查')
    parser.add_argument('--interval', type=int, default=3600, help='检查间隔（秒），默认 3600 秒')
    parser.add_argument('--no-auto-fix', action='store_true', help='禁用自动修复')
    parser.add_argument('--no-notify', action='store_true', help='禁用通知主 Agent')
    args = parser.parse_args()
    
    monitor = DataFreshnessMonitor()
    
    if args.once:
        # 只执行一次
        monitor.run(
            auto_fix=not args.no_auto_fix,
            notify=not args.no_notify
        )
    else:
        # 持续监控
        print("=" * 70)
        print(" " * 16 + "数据新鲜度监控 Agent 启动")
        print("=" * 70)
        print(f"检查间隔：{args.interval} 秒 ({args.interval/60:.0f} 分钟)")
        print(f"最大允许滞后：{monitor.max_age_hours} 小时")
        print(f"自动修复：{'启用' if not args.no_auto_fix else '禁用'}")
        print(f"通知主 Agent: {'启用' if not args.no_notify else '禁用'}")
        print()
        print("按 Ctrl+C 停止监控")
        print("=" * 70)
        
        try:
            while True:
                monitor.run(
                    auto_fix=not args.no_auto_fix,
                    notify=not args.no_notify
                )
                
                next_check = datetime.now() + timedelta(seconds=args.interval)
                print(f"\n⏰ 下次检查：{next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                import time
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")


if __name__ == '__main__':
    main()
