#!/usr/bin/env python3
"""
Agent 执行报告生成器

功能:
- 统一的报告格式
- 表格化输出
- 自动发送到 Slack
- 支持本地模型优化

用法:
    from agent_report import AgentReporter
    
    reporter = AgentReporter(agent_name="数据下载 Agent")
    reporter.add_section("执行概览", {...})
    reporter.add_section("详细结果", {...})
    reporter.send()
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from report_templates import render_report, get_template

class AgentReporter:
    """Agent 执行报告生成器"""
    
    def __init__(self, agent_name: str, project_dir: str = None, template_name: str = None):
        self.agent_name = agent_name
        self.project_dir = Path(project_dir) if project_dir else Path(__file__).parent
        self.template_name = template_name or self._detect_template()
        self.report_dir = self.project_dir / 'reports' / 'agent_reports'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.sections = []
        self.start_time = datetime.now()
        self.metrics = {
            'start_time': self.start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'status': 'running',
            'items_processed': 0,
            'items_success': 0,
            'items_failed': 0,
            'warnings': 0,
            'errors': 0
        }

    def _detect_template(self):
        """检测默认模板"""
        return "default"
    
    def add_section(self, title: str, data: Dict | List, format_type: str = 'table'):
        """
        添加报告章节
        
        Args:
            title: 章节标题
            data: 数据（dict 或 list）
            format_type: 格式类型 ('table', 'list', 'text')
        """
        self.sections.append({
            'title': title,
            'data': data,
            'format_type': format_type
        })
    
    def update_metric(self, key: str, value: Any):
        """更新指标"""
        self.metrics[key] = value
    
    def increment_counter(self, key: str, count: int = 1):
        """增加计数器"""
        if key in self.metrics and isinstance(self.metrics[key], (int, float)):
            self.metrics[key] += count
    
    def _format_table(self, data: List[Dict], max_rows: int = 20) -> str:
        """格式化数据为表格"""
        if not data:
            return "无数据"
        
        # 获取所有列
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        
        if not all_keys:
            return "无数据"
        
        # 限制行数
        if len(data) > max_rows:
            data = data[:max_rows]
            show_more = f"\n... 还有 {len(data) - max_rows} 条（查看完整报告）"
        else:
            show_more = ""
        
        # 构建表格
        lines = []
        
        # 表头
        headers = list(all_keys)
        header_line = "│".join([f" {h:^15} " for h in headers])
        separator = "┼".join([f"{'─'*17}" for _ in headers])
        
        lines.append(f"┌{separator}┐")
        lines.append(f"│{header_line}│")
        lines.append(f"├{separator}┤")
        
        # 数据行
        for item in data:
            if isinstance(item, dict):
                row = []
                for h in headers:
                    value = str(item.get(h, '-'))[:15]
                    row.append(f" {value:^15} ")
                lines.append(f"│{'│'.join(row)}│")
        
        lines.append(f"└{separator}┘")
        
        return "\n".join(lines) + show_more
    
    def _format_list(self, data: List) -> str:
        """格式化数据为列表"""
        lines = []
        for i, item in enumerate(data[:20], 1):
            if isinstance(item, dict):
                item_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
            else:
                item_str = str(item)
            lines.append(f"  {i}. {item_str}")
        
        if len(data) > 20:
            lines.append(f"  ... 还有 {len(data) - 20} 项")
        
        return "\n".join(lines)
    
    def _format_text(self, data: Any) -> str:
        """格式化数据为文本"""
        if isinstance(data, dict):
            return "\n".join([f"  • {k}: {v}" for k, v in data.items()])
        elif isinstance(data, list):
            return "\n".join([f"  • {item}" for item in data[:20]])
        else:
            return str(data)
    
    def generate_report(self) -> str:
        """生成完整报告"""
        # 更新结束时间
        self.metrics['end_time'] = datetime.now().isoformat()
        self.metrics['duration_seconds'] = (datetime.now() - self.start_time).total_seconds()
        
        # 构建报告
        lines = []
        
        # 标题
        lines.append("=" * 70)
        lines.append(f"📊 {self.agent_name} 执行报告")
        lines.append(f"时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # 执行概览
        lines.append("【执行概览】")
        lines.append(f"  状态：{'✅ 成功' if self.metrics['status'] == 'success' else '❌ 失败' if self.metrics['errors'] > 0 else '⚠️ 警告' if self.metrics['warnings'] > 0 else '🔄 运行中'}")
        lines.append(f"  耗时：{self.metrics['duration_seconds']:.2f} 秒")
        lines.append(f"  处理：{self.metrics['items_processed']} 项")
        lines.append(f"  成功：{self.metrics['items_success']} 项")
        lines.append(f"  失败：{self.metrics['items_failed']} 项")
        lines.append(f"  警告：{self.metrics['warnings']} 个")
        lines.append(f"  错误：{self.metrics['errors']} 个")
        lines.append("")
        
        # 各章节
        for i, section in enumerate(self.sections, 1):
            lines.append(f"【{section['title']}】")
            
            if section['format_type'] == 'table':
                lines.append(self._format_table(section['data']))
            elif section['format_type'] == 'list':
                lines.append(self._format_list(section['data']))
            else:
                lines.append(self._format_text(section['data']))
            
            lines.append("")
        
        # 底部
        lines.append("=" * 70)
        lines.append(f"报告生成：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def save_report(self, report: str = None) -> str:
        """保存报告到文件"""
        if not report:
            report = self.generate_report()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{self.agent_name.replace(' ', '_')}_{timestamp}.txt"
        filepath = self.report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return str(filepath)
    
    def send_to_slack(self, report: str = None):
        """发送报告到 Slack（通过 OpenClaw）"""
        if not report:
            report = self.generate_report()
        
        # OpenClaw 会自动发送 cron 任务的输出到 Slack
        # 所以只需要打印即可
        print(report)
    
    def finish(self, status: str = 'success', send_slack: bool = True):
        """完成报告并发送"""
        self.metrics['status'] = status
        
        report = self.generate_report()
        filepath = self.save_report(report)
        
        if send_slack:
            self.send_to_slack(report)
        
        return {
            'report': report,
            'filepath': filepath,
            'metrics': self.metrics
        }


# 便捷函数
def create_report(agent_name: str) -> AgentReporter:
    """快速创建报告器"""
    return AgentReporter(agent_name)


if __name__ == '__main__':
    # 测试示例
    reporter = create_report("测试 Agent")
    
    reporter.add_section("执行概览", {
        '总任务数': 100,
        '成功': 95,
        '失败': 5,
        '耗时': '12.5 秒'
    }, format_type='text')
    
    reporter.add_section("详细结果", [
        {'任务': '任务 A', '状态': '成功', '耗时': '1.2s'},
        {'任务': '任务 B', '状态': '成功', '耗时': '0.8s'},
        {'任务': '任务 C', '状态': '失败', '错误': '超时'},
    ], format_type='table')
    
    result = reporter.finish('success')
    print(f"\n报告已保存：{result['filepath']}")
