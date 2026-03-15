#!/usr/bin/env python3
"""
Human 风格报告生成器

把机器语言翻译成人话
"""

from datetime import datetime
from typing import Dict, List, Optional


class HumanReporter:
    """Human 风格报告生成器"""
    
    def __init__(self, agent_name: str = ""):
        self.agent_name = agent_name
        self.tone = "friendly"  # friendly, casual, professional
    
    def generate_qa_report(self, qa_result: Dict) -> str:
        """生成 QA 检查报告 (人话版)"""
        
        # 提取关键信息
        changes = qa_result.get('changes', [])
        coverage = qa_result.get('coverage', 0)
        passed = qa_result.get('passed', True)
        issues = qa_result.get('issues', [])
        
        # 生成人话报告
        lines = []
        lines.append(f"📋 QA 门禁检查完成 ({datetime.now().strftime('%H:%M')})")
        lines.append("")
        
        if passed and not changes:
            lines.append("今晚的检查一切正常：")
            lines.append(f"✅ 代码变更：无")
            lines.append(f"✅ 测试覆盖率：{coverage:.1f}% (达标)")
            lines.append(f"✅ 质量评分：A")
            lines.append("")
            lines.append("简单来说：没啥问题，代码挺健康，可以继续睡个好觉 😴")
        elif changes:
            lines.append(f"发现 {len(changes)} 个代码变更：")
            for change in changes[:5]:
                lines.append(f"  • {change.get('file', 'unknown')}: {change.get('type', 'changed')}")
            lines.append("")
            if passed:
                lines.append("都通过检查了，放心！✅")
            else:
                lines.append("⚠️ 有几个问题需要看看")
        else:
            lines.append("⚠️ 发现一些问题：")
            for issue in issues[:5]:
                lines.append(f"  • {issue}")
            lines.append("")
            lines.append("建议有空看看，不着急 🔍")
        
        lines.append("")
        lines.append(f"下次检查：{self._next_check_time()}")
        
        return "\n".join(lines)
    
    def generate_manager_report(self, manager_result: Dict) -> str:
        """生成 Manager 报告 (人话版)"""
        
        pending = manager_result.get('pending', 0)
        processing = manager_result.get('processing', 0)
        resolved = manager_result.get('resolved', 0)
        
        lines = []
        lines.append("📊 Manager 问题队列报告")
        lines.append("")
        
        if pending == 0 and processing == 0:
            lines.append("好消息！问题队列清空了 🎉")
            lines.append("")
            lines.append("当前状态：")
            lines.append(f"  ✅ 待处理：{pending} 个")
            lines.append(f"  ✅ 处理中：{processing} 个")
            lines.append(f"  ✅ 已解决：{resolved} 个")
            lines.append("")
            lines.append("系统运行平稳，可以安心 😌")
        elif pending > 0:
            lines.append(f"⚠️ 有 {pending} 个新问题需要处理")
            lines.append("")
            lines.append("当前状态：")
            lines.append(f"  ⏳ 待处理：{pending} 个")
            lines.append(f"  🔄 处理中：{processing} 个")
            lines.append(f"  ✅ 已解决：{resolved} 个")
            lines.append("")
            lines.append("建议：让 Manager 自动处理就行，不着急")
        else:
            lines.append(f"🔄 有 {processing} 个问题正在处理中")
            lines.append("")
            lines.append("当前状态：")
            lines.append(f"  ✅ 待处理：{pending} 个")
            lines.append(f"  🔄 处理中：{processing} 个")
            lines.append(f"  ✅ 已解决：{resolved} 个")
            lines.append("")
            lines.append("Delta 工程师正在干活，稍等一下 ⏳")
        
        lines.append("")
        lines.append(f"下次检查：{self._next_check_time()}")
        
        return "\n".join(lines)
    
    def generate_health_report(self, health_result: Dict) -> str:
        """生成健康检查报告 (人话版)"""
        
        healthy = health_result.get('healthy', True)
        agents_ok = health_result.get('agents_ok', 0)
        agents_total = health_result.get('agents_total', 0)
        issues = health_result.get('issues', [])
        
        lines = []
        lines.append("💓 Agent 健康检查")
        lines.append("")
        
        if healthy:
            lines.append("所有 Agent 都活着，状态不错！💪")
            lines.append("")
            lines.append(f"  ✅ 健康：{agents_ok}/{agents_total} 个")
            lines.append(f"  📊 健康率：{agents_ok/agents_total*100:.0f}%")
            lines.append("")
            lines.append("系统很健康，继续保持 👍")
        else:
            lines.append(f"⚠️ 有 {len(issues)} 个 Agent 不太对劲")
            lines.append("")
            lines.append(f"  ✅ 健康：{agents_ok}/{agents_total} 个")
            lines.append("")
            lines.append("问题列表：")
            for issue in issues[:5]:
                lines.append(f"  • {issue}")
            lines.append("")
            lines.append("建议：看看日志，找找原因 🔍")
        
        lines.append("")
        lines.append(f"下次检查：{self._next_check_time()}")
        
        return "\n".join(lines)
    
    def _next_check_time(self) -> str:
        """计算下次检查时间"""
        from datetime import timedelta
        next_time = datetime.now() + timedelta(minutes=20)
        return next_time.strftime('%H:%M')
    
    def generate_daily_summary(self, daily_result: Dict) -> str:
        """生成每日总结 (人话版)"""
        
        lines = []
        lines.append(f"📝 每日总结 ({datetime.now().strftime('%m-%d')})")
        lines.append("")
        
        # 交易情况
        trades = daily_result.get('trades', 0)
        profit = daily_result.get('profit', 0)
        profit_rate = daily_result.get('profit_rate', 0)
        
        if profit > 0:
            lines.append(f"🎉 今天赚了 ¥{profit:,.2f} (+{profit_rate:.2f}%)")
        elif profit < 0:
            lines.append(f"😅 今天亏了 ¥{abs(profit):,.2f} ({profit_rate:.2f}%)")
        else:
            lines.append("😐 今天没赚没亏，平手")
        
        lines.append("")
        lines.append(f"  • 交易次数：{trades} 次")
        lines.append(f"  • 持仓数量：{daily_result.get('positions', 0)} 只")
        lines.append(f"  • 账户总额：¥{daily_result.get('total_value', 0):,.2f}")
        lines.append("")
        
        # 系统运行情况
        lines.append("系统运行：")
        lines.append(f"  ✅ 任务执行：{daily_result.get('tasks_ok', 0)}/{daily_result.get('tasks_total', 0)} 成功")
        lines.append(f"  ⚠️ 问题数量：{daily_result.get('issues', 0)} 个")
        lines.append("")
        
        lines.append("今天辛苦了，明天继续！💪")
        
        return "\n".join(lines)


# 便捷函数
def human_qa_report(result: Dict) -> str:
    """快速生成 QA 人话报告"""
    return HumanReporter().generate_qa_report(result)


def human_manager_report(result: Dict) -> str:
    """快速生成 Manager 人话报告"""
    return HumanReporter().generate_manager_report(result)


def human_health_report(result: Dict) -> str:
    """快速生成健康检查人话报告"""
    return HumanReporter().generate_health_report(result)


def human_daily_summary(result: Dict) -> str:
    """快速生成每日总结人话报告"""
    return HumanReporter().generate_daily_summary(result)


if __name__ == '__main__':
    # 测试示例
    print("=== QA 报告示例 ===\n")
    print(human_qa_report({
        'changes': [],
        'coverage': 95.2,
        'passed': True,
        'issues': []
    }))
    
    print("\n\n=== Manager 报告示例 ===\n")
    print(human_manager_report({
        'pending': 0,
        'processing': 0,
        'resolved': 499
    }))
    
    print("\n\n=== 健康检查示例 ===\n")
    print(human_health_report({
        'healthy': True,
        'agents_ok': 34,
        'agents_total': 34,
        'issues': []
    }))
