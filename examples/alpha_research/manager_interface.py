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
    """量化 Manager - 协调调度中心"""
    
    def __init__(self):
        self.issue_queue = IssueQueue()
        self.notifier = AlertNotifier()
        self.active_tasks: Dict[str, Dict] = {}
        self.agent_mapping = {
        self.glm_analyzer = GLMErrorAnalyzer()  # GLM 错误分析器
            'engineering': 'delta',
            'qa': 'qa',
            'trading': 'trading-agent',
            'risk': 'cro',
            'data': 'data-agent',
            'general': 'delta',
        }
    
    def handle_error_report(self, issue: Issue):
        """处理错误上报"""
        severity = issue.severity
        
        # 分析错误类型
        task_type = self.analyze_error(issue)
        
        # 选择负责的 Agent
        agent = self.select_agent(task_type)
        
        # 创建任务
        task = {
            'issue_id': issue.id,
            'agent': agent,
            'type': task_type,
            'severity': severity,
            'status': 'assigned',
            'assigned_at': datetime.now().isoformat(),
        }
        
        # 更新问题状态
        self.issue_queue.update_status(
            issue.id, 
            'processing',
            assigned_to=agent
        )
        
        # 记录活跃任务
        self.active_tasks[issue.id] = task
        
        # 根据严重性处理
        if severity == 'P0':
            self.handle_p0(task, issue)
        elif severity == 'P1':
            self.handle_p1(task, issue)
        elif severity == 'P2':
            self.handle_p2(task, issue)
        
        return task
    
    def analyze_error(self, issue: Issue) -> str:
        """分析错误类型 (GLM 增强版)
        
        流程:
        1. 先用规则判断 (快速、准确)
        2. 规则不确定时用 GLM 分析 (智能、灵活)
        3. GLM 失败时 fallback 到默认规则
        """
        error_type = issue.error_type.lower()
        error_msg = issue.error_message.lower()
        
        # 步骤 1: 规则判断 (高置信度直接返回)
        rule_result = self._analyze_by_rules(error_type, error_msg)
        if rule_result['confidence'] >= 0.9:
            return rule_result['task_type']
        
        # 步骤 2: GLM 分析 (规则不确定时)
        try:
            glm_result = self.glm_analyzer.analyze(
                error_type=issue.error_type,
                error_message=issue.error_message,
                context=None  # 可以添加更多上下文
            )
            
            # GLM 置信度高则采用
            if glm_result['confidence'] >= 0.7:
                print(f"🤖 GLM 分析：{rule_result['task_type']} → {glm_result['task_type']} "
                      f"(置信度：{glm_result['confidence']:.2f})")
                return glm_result['task_type']
        except Exception as e:
            print(f"⚠️  GLM 分析失败：{e}, 使用规则判断")
        
        # 步骤 3: Fallback 到规则结果
        return rule_result['task_type']
    
    def _analyze_by_rules(self, error_type: str, error_msg: str) -> Dict:
        """规则判断 (带置信度)"""
        # 工程类错误 (代码 bug) - 高置信度
        if error_type in ['typeerror', 'keyerror', 'indexerror', 'attributeerror',
                         'nameerror', 'importerror', 'moduleNotFoundError']:
            return {'task_type': 'engineering', 'confidence': 0.95}
        
        # QA 类错误 (测试失败)
        if 'test' in error_msg or 'assert' in error_msg:
            return {'task_type': 'qa', 'confidence': 0.9}
        
        # 交易类错误
        if any(kw in error_msg for kw in ['trade', 'order', 'position', 'buy', 'sell']):
            return {'task_type': 'trading', 'confidence': 0.85}
        
        # 风控类错误
        if any(kw in error_msg for kw in ['risk', 'limit', 'stop', 'loss']):
            return {'task_type': 'risk', 'confidence': 0.85}
        
        # 数据类错误
        if any(kw in error_msg for kw in ['data', 'download', 'timeout', 'fetch']):
            return {'task_type': 'data', 'confidence': 0.85}
        
        # 默认工程类 - 低置信度
        return {'task_type': 'engineering', 'confidence': 0.5}
    
    def select_agent(self, task_type: str) -> str:
        """选择合适的 Agent"""
        return self.agent_mapping.get(task_type, 'delta')
    
    def handle_p0(self, task: Dict, issue: Issue):
        """处理 P0 严重错误"""
        # 立即通知
        self.notifier.send_alert(
            self.notifier.create_alert(
                severity='P0',
                agent=issue.agent,
                error=issue.error_message,
                action_taken=f'已调度 {task["agent"]} 紧急修复',
                estimated_fix='10-15 分钟'
            )
        )
        
        # 紧急调度 Delta
        self.dispatch_to_delta(issue, priority='urgent')
    
    def handle_p1(self, task: Dict, issue: Issue):
        """处理 P1 功能异常"""
        # 通知
        self.notifier.send_alert(
            self.notifier.create_alert(
                severity='P1',
                agent=issue.agent,
                error=issue.error_message,
                action_taken=f'已调度 {task["agent"]} 修复',
                estimated_fix='10 分钟'
            )
        )
        
        # 调度 Delta
        self.dispatch_to_delta(issue, priority='high')
    
    def handle_p2(self, task: Dict, issue: Issue):
        """处理 P2 性能问题"""
        # 记录但不立即通知
        task['status'] = 'queued'
        
        # 自动重试或加入待办
        self.auto_retry_or_queue(issue)
    
    def dispatch_to_delta(self, issue: Issue, priority: str = 'normal'):
        """调度 Delta 工程师修复"""
        # 写入 Delta 任务队列
        delta_task_file = Path('./issues/processing/delta_tasks.json')
        
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
    
    def auto_retry_or_queue(self, issue: Issue):
        """自动重试或加入待办"""
        # 对于 P2 问题，尝试自动重试
        # 如果重试失败，加入待办队列
        retry_file = Path('./issues/processing/auto_retry.json')
        
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
            return False
        
        task = self.active_tasks[issue_id]
        
        if success:
            # 更新问题状态为已解决
            self.issue_queue.update_status(
                issue_id,
                'resolved',
                resolution=resolution
            )
            
            # 移除活跃任务
            del self.active_tasks[issue_id]
            
            # 生成完成报告
            report = self.generate_completion_report(issue_id, resolution)
            
            return report
        else:
            # 修复失败，重新打开
            self.issue_queue.update_status(
                issue_id,
                'pending',
                resolution=f'修复失败：{resolution}'
            )
            
            # 重新调度
            task['status'] = 'failed'
            self.handle_error_report(self.issue_queue.read_issue(issue_id))
            
            return None
    
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
        
        # 如果 severity 是 P0/P1，发送完成通知
        if issue.severity in ['P0', 'P1']:
            self.notifier.send_alert(
                self.notifier.create_alert(
                    severity='P3',  # 使用 P3 作为完成通知
                    agent=issue.agent,
                    error=f'问题已解决：{issue.error_message[:50]}',
                    action_taken=resolution,
                    estimated_fix=''
                )
            )
        
        return report
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        pending = self.issue_queue.get_pending_issues()
        
        return {
            'active_tasks': len(self.active_tasks),
            'pending_issues': len(pending),
            'p0_count': len([i for i in pending if i.severity == 'P0']),
            'p1_count': len([i for i in pending if i.severity == 'P1']),
            'p2_count': len([i for i in pending if i.severity == 'P2']),
        }


# 快捷函数
def create_manager() -> QuantManager:
    """创建 Manager 实例"""
    return QuantManager()


if __name__ == '__main__':
    # 测试
    manager = QuantManager()
    
    # 读取测试问题
    pending = manager.issue_queue.get_pending_issues()
    print(f"待处理问题：{len(pending)}")
    
    for issue in pending[:1]:
        print(f"\n处理问题：{issue.id}")
        task = manager.handle_error_report(issue)
        print(f"已调度给：{task['agent']}")
        print(f"任务类型：{task['type']}")
    
    # 获取状态
    status = manager.get_status()
    print(f"\nManager 状态：{status}")

    def check_and_process_issues(self):
        """自动检查并处理问题队列"""
        print("\n" + "="*70)
        print(" " * 20 + "Manager 检查问题队列")
        print("="*70)
        
        # 获取待处理问题
        pending = self.issue_queue.get_pending_issues()
        
        if not pending:
            print("\n✅ 无待处理问题")
            return
        
        print(f"\n发现 {len(pending)} 个待处理问题:")
        
        for issue in pending:
            print(f"\n📌 {issue.id}")
            print(f"   Agent: {issue.agent}")
            print(f"   严重性：{issue.severity}")
            print(f"   类型：{issue.error_type}")
            print(f"   消息：{issue.error_message[:50]}...")
            
            # 分析问题类型并调度
            if issue.error_type in ['missing', 'stale_data', 'data_quality']:
                print(f"   → 调度数据更新 Agent")
                self._dispatch_to_data_agent(issue)
            elif issue.error_type in ['TypeError', 'KeyError', 'AttributeError']:
                print(f"   → 调度 Delta 工程师")
                self._dispatch_to_delta(issue)
            else:
                print(f"   → 记录待处理")
    
    def _dispatch_to_data_agent(self, issue):
        """调度数据更新 Agent"""
        try:
            # 更新问题状态为处理中
            self.issue_queue.update_status(
                issue.id,
                'processing',
                assigned_to='data_agent',
                resolution='已调度数据更新 Agent'
            )
            
            # 触发数据更新脚本
            import subprocess
            result = subprocess.run(
                ['python3', 'stale_data_updater.py', '--auto'],
                cwd=Path('.'),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                # 更新问题为已解决
                self.issue_queue.update_status(
                    issue.id,
                    'resolved',
                    resolution='数据已更新'
                )
                print(f"   ✅ 数据更新完成")
            else:
                print(f"   ⚠️ 数据更新失败：{result.stderr[:100]}")
                
        except Exception as e:
            print(f"   ❌ 调度失败：{e}")
    
    def _dispatch_to_delta(self, issue):
        """调度 Delta 工程师"""
        try:
            # 更新问题状态
            self.issue_queue.update_status(
                issue.id,
                'processing',
                assigned_to='delta',
                resolution='已调度 Delta 工程师'
            )
            
            # 写入 Delta 任务队列
            delta_task_file = Path('./issues/processing/delta_tasks.json')
            tasks = []
            if delta_task_file.exists():
                with open(delta_task_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
            
            tasks.append({
                'issue_id': issue.id,
                'error_type': issue.error_type,
                'error_message': issue.error_message,
                'priority': 'high' if issue.severity == 'P0' else 'normal',
                'assigned_at': datetime.now().isoformat(),
                'status': 'pending'
            })
            
            with open(delta_task_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ 已写入 Delta 任务队列")
            
        except Exception as e:
            print(f"   ❌ 调度失败：{e}")
