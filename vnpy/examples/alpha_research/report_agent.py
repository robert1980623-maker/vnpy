#!/usr/bin/env python3
"""
复盘 Agent - 负责生成每日复盘报告

功能:
- 分析当日交易表现
- 生成持仓分析
- 生成风险指标
- 输出复盘报告
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class ReportAgent:
    """复盘 Agent"""
    
    def __init__(self):
        self.workspace = Path("/Users/rowang/.openclaw/workspace")
        self.project_dir = Path("/Users/rowang/projects/vnpy/examples/alpha_research")
        self.reports_dir = self.project_dir / "reports"
        self.accounts_dir = self.project_dir / "accounts"
        self.account_file = self.accounts_dir / "virtual_2026_account.json"
        
    def generate_daily_review(self) -> Dict:
        """生成每日复盘报告"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 读取账户数据
        account_data = self._load_account_data()
        
        # 读取今日选股结果
        selection_file = self.reports_dir / f"stock_selection_{today}.json"
        selection_data = {}
        if selection_file.exists():
            with open(selection_file, 'r', encoding='utf-8') as f:
                selection_data = json.load(f)
        
        # 读取今日交易计划
        trading_plan_file = self.reports_dir / f"trading_plan_{today}.json"
        trading_plan_data = {}
        if trading_plan_file.exists():
            with open(trading_plan_file, 'r', encoding='utf-8') as f:
                trading_plan_data = json.load(f)
        
        # 计算关键指标
        total_value = account_data.get("cash", 0) + sum(
            p.get("market_value", 0) for p in account_data.get("positions", [])
        )
        positions_count = len(account_data.get("positions", []))
        cash = account_data.get("cash", 0)
        
        # 构建报告
        report = {
            "date": today,
            "account_summary": {
                "total_value": total_value,
                "cash": cash,
                "positions_count": positions_count,
                "positions": account_data.get("positions", [])
            },
            "selection_summary": {
                "selected_stocks": len(selection_data.get("selected_stocks", [])),
                "strategies_used": selection_data.get("strategies_used", [])
            },
            "trading_summary": {
                "planned_trades": len(trading_plan_data.get("trades", [])),
                "execution_status": trading_plan_data.get("execution_status", "pending")
            },
            "risk_metrics": {
                "position_concentration": self._calculate_concentration(account_data),
                "cash_ratio": cash / total_value if total_value > 0 else 0
            }
        }
        
        return report
    
    def _load_account_data(self) -> Dict:
        """加载账户数据"""
        if not self.account_file.exists():
            return {"cash": 1000000.0, "positions": [], "trades": []}
        
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _calculate_concentration(self, account_data: Dict) -> float:
        """计算持仓集中度"""
        positions = account_data.get("positions", [])
        if not positions:
            return 0.0
        
        total_value = sum(p.get("market_value", 0) for p in positions)
        if total_value == 0:
            return 0.0
        
        # 计算最大持仓占比
        max_position_value = max(p.get("market_value", 0) for p in positions)
        return max_position_value / total_value
    
    def save_report(self, report: Dict):
        """保存复盘报告"""
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = self.reports_dir / f"daily_review_{today}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 复盘报告已保存: {report_file}")
        
        # 同时生成 Markdown 报告
        self._generate_markdown_report(report)
    
    def _generate_markdown_report(self, report: Dict):
        """生成 Markdown 格式的复盘报告"""
        today = report["date"]
        md_content = f"""# 每日复盘报告 - {today}

## 账户概览
- **总资产**: ¥{report['account_summary']['total_value']:,.2f}
- **现金余额**: ¥{report['account_summary']['cash']:,.2f}
- **持仓数量**: {report['account_summary']['positions_count']} 只

## 选股情况
- **选股数量**: {report['selection_summary']['selected_stocks']} 只
- **使用策略**: {', '.join(report['selection_summary']['strategies_used'])}

## 交易执行
- **计划交易**: {report['trading_summary']['planned_trades']} 笔
- **执行状态**: {report['trading_summary']['execution_status']}

## 风险指标
- **持仓集中度**: {report['risk_metrics']['position_concentration']:.2%}
- **现金比例**: {report['risk_metrics']['cash_ratio']:.2%}

## 持仓详情
"""
        
        for pos in report['account_summary']['positions']:
            md_content += f"- **{pos.get('symbol', 'N/A')}**: {pos.get('quantity', 0)} 股, 市值 ¥{pos.get('market_value', 0):,.2f}\n"
        
        md_file = self.reports_dir / f"daily_review_{today}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ Markdown 复盘报告已保存: {md_file}")
    
    def run(self):
        """运行复盘 Agent"""
        print("🚀 启动复盘 Agent...")
        
        try:
            report = self.generate_daily_review()
            self.save_report(report)
            print("✅ 复盘 Agent 执行完成!")
            
        except Exception as e:
            print(f"❌ 复盘 Agent 执行失败: {e}")
            raise


if __name__ == "__main__":
    agent = ReportAgent()
    agent.run()
