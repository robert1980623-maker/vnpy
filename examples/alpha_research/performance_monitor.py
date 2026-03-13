#!/usr/bin/env python3
"""
性能监控面板

功能:
- 任务执行时间监控
- API 响应延迟监控
- 错误率/成功率统计
- 资源使用率监控
- 性能告警
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: str
    task_name: str
    execution_time: float  # 执行时间 (秒)
    success: bool
    error_message: Optional[str] = None
    api_latency: Optional[float] = None  # API 延迟 (毫秒)
    memory_usage: Optional[float] = None  # 内存使用 (MB)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, log_dir: str = './logs/performance'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置文件
        self.config_file = Path('./config/performance_config.yaml')
        self.config = self._load_config()
        
        # 性能数据
        self.metrics: List[PerformanceMetrics] = []
        
        # 告警阈值
        self.thresholds = {
            'max_execution_time': 300,  # 5 分钟
            'max_api_latency': 5000,    # 5 秒
            'max_error_rate': 0.05,     # 5%
            'min_success_rate': 0.95    # 95%
        }
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if self.config_file.exists():
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def record_metric(self, task_name: str, execution_time: float, 
                     success: bool, error_message: str = None,
                     api_latency: float = None):
        """记录性能指标"""
        metric = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            task_name=task_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            api_latency=api_latency
        )
        
        self.metrics.append(metric)
        
        # 保存到日志
        self._save_metric(metric)
        
        # 检查是否触发告警
        self._check_alerts(metric)
    
    def _save_metric(self, metric: PerformanceMetrics):
        """保存指标到日志"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f'performance_{date_str}.jsonl'
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(metric), ensure_ascii=False) + '\n')
    
    def _check_alerts(self, metric: PerformanceMetrics):
        """检查是否触发告警"""
        alerts = []
        
        # 执行时间过长
        if metric.execution_time > self.thresholds['max_execution_time']:
            alerts.append(f"⚠️ 任务执行时间过长：{metric.task_name} ({metric.execution_time:.1f}s)")
        
        # API 延迟过高
        if metric.api_latency and metric.api_latency > self.thresholds['max_api_latency']:
            alerts.append(f"⚠️ API 延迟过高：{metric.task_name} ({metric.api_latency:.0f}ms)")
        
        # 任务失败
        if not metric.success:
            alerts.append(f"❌ 任务失败：{metric.task_name}")
            if metric.error_message:
                alerts.append(f"   错误：{metric.error_message[:100]}")
        
        # 发送告警
        if alerts:
            self._send_alert(alerts)
    
    def _send_alert(self, alerts: List[str]):
        """发送告警"""
        alert_message = "\n".join(alerts)
        
        # 保存到告警日志
        date_str = datetime.now().strftime('%Y-%m-%d')
        alert_file = self.log_dir / f'alerts_{date_str}.txt'
        
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now().isoformat()}]\n")
            f.write(alert_message + "\n\n")
        
        # 打印告警
        print("\n" + "!"*60)
        print("⚠️  性能告警")
        print("!"*60)
        for alert in alerts:
            print(alert)
        print("!"*60 + "\n")
    
    def generate_report(self, days: int = 1) -> Dict:
        """生成性能报告"""
        # 读取历史数据
        metrics = self._load_metrics(days)
        
        if not metrics:
            return {'period_days': days, 'summary': {}, 'task_stats': {}, 'error': '无数据'}
        
        # 统计分析
        total_tasks = len(metrics)
        success_tasks = sum(1 for m in metrics if m['success'])
        failed_tasks = total_tasks - success_tasks
        
        success_rate = success_tasks / total_tasks if total_tasks > 0 else 0
        error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
        
        avg_execution_time = sum(m['execution_time'] for m in metrics) / total_tasks
        max_execution_time = max(m['execution_time'] for m in metrics)
        
        # 按任务统计
        task_stats = {}
        for m in metrics:
            task_name = m['task_name']
            if task_name not in task_stats:
                task_stats[task_name] = {
                    'count': 0,
                    'success': 0,
                    'failed': 0,
                    'total_time': 0,
                    'avg_time': 0
                }
            
            task_stats[task_name]['count'] += 1
            task_stats[task_name]['total_time'] += m['execution_time']
            
            if m['success']:
                task_stats[task_name]['success'] += 1
            else:
                task_stats[task_name]['failed'] += 1
        
        # 计算平均时间
        for task_name in task_stats:
            task_stats[task_name]['avg_time'] = (
                task_stats[task_name]['total_time'] / task_stats[task_name]['count']
            )
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'period_days': days,
            'summary': {
                'total_tasks': total_tasks,
                'success_tasks': success_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': f"{success_rate*100:.1f}%",
                'error_rate': f"{error_rate*100:.1f}%",
                'avg_execution_time': f"{avg_execution_time:.2f}s",
                'max_execution_time': f"{max_execution_time:.2f}s"
            },
            'task_stats': task_stats
        }
        
        return report
    
    def _load_metrics(self, days: int) -> List[Dict]:
        """加载历史数据"""
        metrics = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            log_file = self.log_dir / f'performance_{date_str}.jsonl'
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        metrics.append(json.loads(line))
        
        return metrics
    
    def print_report(self, days: int = 1):
        """打印性能报告"""
        report = self.generate_report(days)
        
        print("\n" + "="*70)
        print(" " * 20 + "性能监控报告")
        print("="*70)
        print(f"统计周期：{report['period_days']} 天")
        print(f"生成时间：{report['timestamp']}")
        print()
        
        if 'error' in report:
            print(report['error'])
            return
        
        summary = report['summary']
        print("📊 总体统计:")
        print(f"  总任务数：{summary['total_tasks']}")
        print(f"  成功：{summary['success_tasks']} ({summary['success_rate']})")
        print(f"  失败：{summary['failed_tasks']} ({summary['error_rate']})")
        print(f"  平均执行时间：{summary['avg_execution_time']}")
        print(f"  最长执行时间：{summary['max_execution_time']}")
        print()
        
        print("📋 任务统计:")
        for task_name, stats in sorted(report['task_stats'].items(), 
                                      key=lambda x: x[1]['count'], reverse=True)[:10]:
            print(f"\n  {task_name}:")
            print(f"    执行次数：{stats['count']}")
            print(f"    成功：{stats['success']} ({stats['success']/stats['count']*100:.1f}%)")
            print(f"    失败：{stats['failed']} ({stats['failed']/stats['count']*100:.1f}%)")
            print(f"    平均时间：{stats['avg_time']:.2f}s")
        
        print("\n" + "="*70)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='性能监控')
    parser.add_argument('--report', action='store_true', help='生成报告')
    parser.add_argument('--days', type=int, default=1, help='统计天数')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor()
    
    if args.report:
        monitor.print_report(args.days)
    else:
        print("性能监控器已就绪")
        print("使用 --report 生成报告")


if __name__ == '__main__':
    main()


# 集成到 Cron 任务的装饰器
def monitor_performance(task_name: str):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                
                # 记录性能指标
                monitor = PerformanceMonitor()
                monitor.record_metric(
                    task_name=task_name,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message
                )
        
        return wrapper
    return decorator
