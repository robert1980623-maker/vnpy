#!/usr/bin/env python3
"""
Delta Agent - 架构审查结果 Review 与优化方案制定
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict

class DeltaArchitectReviewer:
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy')
        self.report_dir = Path('./reports/architecture')
        self.optimization_plan_dir = Path('./reports/optimization_plans')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.optimization_plan_dir.mkdir(parents=True, exist_ok=True)
    
    def load_architect_report(self) -> Dict:
        print("\n" + "="*70)
        print("📥 加载架构师审查报告")
        print("="*70)
        
        report_files = sorted(self.report_dir.glob('architecture_review_*.json'), reverse=True)
        if not report_files:
            print("❌ 未找到架构师审查报告")
            return None
        
        latest_report = report_files[0]
        print(f"加载报告：{latest_report.name}")
        
        with open(latest_report, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        print(f"审查日期：{report.get('review_date', 'Unknown')}")
        print(f"发现问题：{report.get('summary', {}).get('total_issues', 0)} 个")
        return report
    
    def evaluate_issue(self, issue: Dict) -> Dict:
        severity = issue.get('severity', '中')
        issue_type = issue.get('type', '')
        description = issue.get('description', '')
        
        impact = '高' if '依赖' in issue_type or '安全' in description else '中' if '代码' in issue_type else '低'
        effort = '小' if '文档' in issue_type else '中' if '依赖' in issue_type else '大' if '代码' in issue_type else '中'
        risk = '中' if '依赖' in issue_type else '高' if '安全' in description else '低'
        urgency = '高' if severity == '高' else '中' if severity == '中' else '低'
        testability = '是' if '代码' in issue_type or '函数' in description or '依赖' in issue_type else '否'
        
        return {'impact': impact, 'effort': effort, 'risk': risk, 'urgency': urgency, 'testability': testability}
    
    def create_fix_plan(self, issue: Dict, evaluation: Dict) -> Dict:
        issue_type = issue.get('type', '问题')
        description = issue.get('description', '')
        suggestion = issue.get('suggestion', '')
        examples = issue.get('examples', [])
        
        fix_steps = []
        verification_steps = []
        
        if '依赖' in issue_type:
            fix_steps = ['1. 创建 requirements.txt', '2. 列出所有依赖', '3. 验证依赖树', '4. 添加到 git']
            verification_steps = ['✓ 新环境安装成功', '✓ 模块导入正常', '✓ 测试通过']
        elif '过长函数' in description:
            fix_steps = ['1. 识别大函数', '2. 拆分逻辑', '3. 提取子函数', '4. 更新调用', '5. 添加测试']
            verification_steps = ['✓ 每个函数<50 行', '✓ 测试通过', '✓ 新函数有测试']
            if examples:
                fix_steps.append('\n待修复文件:')
                for ex in examples[:5]:
                    fix_steps.append(f"  - {ex.get('file')}:{ex.get('line')} ({ex.get('estimated_lines',0)}行)")
        elif '错误处理' in issue_type:
            fix_steps = ['1. 搜索裸 except', '2. 替换为具体异常', '3. 添加日志', '4. 更新文档']
            verification_steps = ['✓ 无裸 except', '✓ 异常处理正确', '✓ 日志完整']
        else:
            fix_steps = ['1. 分析问题', '2. 制定方案', '3. 实施修复', '4. 测试', '5. 审查']
            verification_steps = ['✓ 问题解决', '✓ 无新问题', '✓ 审查通过']
        
        effort_hours = {'小': 2, '中': 8, '大': 24}.get(evaluation['effort'], 8)
        priority = 0
        priority += {'高': 25, '中': 15, '低': 5}.get(evaluation['impact'], 15)
        priority += {'高': 25, '中': 15, '低': 5}.get(evaluation['urgency'], 15)
        priority += {'高': 5, '中': 15, '低': 25}.get(evaluation['risk'], 15)
        priority += 25 if evaluation['testability'] == '是' else 10
        
        return {
            'issue_id': f"ISSUE-{abs(hash(description)) % 10000:04d}",
            'issue_type': issue_type,
            'description': description,
            'suggestion': suggestion,
            'original_severity': issue.get('severity', '中'),
            'evaluation': evaluation,
            'fix_steps': fix_steps,
            'verification_steps': verification_steps,
            'estimated_hours': effort_hours,
            'priority_score': min(priority, 100)
        }
    
    def generate_optimization_plan(self, architect_report: Dict) -> Dict:
        print("\n" + "="*70)
        print("📋 制定优化方案")
        print("="*70)
        
        all_issues = architect_report.get('issues', [])
        fix_plans = [self.create_fix_plan(issue, self.evaluate_issue(issue)) for issue in all_issues]
        fix_plans.sort(key=lambda x: x['priority_score'], reverse=True)
        
        for i, fp in enumerate(fix_plans, 1):
            print(f"[{i}/{len(fix_plans)}] {fp['issue_type']}: 优先级{fp['priority_score']}, 工时{fp['estimated_hours']}h")
        
        return {
            'plan_id': f"PLAN-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'created_at': datetime.now().isoformat(),
            'based_on_report': architect_report.get('review_date', 'Unknown'),
            'total_issues': len(fix_plans),
            'total_estimated_hours': sum(p['estimated_hours'] for p in fix_plans),
            'fix_plans': fix_plans,
            'summary': {
                'high_priority': len([p for p in fix_plans if p['priority_score'] >= 70]),
                'medium_priority': len([p for p in fix_plans if 40 <= p['priority_score'] < 70]),
                'low_priority': len([p for p in fix_plans if p['priority_score'] < 40]),
                'testable_items': len([p for p in fix_plans if p['evaluation']['testability'] == '是'])
            }
        }
    
    def save_optimization_plan(self, plan: Dict):
        print("\n" + "="*70)
        print("💾 保存优化方案")
        print("="*70)
        
        plan_file = self.optimization_plan_dir / f"optimization_plan_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存：{plan_file.name}")
        return plan_file
    
    def update_progress_doc(self, plan: Dict):
        print("\n" + "="*70)
        print("📝 更新项目进度文档")
        print("="*70)
        
        progress_file = self.project_root / '开发进度.md'
        if not progress_file.exists():
            print("⚠️ 开发进度.md 不存在")
            return
        
        with open(progress_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        execution_plan = f"\n\n## 🎯 待执行优化计划（Delta 制定）- {datetime.now().strftime('%Y-%m-%d')}\n\n"
        execution_plan += f"**方案编号**: {plan['plan_id']}  \n"
        execution_plan += f"**总工时**: {plan['total_estimated_hours']} 小时\n\n"
        
        high_priority = [p for p in plan['fix_plans'] if p['priority_score'] >= 70]
        execution_plan += "### 高优先级任务\n\n"
        for fp in high_priority:
            execution_plan += f"#### [{fp['issue_id']}] {fp['issue_type']}\n"
            execution_plan += f"- **问题**: {fp['description']}\n"
            execution_plan += f"- **步骤**: {' → '.join(fp['fix_steps'][:3])}\n"
            execution_plan += f"- **验证**: {' ✓ '.join(fp['verification_steps'][:2])}\n"
            execution_plan += f"- **工时**: {fp['estimated_hours']}h\n"
            execution_plan += f"- **状态**: ⏳ 待执行\n\n"
        
        if '## 🎯 待执行优化计划' in content:
            import re
            content = re.sub(r'## 🎯 待执行优化计划.*?(?=## |\Z)', execution_plan, content, flags=re.DOTALL)
        else:
            content += execution_plan
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 项目进度文档已更新")
    
    def run(self):
        print("\n" + "="*70)
        print(f"🤖 Delta Agent - 架构审查结果 Review")
        print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        architect_report = self.load_architect_report()
        if not architect_report:
            print("❌ 无法加载架构师报告")
            return None
        
        optimization_plan = self.generate_optimization_plan(architect_report)
        self.save_optimization_plan(optimization_plan)
        self.update_progress_doc(optimization_plan)
        
        print("\n" + "="*70)
        print("✅ Delta Review 完成")
        print("="*70)
        
        return optimization_plan

if __name__ == '__main__':
    reviewer = DeltaArchitectReviewer()
    reviewer.run()
