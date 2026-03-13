#!/usr/bin/env python3
"""
QA Agent - 测试用例生成与迭代审核

功能：
1. 为 Delta 的每个优化方案生成测试用例
2. 提交给架构师审核
3. 根据审核意见修改测试用例
4. 迭代直到架构师审核通过
5. 记录完整的审核历史
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class QATestGenerator:
    """QA Agent - 测试用例生成"""
    
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy')
        self.optimization_plan_dir = Path('./reports/optimization_plans')
        self.test_case_dir = Path('./reports/test_cases')
        self.review_history_dir = Path('./reports/review_history')
        self.test_case_dir.mkdir(parents=True, exist_ok=True)
        self.review_history_dir.mkdir(parents=True, exist_ok=True)
        
        # 审核状态
        self.review_status = {
            'pending': '待审核',
            'revision_required': '需要修改',
            'approved': '已通过'
        }
    
    def load_latest_optimization_plan(self) -> Dict:
        """加载最新的优化方案"""
        print("\n" + "="*70)
        print("📥 加载最新优化方案")
        print("="*70)
        
        plan_files = sorted(self.optimization_plan_dir.glob('optimization_plan_*.json'), reverse=True)
        
        if not plan_files:
            print("❌ 未找到优化方案")
            return None
        
        latest_plan = plan_files[0]
        print(f"加载方案：{latest_plan.name}")
        
        with open(latest_plan, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        print(f"方案编号：{plan.get('plan_id', 'Unknown')}")
        print(f"总任务数：{plan.get('total_issues', 0)}")
        
        return plan
    
    def generate_test_case(self, fix_plan: Dict) -> Dict:
        """为单个修复方案生成测试用例"""
        issue_id = fix_plan.get('issue_id', 'UNKNOWN')
        issue_type = fix_plan.get('issue_type', '问题')
        description = fix_plan.get('description', '')
        fix_steps = fix_plan.get('fix_steps', [])
        verification_steps = fix_plan.get('verification_steps', [])
        
        # 生成测试用例
        test_cases = []
        
        # 根据问题类型生成不同的测试用例
        if '依赖' in issue_type:
            test_cases = [
                {
                    'test_id': f"{issue_id}-TC01",
                    'name': '依赖安装测试',
                    'type': '自动化',
                    'description': '验证 requirements.txt 可以成功安装所有依赖',
                    'precondition': '干净 Python 环境',
                    'steps': [
                        '1. 创建虚拟环境',
                        '2. 运行 pip install -r requirements.txt',
                        '3. 检查安装结果'
                    ],
                    'expected_result': '所有依赖安装成功，无错误',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC02",
                    'name': '模块导入测试',
                    'type': '自动化',
                    'description': '验证所有模块可以正常导入',
                    'precondition': '依赖已安装',
                    'steps': [
                        '1. 遍历所有 Python 文件',
                        '2. 尝试导入每个模块',
                        '3. 记录导入失败的模块'
                    ],
                    'expected_result': '所有模块导入成功',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC03",
                    'name': '功能回归测试',
                    'type': '自动化',
                    'description': '运行现有测试用例确保功能正常',
                    'precondition': '环境已配置',
                    'steps': [
                        '1. 运行 pytest tests/',
                        '2. 检查测试结果',
                        '3. 分析失败的测试'
                    ],
                    'expected_result': '所有测试通过',
                    'priority': '高',
                    'automated': True
                }
            ]
        
        elif '过长函数' in description or '代码' in issue_type:
            test_cases = [
                {
                    'test_id': f"{issue_id}-TC01",
                    'name': '函数长度检查',
                    'type': '静态检查',
                    'description': '验证拆分后的函数长度符合要求',
                    'precondition': '代码已修改',
                    'steps': [
                        '1. 使用脚本扫描所有 Python 文件',
                        '2. 检查每个函数的行数',
                        '3. 列出超过 50 行的函数'
                    ],
                    'expected_result': '所有函数行数 < 50 行',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC02",
                    'name': '原有功能测试',
                    'type': '自动化',
                    'description': '验证拆分后功能与原来一致',
                    'precondition': '代码已修改',
                    'steps': [
                        '1. 运行原有测试用例',
                        '2. 对比修改前后的测试结果',
                        '3. 确认行为一致'
                    ],
                    'expected_result': '测试全部通过，行为一致',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC03",
                    'name': '新函数单元测试',
                    'type': '自动化',
                    'description': '为拆分出的新函数编写单元测试',
                    'precondition': '新函数已创建',
                    'steps': [
                        '1. 识别所有新函数',
                        '2. 为每个函数编写测试',
                        '3. 运行测试验证'
                    ],
                    'expected_result': '新函数测试覆盖率 100%',
                    'priority': '中',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC04",
                    'name': '代码审查检查',
                    'type': '人工审查',
                    'description': '人工审查代码拆分合理性',
                    'precondition': '代码已修改',
                    'steps': [
                        '1. 审查代码结构',
                        '2. 确认函数职责单一',
                        '3. 确认命名清晰'
                    ],
                    'expected_result': '通过代码审查',
                    'priority': '中',
                    'automated': False
                }
            ]
        
        elif '错误处理' in issue_type:
            test_cases = [
                {
                    'test_id': f"{issue_id}-TC01",
                    'name': '裸 except 检查',
                    'type': '静态检查',
                    'description': '验证代码中没有裸 except 语句',
                    'precondition': '代码已修改',
                    'steps': [
                        '1. 使用 grep 搜索 except:',
                        '2. 检查每个 except 是否有具体类型',
                        '3. 列出所有裸 except'
                    ],
                    'expected_result': '没有裸 except 语句',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC02",
                    'name': '异常触发测试',
                    'type': '自动化',
                    'description': '触发各种异常验证处理正确',
                    'precondition': '测试环境准备',
                    'steps': [
                        '1. 构造各种异常情况',
                        '2. 调用相关函数',
                        '3. 验证异常被正确捕获和处理'
                    ],
                    'expected_result': '所有异常正确处理',
                    'priority': '高',
                    'automated': True
                },
                {
                    'test_id': f"{issue_id}-TC03",
                    'name': '日志记录检查',
                    'type': '人工审查',
                    'description': '验证异常日志记录完整',
                    'precondition': '代码已修改',
                    'steps': [
                        '1. 检查异常处理代码',
                        '2. 确认日志包含必要信息',
                        '3. 验证日志级别正确'
                    ],
                    'expected_result': '日志记录完整',
                    'priority': '中',
                    'automated': False
                }
            ]
        
        else:
            # 通用测试用例
            test_cases = [
                {
                    'test_id': f"{issue_id}-TC01",
                    'name': '问题修复验证',
                    'type': '功能测试',
                    'description': f'验证问题已解决：{description[:50]}',
                    'precondition': '修复已完成',
                    'steps': [
                        '1. 重现原问题',
                        '2. 应用修复',
                        '3. 验证问题不再出现'
                    ],
                    'expected_result': '问题已解决',
                    'priority': '高',
                    'automated': False
                },
                {
                    'test_id': f"{issue_id}-TC02",
                    'name': '回归测试',
                    'type': '自动化',
                    'description': '确保修复没有引入新问题',
                    'precondition': '修复已完成',
                    'steps': [
                        '1. 运行相关测试用例',
                        '2. 检查测试结果',
                        '3. 分析失败原因'
                    ],
                    'expected_result': '所有测试通过',
                    'priority': '高',
                    'automated': True
                }
            ]
        
        return {
            'issue_id': issue_id,
            'issue_type': issue_type,
            'description': description,
            'test_cases': test_cases,
            'total_cases': len(test_cases),
            'automated_cases': len([tc for tc in test_cases if tc.get('automated', False)]),
            'manual_cases': len([tc for tc in test_cases if not tc.get('automated', False)]),
            'status': 'pending_review',
            'review_history': []
        }
    
    def generate_all_test_cases(self, optimization_plan: Dict) -> Dict:
        """为所有优化方案生成测试用例"""
        print("\n" + "="*70)
        print("📝 生成测试用例")
        print("="*70)
        
        fix_plans = optimization_plan.get('fix_plans', [])
        all_test_suites = []
        
        for i, fix_plan in enumerate(fix_plans, 1):
            print(f"[{i}/{len(fix_plans)}] 为 {fix_plan.get('issue_id')} 生成测试用例...")
            test_suite = self.generate_test_case(fix_plan)
            all_test_suites.append(test_suite)
            print(f"  ✓ 生成 {test_suite['total_cases']} 个测试用例 ({test_suite['automated_cases']}自动化/{test_suite['manual_cases']}人工)")
        
        test_plan = {
            'plan_id': f"QA-PLAN-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'created_at': datetime.now().isoformat(),
            'based_on_optimization': optimization_plan.get('plan_id', 'Unknown'),
            'total_suites': len(all_test_suites),
            'total_test_cases': sum(ts['total_cases'] for ts in all_test_suites),
            'total_automated': sum(ts['automated_cases'] for ts in all_test_suites),
            'total_manual': sum(ts['manual_cases'] for ts in all_test_suites),
            'test_suites': all_test_suites,
            'summary': {
                'high_priority_cases': sum(len([tc for tc in ts['test_cases'] if tc.get('priority') == '高']) for ts in all_test_suites),
                'medium_priority_cases': sum(len([tc for tc in ts['test_cases'] if tc.get('priority') == '中']) for ts in all_test_suites),
                'low_priority_cases': sum(len([tc for tc in ts['test_cases'] if tc.get('priority') == '低']) for ts in all_test_suites)
            }
        }
        
        print(f"\n✅ 测试用例生成完成")
        print(f"   测试套件：{test_plan['total_suites']}")
        print(f"   总测试用例：{test_plan['total_test_cases']}")
        print(f"   自动化：{test_plan['total_automated']}")
        print(f"   人工：{test_plan['total_manual']}")
        
        return test_plan
    
    def save_test_plan(self, test_plan: Dict):
        """保存测试计划"""
        print("\n" + "="*70)
        print("💾 保存测试计划")
        print("="*70)
        
        plan_file = self.test_case_dir / f"test_plan_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(test_plan, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存：{plan_file.name}")
        return plan_file
    
    def submit_for_review(self, test_plan: Dict) -> Dict:
        """提交测试计划给架构师审核"""
        print("\n" + "="*70)
        print("📤 提交架构师审核")
        print("="*70)
        
        review_request = {
            'review_id': f"REVIEW-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'submitted_at': datetime.now().isoformat(),
            'test_plan': test_plan,
            'status': 'pending',
            'reviewer': 'system_architect',
            'comments': [],
            'revision_count': 0
        }
        
        # 保存审核请求
        review_file = self.review_history_dir / f"review_request_{review_request['review_id']}.json"
        with open(review_file, 'w', encoding='utf-8') as f:
            json.dump(review_request, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 审核请求已提交：{review_request['review_id']}")
        print(f"   状态：{review_request['status']}")
        print(f"   审核人：{review_request['reviewer']}")
        
        return review_request
    
    def revise_test_plan(self, review_request: Dict, revision_comments: List[Dict]) -> Dict:
        """根据审核意见修改测试计划"""
        print("\n" + "="*70)
        print("✏️  修改测试计划")
        print("="*70)
        
        test_plan = review_request.get('test_plan', {})
        test_plan['revision_count'] = test_plan.get('revision_count', 0) + 1
        
        # 记录修改历史
        for suite in test_plan.get('test_suites', []):
            suite['review_history'].append({
                'revision': test_plan['revision_count'],
                'revised_at': datetime.now().isoformat(),
                'comments': revision_comments,
                'status': 'revised'
            })
        
        print(f"✅ 测试计划已修改 (版本 v{test_plan['revision_count']})")
        
        return test_plan
    
    def run(self):
        """运行完整 QA 流程"""
        print("\n" + "="*70)
        print(f"🧪 QA Agent - 测试用例生成")
        print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 加载优化方案
        optimization_plan = self.load_latest_optimization_plan()
        
        if not optimization_plan:
            print("❌ 无法加载优化方案，退出")
            return None
        
        # 步骤 2: 生成测试用例
        test_plan = self.generate_all_test_cases(optimization_plan)
        
        # 步骤 3: 保存测试计划
        self.save_test_plan(test_plan)
        
        # 步骤 4: 提交架构师审核
        review_request = self.submit_for_review(test_plan)
        
        print("\n" + "="*70)
        print("✅ QA 流程完成")
        print("="*70)
        print(f"测试计划已生成并提交审核")
        print(f"下一步：等待架构师审核")
        
        return review_request


if __name__ == '__main__':
    qa = QATestGenerator()
    qa.run()
