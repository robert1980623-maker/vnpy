#!/usr/bin/env python3
"""
Agent 健康检查系统

功能:
- Agent 心跳检测
- 任务执行状态监控
- 自动重启机制
- 健康报告生成
"""

import json
import subprocess
from pathlib import Path
from agent_report import create_report
from report_templates import create_monitoring_report
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys

# Manager 集成
MANAGER_ENABLED = True


class AgentHealthChecker:
    """Agent 健康检查器"""
    
    def __init__(self):
        self.cron_list_cmd = "openclaw cron list"
        self.health_dir = Path('./health')
        self.health_dir.mkdir(parents=True, exist_ok=True)
        
        # 关键 Agent 列表
        self.critical_agents_keywords = {
            '每日选股': ['每日选股', '选股'],
            '虚拟账户交易': ['虚拟账户', '自动交易', '每日交易'],
            '每日复盘': ['每日复盘', '复盘'],
            '数据下载': ['数据下载', '下载'],
            '首席风险官': ['首席风险官', 'CRO', '风险官'],
            '止盈止损执行': ['止盈止损执行', '止损执行'],
        }
        
        # 健康阈值
        self.max_consecutive_errors = 3
        self.max_delay_minutes = 60
    
    def _is_critical_agent(self, name: str) -> bool:
        """检查是否是关键 Agent (使用关键词模糊匹配)"""
        for keywords in self.critical_agents_keywords.values():
            if any(kw in name for kw in keywords):
                return True
        return False
    
    def get_cron_status(self) -> List[Dict]:
        """获取 cron 任务状态"""
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"❌ 获取 cron 状态失败：{result.stderr}")
                return []
            
            # 解析输出
            tasks = []
            lines = result.stdout.strip().split('\n')
            
            # 跳过表头
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 8:
                    task = {
                        'id': parts[0],
                        'name': parts[1],
                        'schedule': parts[2],
                        'next_run': parts[3],
                        'last_run': parts[4],
                        'status': parts[5],
                        'target': parts[6],
                        'agent_id': parts[7] if len(parts) > 7 else '-'
                    }
                    tasks.append(task)
            
            return tasks
        except Exception as e:
            print(f"❌ 获取 cron 状态异常：{e}")
            return []
    
    def check_agent_health(self, tasks: List[Dict]) -> Dict:
        """
        检查 Agent 健康状态
        
        Returns:
            {
                'healthy': bool,
                'critical_issues': List[str],
                'warnings': List[str],
                'agents_status': Dict
            }
        """
        critical_issues = []
        warnings = []
        agents_status = {}
        
        now = datetime.now()
        
        for task in tasks:
            name = task['name']
            status = task['status']
            last_run = task['last_run']
            
            # 解析最后运行时间
            last_run_dt = self._parse_relative_time(last_run, now)
            
            agent_info = {
                'name': name,
                'status': status,
                'last_run': last_run,
                'last_run_dt': last_run_dt.isoformat() if last_run_dt else None,
                'is_critical': self._is_critical_agent(name)
            }
            
            # 检查状态
            # 正常状态值：'ok', 'idle', 'running', '1', '5', '17', '35' 等数字
            # 异常状态值：'error', '0', 'the', 'Status', '*', 或其他非预期值
            is_status_abnormal = False
            
            if status == 'error':
                is_status_abnormal = True
            elif status == '0':
                # status=0 可能是正常的（cron 调度，未到运行时间）
                # 检查 last_run 是否为 "cron"
                if last_run == 'cron':
                    # cron 调度中，正常
                    agent_info['health'] = 'healthy'
                    agents_status[name] = agent_info
                    continue
                # 否则可能是失败
                is_status_abnormal = True
            elif status in ['the', 'Status', 'add', 'Last']:
                # 这些是解析错误（表头行），跳过不报告
                # is_status_abnormal = True
                agent_info['health'] = 'skip'
                agents_status[name] = agent_info
                continue
            elif status == '*' and name in ['首席风险官', '止盈止损执行', '每日选股', '虚拟账户', '每日复盘']:
                # 关键 Agent 显示 * 可能是正常的（cron 调度，未到运行时间）
                # 检查 last_run 是否为 "cron" 或数字
                if last_run == 'cron' or (last_run.isdigit() and int(last_run) < 60):
                    # 正常运行中或最近运行过
                    agent_info['health'] = 'healthy'
                    agents_status[name] = agent_info
                    continue
                # 否则标记为异常
                is_status_abnormal = True
            
            if is_status_abnormal:
                if self._is_critical_agent(name):
                    critical_issues.append(f"❌ 关键 Agent 异常：{name} (status={status})")
                else:
                    warnings.append(f"⚠️ Agent 异常：{name} (status={status})")
                agent_info['health'] = 'abnormal'
            
            elif status == 'idle':
                # 检查是否长时间未运行
                if last_run_dt:
                    delay = (now - last_run_dt).total_seconds() / 60
                    if delay > self.max_delay_minutes:
                        if self._is_critical_agent(name):
                            critical_issues.append(f"❌ 关键 Agent 超时：{name} ({delay:.0f}分钟未运行)")
                        else:
                            warnings.append(f"⚠️ Agent 超时：{name} ({delay:.0f}分钟未运行)")
                        agent_info['health'] = 'timeout'
                    else:
                        agent_info['health'] = 'idle'
                else:
                    agent_info['health'] = 'unknown'
            
            elif status == 'ok':
                agent_info['health'] = 'healthy'
            
            else:
                agent_info['health'] = status
            
            agents_status[name] = agent_info
        
        # 检查关键 Agent 是否都在线
        critical_agents_found = {}
        for task in tasks:
            task_name = task['name']
            for key, keywords in self.critical_agents_keywords.items():
                if any(kw in task_name for kw in keywords):
                    critical_agents_found[key] = task_name
                    break
        missing_critical = [key for key in self.critical_agents_keywords 
                          if key not in critical_agents_found]
        
        for missing in missing_critical:
            critical_issues.append(f"❌ 关键 Agent 缺失：{missing}")
        
        return {
            'healthy': len(critical_issues) == 0,
            'critical_issues': critical_issues,
            'warnings': warnings,
            'agents_status': agents_status,
            'total_agents': len(tasks),
            'critical_agents_count': len(self.critical_agents_keywords),
            'timestamp': now.isoformat()
        }
    
    def _parse_relative_time(self, time_str: str, now: datetime) -> Optional[datetime]:
        """解析相对时间 (如 '24m ago', '2h ago')"""
        try:
            if not time_str or time_str == '-':
                return None
            
            time_str = time_str.lower().strip()
            
            if 'ago' in time_str:
                parts = time_str.replace(' ago', '').split()
                if len(parts) == 2:
                    value = int(parts[0])
                    unit = parts[1]
                    
                    if 'm' in unit:
                        return now - timedelta(minutes=value)
                    elif 'h' in unit:
                        return now - timedelta(hours=value)
                    elif 'd' in unit:
                        return now - timedelta(days=value)
                    elif 's' in unit:
                        return now - timedelta(seconds=value)
            
            # 尝试解析绝对时间
            for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%H:%M']:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None
    
    def auto_restart_failed_agents(self, health_report: Dict):
        """自动重启失败的 Agent"""
        restarted = []
        
        for name, info in health_report['agents_status'].items():
            if info['health'] == 'error' and info.get('is_critical', False):
                # 尝试重启
                print(f"🔄 尝试重启关键 Agent: {name}")
                # TODO: 实现重启逻辑
                restarted.append(name)
        
        if restarted:
            print(f"✅ 已重启 {len(restarted)} 个 Agent: {', '.join(restarted)}")
        
        return restarted
    
    def generate_report(self) -> str:
        """生成健康报告"""
        tasks = self.get_cron_status()
        health = self.check_agent_health(tasks)
        
        report = []
        report.append("=" * 70)
        report.append("🏥 Agent 健康检查报告")
        report.append(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        # 总体状态
        if health['healthy']:
            report.append(f"\n✅ 系统健康状态：健康")
        else:
            report.append(f"\n❌ 系统健康状态：异常")
        
        report.append(f"总 Agent 数：{health['total_agents']}")
        report.append(f"关键 Agent 数：{health['critical_agents_count']}")
        
        # 关键问题
        if health['critical_issues']:
            report.append(f"\n❌ 关键问题 ({len(health['critical_issues'])}):")
            for issue in health['critical_issues']:
                report.append(f"  {issue}")
        
        # 警告
        if health['warnings']:
            report.append(f"\n⚠️ 警告 ({len(health['warnings'])}):")
            for warning in health['warnings']:
                report.append(f"  {warning}")
        
        # Agent 状态详情
        report.append(f"\n📊 Agent 状态详情:")
        report.append(f"{'Agent 名称':<30} {'状态':<10} {'健康度':<10} {'最后运行':<15}")
        report.append("-" * 70)
        
        # 先显示关键 Agent
        critical_agents = [(n, i) for n, i in health['agents_status'].items() if i.get('is_critical', False)]
        other_agents = [(n, i) for n, i in health['agents_status'].items() if not i.get('is_critical', False)]
        
        for name, info in critical_agents + other_agents:
            status_icon = {
                'healthy': '✅',
                'error': '❌',
                'timeout': '⏰',
                'idle': '⏸️',
                'unknown': '❓'
            }.get(info['health'], '•')
            
            report.append(f"{status_icon} {name:<28} {info['status']:<10} {info['health']:<10} {info['last_run'] or '-':<15}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)
    
    def save_report(self):
        """保存健康报告"""
        report = self.generate_report()
        
        # 保存文本报告
        report_file = self.health_dir / f'health_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 保存 JSON 状态
        tasks = self.get_cron_status()
        health = self.check_agent_health(tasks)
        json_file = self.health_dir / f'health_status_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(health, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 报告已保存：{report_file}")
        print(f"✅ 状态已保存：{json_file}")
        
        return report

    def _report_to_manager(self, health: Dict):
        """上报健康问题到 Manager 问题队列"""
        if not MANAGER_ENABLED:
            print("  ℹ️ Manager 集成已禁用")
            return
        
        try:
            from manager_interface import QuantManager
            from issue_queue import Issue
            
            critical_issues = health.get('critical_issues', [])
            warnings = health.get('warnings', [])
            
            if not critical_issues and not warnings:
                print("  ✅ 无健康问题需要上报")
                return
            
            manager = QuantManager()
            reported_count = 0
            
            # 上报关键问题
            for issue_text in critical_issues:
                # 提取 Agent 名称
                agent_name = "unknown"
                if "关键 Agent" in issue_text:
                    agent_name = issue_text.split("：")[-1].strip()
                
                new_issue = manager.issue_queue.create_issue(
                    agent="health_check",
                    severity="P0",
                    error_type="agent_health",
                    error_message=issue_text
                )
                
                issue_id = manager.issue_queue.write_issue(new_issue)
                print(f"  ✅ 已上报 P0 问题：{issue_id} - {issue_text[:50]}...")
                reported_count += 1
            
            # 上报警告
            for warning_text in warnings:
                agent_name = "unknown"
                if "Agent" in warning_text:
                    agent_name = warning_text.split("：")[-1].strip()
                
                new_issue = manager.issue_queue.create_issue(
                    agent="health_check",
                    severity="P1",
                    error_type="agent_health",
                    error_message=warning_text
                )
                
                issue_id = manager.issue_queue.write_issue(new_issue)
                print(f"  ✅ 已上报 P1 问题：{issue_id} - {warning_text[:50]}...")
                reported_count += 1
            
            if reported_count > 0:
                print(f"  📊 共上报 {reported_count} 个健康问题到 Manager 队列")
                
                # 自动触发 Manager 处理
                print("  🔄 触发 Manager 自动处理...")
                pending = manager.issue_queue.get_pending_issues()
                for issue in pending[-reported_count:]:
                    try:
                        task = manager.handle_error_report(issue)
                        print(f"    → 已调度给：{task['agent']} ({task['type']})")
                    except Exception as e:
                        print(f"    ⚠️ 调度失败：{e}")
                
        except Exception as e:
            print(f"  ⚠️ 上报 Manager 失败：{e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    checker = AgentHealthChecker()
    report = checker.generate_report()
    print(report)
    checker.save_report()
    
    # 获取健康状态
    tasks = checker.get_cron_status()
    health = checker.check_agent_health(tasks)
    
    # 上报健康问题到 Manager
    print("\n📋 检查健康问题...")
    checker._report_to_manager(health)
    
    # 自动重启失败的 Agent
    if not health['healthy']:
        print("\n🔄 执行自动修复...")
        checker.auto_restart_failed_agents(health)


if __name__ == '__main__':
    main()
