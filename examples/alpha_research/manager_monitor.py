#!/usr/bin/env python3
"""
Manager 问题队列监控和自动处理

功能:
- 检查问题队列状态
- 自动分配问题给对应 Agent
- 跟踪处理进度
- 生成 Human 风格报告

用法:
    python3 manager_monitor.py --action check      # 检查队列
    python3 manager_monitor.py --action process    # 处理问题
    python3 manager_monitor.py --action all        # 检查 + 处理
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager
from human_report import human_manager_report


class ManagerMonitor:
    """Manager 问题队列监控器"""
    
    def __init__(self):
        self.manager = QuantManager()
        self.issue_queue = IssueQueue()
    
    def check_queue(self) -> dict:
        """检查问题队列状态"""
        pending = self.issue_queue.get_pending_issues()
        
        # 统计处理中的问题
        processing_dir = Path('issues/processing')
        processing_count = len(list(processing_dir.glob('*.json'))) if processing_dir.exists() else 0
        
        # 统计已解决的问题
        resolved_dir = Path('issues/resolved')
        resolved_count = len(list(resolved_dir.glob('*.json'))) if resolved_dir.exists() else 0
        
        return {
            'pending': len(pending),
            'processing': processing_count,
            'resolved': resolved_count,
            'timestamp': datetime.now().isoformat()
        }
    
    def process_pending_issues(self) -> dict:
        """处理待处理问题"""
        pending = self.issue_queue.get_pending_issues()
        
        processed_count = 0
        assigned_count = 0
        failed_count = 0
        
        for issue in pending:
            try:
                # 分析问题类型
                task_type = self.manager.analyze_error(issue)
                
                # 选择处理 Agent
                agent = self.manager.select_agent(task_type)
                
                # 创建任务
                task = {
                    'issue_id': issue.id,
                    'agent': agent,
                    'type': task_type,
                    'severity': issue.severity,
                    'status': 'assigned',
                    'assigned_at': datetime.now().isoformat(),
                }
                
                # 更新问题状态
                self.issue_queue.update_status(
                    issue.id,
                    'processing',
                    assigned_to=agent
                )
                
                self.manager.active_tasks[issue.id] = task
                processed_count += 1
                assigned_count += 1
                
            except Exception as e:
                failed_count += 1
                print(f"❌ 处理问题 {issue.id} 失败：{e}")
        
        return {
            'processed': processed_count,
            'assigned': assigned_count,
            'failed': failed_count,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_report(self, check_result: dict, process_result: dict = None) -> str:
        """生成 Human 风格报告"""
        report_data = {
            'pending': check_result['pending'],
            'processing': check_result['processing'],
            'resolved': check_result['resolved'],
        }
        
        if process_result:
            report_data['processed_today'] = process_result['processed']
            report_data['assigned_today'] = process_result['assigned']
        
        return human_manager_report(report_data)


def main():
    parser = argparse.ArgumentParser(description='Manager 问题队列监控器')
    parser.add_argument('--action', type=str, choices=['check', 'process', 'all'],
                       default='check', help='操作类型')
    
    args = parser.parse_args()
    
    monitor = ManagerMonitor()
    
    print("=" * 70)
    print("📊 Manager 问题队列监控")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.action == 'check' or args.action == 'all':
        # 检查队列
        print("【检查问题队列】")
        check_result = monitor.check_queue()
        print(f"  待处理：{check_result['pending']} 个")
        print(f"  处理中：{check_result['processing']} 个")
        print(f"  已解决：{check_result['resolved']} 个")
        print()
    
    if args.action == 'process' or args.action == 'all':
        # 处理问题
        print("【处理待处理问题】")
        process_result = monitor.process_pending_issues()
        print(f"  处理：{process_result['processed']} 个")
        print(f"  已分配：{process_result['assigned']} 个")
        print(f"  失败：{process_result['failed']} 个")
        print()
    
    # 生成 Human 风格报告
    if args.action == 'check' or args.action == 'all':
        report = monitor.generate_report(check_result, process_result if args.action in ['process', 'all'] else None)
        print("=" * 70)
        print("📋 Human 风格报告")
        print("=" * 70)
        print(report)
        print("=" * 70)


if __name__ == '__main__':
    main()
