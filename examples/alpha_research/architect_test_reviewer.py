#!/usr/bin/env python3
"""
架构师 - 测试用例审核

功能：
1. 审核 QA 提交的测试用例
2. 提出修改意见
3. 批准通过的测试用例
4. 记录审核历史
"""

import os
from notification_utils import notify_task_start, notify_task_complete, notify_task_error
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class ArchitectTestReviewer:
    """架构师 - 测试用例审核"""
    
    def __init__(self):
        self.review_history_dir = Path('./reports/review_history')
        self.review_history_dir.mkdir(parents=True, exist_ok=True)
        
        # 审核标准
        self.review_criteria = [
            '测试用例是否覆盖所有修复步骤',
            '预期结果是否明确可验证',
            '前置条件是否清晰',
            '测试步骤是否可执行',
            '自动化测试是否合理',
            '优先级设置是否恰当'
        ]
    
    def load_pending_review(self) -> Dict:
        """加载待审核的测试计划"""
        print("\n" + "="*70)
        print("📥 加载待审核测试计划")
        print("="*70)
        
        review_files = sorted(self.review_history_dir.glob('review_request_*.json'), reverse=True)
        
        for rf in review_files:
            with open(rf, 'r', encoding='utf-8') as f:
                review = json.load(f)
            if review.get('status') == 'pending':
                print(f"加载审核：{rf.name}")
                return review
        
        print("✅ 没有待审核的测试计划")
        return None
    
    def evaluate_test_case(self, test_case: Dict) -> Dict:
        """评估单个测试用例"""
        issues = []
        suggestions = []
        
        # 检查覆盖度
        if len(test_case.get('steps', [])) < 2:
            issues.append("测试步骤过少，建议增加详细步骤")
        
        # 检查预期结果
        if not test_case.get('expected_result'):
            issues.append("缺少预期结果")
        elif len(test_case.get('expected_result', '')) < 10:
            suggestions.append("预期结果可以更具体")
        
        # 检查前置条件
        if not test_case.get('precondition'):
            suggestions.append("建议添加前置条件说明")
        
        # 检查优先级
        if test_case.get('priority') not in ['高', '中', '低']:
            issues.append("优先级设置不正确")
        
        # 检查自动化标记
        if 'automated' not in test_case:
            suggestions.append("建议明确标注是否可自动化")
        
        return {
            'test_id': test_case.get('test_id', 'UNKNOWN'),
            'passed': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions,
            'recommendation': 'approve' if len(issues) == 0 else 'revision'
        }
    
    def review_test_suite(self, test_suite: Dict) -> Dict:
        """审核整个测试套件"""
        print(f"\n审核 {test_suite.get('issue_id', 'UNKNOWN')} 的测试用例...")
        
        evaluations = []
        all_passed = True
        revision_needed = False
        
        for tc in test_suite.get('test_cases', []):
            eval_result = self.evaluate_test_case(tc)
            evaluations.append(eval_result)
            
            if not eval_result['passed']:
                all_passed = False
                revision_needed = True
                print(f"  ⚠️ {tc.get('test_id')}: 需要修改")
                for issue in eval_result['issues']:
                    print(f"     - {issue}")
            else:
                print(f"  ✅ {tc.get('test_id')}: 通过")
        
        return {
            'issue_id': test_suite.get('issue_id'),
            'all_passed': all_passed,
            'revision_needed': revision_needed,
            'evaluations': evaluations,
            'total_cases': len(test_suite.get('test_cases', [])),
            'passed_cases': len([e for e in evaluations if e['passed']]),
            'failed_cases': len([e for e in evaluations if not e['passed']])
        }
    
    def generate_review_report(self, review_request: Dict, suite_reviews: List[Dict]) -> Dict:
        """生成审核报告"""
        print("\n" + "="*70)
        print("📝 生成审核报告")
        print("="*70)
        
        all_passed = all(sr['all_passed'] for sr in suite_reviews)
        total_passed = sum(sr['passed_cases'] for sr in suite_reviews)
        total_failed = sum(sr['failed_cases'] for sr in suite_reviews)
        
        review_report = {
            'review_id': review_request.get('review_id'),
            'reviewed_at': datetime.now().isoformat(),
            'reviewer': 'system_architect',
            'test_plan_id': review_request.get('test_plan', {}).get('plan_id'),
            'overall_status': 'approved' if all_passed else 'revision_required',
            'summary': {
                'total_suites': len(suite_reviews),
                'passed_suites': len([sr for sr in suite_reviews if sr['all_passed']]),
                'failed_suites': len([sr for sr in suite_reviews if not sr['all_passed']]),
                'total_cases': total_passed + total_failed,
                'passed_cases': total_passed,
                'failed_cases': total_failed
            },
            'suite_reviews': suite_reviews,
            'comments': [],
            'next_action': 'approve' if all_passed else 'request_revision'
        }
        
        # 生成总体意见
        if all_passed:
            review_report['comments'].append({
                'type': 'positive',
                'content': '测试用例设计合理，覆盖全面，可以批准执行'
            })
            print("✅ 所有测试用例通过审核")
        else:
            review_report['comments'].append({
                'type': 'revision',
                'content': f'有 {total_failed} 个测试用例需要修改，请 QA Agent 根据具体意见修改后重新提交'
            })
            print(f"⚠️ {total_failed} 个测试用例需要修改")
        
        return review_report
    
    def save_review_report(self, review_report: Dict):
        """保存审核报告"""
        print("\n" + "="*70)
        print("💾 保存审核报告")
        print("="*70)
        
        report_file = self.review_history_dir / f"review_report_{review_report['review_id']}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(review_report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 审核报告已保存：{report_file.name}")
        
        return report_file
    
    def run(self):
        """运行完整审核流程"""
        print("\n" + "="*70)
        print(f"🏗️  架构师 - 测试用例审核")
        print(f"审核时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 加载待审核
        review_request = self.load_pending_review()
        
        if not review_request:
            print("✅ 没有待审核项")
            return None
        
        # 步骤 2: 审核每个测试套件
        test_suites = review_request.get('test_plan', {}).get('test_suites', [])
        suite_reviews = [self.review_test_suite(ts) for ts in test_suites]
        
        # 步骤 3: 生成审核报告
        review_report = self.generate_review_report(review_request, suite_reviews)
        
        # 步骤 4: 保存报告
        self.save_review_report(review_report)
        
        # 步骤 5: 更新审核请求状态
        review_request['status'] = review_report['overall_status']
        review_request['review_report'] = review_report
        
        with open(self.review_history_dir / f"review_request_{review_request['review_id']}.json", 'w') as f:
            json.dump(review_request, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*70)
        print("✅ 审核完成")
        print("="*70)
        print(f"状态：{review_report['overall_status']}")
        print(f"通过：{review_report['summary']['passed_cases']}/{review_report['summary']['total_cases']}")
        
        # 步骤 6: 更新原始测试计划状态
        if review_report['overall_status'] == 'approved':
            self.update_test_plan_status(review_request)
        
        return review_report
    
    def update_test_plan_status(self, review_request: Dict):
        """更新测试计划状态并触发测试执行"""
        print("\n" + "="*70)
        print("📝 更新测试计划状态")
        print("="*70)
        
        test_plan = review_request.get('test_plan', {})
        plan_id = test_plan.get('plan_id', '')
        
        # 查找原始测试计划文件
        test_case_dir = Path('./reports/test_cases')
        plan_files = list(test_case_dir.glob(f'test_plan_*{plan_id.split("-")[-1]}.json'))
        
        if plan_files:
            plan_file = plan_files[0]
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            
            # 更新状态
            plan['status'] = 'approved'
            
            # 确保 review_history 存在
            if 'review_history' not in plan:
                plan['review_history'] = []
            
            plan['review_history'].append({
                'review_id': review_request.get('review_id', ''),
                'reviewed_at': review_request.get('reviewed_at', ''),
                'result': 'approved',
                'passed_cases': review_request.get('review_report', {}).get('summary', {}).get('passed_cases', 0),
                'total_cases': review_request.get('review_report', {}).get('summary', {}).get('total_cases', 0)
            })
            
            # 更新每个套件状态
            for i, suite in enumerate(plan.get('test_suites', [])):
                suite['status'] = 'approved'
            
            # 添加审核历史 (如果不存在则创建)
            if 'review_history' not in plan:
                plan['review_history'] = []
            
            plan['review_history'].append({
                'review_id': review_request.get('review_id', ''),
                'reviewed_at': review_request.get('reviewed_at', ''),
                'result': 'approved',
                'passed_cases': review_request.get('review_report', {}).get('summary', {}).get('passed_cases', 0),
                'total_cases': review_request.get('review_report', {}).get('summary', {}).get('total_cases', 0)
            })
            
            # 保存更新
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 测试计划状态已更新：{plan_file.name}")
            print(f"   状态：approved")
            print(f"   套件：{len(plan.get('test_suites', []))} 个全部通过")
            
            # 触发测试执行
            self.trigger_test_execution(plan)
        else:
            print(f"⚠️ 未找到测试计划文件：{plan_id}")
    
    def trigger_test_execution(self, plan: Dict):
        """触发自动化测试执行"""
        print("\n" + "="*70)
        print("🧪 触发自动化测试执行")
        print("="*70)
        
        try:
            import subprocess
            
            # 运行集成测试
            result = subprocess.run(
                ['python3', '-m', 'pytest', 'tests/integration/', '-v', '--tb=short'],
                cwd=Path('.'),
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            print(result.stdout[-2000:])
            
            if result.returncode == 0:
                print("\n✅ 所有测试通过！")
                # 通知 Manager 关闭问题
                self.notify_manager_success(plan)
            else:
                print(f"\n❌ 测试失败：{result.stderr[:500]}")
                # 上报问题给 Manager
                self.report_test_failures(plan, result)
        
        except Exception as e:
            print(f"⚠️ 测试执行失败：{e}")
    
    def notify_manager_success(self, plan: Dict):
        """通知 Manager 测试通过"""
        print("\n📬 通知 Manager 测试通过")
        # TODO: 实现 Manager 通知逻辑
        print("   (待实现：调用 Manager API 关闭问题)")
    
    def report_test_failures(self, plan: Dict, test_result):
        """上报测试失败给 Manager"""
        print("\n📬 上报测试失败给 Manager")
        # TODO: 实现 Manager 上报逻辑
        print("   (待实现：创建 Issue 并上报 Manager)")
        


if __name__ == '__main__':

    # 发送通知
    try:
        notify_task_start("架构师代码审查", {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "类型": "代码审查"
        })
        
        result = main()
        
        notify_task_complete("架构师代码审查", {
            "状态": "完成"
        })
    except Exception as e:
        notify_task_error("架构师代码审查", str(e))
        raise

    reviewer = ArchitectTestReviewer()
    reviewer.run()
