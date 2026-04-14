#!/usr/bin/env python3
"""
Manager 接口 (P0-2 增强版 - 状态追踪)

功能:
- 接收错误上报
- 分析错误类型
- 调度对应 Agent 修复
- 跟踪修复进度 (P0-2 新增)
- 生成最终报告
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from issue_queue import IssueQueue, Issue
from human_report import human_manager_report
from alert_notifier import AlertNotifier, Alert
from vnpy_config import get_manager_config
from glm_error_analyzer import GLMErrorAnalyzer
from file_lock import FileLock


class QuantManager:
    """量化 Manager - 协调调度中心 (P0-2 增强版)"""
    
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
        # P0-2 新增：超时配置（从统一配置读取）
        cfg = get_manager_config()
        self.default_timeout_minutes = cfg.get('default_timeout_minutes', 30)
        self.max_retries = cfg.get('max_retries', 3)

    def handle_error_report(self, issue: Issue):
        """处理错误上报"""
        severity = issue.severity
        
        task_type = self.analyze_error(issue)
        agent = self.select_agent(task_type)
        
        assigned_at = datetime.now().isoformat()
        
        task = {
            'issue_id': issue.id,
            'agent': agent,
            'type': task_type,
            'severity': severity,
            'status': 'assigned',
            'assigned_at': assigned_at,
        }
        
        # P0-2 修复：更新 Issue 状态时添加追踪字段
        self.issue_queue.update_status(
            issue.id, 
            'processing', 
            assigned_to=agent,
            assigned_agent=agent,
            assigned_at=assigned_at,
            timeout_minutes=self.default_timeout_minutes
        )
        self.active_tasks[issue.id] = task
        
        try:
            if severity == 'P0':
                self.handle_p0(task, issue)
            elif severity == 'P1':
                self.handle_p1(task, issue)
            elif severity == 'P2':
                self.handle_p2(task, issue)
        except Exception as e:
            # MG-01 修复：确保异常时也从 active_tasks 清理
            print(f"⚠️ 处理任务时异常：{e}")
            if issue.id in self.active_tasks:
                del self.active_tasks[issue.id]
            raise
        
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
        except Exception as e:  # pragma: no cover
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
        """调度 Delta（线程安全，原子性读写）"""
        delta_task_file = self.base_dir / 'processing' / 'delta_tasks.json'
        
        new_task = {
            'issue_id': issue.id,
            'agent': issue.agent,
            'error_type': issue.error_type,
            'error_message': issue.error_message,
            'priority': priority,
            'assigned_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        def append_task(tasks: List) -> List:
            tasks.append(new_task)
            return tasks
        
        FileLock.locked_read_write(delta_task_file, append_task)
    
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
        except Exception as e:  # pragma: no cover
            print(f"   ❌ 调度失败：{e}")
    
    def auto_retry_or_queue(self, issue: Issue):
        """自动重试（线程安全）"""
        retry_file = self.base_dir / 'processing' / 'auto_retry.json'
        
        new_retry = {
            'issue_id': issue.id,
            'agent': issue.agent,
            'retry_count': 0,
            'max_retries': get_manager_config().get('max_retries', 3),
            'next_retry': datetime.now().isoformat(),
        }
        
        def append_retry(retries: List) -> List:
            retries.append(new_retry)
            return retries
        
        FileLock.locked_read_write(retry_file, append_retry)
    
    # ========== P0-2 新增方法 ==========
    
    def complete_issue(self, issue_id: str, result: Dict = None):
        """
        P0-2 新增：完成 Issue
        
        由 Agent 修复完成后调用，更新状态为 resolved，记录完成时间
        
        Args:
            issue_id: Issue ID
            result: 修复结果（可选）
        """
        completed_at = datetime.now().isoformat()
        
        resolution = result.get('resolution', '修复完成') if result else '修复完成'
        success = result.get('success', True) if result else True
        
        self.issue_queue.update_status(
            issue_id,
            'resolved' if success else 'failed',
            resolution=resolution,
            completed_at=completed_at
        )
        
        # 从活跃任务中移除
        if issue_id in self.active_tasks:
            del self.active_tasks[issue_id]
        
        print(f"✅ Issue {issue_id} 已标记为完成")
        
        # 生成完成报告
        if success:
            self.generate_completion_report(issue_id, resolution)
        
        return success
    
    def retry_issue(self, issue_id: str):
        """
        P0-2 新增：重试 Issue
        
        超时或失败时重新分配，超过 3 次重试升级为 escalated
        
        Args:
            issue_id: Issue ID
        """
        issue = self.issue_queue.read_issue(issue_id)
        if not issue:
            print(f"❌ Issue {issue_id} 不存在")
            return False
        
        retry_count = issue.retry_count + 1
        print(f"🔄 重试 Issue {issue_id} (第 {retry_count}/{self.max_retries} 次)")
        
        if retry_count >= self.max_retries:
            # 超过最大重试次数，升级
            self.issue_queue.update_status(
                issue_id,
                'escalated',
                retry_count=retry_count,
                escalation_level=issue.escalation_level + 1
            )
            print(f"🚨 Issue {issue_id} 已升级，需要人工介入")
            
            # 发送升级通知
            self.notifier.send_alert(
                self.notifier.create_alert(
                    severity='P0',
                    agent=issue.agent,
                    error=f'Issue {issue_id} 重试 {retry_count} 次失败',
                    action_taken='已升级，需要人工介入',
                    estimated_fix=''
                )
            )
        else:
            # 重新分配
            self.issue_queue.update_status(
                issue_id,
                'processing',
                retry_count=retry_count,
                assigned_at=datetime.now().isoformat()
            )
            
            # 重新调度
            task_type = self.analyze_error(issue)
            agent = self.select_agent(task_type)
            self.dispatch_to_delta(issue, priority='high' if retry_count > 1 else 'normal')
            
            print(f"✅ Issue {issue_id} 已重新分配给 {agent}")
        
        return True
    
    def check_timeout(self):
        """
        P0-2 新增：检查超时 Issue
        
        定期检查 processing 状态的 Issue，超时后标记为 timeout，触发重试或升级
        """
        print("\n" + "="*70)
        print(" " * 20 + "检查超时 Issue")
        print("="*70)
        
        processing_issues = self.issue_queue.get_processing_issues()
        now = datetime.now()
        timeout_count = 0
        
        for issue in processing_issues:
            if not issue.assigned_at:
                continue
            
            assigned_at = datetime.fromisoformat(issue.assigned_at)
            timeout_minutes = issue.timeout_minutes or self.default_timeout_minutes
            elapsed = (now - assigned_at).total_seconds() / 60
            
            if elapsed > timeout_minutes:
                print(f"  ⏰ 超时：{issue.id} (已耗时 {elapsed:.0f} 分钟，上限 {timeout_minutes} 分钟)")
                timeout_count += 1
                
                # 标记为 timeout
                self.issue_queue.update_status(
                    issue.id,
                    'timeout',
                    resolution=f'执行超时 ({elapsed:.0f} 分钟)'
                )
                
                # 触发重试
                self.retry_issue(issue.id)
        
        if timeout_count == 0:
            print("  ✅ 无超时 Issue")
        else:
            print(f"\n📊 统计：{timeout_count} 个 Issue 超时")
        
        return timeout_count
    
    def track_agent_execution(self, issue_id: str, agent: str, timeout: int = 300, 
                               poll_interval: int = 2) -> Dict:
        """
        P0-2 新增：追踪 Agent 执行结果
        
        MG-02 修复：从阻塞轮询改为带超时的非阻塞轮询
        
        Args:
            issue_id: Issue ID
            agent: 执行的 Agent 名称
            timeout: 超时时间（秒），默认 300 秒
            poll_interval: 轮询间隔（秒），默认 2 秒（原为 5 秒）
        
        Returns:
            {'status': 'success'/'failed'/'timeout', 'result': ...}
        """
        start_time = time.time()
        
        # MG-02 修复：轮询间隔从 5 秒减少到 2 秒，提高响应速度
        if poll_interval < 1:
            poll_interval = 1  # 最小 1 秒
        
        while time.time() - start_time < timeout:
            # 检查 Agent 是否完成
            result_file = Path(f'./reports/agent_results/{issue_id}.json')
            if result_file.exists():
                with open(result_file, 'r') as f:
                    result = json.load(f)
                
                # 更新 Issue 状态
                if result.get('status') == 'success':
                    self.complete_issue(issue_id, result)
                else:
                    self.retry_issue(issue_id)
                
                return result
            
            # 非阻塞等待：只 sleep 一个轮询间隔
            time.sleep(poll_interval)
        
        # 超时
        self.retry_issue(issue_id)
        return {'status': 'timeout'}
    
    def check_agent_execution(self, issue_id: str) -> Dict:
        """
        MG-02 新增：非阻塞检查 Agent 执行状态
        
        不等待，立即返回当前状态
        
        Returns:
            {'status': 'running'/'completed'/'not_found', 'result': ...}
        """
        result_file = Path(f'./reports/agent_results/{issue_id}.json')
        if result_file.exists():
            with open(result_file, 'r') as f:
                result = json.load(f)
            return {'status': 'completed', 'result': result}
        
        # 检查 Issue 状态
        issue = self.issue_queue.read_issue(issue_id)
        if issue:
            if issue.status in ['resolved', 'failed', 'escalated']:
                return {'status': 'completed', 'result': {'status': issue.status}}
            return {'status': 'running'}
        
        return {'status': 'not_found'}
    
    # ========== 原有方法 ==========
    
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
        
        # 先检查超时
        self.check_timeout()
        
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
        processing = self.issue_queue.get_processing_issues()
        
        return {
            'active_tasks': len(self.active_tasks),
            'pending_issues': len(pending),
            'processing_issues': len(processing),
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
    
    # 检查超时
    manager.check_timeout()
