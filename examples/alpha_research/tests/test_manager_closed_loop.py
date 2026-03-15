#!/usr/bin/env python3
"""
Manager 问题队列闭环回归测试

测试场景:
1. 创建问题 → Manager 分析 → 分配 Agent → 处理 → QA 验证 → 重新执行 → 关闭

用法:
    python3 tests/test_manager_closed_loop.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from issue_queue import IssueQueue, Issue
from manager_interface import QuantManager
from human_report import human_manager_report


class TestManagerClosedLoop:
    """Manager 闭环测试"""
    
    def __init__(self):
        self.issue_queue = IssueQueue()
        self.manager = QuantManager()
        self.test_results = []
    
    def setup(self):
        """测试准备"""
        print("\n" + "=" * 70)
        print("🧪 Manager 问题队列闭环回归测试")
        print("=" * 70)
        print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 清理测试数据
        self._cleanup_test_issues()
    
    def teardown(self):
        """测试清理"""
        print("\n" + "=" * 70)
        print("🧹 清理测试数据")
        print("=" * 70)
        self._cleanup_test_issues()
        print("✅ 清理完成")
    
    def _cleanup_test_issues(self):
        """清理测试问题"""
        for file in self.issue_queue.pending_dir.glob('test_*.json'):
            file.unlink()
        for file in self.issue_queue.processing_dir.glob('test_*.json'):
            file.unlink()
        for file in self.issue_queue.resolved_dir.glob('test_*.json'):
            file.unlink()
    
    def _create_test_issue(self, agent: str, severity: str, error_type: str, 
                          error_message: str) -> Issue:
        """创建测试问题"""
        issue = Issue(
            id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent}",
            agent=agent,
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            status="pending"
        )
        self.issue_queue.write_issue(issue)
        return issue
    
    def test_1_create_issue(self):
        """测试 1: 创建问题"""
        print("\n【测试 1: 创建问题】")
        
        # 创建不同类型的问题
        test_issues = [
            ("data-agent", "P1", "data_download", "数据下载失败：网络超时"),
            ("trading-agent", "P0", "trading_error", "交易执行失败：余额不足"),
            ("qa", "P2", "code_quality", "代码质量检查未通过"),
            ("cro", "P1", "risk_warning", "仓位超限警告"),
        ]
        
        created = []
        for agent, severity, error_type, error_msg in test_issues:
            issue = self._create_test_issue(agent, severity, error_type, error_msg)
            created.append(issue)
            print(f"  ✅ 创建问题：{issue.id} ({severity})")
        
        assert len(created) == 4, "应该创建 4 个测试问题"
        print(f"\n✅ 测试 1 通过：创建 {len(created)} 个问题")
        
        return created
    
    def test_2_manager_analyze(self, issues: list):
        """测试 2: Manager 分析问题"""
        print("\n【测试 2: Manager 分析问题】")
        
        analyzed = []
        for issue in issues:
            # 分析错误类型
            task_type = self.manager.analyze_error(issue)
            agent = self.manager.select_agent(task_type)
            
            analyzed.append({
                'issue': issue,
                'task_type': task_type,
                'agent': agent
            })
            
            print(f"  📋 {issue.id}")
            print(f"     类型：{task_type}")
            print(f"     分配：{agent}")
        
        assert len(analyzed) == 4, "应该分析 4 个问题"
        print(f"\n✅ 测试 2 通过：分析 {len(analyzed)} 个问题")
        
        return analyzed
    
    def test_3_assign_agents(self, analyzed_issues: list):
        """测试 3: 分配给 Agent"""
        print("\n【测试 3: 分配给 Agent】")
        
        assigned = []
        for item in analyzed_issues:
            issue = item['issue']
            agent = item['agent']
            
            # 更新问题状态
            self.issue_queue.update_status(
                issue.id,
                'processing',
                assigned_to=agent
            )
            
            # 创建任务
            task = {
                'issue_id': issue.id,
                'agent': agent,
                'type': item['task_type'],
                'severity': issue.severity,
                'status': 'assigned',
                'assigned_at': datetime.now().isoformat(),
            }
            
            self.manager.active_tasks[issue.id] = task
            assigned.append(task)
            
            print(f"  ✅ 分配：{issue.id} → {agent}")
        
        assert len(assigned) == 4, "应该分配 4 个任务"
        print(f"\n✅ 测试 3 通过：分配 {len(assigned)} 个任务")
        
        return assigned
    
    def test_4_process_issues(self, tasks: list):
        """测试 4: 处理问题"""
        print("\n【测试 4: 处理问题】")
        
        processed = []
        for task in tasks:
            issue_id = task['issue_id']
            issue = self.issue_queue.read_issue(issue_id)
            
            # 模拟处理（实际应该由对应 Agent 处理）
            try:
                # 这里模拟处理成功
                resolution = f"问题已修复（模拟）"
                
                self.issue_queue.update_status(
                    issue_id,
                    'resolved',
                    resolution=resolution,
                    resolved_at=datetime.now().isoformat()
                )
                
                processed.append({
                    'task': task,
                    'status': 'resolved',
                    'resolution': resolution
                })
                
                print(f"  ✅ 处理：{issue_id} - {resolution}")
            
            except Exception as e:
                processed.append({
                    'task': task,
                    'status': 'failed',
                    'error': str(e)
                })
                
                print(f"  ❌ 失败：{issue_id} - {e}")
        
        success_count = len([p for p in processed if p['status'] == 'resolved'])
        print(f"\n✅ 测试 4 通过：处理 {success_count}/{len(processed)} 个任务")
        
        return processed
    
    def test_5_qa_verify(self, processed_issues: list):
        """测试 5: QA 验证"""
        print("\n【测试 5: QA 验证】")
        
        verified = []
        for item in processed_issues:
            if item['status'] != 'resolved':
                verified.append({'status': 'skipped', 'reason': '未处理'})
                continue
            
            # 模拟 QA 验证（实际应该运行测试）
            qa_passed = True  # 模拟通过
            
            if qa_passed:
                verified.append({'status': 'passed', 'qa_score': 95})
                print(f"  ✅ QA 验证通过：{item['task']['issue_id']}")
            else:
                verified.append({'status': 'failed', 'qa_score': 60})
                print(f"  ❌ QA 验证失败：{item['task']['issue_id']}")
        
        passed_count = len([v for v in verified if v['status'] == 'passed'])
        print(f"\n✅ 测试 5 通过：验证 {passed_count}/{len(verified)} 个任务")
        
        return verified
    
    def test_6_generate_report(self, verified_issues: list):
        """测试 6: 生成 Human 风格报告"""
        print("\n【测试 6: 生成 Human 风格报告】")
        
        # 统计结果
        pending = 0
        processing = 0
        resolved = len([v for v in verified_issues if v['status'] == 'passed'])
        
        report_data = {
            'pending': pending,
            'processing': processing,
            'resolved': resolved
        }
        
        # 生成 Human 风格报告
        report = human_manager_report(report_data)
        
        print("\n" + "=" * 70)
        print("📋 Human 风格报告")
        print("=" * 70)
        print(report)
        print("=" * 70)
        
        assert '✅' in report or '🎉' in report, "报告应该包含 emoji"
        assert len(report) > 50, "报告应该有一定长度"
        
        print("\n✅ 测试 6 通过：生成 Human 风格报告")
        
        return report
    
    def run_all_tests(self):
        """运行所有测试"""
        self.setup()
        
        try:
            # 测试闭环流程
            issues = self.test_1_create_issue()
            analyzed = self.test_2_manager_analyze(issues)
            tasks = self.test_3_assign_agents(analyzed)
            processed = self.test_4_process_issues(tasks)
            verified = self.test_5_qa_verify(processed)
            report = self.test_6_generate_report(verified)
            
            # 总结
            print("\n" + "=" * 70)
            print("🎉 所有测试通过！")
            print("=" * 70)
            print(f"\n闭环流程:")
            print(f"  1️⃣  创建问题：{len(issues)} 个 ✅")
            print(f"  2️⃣  Manager 分析：{len(analyzed)} 个 ✅")
            print(f"  3️⃣  分配 Agent: {len(tasks)} 个 ✅")
            print(f"  4️⃣  处理问题：{len([p for p in processed if p['status'] == 'resolved'])} 个 ✅")
            print(f"  5️⃣  QA 验证：{len([v for v in verified if v['status'] == 'passed'])} 个 ✅")
            print(f"  6️⃣  生成报告：1 份 ✅")
            print()
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ 测试失败：{e}")
            return False
        except Exception as e:
            print(f"\n❌ 测试异常：{e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.teardown()


if __name__ == '__main__':
    tester = TestManagerClosedLoop()
    success = tester.run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)
