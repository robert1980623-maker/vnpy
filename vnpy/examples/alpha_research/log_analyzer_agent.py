#!/usr/bin/env python3
"""
日志分析 Agent

职责:
1. 每 30 分钟检查日志
2. 分析错误模式和频率
3. 发现异常时通知主 Agent
4. 建议调用 Delta 修复

模型：lmstudio/zai-org/glm-4.7-flash
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess


class LogAnalyzerAgent:
    """日志分析 Agent"""
    
    def __init__(self, log_dir: str = './logs'):
        self.log_dir = Path(log_dir)
        self.cache_dir = Path('./cache/log_analyzer')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置
        self.check_interval_minutes = 30
        self.error_threshold_per_hour = 5  # 每小时错误阈值
        self.critical_threshold = 1  # CRITICAL 级别立即告警
        
        # 分析结果
        self.analysis_result = {
            'check_time': datetime.now().isoformat(),
            'status': 'unknown',
            'error_count': 0,
            'critical_count': 0,
            'warning_count': 0,
            'error_patterns': [],
            'affected_tasks': [],
            'alerts': [],
            'suggested_actions': []
        }
    
    def read_error_logs(self, hours: int = 2) -> list:
        """读取最近 N 小时的错误日志"""
        errors = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 读取今日错误日志
        today = datetime.now().strftime('%Y-%m-%d')
        error_log_file = self.log_dir / f"errors_{today}.jsonl"
        
        if error_log_file.exists():
            with open(error_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        error_data = json.loads(line.strip())
                        error_time = datetime.fromisoformat(error_data['timestamp'])
                        
                        if error_time >= cutoff_time:
                            errors.append(error_data)
                    except:
                        continue
        
        return errors
    
    def analyze_errors(self, errors: list) -> dict:
        """分析错误模式"""
        if not errors:
            return {
                'total': 0,
                'by_level': {},
                'by_task': {},
                'by_exception': {},
                'trends': 'stable'
            }
        
        # 按级别统计
        by_level = defaultdict(int)
        for error in errors:
            level = error.get('level', 'ERROR')
            by_level[level] += 1
        
        # 按任务统计
        by_task = defaultdict(int)
        for error in errors:
            task = error.get('task_name', 'unknown')
            by_task[task] += 1
        
        # 按异常类型统计
        by_exception = defaultdict(int)
        for error in errors:
            exc_type = error.get('exception_type', 'Unknown')
            if exc_type:
                by_exception[exc_type] += 1
        
        # 计算错误率（每小时）
        hours_span = 2  # 分析最近 2 小时
        errors_per_hour = len(errors) / hours_span
        
        # 判断趋势
        if errors_per_hour > self.error_threshold_per_hour * 2:
            trends = 'increasing_fast'
        elif errors_per_hour > self.error_threshold_per_hour:
            trends = 'increasing'
        else:
            trends = 'stable'
        
        return {
            'total': len(errors),
            'by_level': dict(by_level),
            'by_task': dict(by_task),
            'by_exception': dict(by_exception),
            'errors_per_hour': round(errors_per_hour, 1),
            'trends': trends
        }
    
    def detect_anomalies(self, error_stats: dict) -> list:
        """检测异常"""
        anomalies = []
        
        # 1. 检查 CRITICAL 错误
        critical_count = error_stats['by_level'].get('CRITICAL', 0)
        if critical_count >= self.critical_threshold:
            anomalies.append({
                'type': 'critical_errors',
                'severity': 'high',
                'message': f'发现 {critical_count} 个 CRITICAL 级别错误',
                'action': '立即通知主 Agent'
            })
        
        # 2. 检查错误率
        if error_stats['trends'] == 'increasing_fast':
            anomalies.append({
                'type': 'error_rate_high',
                'severity': 'high',
                'message': f'错误率过高：{error_stats["errors_per_hour"]}/小时',
                'action': '需要检查系统健康'
            })
        elif error_stats['trends'] == 'increasing':
            anomalies.append({
                'type': 'error_rate_increasing',
                'severity': 'medium',
                'message': f'错误率上升：{error_stats["errors_per_hour"]}/小时',
                'action': '需要关注'
            })
        
        # 3. 检查单一任务频繁失败
        for task, count in error_stats['by_task'].items():
            if count >= 5:  # 同一任务失败 5 次以上
                anomalies.append({
                    'type': 'task_repeated_failure',
                    'severity': 'medium',
                    'message': f'任务 {task} 频繁失败 ({count} 次)',
                    'action': f'调用 Delta 修复 {task}'
                })
        
        # 4. 检查特定异常类型
        for exc_type, count in error_stats['by_exception'].items():
            if count >= 3 and exc_type not in ['ValueError', 'KeyError']:
                anomalies.append({
                    'type': 'exception_pattern',
                    'severity': 'medium',
                    'message': f'异常模式：{exc_type} 出现 {count} 次',
                    'action': '需要代码审查'
                })
        
        return anomalies
    
    def generate_alert(self, anomalies: list, error_stats: dict) -> dict:
        """生成告警"""
        if not anomalies:
            return None
        
        # 确定告警级别
        severities = [a['severity'] for a in anomalies]
        if 'high' in severities:
            alert_level = 'critical'
            emoji = '🚨'
        elif 'medium' in severities:
            alert_level = 'warning'
            emoji = '⚠️'
        else:
            alert_level = 'info'
            emoji = 'ℹ️'
        
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': alert_level,
            'emoji': emoji,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'error_stats': error_stats,
            'suggested_actions': self._generate_suggested_actions(anomalies)
        }
        
        return alert
    
    def _generate_suggested_actions(self, anomalies: list) -> list:
        """生成建议操作"""
        actions = []
        
        for anomaly in anomalies:
            if anomaly['type'] == 'critical_errors':
                actions.append({
                    'priority': 1,
                    'action': 'notify_main_agent',
                    'description': '立即通知主 Agent',
                    'details': '发现 CRITICAL 级别错误，需要紧急处理'
                })
            
            elif anomaly['type'] == 'task_repeated_failure':
                task_name = anomaly['message'].split('任务 ')[1].split(' ')[0] if '任务 ' in anomaly['message'] else 'unknown'
                actions.append({
                    'priority': 2,
                    'action': 'call_delta',
                    'description': f'调用 Delta 修复 {task_name}',
                    'details': f'任务 {task_name} 频繁失败，需要代码修复'
                })
            
            elif anomaly['type'] == 'error_rate_high':
                actions.append({
                    'priority': 1,
                    'action': 'check_system_health',
                    'description': '检查系统健康状态',
                    'details': '错误率过高，需要全面检查'
                })
        
        # 按优先级排序
        actions.sort(key=lambda x: x['priority'])
        
        return actions
    
    def notify_main_agent(self, alert: dict):
        """通知主 Agent"""
        print("\n" + "=" * 70)
        print(" " * 20 + "通知主 Agent")
        print("=" * 70)
        
        message = f"""{alert['emoji']} 日志分析告警 - {alert['level'].upper()}

检查时间：{alert['timestamp']}
异常数量：{alert['anomaly_count']} 个

📊 错误统计:
- 总错误数：{alert['error_stats']['total']}
- 每小时错误率：{alert['error_stats'].get('errors_per_hour', 'N/A')}
- 趋势：{alert['error_stats'].get('trends', 'N/A')}

🔴 异常详情:
"""
        
        for i, anomaly in enumerate(alert['anomalies'], 1):
            message += f"\n{i}. [{anomaly['severity'].upper()}] {anomaly['message']}"
            message += f"\n   操作：{anomaly['action']}"
        
        message += "\n\n💡 建议操作:\n"
        for action in alert['suggested_actions']:
            message += f"\n{action['priority']}. {action['description']}"
            message += f"\n   {action['details']}"
        
        print(message)
        
        # 保存告警文件
        alert_file = self.cache_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(alert_file, 'w', encoding='utf-8') as f:
            json.dump(alert, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 告警已保存：{alert_file}")
        
        # 保存主 Agent 可读的通知文件
        main_agent_notification = self.cache_dir / 'main_agent_notification.json'
        notification = {
            'type': 'log_analysis_alert',
            'timestamp': alert['timestamp'],
            'level': alert['level'],
            'message': alert['emoji'] + ' 日志异常，需要处理',
            'alert': alert,
            'requires_delta': any(a['action'] == 'call_delta' for a in alert['suggested_actions'])
        }
        
        with open(main_agent_notification, 'w', encoding='utf-8') as f:
            json.dump(notification, f, ensure_ascii=False, indent=2)
        
        print(f"📩 主 Agent 通知已保存：{main_agent_notification}")
        
        return alert_file
    
    def save_analysis_report(self):
        """保存分析报告"""
        report_file = self.cache_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"📄 分析报告已保存：{report_file}")
        return report_file
    
    def run(self, notify: bool = True):
        """执行完整分析流程"""
        print("=" * 70)
        print(" " * 16 + f"日志分析 Agent - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        
        # 步骤 1: 读取错误日志
        print(f"\n📖 读取最近 2 小时错误日志...")
        errors = self.read_error_logs(hours=2)
        print(f"  发现 {len(errors)} 条错误记录")
        
        if not errors:
            print("\n✅ 无错误日志，系统健康")
            self.analysis_result['status'] = 'healthy'
            self.analysis_result['error_count'] = 0
            self.save_analysis_report()
            return True
        
        # 步骤 2: 分析错误
        print(f"\n🔍 分析错误模式...")
        error_stats = self.analyze_errors(errors)
        
        print(f"  总错误数：{error_stats['total']}")
        print(f"  每小时错误率：{error_stats.get('errors_per_hour', 'N/A')}")
        print(f"  趋势：{error_stats.get('trends', 'N/A')}")
        
        if error_stats['by_task']:
            print(f"\n  按任务统计:")
            for task, count in sorted(error_stats['by_task'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {task}: {count} 次")
        
        if error_stats['by_exception']:
            print(f"\n  按异常类型:")
            for exc, count in sorted(error_stats['by_exception'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {exc}: {count} 次")
        
        # 步骤 3: 检测异常
        print(f"\n🚨 检测异常...")
        anomalies = self.detect_anomalies(error_stats)
        
        if not anomalies:
            print("  ✅ 未检测到异常")
            self.analysis_result['status'] = 'healthy'
        else:
            print(f"  ⚠️ 发现 {len(anomalies)} 个异常")
            for anomaly in anomalies[:3]:
                print(f"    - [{anomaly['severity']}] {anomaly['message']}")
        
        # 步骤 4: 生成告警
        self.analysis_result['error_count'] = error_stats['total']
        self.analysis_result['error_patterns'] = anomalies
        
        if anomalies:
            alert = self.generate_alert(anomalies, error_stats)
            self.analysis_result['alerts'] = anomalies
            self.analysis_result['suggested_actions'] = alert['suggested_actions'] if alert else []
            self.analysis_result['status'] = 'anomaly_detected'
            
            # 步骤 5: 通知主 Agent
            if notify:
                self.notify_main_agent(alert)
        else:
            self.analysis_result['status'] = 'healthy'
        
        # 保存报告
        self.save_analysis_report()
        
        print("\n" + "=" * 70)
        print(" " * 20 + "分析完成")
        print("=" * 70)
        
        return len(anomalies) == 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='日志分析 Agent')
    parser.add_argument('--once', action='store_true', help='只执行一次检查')
    parser.add_argument('--interval', type=int, default=1800, help='检查间隔（秒），默认 1800 秒 (30 分钟)')
    parser.add_argument('--no-notify', action='store_true', help='禁用通知主 Agent')
    args = parser.parse_args()
    
    agent = LogAnalyzerAgent()
    
    if args.once:
        # 只执行一次
        agent.run(notify=not args.no_notify)
    else:
        # 持续监控
        print("=" * 70)
        print(" " * 18 + "日志分析 Agent 启动")
        print("=" * 70)
        print(f"检查间隔：{args.interval} 秒 ({args.interval/60:.0f} 分钟)")
        print(f"错误阈值：{agent.error_threshold_per_hour}/小时")
        print(f"通知主 Agent: {'启用' if not args.no_notify else '禁用'}")
        print()
        print("按 Ctrl+C 停止监控")
        print("=" * 70)
        
        try:
            while True:
                agent.run(notify=not args.no_notify)
                
                next_check = datetime.now() + timedelta(seconds=args.interval)
                print(f"\n⏰ 下次检查：{next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                import time
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")


if __name__ == '__main__':
    main()
