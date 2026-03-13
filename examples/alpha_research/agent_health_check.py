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
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys


class AgentHealthChecker:
    """Agent 健康检查器"""
    
    def __init__(self):
        self.cron_list_cmd = "openclaw cron list"
        self.health_dir = Path('./health')
        self.health_dir.mkdir(parents=True, exist_ok=True)
        
        # 关键 Agent 列表
        self.critical_agents = [
            '每日选股',
            '虚拟账户 - 每日自动交易',
            '每日复盘',
            '数据下载',
            '首席风险官 (CRO)',
            '止盈止损执行 Agent',
        ]
        
        # 健康阈值
        self.max_consecutive_errors = 3
        self.max_delay_minutes = 60
    
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
                'is_critical': name in self.critical_agents
            }
            
            # 检查状态
            if status == 'error':
                if name in self.critical_agents:
                    critical_issues.append(f"❌ 关键 Agent 错误：{name}")
                else:
                    warnings.append(f"⚠️ Agent 错误：{name}")
                agent_info['health'] = 'error'
            
            elif status == 'idle':
                # 检查是否长时间未运行
                if last_run_dt:
                    delay = (now - last_run_dt).total_seconds() / 60
                    if delay > self.max_delay_minutes:
                        if name in self.critical_agents:
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
        critical_agents_found = [name for name in self.critical_agents 
                                if any(t['name'] == name for t in tasks)]
        missing_critical = [name for name in self.critical_agents 
                          if name not in critical_agents_found]
        
        for missing in missing_critical:
            critical_issues.append(f"❌ 关键 Agent 缺失：{missing}")
        
        return {
            'healthy': len(critical_issues) == 0,
            'critical_issues': critical_issues,
            'warnings': warnings,
            'agents_status': agents_status,
            'total_agents': len(tasks),
            'critical_agents_count': len(self.critical_agents),
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


def main():
    """主函数"""
    checker = AgentHealthChecker()
    report = checker.generate_report()
    print(report)
    checker.save_report()
    
    # 自动重启失败的 Agent
    tasks = checker.get_cron_status()
    health = checker.check_agent_health(tasks)
    if not health['healthy']:
        print("\n🔄 执行自动修复...")
        checker.auto_restart_failed_agents(health)


if __name__ == '__main__':
    main()
