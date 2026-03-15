#!/usr/bin/env python3
"""
每小时增强报告 Agent

功能:
1. 收集系统状态
2. 运行预测分析
3. 使用 nemotron 增强报告
4. 发送到 Slack

频率：每小时一次
模型：nemotron-3-nano (本地)
成本：¥0
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'world_model'))

from world_model.nemotron_enhancer import NemotronEnhancer
from world_model.predictive_analytics import PredictiveAnalytics


class HourlyEnhancedReport:
    """每小时增强报告 Agent"""
    
    def __init__(self):
        self.enhancer = NemotronEnhancer()
        self.analytics = PredictiveAnalytics()
        self.report_dir = Path(__file__).parent / 'reports' / 'hourly_enhanced'
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_system_state(self) -> dict:
        """收集系统状态"""
        
        # 模拟数据 (实际应该从 Neo4j、cron、issue queue 收集)
        state = {
            'timestamp': datetime.now().isoformat(),
            'agent_count': 15,
            'agent_health_rate': 0.95,
            'task_success_rate': 0.98,
            'issue_pending': 0,
            'neo4j_nodes': 92,
            'cron_tasks': 34,
            'session_messages': 25
        }
        
        # 保存到历史
        self.analytics.history['agent_stats'].append({
            'timestamp': state['timestamp'],
            'value': state['agent_health_rate']
        })
        self.analytics._save_history()
        
        return state
    
    def generate_report(self) -> str:
        """生成增强报告"""
        
        # 1. 收集系统状态
        system_state = self.collect_system_state()
        
        # 2. 运行预测分析
        data_points = self.analytics.history['agent_stats'][-20:]
        prediction = self.analytics.analyze_timeseries(data_points, 'agent_health_rate')
        
        # 3. 使用 nemotron 增强
        enhanced_report = self.enhancer.generate_hourly_report({
            **system_state,
            'prediction': prediction
        })
        
        # 4. 保存报告
        report_file = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 每小时增强报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(enhanced_report)
        
        return enhanced_report
    
    def send_to_slack(self, report: str):
        """发送到 Slack (通过 OpenClaw)"""
        print("\n" + "=" * 70)
        print("📱 发送到 Slack")
        print("=" * 70)
        print(report)
        print("=" * 70)
        print("\n✅ 报告已发送 (OpenClaw 会自动推送到 Slack)")
    
    def run(self):
        """运行小时报告"""
        print("\n" + "=" * 70)
        print("🤖 每小时增强报告 Agent")
        print("=" * 70)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"模型：{self.enhancer.model}")
        print()
        
        # 生成报告
        report = self.generate_report()
        
        # 发送到 Slack
        self.send_to_slack(report)
        
        print(f"\n✅ 小时报告生成完成！")
        
        return report


def main():
    agent = HourlyEnhancedReport()
    agent.run()


if __name__ == '__main__':
    main()
