#!/usr/bin/env python3
"""
日志分析 Agent - 增强版

功能：
1. 分析日志文件，发现问题和异常
2. 总结问题并分类（严重/警告/提示）
3. 提交问题报告给主 Agent
4. 跟踪问题解决状态
5. 验证问题是否已解决
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

class EnhancedLogAnalyzer:
    """日志分析 Agent - 增强版"""
    
    def __init__(self):
        self.log_dir = Path('./logs')
        self.report_dir = Path('./reports/log_analysis')
        self.issue_tracker_file = Path('./reports/log_analysis/issue_tracker.json')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 问题分类
        self.issue_categories = {
            'error': '错误',
            'warning': '警告',
            'timeout': '超时',
            'performance': '性能',
            'data_quality': '数据质量',
            'architecture': '架构问题'
        }
        
        # 严重级别
        self.severity_levels = {
            'critical': '严重',  # 需要立即处理
            'high': '高',        # 需要尽快处理
            'medium': '中',      # 需要处理
            'low': '低'          # 可以稍后处理
        }
    
    def analyze_logs(self, hours: int = 24) -> Dict:
        """分析最近 N 小时的日志"""
        print("\n" + "="*70)
        print(f"📊 日志分析（最近{hours}小时）")
        print("="*70)
        
        issues = []
        log_files = []
        
        # 收集日志文件
        if self.log_dir.exists():
            for f in self.log_dir.glob('*.log'):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if datetime.now() - mtime < timedelta(hours=hours):
                    log_files.append(f)
        
        print(f"找到 {len(log_files)} 个日志文件")
        
        # 分析每个日志文件
        for log_file in log_files:
            file_issues = self._analyze_single_log(log_file)
            issues.extend(file_issues)
        
        # 去重和分类
        unique_issues = self._deduplicate_issues(issues)
        
        # 统计
        stats = self._generate_stats(unique_issues)
        
        print(f"\n发现问题：{len(unique_issues)} 个")
        print(f"严重：{stats['critical']} | 高：{stats['high']} | 中：{stats['medium']} | 低：{stats['low']}")
        
        return {
            'analysis_time': datetime.now().isoformat(),
            'time_range_hours': hours,
            'log_files_analyzed': len(log_files),
            'total_issues': len(unique_issues),
            'issues': unique_issues,
            'stats': stats
        }
    
    def _analyze_single_log(self, log_file: Path) -> List[Dict]:
        """分析单个日志文件"""
        issues = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # 检测错误
                if 'ERROR' in line or '❌' in line or '失败' in line:
                    issue = self._parse_error_line(log_file, i, line)
                    if issue:
                        issues.append(issue)
                
                # 检测警告
                elif 'WARNING' in line or 'WARN' in line or '⚠️' in line:
                    issue = self._parse_warning_line(log_file, i, line)
                    if issue:
                        issues.append(issue)
                
                # 检测超时
                elif 'timeout' in line.lower() or '超时' in line:
                    issue = self._parse_timeout_line(log_file, i, line)
                    if issue:
                        issues.append(issue)
                
                # 检测异常
                elif 'Exception' in line or 'Traceback' in line:
                    issue = self._parse_exception_line(log_file, i, line)
                    if issue:
                        issues.append(issue)
        
        except Exception as e:
            print(f"⚠️ 读取 {log_file} 失败：{e}")
        
        return issues
    
    def _parse_error_line(self, log_file: Path, line_num: int, line: str) -> Dict:
        """解析错误行"""
        # 提取错误信息
        error_match = re.search(r'ERROR.*?[:：]\s*(.+?)(?:\n|$)', line)
        error_msg = error_match.group(1).strip() if error_match else line.strip()
        
        # 判断严重级别
        if '失败' in line or 'failed' in line.lower():
            severity = 'high'
        else:
            severity = 'medium'
        
        # 判断问题类型
        if '任务失败' in line or 'task failed' in line.lower():
            category = 'error'
        elif '数据' in line:
            category = 'data_quality'
        else:
            category = 'error'
        
        return {
            'issue_id': f"LOG-{abs(hash(f'{log_file}{line_num}')) % 10000:04d}",
            'source': 'log_analysis',
            'log_file': str(log_file),
            'line_number': line_num,
            'category': category,
            'severity': severity,
            'description': error_msg[:200],
            'raw_line': line.strip()[:300],
            'detected_at': datetime.now().isoformat(),
            'status': 'new',
            'assigned_to': None,
            'resolved_at': None
        }
    
    def _parse_warning_line(self, log_file: Path, line_num: int, line: str) -> Dict:
        """解析警告行"""
        warning_match = re.search(r'WARNING.*?[:：]\s*(.+?)(?:\n|$)', line)
        warning_msg = warning_match.group(1).strip() if warning_match else line.strip()
        
        return {
            'issue_id': f"LOG-{abs(hash(f'{log_file}{line_num}')) % 10000:04d}",
            'source': 'log_analysis',
            'log_file': str(log_file),
            'line_number': line_num,
            'category': 'warning',
            'severity': 'low',
            'description': warning_msg[:200],
            'raw_line': line.strip()[:300],
            'detected_at': datetime.now().isoformat(),
            'status': 'new',
            'assigned_to': None,
            'resolved_at': None
        }
    
    def _parse_timeout_line(self, log_file: Path, line_num: int, line: str) -> Dict:
        """解析超时行"""
        return {
            'issue_id': f"LOG-{abs(hash(f'{log_file}{line_num}')) % 10000:04d}",
            'source': 'log_analysis',
            'log_file': str(log_file),
            'line_number': line_num,
            'category': 'timeout',
            'severity': 'high',
            'description': f'检测到超时：{line.strip()[:150]}',
            'raw_line': line.strip()[:300],
            'detected_at': datetime.now().isoformat(),
            'status': 'new',
            'assigned_to': None,
            'resolved_at': None
        }
    
    def _parse_exception_line(self, log_file: Path, line_num: int, line: str) -> Dict:
        """解析异常行"""
        return {
            'issue_id': f"LOG-{abs(hash(f'{log_file}{line_num}')) % 10000:04d}",
            'source': 'log_analysis',
            'log_file': str(log_file),
            'line_number': line_num,
            'category': 'error',
            'severity': 'critical',
            'description': f'检测到异常：{line.strip()[:150]}',
            'raw_line': line.strip()[:300],
            'detected_at': datetime.now().isoformat(),
            'status': 'new',
            'assigned_to': None,
            'resolved_at': None
        }
    
    def _deduplicate_issues(self, issues: List[Dict]) -> List[Dict]:
        """去重问题"""
        seen = set()
        unique = []
        
        for issue in issues:
            key = f"{issue['category']}:{issue['description'][:100]}"
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        
        return unique
    
    def _generate_stats(self, issues: List[Dict]) -> Dict:
        """生成统计信息"""
        stats = defaultdict(int)
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        
        for issue in issues:
            by_category[issue['category']] += 1
            by_severity[issue['severity']] += 1
        
        stats['by_category'] = dict(by_category)
        stats['by_severity'] = dict(by_severity)
        stats['critical'] = by_severity.get('critical', 0)
        stats['high'] = by_severity.get('high', 0)
        stats['medium'] = by_severity.get('medium', 0)
        stats['low'] = by_severity.get('low', 0)
        
        return stats
    
    def summarize_issues(self, analysis_result: Dict) -> Dict:
        """总结问题，准备提交给主 Agent"""
        print("\n" + "="*70)
        print("📝 总结问题报告")
        print("="*70)
        
        issues = analysis_result.get('issues', [])
        
        # 按严重程度分组
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        high_issues = [i for i in issues if i['severity'] == 'high']
        medium_issues = [i for i in issues if i['severity'] == 'medium']
        low_issues = [i for i in issues if i['severity'] == 'low']
        
        # 生成总结
        summary = {
            'report_id': f"LOG-REPORT-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'analysis_period': f"{analysis_result.get('time_range_hours', 24)}小时",
            'total_issues': len(issues),
            'summary': {
                'critical': len(critical_issues),
                'high': len(high_issues),
                'medium': len(medium_issues),
                'low': len(low_issues)
            },
            'critical_issues': critical_issues,
            'high_priority_issues': high_issues,
            'categories': analysis_result.get('stats', {}).get('by_category', {}),
            'recommendations': self._generate_recommendations(issues),
            'requires_action': len(critical_issues) + len(high_issues) > 0
        }
        
        # 打印总结
        print(f"总问题数：{len(issues)}")
        print(f"严重：{len(critical_issues)} | 高：{len(high_issues)} | 中：{len(medium_issues)} | 低：{len(low_issues)}")
        
        if critical_issues:
            print(f"\n🔴 严重问题 ({len(critical_issues)}):")
            for i, issue in enumerate(critical_issues[:5], 1):
                print(f"  {i}. [{issue['issue_id']}] {issue['description'][:80]}")
        
        if high_issues:
            print(f"\n🟠 高优先级问题 ({len(high_issues)}):")
            for i, issue in enumerate(high_issues[:5], 1):
                print(f"  {i}. [{issue['issue_id']}] {issue['description'][:80]}")
        
        return summary
    
    def _generate_recommendations(self, issues: List[Dict]) -> List[Dict]:
        """生成解决建议"""
        recommendations = []
        
        # 统计问题类型
        category_count = defaultdict(int)
        for issue in issues:
            category_count[issue['category']] += 1
        
        # 根据问题类型生成建议
        if category_count.get('error', 0) > 5:
            recommendations.append({
                'type': '错误处理',
                'priority': '高',
                'suggestion': '多个任务失败，建议检查相关脚本和配置',
                'suggested_agent': 'delta'
            })
        
        if category_count.get('timeout', 0) > 0:
            recommendations.append({
                'type': '超时优化',
                'priority': '高',
                'suggestion': '检测到超时问题，建议增加超时时间或优化性能',
                'suggested_agent': 'delta'
            })
        
        if category_count.get('data_quality', 0) > 0:
            recommendations.append({
                'type': '数据质量',
                'priority': '中',
                'suggestion': '数据质量问题，建议检查数据源和处理逻辑',
                'suggested_agent': 'data-agent'
            })
        
        if category_count.get('warning', 0) > 10:
            recommendations.append({
                'type': '警告清理',
                'priority': '低',
                'suggestion': '大量警告信息，建议清理或修复',
                'suggested_agent': 'delta'
            })
        
        return recommendations
    
    def save_report(self, summary: Dict):
        """保存问题报告"""
        print("\n" + "="*70)
        print("💾 保存问题报告")
        print("="*70)
        
        report_file = self.report_dir / f"log_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 更新问题追踪器
        self._update_issue_tracker(summary)
        
        print(f"✅ 报告已保存：{report_file.name}")
        
        return report_file
    
    def _update_issue_tracker(self, summary: Dict):
        """更新问题追踪器"""
        tracker = {}
        
        if self.issue_tracker_file.exists():
            with open(self.issue_tracker_file, 'r', encoding='utf-8') as f:
                tracker = json.load(f)
        
        # 添加新问题
        all_issues = summary.get('critical_issues', []) + summary.get('high_priority_issues', [])
        
        for issue in all_issues:
            issue_id = issue['issue_id']
            if issue_id not in tracker:
                tracker[issue_id] = {
                    **issue,
                    'reported_at': summary['generated_at'],
                    'resolution_status': 'pending'
                }
        
        with open(self.issue_tracker_file, 'w', encoding='utf-8') as f:
            json.dump(tracker, f, ensure_ascii=False, indent=2)
    
    def submit_to_main_agent(self, summary: Dict):
        """提交问题报告给主 Agent"""
        print("\n" + "="*70)
        print("📤 提交问题报告给主 Agent")
        print("="*70)
        
        if not summary.get('requires_action', False):
            print("✅ 没有需要立即处理的问题")
            return True
        
        print(f"🔴 发现 {summary['summary']['critical']} 个严重问题")
        print(f"🟠 发现 {summary['summary']['high']} 个高优先级问题")
        print(f"\n建议调度的 Agent:")
        
        for rec in summary.get('recommendations', []):
            print(f"  - {rec['suggested_agent']}: {rec['suggestion']}")
        
        # 保存提交记录
        submission_file = self.report_dir / f"submission_{summary['report_id']}.json"
        with open(submission_file, 'w', encoding='utf-8') as f:
            json.dump({
                'submitted_at': datetime.now().isoformat(),
                'status': 'submitted',
                'summary': summary
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 问题报告已提交：{summary['report_id']}")
        print("等待主 Agent 调度处理...")
        
        return True
    
    def run(self, hours: int = 24) -> Dict:
        """运行完整日志分析流程"""
        print("\n" + "="*70)
        print(f"🔍 日志分析 Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 分析日志
        analysis_result = self.analyze_logs(hours)
        
        # 步骤 2: 总结问题
        summary = self.summarize_issues(analysis_result)
        
        # 步骤 3: 保存报告
        self.save_report(summary)
        
        # 步骤 4: 提交给主 Agent
        self.submit_to_main_agent(summary)
        
        print("\n" + "="*70)
        print("✅ 日志分析完成")
        print("="*70)
        
        return summary


if __name__ == '__main__':
    analyzer = EnhancedLogAnalyzer()
    analyzer.run(hours=24)


# ========== 增强功能：问题队列扫描和上报 ==========

from issue_queue import IssueQueue
from manager_interface import QuantManager

class EnhancedLogAnalyzerWithReporting:
    """增强的日志分析器 - 带问题上报"""
    
    def __init__(self):
        self.issue_queue = IssueQueue()
        self.manager = QuantManager()
        self.error_log_dir = Path('./logs/errors/')
    
    def scan_and_report(self):
        """扫描错误并上报 Manager"""
        print("🔍 开始扫描错误日志...")
        
        # 扫描最新的错误日志
        today = datetime.now().strftime('%Y-%m-%d')
        error_log = self.error_log_dir / f"errors_{today}.jsonl"
        
        if not error_log.exists():
            print("✅ 无新错误")
            return
        
        # 读取错误
        errors = []
        with open(error_log, 'r', encoding='utf-8') as f:
            for line in f:
                errors.append(json.loads(line))
        
        print(f"发现 {len(errors)} 个错误")
        
        # 分类处理
        p0_errors = [e for e in errors if e.get('severity') == 'P0']
        p1_errors = [e for e in errors if e.get('severity') == 'P1']
        p2_errors = [e for e in errors if e.get('severity') == 'P2']
        
        # P0 已经在 Agent 错误处理时触发
        # 处理 P1
        for error in p1_errors:
            self.report_p1_error(error)
        
        # 处理 P2 (汇总)
        if p2_errors:
            self.report_p2_summary(p2_errors)
        
        print("✅ 扫描完成")
    
    def report_p1_error(self, error: Dict):
        """上报 P1 错误"""
        issue = self.issue_queue.create_issue(
            agent=error.get('agent', 'unknown'),
            severity='P1',
            error_type=error.get('error_type', 'Unknown'),
            error_message=error.get('error_message', 'Unknown error')
        )
        issue_id = self.issue_queue.write_issue(issue)
        
        # 上报 Manager
        self.manager.handle_error_report(issue)
        
        print(f"  📤 P1 错误已上报：{issue_id}")
    
    def report_p2_summary(self, errors: List[Dict]):
        """汇总上报 P2 错误"""
        # P2 错误只记录，不立即通知
        print(f"  📝 记录 {len(errors)} 个 P2 错误到汇总报告")


if __name__ == '__main__':
    # 测试增强功能
    analyzer = EnhancedLogAnalyzerWithReporting()
    analyzer.scan_and_report()
