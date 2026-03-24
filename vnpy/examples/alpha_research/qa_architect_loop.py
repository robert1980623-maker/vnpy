#!/usr/bin/env python3
"""
QA-Architect 迭代协调器

功能：
1. 协调 QA 和架构师之间的审核迭代
2. 自动触发修改和重新审核
3. 记录完整的审核历史
4. 直到测试用例通过审核
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class QAArchitectLoop:
    """QA-Architect 迭代协调器"""
    
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy/examples/alpha_research')
        self.review_history_dir = Path('./reports/review_history')
        self.review_history_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_iterations = 5  # 最大迭代次数
    
    def run_qa_generator(self) -> Optional[Dict]:
        """运行 QA 测试用例生成"""
        print("\n" + "="*70)
        print("🧪 运行 QA Agent")
        print("="*70)
        
        try:
            result = subprocess.run(
                ['python3', 'qa_test_generator.py'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            print(result.stdout[-1500:])  # 显示输出
            
            if result.returncode == 0:
                print("✅ QA 测试用例生成成功")
                return self._load_latest_review_request()
            else:
                print(f"❌ QA 生成失败：{result.stderr[:200]}")
                return None
        except Exception as e:
            print(f"❌ 运行 QA 失败：{e}")
            return None
    
    def run_architect_review(self) -> Optional[Dict]:
        """运行架构师审核"""
        print("\n" + "="*70)
        print("🏗️  运行架构师审核")
        print("="*70)
        
        try:
            result = subprocess.run(
                ['python3', 'architect_test_reviewer.py'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            print(result.stdout[-1500:])
            
            if result.returncode == 0:
                print("✅ 架构师审核完成")
                return self._load_latest_review_report()
            else:
                print(f"❌ 架构师审核失败：{result.stderr[:200]}")
                return None
        except Exception as e:
            print(f"❌ 运行架构师审核失败：{e}")
            return None
    
    def _load_latest_review_request(self) -> Optional[Dict]:
        """加载最新的审核请求"""
        review_files = sorted(self.review_history_dir.glob('review_request_*.json'), reverse=True)
        if review_files:
            with open(review_files[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _load_latest_review_report(self) -> Optional[Dict]:
        """加载最新的审核报告"""
        report_files = sorted(self.review_history_dir.glob('review_report_*.json'), reverse=True)
        if report_files:
            with open(report_files[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def revise_and_resubmit(self, review_report: Dict) -> bool:
        """根据审核意见修改并重新提交"""
        print("\n" + "="*70)
        print("✏️  修改测试用例并重新提交")
        print("="*70)
        
        # 读取审核意见
        revision_comments = review_report.get('comments', [])
        suite_reviews = review_report.get('suite_reviews', [])
        
        print(f"审核意见：{len(revision_comments)} 条")
        for comment in revision_comments:
            print(f"  - {comment.get('content', '')}")
        
        # 标记需要修改的测试套件
        failed_suites = [sr for sr in suite_reviews if sr.get('revision_needed')]
        print(f"\n需要修改的测试套件：{len(failed_suites)}")
        
        for sr in failed_suites:
            print(f"  - {sr.get('issue_id')}: {sr.get('failed_cases')} 个用例需要修改")
            for eval_result in sr.get('evaluations', []):
                if not eval_result.get('passed'):
                    print(f"    ⚠️ {eval_result.get('test_id')}:")
                    for issue in eval_result.get('issues', []):
                        print(f"       - {issue}")
        
        # 重新运行 QA 生成（会创建新版本）
        print("\n🔄 重新生成测试用例...")
        return True
    
    def run(self):
        """运行完整迭代流程"""
        print("\n" + "="*70)
        print(f"🔄 QA-Architect 迭代协调器")
        print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        iteration = 0
        approved = False
        review_history = []
        
        while iteration < self.max_iterations and not approved:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"📍 第 {iteration} 轮迭代")
            print(f"{'='*70}")
            
            # 步骤 1: QA 生成测试用例
            review_request = self.run_qa_generator()
            
            if not review_request:
                print("❌ QA 生成失败，终止流程")
                break
            
            # 步骤 2: 架构师审核
            review_report = self.run_architect_review()
            
            if not review_report:
                print("❌ 架构师审核失败，终止流程")
                break
            
            # 记录审核历史
            review_history.append({
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'status': review_report.get('overall_status', 'unknown'),
                'passed_cases': review_report.get('summary', {}).get('passed_cases', 0),
                'total_cases': review_report.get('summary', {}).get('total_cases', 0)
            })
            
            # 检查是否通过
            if review_report.get('overall_status') == 'approved':
                approved = True
                print("\n🎉 测试用例审核通过！")
            else:
                print(f"\n⚠️ 测试用例需要修改，继续下一轮迭代")
                
                # 修改并重新提交
                if iteration < self.max_iterations:
                    self.revise_and_resubmit(review_report)
                else:
                    print(f"\n❌ 达到最大迭代次数 ({self.max_iterations})，终止流程")
        
        # 生成最终报告
        final_report = self.generate_final_report(approved, review_history)
        
        print("\n" + "="*70)
        print("✅ 迭代流程完成")
        print("="*70)
        print(f"总迭代次数：{iteration}")
        print(f"最终状态：{'✅ 通过' if approved else '❌ 未通过'}")
        
        return final_report
    
    def generate_final_report(self, approved: bool, review_history: list) -> Dict:
        """生成最终报告"""
        print("\n" + "="*70)
        print("📝 生成最终报告")
        print("="*70)
        
        final_report = {
            'report_id': f"FINAL-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'approved': approved,
            'total_iterations': len(review_history),
            'review_history': review_history,
            'summary': {
                'first_iteration_passed': review_history[0]['passed_cases'] if review_history else 0,
                'final_passed': review_history[-1]['passed_cases'] if review_history else 0,
                'improvement': (review_history[-1]['passed_cases'] - review_history[0]['passed_cases']) if len(review_history) > 1 else 0
            }
        }
        
        report_file = self.review_history_dir / f"final_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 最终报告已保存：{report_file.name}")
        
        return final_report


if __name__ == '__main__':
    loop = QAArchitectLoop()
    loop.run()
