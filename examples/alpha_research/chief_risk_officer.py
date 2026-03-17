#!/usr/bin/env python3
"""
首席风险官 (CRO) Agent - 风险控制与自动止损

功能：
1. 实时监控仓位风险
2. 自动执行止损止盈
3. 仓位上限控制
4. 黑天鹅事件应对
5. 风险报告生成
"""

import json
from notification_utils import notify_task_start, notify_task_complete, notify_task_error
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from agent_report import create_report
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive

class ChiefRiskOfficer:
    """首席风险官 Agent"""
    
    def __init__(self):
        self.account_file = Path('./accounts/virtual_2026_account.json')
        self.report_dir = Path('./reports/risk_control')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 风控规则
        self.risk_rules = {
            'single_position_limit': 0.20,  # 单只股票上限 20%
            'total_position_limit': 0.95,   # 总仓位上限 95%
            'cash_reserve_min': 0.05,       # 最低现金储备 5%
            'stop_loss_rate': -0.15,        # 止损线 -15%
            'take_profit_rate': 0.30,       # 止盈线 +30%
            'daily_loss_limit': -0.05,      # 单日亏损上限 -5%
            'warning_level': 0.80,          # 预警线 80%
        }
    
    def load_account(self) -> Dict:
        """加载账户数据"""
        if not self.account_file.exists():
            print("❌ 账户文件不存在")
            return None
        
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def check_position_risk(self, account: Dict) -> List[Dict]:
        """检查仓位风险"""
        print("\n" + "="*70)
        print("📊 仓位风险检查")
        print("="*70)
        
        risks = []
        cash = account.get('cash', 0)
        positions = account.get('positions', [])
        total_value = cash + sum(p.get('market_value', 0) for p in positions)
        
        # 检查单只股票仓位
        for pos in positions:
            symbol = pos.get('symbol', 'Unknown')
            market_value = pos.get('market_value', 0)
            position_ratio = market_value / total_value if total_value > 0 else 0
            
            if position_ratio > self.risk_rules['single_position_limit']:
                risks.append({
                    'type': 'single_position_overweight',
                    'level': 'high',
                    'symbol': symbol,
                    'current_ratio': f"{position_ratio*100:.1f}%",
                    'limit': f"{self.risk_rules['single_position_limit']*100:.0f}%",
                    'action': f"建议减仓至{self.risk_rules['single_position_limit']*100:.0f}%以下"
                })
                print(f"🔴 {symbol} 仓位过重：{position_ratio*100:.1f}% (上限{self.risk_rules['single_position_limit']*100:.0f}%)")
        
        # 检查总仓位
        total_position_value = sum(p.get('market_value', 0) for p in positions)
        position_ratio = total_position_value / total_value if total_value > 0 else 0
        
        if position_ratio > self.risk_rules['total_position_limit']:
            risks.append({
                'type': 'total_position_overweight',
                'level': 'high',
                'current_ratio': f"{position_ratio*100:.1f}%",
                'limit': f"{self.risk_rules['total_position_limit']*100:.0f}%",
                'action': '建议降低总仓位'
            })
            print(f"🔴 总仓位过重：{position_ratio*100:.1f}% (上限{self.risk_rules['total_position_limit']*100:.0f}%)")
        
        # 检查现金储备
        cash_ratio = cash / total_value if total_value > 0 else 0
        if cash_ratio < self.risk_rules['cash_reserve_min']:
            risks.append({
                'type': 'cash_reserve_low',
                'level': 'medium',
                'current_ratio': f"{cash_ratio*100:.1f}%",
                'min_required': f"{self.risk_rules['cash_reserve_min']*100:.0f}%",
                'action': '建议保留更多现金'
            })
            print(f"🟠 现金储备不足：{cash_ratio*100:.1f}% (最低{self.risk_rules['cash_reserve_min']*100:.0f}%)")
        
        if not risks:
            print("✅ 仓位风险检查通过")
        
        return risks
    
    def check_stop_loss(self, account: Dict) -> List[Dict]:
        """检查止损止盈"""
        print("\n" + "="*70)
        print("🛑 止损止盈检查")
        print("="*70)
        
        actions = []
        positions = account.get('positions', [])
        
        for pos in positions:
            symbol = pos.get('symbol', 'Unknown')
            cost_price = pos.get('cost_price', 0)
            current_price = pos.get('current_price', 0)
            quantity = pos.get('quantity', 0)
            
            if cost_price <= 0 or current_price <= 0:
                continue
            
            profit_rate = (current_price - cost_price) / cost_price
            
            # 检查止损
            if profit_rate < self.risk_rules['stop_loss_rate']:
                actions.append({
                    'type': 'stop_loss',
                    'level': 'critical',
                    'symbol': symbol,
                    'profit_rate': f"{profit_rate*100:.1f}%",
                    'stop_loss_line': f"{self.risk_rules['stop_loss_rate']*100:.0f}%",
                    'action': '立即止损卖出',
                    'quantity': quantity
                })
                print(f"🔴 {symbol} 触发止损：{profit_rate*100:.1f}% (止损线{self.risk_rules['stop_loss_rate']*100:.0f}%)")
            
            # 检查止盈
            elif profit_rate > self.risk_rules['take_profit_rate']:
                actions.append({
                    'type': 'take_profit',
                    'level': 'medium',
                    'symbol': symbol,
                    'profit_rate': f"{profit_rate*100:.1f}%",
                    'take_profit_line': f"{self.risk_rules['take_profit_rate']*100:.0f}%",
                    'action': '建议止盈卖出',
                    'quantity': quantity
                })
                print(f"🟢 {symbol} 触发止盈：{profit_rate*100:.1f}% (止盈线{self.risk_rules['take_profit_rate']*100:.0f}%)")
        
        if not actions:
            print("✅ 无触发止损止盈的股票")
        
        return actions
    
    def execute_risk_control(self, actions: List[Dict]) -> Dict:
        """执行风控措施"""
        print("\n" + "="*70)
        print("⚡ 执行风控措施")
        print("="*70)
        
        executed = []
        
        for action in actions:
            if action['level'] == 'critical' and action['type'] == 'stop_loss':
                # 自动止损（虚拟账户标记）
                executed.append({
                    **action,
                    'status': 'executed',
                    'executed_at': datetime.now().isoformat(),
                    'note': '自动止损执行'
                })
                print(f"✅ 已执行：{action['symbol']} 止损卖出 {action['quantity']} 股")
            elif action['level'] == 'medium' and action['type'] == 'take_profit':
                # 止盈建议（需要人工确认）
                executed.append({
                    **action,
                    'status': 'pending_approval',
                    'note': '等待人工确认'
                })
                print(f"⏳ 待确认：{action['symbol']} 止盈卖出 {action['quantity']} 股")
        
        return {
            'executed_at': datetime.now().isoformat(),
            'total_actions': len(actions),
            'executed_count': len([a for a in executed if a['status'] == 'executed']),
            'pending_count': len([a for a in executed if a['status'] == 'pending_approval']),
            'actions': executed
        }
    
    def generate_risk_report(self, risks: List[Dict], actions: List[Dict], execution_result: Dict) -> Dict:
        """生成风险报告"""
        report = {
            'report_id': f"CRO-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'risk_summary': {
                'total_risks': len(risks),
                'high_risk': len([r for r in risks if r.get('level') == 'high']),
                'medium_risk': len([r for r in risks if r.get('level') == 'medium']),
                'low_risk': len([r for r in risks if r.get('level') == 'low'])
            },
            'action_summary': {
                'total_actions': len(actions),
                'stop_loss': len([a for a in actions if a.get('type') == 'stop_loss']),
                'take_profit': len([a for a in actions if a.get('type') == 'take_profit'])
            },
            'execution_result': execution_result,
            'risks': risks,
            'actions': actions,
            'risk_level': 'high' if len(risks) > 3 else 'medium' if len(risks) > 0 else 'low'
        }
        
        # 保存报告
        report_file = self.report_dir / f"risk_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 风险报告已保存：{report_file.name}")
        
        return report
    
    def run(self):
        """运行完整风控流程"""
        print("\n" + "="*70)
        print(f"🛡️  首席风险官 (CRO) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 加载账户
        account = self.load_account()
        if not account:
            return None
        
        # 检查仓位风险
        risks = self.check_position_risk(account)
        
        # 检查止损止盈
        stop_actions = self.check_stop_loss(account)
        
        # 执行风控措施
        execution_result = self.execute_risk_control(stop_actions)
        
        # 生成风险报告
        report = self.generate_risk_report(risks, stop_actions, execution_result)
        
        print("\n" + "="*70)
        print("✅ 风控检查完成")
        print("="*70)
        print(f"风险总数：{len(risks)}")
        print(f"触发止损：{len([a for a in stop_actions if a['type'] == 'stop_loss'])}")
        print(f"触发止盈：{len([a for a in stop_actions if a['type'] == 'take_profit'])}")
        print(f"已执行：{execution_result['executed_count']}")
        print(f"待确认：{execution_result['pending_count']}")
        
        return report


if __name__ == '__main__':

    # 发送通知
    try:
        notify_task_start("首席风险官", {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "类型": "风险评估"
        })
        
        result = main()
        
        # 检查是否有风险
        if result and isinstance(result, dict) and result.get('risks'):
            notify_task_error("首席风险官", f"发现{len(result['risks'])}个风险", {
                "风险数量": str(len(result['risks']))
            })
        else:
            notify_task_complete("首席风险官", {
                "状态": "无风险"
            })
    except Exception as e:
        notify_task_error("首席风险官", str(e))
        raise

    cro = ChiefRiskOfficer()
    cro.run()
