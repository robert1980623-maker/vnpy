#!/usr/bin/env python3
"""
主 Agent - 问题调度与解决验证

功能：
1. 接收日志分析 Agent 提交的问题报告
2. 根据问题类型调度合适的 Agent（Delta/Architect/QA/Data-Agent）
3. 跟踪问题解决进度
4. 验证所有问题是否已解决
5. 生成解决报告
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

class MainAgentDispatcher:
    """主 Agent - 问题调度与解决验证"""
    
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy/examples/alpha_research')
        self.report_dir = Path('./reports/log_analysis')
        self.resolution_dir = Path('./reports/resolutions')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.resolution_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent 映射
        self.agent_mapping = {
            'delta': {
                'script': 'delta_architect_review.py',
                'handles': ['代码复杂度', '错误处理', '性能优化', '重构'],
                'timeout': 1800
            },
            'architect': {
                'script': 'system_architect_review.py',
                'handles': ['架构问题', '模块设计', '依赖管理'],
                'timeout': 1800
            },
            'qa': {
                'script': 'qa_architect_loop.py',
                'handles': ['测试', '验证', '质量'],
                'timeout': 1800
            },
            'data-agent': {
                'script': 'check_data_quality.py',
                'handles': ['数据质量', '数据完整性'],
                'timeout': 900
            }
        }
    
    def load_pending_issues(self) -> List[Dict]:
        """加载待处理的问题"""
        print("\n" + "="*70)
        print("📥 加载待处理问题")
        print("="*70)
        
        issue_tracker_file = self.report_dir / 'issue_tracker.json'
        
        if not issue_tracker_file.exists():
            print("✅ 没有待处理问题")
            return []
        
        with open(issue_tracker_file, 'r', encoding='utf-8') as f:
            tracker = json.load(f)
        
        pending = [
            issue for issue in tracker.values()
            if issue.get('resolution_status') == 'pending'
        ]
        
        print(f"待处理问题：{len(pending)} 个")
        
        return pending
    
    def categorize_issues(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """将问题分类并映射到对应 Agent"""
        print("\n" + "="*70)
        print("📋 问题分类")
        print("="*70)
        
        categorized = {
            'delta': [],
            'architect': [],
            'qa': [],
            'data-agent': []
        }
        
        for issue in issues:
            category = issue.get('category', 'error')
            description = issue.get('description', '').lower()
            
            # 根据问题类型和描述分配 Agent
            if '代码' in description or '函数' in description or '重构' in description:
                categorized['delta'].append(issue)
            elif '架构' in description or '模块' in description or '依赖' in description:
                categorized['architect'].append(issue)
            elif '数据' in description or '质量' in description:
                categorized['data-agent'].append(issue)
            elif '测试' in description or '验证' in description:
                categorized['qa'].append(issue)
            else:
                # 默认分配给 Delta
                categorized['delta'].append(issue)
        
        # 打印分配结果
        for agent, agent_issues in categorized.items():
            if agent_issues:
                print(f"  🤖 {agent}: {len(agent_issues)} 个问题")
        
        return categorized
    
    def dispatch_to_agent(self, agent_name: str, issues: List[Dict]) -> Dict:
        """调度 Agent 解决问题"""
        print("\n" + "="*70)
        print(f"🚀 调度 {agent_name} 解决问题")
        print("="*70)
        
        if agent_name not in self.agent_mapping:
            print(f"⚠️ 未知 Agent: {agent_name}")
            return {'status': 'error', 'message': 'Unknown agent'}
        
        agent_config = self.agent_mapping[agent_name]
        script_path = self.project_root / agent_config['script']
        
        if not script_path.exists():
            print(f"⚠️ 脚本不存在：{script_path}")
            return {'status': 'error', 'message': 'Script not found'}
        
        print(f"执行脚本：{agent_config['script']}")
        print(f"处理问题：{len(issues)} 个")
        
        try:
            # 运行 Agent 脚本
            result = subprocess.run(
                ['python3', agent_config['script']],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=agent_config['timeout']
            )
            
            output = result.stdout[-2000:] if result.stdout else ''
            
            if result.returncode == 0:
                print(f"✅ {agent_name} 执行成功")
                return {
                    'status': 'success',
                    'agent': agent_name,
                    'issues_handled': len(issues),
                    'output': output
                }
            else:
                print(f"⚠️ {agent_name} 执行失败：{result.stderr[:200]}")
                return {
                    'status': 'error',
                    'agent': agent_name,
                    'error': result.stderr[:500]
                }
        
        except subprocess.TimeoutExpired:
            print(f"⚠️ {agent_name} 执行超时")
            return {
                'status': 'timeout',
                'agent': agent_name
            }
        except Exception as e:
            print(f"⚠️ {agent_name} 执行异常：{e}")
            return {
                'status': 'error',
                'agent': agent_name,
                'error': str(e)
            }
    
    def verify_resolution(self, issues: List[Dict], agent_results: Dict) -> Dict:
        """验证问题是否已解决"""
        print("\n" + "="*70)
        print("✅ 验证问题解决状态")
        print("="*70)
        
        resolved = []
        unresolved = []
        
        for issue in issues:
            issue_id = issue.get('issue_id')
            
            # 检查是否有对应的解决结果
            agent_result = agent_results.get(issue.get('assigned_to', 'unknown'))
            
            if agent_result and agent_result.get('status') == 'success':
                resolved.append({
                    **issue,
                    'resolution_status': 'resolved',
                    'resolved_at': datetime.now().isoformat(),
                    'resolved_by': issue.get('assigned_to')
                })
            else:
                unresolved.append({
                    **issue,
                    'resolution_status': 'unresolved',
                    'reason': 'Agent execution failed or not completed'
                })
        
        print(f"已解决：{len(resolved)}")
        print(f"未解决：{len(unresolved)}")
        
        return {
            'verification_time': datetime.now().isoformat(),
            'total_issues': len(issues),
            'resolved': len(resolved),
            'unresolved': len(unresolved),
            'resolved_issues': resolved,
            'unresolved_issues': unresolved,
            'all_resolved': len(unresolved) == 0
        }
    
    def update_issue_tracker(self, verification_result: Dict):
        """更新问题追踪器"""
        print("\n" + "="*70)
        print("💾 更新问题追踪器")
        print("="*70)
        
        issue_tracker_file = self.report_dir / 'issue_tracker.json'
        
        tracker = {}
        if issue_tracker_file.exists():
            with open(issue_tracker_file, 'r', encoding='utf-8') as f:
                tracker = json.load(f)
        
        # 更新已解决的问题
        for resolved in verification_result.get('resolved_issues', []):
            issue_id = resolved['issue_id']
            if issue_id in tracker:
                tracker[issue_id].update({
                    'resolution_status': 'resolved',
                    'resolved_at': resolved['resolved_at'],
                    'resolved_by': resolved['resolved_by']
                })
        
        # 保存更新
        with open(issue_tracker_file, 'w', encoding='utf-8') as f:
            json.dump(tracker, f, ensure_ascii=False, indent=2)
        
        print("✅ 问题追踪器已更新")
    
    def generate_resolution_report(self, verification_result: Dict) -> Dict:
        """生成解决报告"""
        print("\n" + "="*70)
        print("📝 生成解决报告")
        print("="*70)
        
        report = {
            'report_id': f"RESOLUTION-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_issues': verification_result['total_issues'],
                'resolved': verification_result['resolved'],
                'unresolved': verification_result['unresolved'],
                'resolution_rate': verification_result['resolved'] / verification_result['total_issues'] * 100 if verification_result['total_issues'] > 0 else 0
            },
            'all_resolved': verification_result['all_resolved'],
            'resolved_issues': verification_result['resolved_issues'],
            'unresolved_issues': verification_result['unresolved_issues'],
            'next_steps': []
        }
        
        # 生成后续步骤建议
        if not verification_result['all_resolved']:
            report['next_steps'].append({
                'priority': '高',
                'action': '重新调度未解决问题',
                'details': f"{verification_result['unresolved']} 个问题未解决，需要重新处理"
            })
        else:
            report['next_steps'].append({
                'priority': '低',
                'action': '持续监控',
                'details': '所有问题已解决，继续监控日志'
            })
        
        # 保存报告
        report_file = self.resolution_dir / f"resolution_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 解决报告已保存：{report_file.name}")
        print(f"解决率：{report['summary']['resolution_rate']:.1f}%")
        
        return report
    
    def run(self) -> Dict:
        """运行完整调度流程"""
        print("\n" + "="*70)
        print(f"🤖 主 Agent - 问题调度与解决")
        print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 加载待处理问题
        issues = self.load_pending_issues()
        
        if not issues:
            print("✅ 没有待处理问题")
            return {'status': 'no_issues'}
        
        # 步骤 2: 问题分类
        categorized = self.categorize_issues(issues)
        
        # 步骤 3: 调度 Agent 解决
        agent_results = {}
        for agent_name, agent_issues in categorized.items():
            if agent_issues:
                # 标记问题已分配
                for issue in agent_issues:
                    issue['assigned_to'] = agent_name
                
                result = self.dispatch_to_agent(agent_name, agent_issues)
                agent_results[agent_name] = result
        
        # 步骤 4: 验证解决状态
        verification = self.verify_resolution(issues, agent_results)
        
        # 步骤 5: 更新追踪器
        self.update_issue_tracker(verification)
        
        # 步骤 6: 生成解决报告
        resolution_report = self.generate_resolution_report(verification)
        
        print("\n" + "="*70)
        print("✅ 问题调度与解决完成")
        print("="*70)
        print(f"总问题：{verification['total_issues']}")
        print(f"已解决：{verification['resolved']}")
        print(f"未解决：{verification['unresolved']}")
        print(f"解决率：{resolution_report['summary']['resolution_rate']:.1f}%")
        
        return resolution_report


if __name__ == '__main__':
    dispatcher = MainAgentDispatcher()
    dispatcher.run()
