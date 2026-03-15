#!/usr/bin/env python3
"""
Manager 接口

功能:
- 接收错误上报
- 分析错误类型
- 调度对应 Agent 修复
- 跟踪修复进度
- 生成最终报告
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from issue_queue import IssueQueue, Issue
from alert_notifier import AlertNotifier, Alert
from glm_error_analyzer import GLMErrorAnalyzer


class QuantManager:
    def __init__(self, base_dir: str = "./issues"):
        self.base_dir = base_dir
        self.issue_queue = IssueQueue(base_dir)
        self.notifier = AlertNotifier()
        self.active_tasks: Dict[str, Dict] = {}
        self.agent_mapping = {
            "qa": "qa",
            "trading": "trading-agent",
            "risk": "cro",
            "data": "data-agent",
            "general": "delta",
        }
        self.glm_analyzer = GLMErrorAnalyzer()
    """量化 Manager - 协调调度中心"""
    
    def __init__(self, base_dir: str = "./issues"):
        self.base_dir = Path(base_dir)
        self.issue_queue = IssueQueue(base_dir=base_dir)
        self.notifier = AlertNotifier()
        self.active_tasks: Dict[str, Dict] = {}
        self.glm_analyzer = GLMErrorAnalyzer()
        self.agent_mapping = {
            'qa': 'qa',
            'trading': 'trading-agent',
            'risk': 'cro',
            'data': 'data-agent',
            'engineering': 'delta',
            'general': 'delta',
        }
    
    def handle_error_report(self, issue: Issue):
        """处理错误上报"""
        severity = issue.severity
        
        task_type = self.analyze_error(issue)
        agent = self.select_agent(task_type)
        
        task = {
            'issue_id': issue.id,
            'agent': agent,
            'type': task_type,
            'severity': severity,
            'status': 'assigned',
            'assigned_at': datetime.now().isoformat(),
        }
        
        self.issue_queue.update_status(issue.id, 'processing', assigned_to=agent)
        self.active_tasks[issue.id] = task
        
        if severity == 'P0':
            self.handle_p0(task, issue)
        elif severity == 'P1':
            self.handle_p1(task, issue)
        elif severity == 'P2':
            self.handle_p2(task, issue)
        
        return task
    
    def analyze_error(self, issue: Issue) -> str:
        """分析错误类型"""
        error_type = issue.error_type.lower()
        error_msg = issue.error_message.lower()
        
        rule_result = self._analyze_by_rules(error_type, error_msg)
        if rule_result['confidence'] >= 0.9:
            return rule_result['task_type']
        
        try:
            glm_result = self.glm_analyzer.analyze(
                error_type=issue.error_type,
                error_message=issue.error_message,
                context=None
            )
            if glm_result['confidence'] >= 0.7:
                return glm_result['task_type']
        except Exception as e:
            print(f"⚠️  GLM 分析失败：{e}")
        
        return rule_result['task_type']
    
    def _analyze_by_rules(self, error_type: str, error_msg: str) -> Dict:
        """规则判断"""
        if error_type in ['typeerror', 'keyerror', 'indexerror', 'attributeerror',
                         'nameerror', 'importerror', 'moduleNotFoundError']:
            return {'task_type': 'engineering', 'confidence': 0.95}
        
        if 'test' in error_msg or 'assert' in error_msg:
            return {'task_type': 'qa', 'confidence': 0.9}
        
        if any(kw in error_msg for kw in ['trade', 'order', 'position', 'buy', 'sell']):
            return {'task_type': 'trading', 'confidence': 0.85}
        
        if any(kw in error_msg for kw in ['risk', 'limit', 'stop', 'loss']):
            return {'task_type': 'risk', 'confidence': 0.85}
        
        if any(kw in error_msg for kw in ['data', 'download', 'timeout', 'fetch']):
            return {'task_type': 'data', 'confidence': 0.85}
        
        return {'task_type': 'engineering', 'confidence': 0.5}
    
    def select_agent(self, task_type: str) -> str:
        """选择 Agent"""
        return self.agent_mapping.get(task_type, 'delta')
    
    def handle_p0(self, task: Dict, issue: Issue):
        """处理 P0"""
        agent = task.get('agent', 'delta')
        self.notifier.send_alert(
            self.notifier.create_alert(
                severity='P0',
                agent=issue.agent,
                error=issue.error_message,
                action_taken=f'已调度 {agent} 紧急修复',
                estimated_fix='10-15 分钟'
            )
        )
        self.dispatch_to_delta(issue, priority='urgent')
        return {'status': 'urgent_dispatch', 'agent': agent}
    
    def handle_p1(self, task: Dict, issue: Issue):
        """处理 P1"""
        agent = task.get('agent', 'delta')
        self.notifier.send_alert(
            self.notifier.create_alert(
                severity='P1',
                agent=issue.agent,
                error=issue.error_message,
                action_taken=f'已调度 {agent} 修复',
                estimated_fix='10 分钟'
            )
        )
        self.dispatch_to_delta(issue, priority='high')
        return {'status': 'high_dispatch', 'agent': agent}
    
    def handle_p2(self, task: Dict, issue: Issue):
        """处理 P2"""
        task['status'] = 'queued'
        self.auto_retry_or_queue(issue)
        return {'status': 'queued', 'agent': task.get('agent', 'delta')}
    
    def dispatch_to_delta(self, issue: Issue, priority: str = 'normal'):
        """调度 Delta"""
        delta_task_file = self.base_dir / 'processing' / 'delta_tasks.json'
        
        tasks = []
        if delta_task_file.exists():
            with open(delta_task_file, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        
        tasks.append({
            'issue_id': issue.id,
            'agent': issue.agent,
            'error_type': issue.error_type,
            'error_message': issue.error_message,
            'priority': priority,
            'assigned_at': datetime.now().isoformat(),
            'status': 'pending'
        })
        
        with open(delta_task_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    def _dispatch_to_delta(self, issue: Issue, priority: str = 'high'):
        """私有方法：调度 Delta"""
        self.dispatch_to_delta(issue, priority)
    
    def _dispatch_to_data_agent(self, issue: Issue):
        """私有方法：调度数据 Agent"""
        try:
            self.issue_queue.update_status(
                issue.id,
                'processing',
                assigned_to='data_agent',
                resolution='已调度数据更新 Agent'
            )
            
            import subprocess
            result = subprocess.run(
                ['python3', 'stale_data_updater.py', '--auto'],
                cwd=Path('.'),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.issue_queue.update_status(
                    issue.id,
                    'resolved',
                    resolution='数据已更新'
                )
        except Exception as e:
            print(f"   ❌ 调度失败：{e}")
    
    def auto_retry_or_queue(self, issue: Issue):
        """自动重试"""
        retry_file = self.base_dir / 'processing' / 'auto_retry.json'
        
        retries = []
        if retry_file.exists():
            with open(retry_file, 'r', encoding='utf-8') as f:
                retries = json.load(f)
        
        retries.append({
            'issue_id': issue.id,
            'agent': issue.agent,
            'retry_count': 0,
            'max_retries': 3,
            'next_retry': datetime.now().isoformat(),
        })
        
        with open(retry_file, 'w', encoding='utf-8') as f:
            json.dump(retries, f, ensure_ascii=False, indent=2)
    
    def complete_task(self, issue_id: str, resolution: str, success: bool = True):
        """完成任务"""
        if issue_id not in self.active_tasks:
            # 任务不在活跃列表中，直接更新状态
            if success:
                self.issue_queue.update_status(
                    issue_id,
                    'resolved',
                    resolution=resolution
                )
                return self.generate_completion_report(issue_id, resolution)
            else:
                self.issue_queue.update_status(
                    issue_id,
                    'pending',
                    resolution=f'修复失败：{resolution}'
                )
                return None
        
        task = self.active_tasks[issue_id]
        
        if success:
            self.issue_queue.update_status(issue_id, 'resolved', resolution=resolution)
            del self.active_tasks[issue_id]
            return self.generate_completion_report(issue_id, resolution)
        else:
            # 重新打开问题，状态设为 pending
            self.issue_queue.update_status(
                issue_id,
                'pending',
                resolution=f'修复失败：{resolution}'
            )
            task['status'] = 'failed'
            # 从活跃任务中移除，不重新调度
            if issue_id in self.active_tasks:
                del self.active_tasks[issue_id]
            return None
    
    def resolve_issue(self, issue_id: str, resolution: str, success: bool = True) -> bool:
        """解决问题"""
        return self.complete_task(issue_id, resolution, success=True)
    
    def generate_completion_report(self, issue_id: str, resolution: str) -> Dict:
        """生成完成报告"""
        issue = self.issue_queue.read_issue(issue_id)
        if not issue:
            return {}
        
        report = {
            'type': 'issue_resolved',
            'issue_id': issue_id,
            'agent': issue.agent,
            'severity': issue.severity,
            'problem': issue.error_message,
            'resolution': resolution,
            'resolved_at': issue.resolved_at,
            'status': 'resolved'
        }
        
        if issue.severity in ['P0', 'P1']:
            self.notifier.send_alert(
                self.notifier.create_alert(
                    severity='P3',
                    agent=issue.agent,
                    error=f'问题已解决：{issue.error_message[:50]}',
                    action_taken=resolution,
                    estimated_fix=''
                )
            )
        
        return report
    
    def check_and_process_issues(self):
        """检查并处理问题"""
        print("\n" + "="*70)
        print(" " * 20 + "Manager 检查问题队列")
        print("="*70)
        
        pending = self.issue_queue.get_pending_issues()
        
        if not pending:
            print("\n✅ 无待处理问题")
            return
        
        print(f"\n发现 {len(pending)} 个待处理问题:")
        
        for issue in pending:
            if issue.error_type in ['missing', 'stale_data', 'data_quality']:
                self._dispatch_to_data_agent(issue)
            elif issue.error_type in ['TypeError', 'KeyError', 'AttributeError']:
                self._dispatch_to_delta(issue)
    
    def get_status(self) -> Dict:
        """获取状态"""
        pending = self.issue_queue.get_pending_issues()
        
        return {
            'active_tasks': len(self.active_tasks),
            'pending_issues': len(pending),
            'p0_count': len([i for i in pending if i.severity == 'P0']),
            'p1_count': len([i for i in pending if i.severity == 'P1']),
            'p2_count': len([i for i in pending if i.severity == 'P2']),
        }


def create_manager() -> QuantManager:
    """创建 Manager"""
    return QuantManager()


if __name__ == '__main__':
    manager = QuantManager()
    pending = manager.issue_queue.get_pending_issues()
    print(f"待处理问题：{len(pending)}")
    
    status = manager.get_status()
    print(f"Manager 状态：{status}")
