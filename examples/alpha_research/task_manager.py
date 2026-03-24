#!/usr/bin/env python3
"""
任务管理闭环系统

流程:
1. Manager 派发任务 → Agent
2. Agent 执行任务
3. Manager 检查结果
4. 成功 → 关闭任务
5. 失败 → 触发 QA 闭环 → 重新派发

核心组件:
- TaskManager: 任务调度与检查
- AgentExecutor: Agent 执行器
- QALoopTrigger: QA 闭环触发器
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager


class TaskStatus:
    """任务状态"""
    PENDING = 'pending'      # 待派发
    ASSIGNED = 'assigned'    # 已派发
    RUNNING = 'running'      # 执行中
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'        # 失败
    QA_REVIEW = 'qa_review'  # QA 审核中


class TaskManager:
    """任务管理器 - 派发、检查、闭环"""
    
    def __init__(self):
        self.manager = QuantManager()
        self.issue_queue = self.manager.issue_queue
        self.tasks: Dict[str, Dict] = {}
        self.task_history: List[Dict] = []
    
    def create_task(self, issue_id: str, agent: str, task_type: str, 
                   priority: str = 'normal') -> str:
        """创建任务"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{issue_id}"
        
        task = {
            'task_id': task_id,
            'issue_id': issue_id,
            'agent': agent,
            'type': task_type,
            'priority': priority,
            'status': TaskStatus.PENDING,
            'created_at': datetime.now().isoformat(),
            'assigned_at': None,
            'started_at': None,
            'completed_at': None,
            'result': None,
            'qa_triggered': False,
            'qa_attempts': 0
        }
        
        self.tasks[task_id] = task
        self.issue_queue.update_status(issue_id, 'processing', assigned_to=agent)
        
        print(f"✅ 任务创建：{task_id}")
        print(f"   Issue: {issue_id}")
        print(f"   Agent: {agent}")
        print(f"   类型：{task_type}")
        print(f"   优先级：{priority}")
        
        return task_id
    
    def assign_task(self, task_id: str) -> bool:
        """派发任务给 Agent"""
        if task_id not in self.tasks:
            print(f"❌ 任务不存在：{task_id}")
            return False
        
        task = self.tasks[task_id]
        task['status'] = TaskStatus.ASSIGNED
        task['assigned_at'] = datetime.now().isoformat()
        
        print(f"📤 任务派发：{task_id} → {task['agent']}")
        
        return True
    
    def execute_task(self, task_id: str, script: str, timeout: int = 600) -> Tuple[bool, str]:
        """执行任务"""
        if task_id not in self.tasks:
            return False, "任务不存在"
        
        task = self.tasks[task_id]
        task['status'] = TaskStatus.RUNNING
        task['started_at'] = datetime.now().isoformat()
        
        print(f"▶️  任务执行：{task_id}")
        print(f"   脚本：{script}")
        print(f"   超时：{timeout}s")
        
        try:
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd='/Users/rowang/projects/vnpy/examples/alpha_research'
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            task['result'] = {
                'success': success,
                'output': output[-2000:],  # 保留最后 2000 字
                'returncode': result.returncode
            }
            
            if success:
                task['status'] = TaskStatus.COMPLETED
                task['completed_at'] = datetime.now().isoformat()
                print(f"✅ 任务完成：{task_id}")
            else:
                task['status'] = TaskStatus.FAILED
                print(f"❌ 任务失败：{task_id}")
                print(f"   错误：{output[:500]}")
            
            return success, output
            
        except subprocess.TimeoutExpired:
            task['status'] = TaskStatus.FAILED
            task['result'] = {'success': False, 'output': '执行超时', 'returncode': -1}
            print(f"❌ 任务超时：{task_id}")
            return False, "执行超时"
        except Exception as e:
            task['status'] = TaskStatus.FAILED
            task['result'] = {'success': False, 'output': str(e), 'returncode': -1}
            print(f"❌ 任务异常：{task_id} - {e}")
            return False, str(e)
    
    def check_task_result(self, task_id: str) -> bool:
        """检查任务结果"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task['status'] != TaskStatus.COMPLETED:
            print(f"⚠️  任务未完成：{task_id} (状态：{task['status']})")
            return False
        
        result = task.get('result', {})
        success = result.get('success', False)
        
        if success:
            print(f"✅ 任务检查通过：{task_id}")
            self.issue_queue.update_status(
                task['issue_id'],
                'resolved',
                resolution=f"任务 {task_id} 成功完成"
            )
            self._archive_task(task_id)
            return True
        else:
            print(f"❌ 任务检查失败：{task_id}")
            return False
    
    def trigger_qa_loop(self, task_id: str) -> bool:
        """触发 QA 闭环"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task['qa_triggered'] = True
        task['qa_attempts'] += 1
        task['status'] = TaskStatus.QA_REVIEW
        
        print(f"\n{'='*70}")
        print(f"🔄 触发 QA 闭环 (第 {task['qa_attempts']} 次)")
        print(f"{'='*70}")
        print(f"任务：{task_id}")
        print(f"Issue: {task['issue_id']}")
        print(f"Agent: {task['agent']}")
        print(f"失败原因：{task.get('result', {}).get('output', '未知')[:200]}")
        
        # 创建 QA 问题
        qa_issue = self.issue_queue.create_issue(
            agent='qa_architect_loop',
            severity='P1',
            error_type='TaskFailure',
            error_message=f"任务 {task_id} 执行失败，需要 QA 闭环验证"
        )
        qa_issue.details = {
            'task_id': task_id,
            'original_issue': task['issue_id'],
            'failed_script': '未知',
            'attempt': task['qa_attempts']
        }
        self.issue_queue.write_issue(qa_issue)
        
        # 运行 QA 闭环
        print(f"\n▶️  运行 QA-Architect 闭环...")
        try:
            result = subprocess.run(
                ['python3', 'qa_architect_loop.py'],
                capture_output=True,
                text=True,
                timeout=1800,
                cwd='/Users/rowang/projects/vnpy/examples/alpha_research'
            )
            
            qa_success = '✅ 通过' in result.stdout or '最终状态：✅ 通过' in result.stdout
            
            if qa_success:
                print(f"✅ QA 闭环通过")
                task['status'] = TaskStatus.PENDING  # 重新派发
                task['qa_triggered'] = False
                self.issue_queue.resolve_issue(qa_issue.id, 'QA 闭环验证通过')
            else:
                print(f"❌ QA 闭环失败")
                task['status'] = TaskStatus.FAILED
                self.issue_queue.update_status(qa_issue.id, 'pending')
            
            return qa_success
            
        except Exception as e:
            print(f"❌ QA 闭环异常：{e}")
            task['status'] = TaskStatus.FAILED
            return False
    
    def _archive_task(self, task_id: str):
        """归档任务"""
        if task_id in self.tasks:
            self.task_history.append(self.tasks[task_id])
            del self.tasks[task_id]
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def generate_report(self) -> Dict:
        """生成任务报告"""
        report = {
            'total_tasks': len(self.tasks) + len(self.task_history),
            'active_tasks': len(self.tasks),
            'completed_tasks': len([t for t in self.task_history if t['status'] == TaskStatus.COMPLETED]),
            'failed_tasks': len([t for t in self.task_history if t['status'] == TaskStatus.FAILED]),
            'qa_triggered': len([t for t in self.task_history if t.get('qa_triggered', False)]),
            'tasks': self.get_all_tasks(),
            'history': self.task_history[-10:]  # 最近 10 个历史
        }
        return report


def main():  # pragma: no cover
    """示例：完整任务闭环流程"""
    print("="*70)
    print("🎯 任务管理闭环系统演示")
    print("="*70)
    
    tm = TaskManager()
    
    # 步骤 1: 创建 Issue
    issue = tm.issue_queue.create_issue(
        agent='test',
        severity='P1',
        error_type='TestError',
        error_message='测试任务错误'
    )
    issue_id = tm.issue_queue.write_issue(issue)
    print(f"\n✅ 创建 Issue: {issue_id}")
    
    # 步骤 2: Manager 派发任务
    task_id = tm.create_task(issue_id, 'delta', 'code_fix', priority='high')
    tm.assign_task(task_id)
    
    # 步骤 3: Agent 执行任务
    success, output = tm.execute_task(task_id, 'python3 -c "print(\'任务执行成功\')"')
    
    # 步骤 4: Manager 检查结果
    if success:
        tm.check_task_result(task_id)
        print("\n✅ 任务成功闭环")
    else:
        # 步骤 5: 失败 → 触发 QA 闭环
        tm.trigger_qa_loop(task_id)
        print("\n🔄 QA 闭环已触发")
    
    # 生成报告
    report = tm.generate_report()
    print(f"\n📊 任务报告:")
    print(f"   总任务数：{report['total_tasks']}")
    print(f"   活跃任务：{report['active_tasks']}")
    print(f"   完成任务：{report['completed_tasks']}")
    print(f"   失败任务：{report['failed_tasks']}")
    print(f"   QA 触发：{report['qa_triggered']}")


if __name__ == '__main__':
    main()
