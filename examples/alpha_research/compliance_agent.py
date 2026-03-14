#!/usr/bin/env python3
"""
合规检查 Agent

负责执行交易前的合规检查，确保所有交易符合监管要求和内部风控标准。
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class ComplianceAgent:
    """合规检查 Agent"""
    
    def __init__(self):
        self.workspace = Path("/Users/rowang/projects/vnpy/examples/alpha_research")
        self.account_file = self.workspace / "accounts" / "virtual_2026_account.json"
        self.reports_dir = self.workspace / "reports" / "compliance"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def load_account(self) -> Dict:
        """加载账户信息"""
        if not self.account_file.exists():
            print(f"❌ 账户文件不存在: {self.account_file}")
            return {}
            
        try:
            with open(self.account_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载账户文件失败: {e}")
            return {}
            
    def check_position_limits(self, account: Dict) -> Dict:
        """检查持仓限制"""
        violations = []
        
        # 检查单只股票持仓比例
        total_value = account.get('cash', 0) + sum(p.get('market_value', 0) for p in account.get('positions', []))
        if total_value > 0:
            for position in account.get('positions', []):
                symbol = position.get('symbol', '')
                market_value = position.get('market_value', 0)
                weight = market_value / total_value
                
                if weight > 0.1:  # 单只股票不超过10%
                    violations.append({
                        'type': 'position_limit',
                        'symbol': symbol,
                        'weight': weight,
                        'limit': 0.1,
                        'message': f'单只股票 {symbol} 持仓比例 {weight:.2%} 超过限制 10%'
                    })
                    
        return {'violations': violations}
        
    def check_trading_limits(self, account: Dict) -> Dict:
        """检查交易限制"""
        violations = []
        
        # 检查每日交易金额限制（假设为总资产的20%）
        total_value = account.get('cash', 0) + sum(p.get('market_value', 0) for p in account.get('positions', []))
        daily_limit = total_value * 0.2
        
        # 获取今日交易计划
        today = datetime.now().strftime('%Y-%m-%d')
        trading_plan_file = self.workspace / "reports" / f"trading_plan_{today}.json"
        
        if trading_plan_file.exists():
            try:
                with open(trading_plan_file, 'r', encoding='utf-8') as f:
                    trading_plan = json.load(f)
                    
                planned_amount = 0
                for trade in trading_plan.get('trades', []):
                    planned_amount += abs(trade.get('amount', 0)) * trade.get('price', 0)
                    
                if planned_amount > daily_limit:
                    violations.append({
                        'type': 'trading_limit',
                        'planned_amount': planned_amount,
                        'daily_limit': daily_limit,
                        'message': f'计划交易金额 {planned_amount:,.2f} 超过日限额 {daily_limit:,.2f}'
                    })
                    
            except Exception as e:
                print(f"⚠️ 读取交易计划失败: {e}")
                
        return {'violations': violations}
        
    def generate_compliance_report(self, checks: List[Dict]) -> Dict:
        """生成合规报告"""
        all_violations = []
        for check in checks:
            all_violations.extend(check.get('violations', []))
            
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'PASS' if not all_violations else 'FAIL',
            'violations': all_violations,
            'summary': {
                'total_checks': len(checks),
                'total_violations': len(all_violations)
            }
        }
        
        # 保存报告
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = self.reports_dir / f"compliance_report_{today}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        return report
        
    def run_compliance_check(self) -> bool:
        """执行合规检查"""
        print("🔍 开始执行合规检查...")
        
        # 加载账户信息
        account = self.load_account()
        if not account:
            print("❌ 无法加载账户信息，合规检查失败")
            return False
            
        # 执行各项检查
        checks = []
        checks.append(self.check_position_limits(account))
        checks.append(self.check_trading_limits(account))
        
        # 生成报告
        report = self.generate_compliance_report(checks)
        
        if report['status'] == 'PASS':
            print("✅ 合规检查通过")
            return True
        else:
            print(f"❌ 合规检查失败，发现 {len(report['violations'])} 个违规项")
            for violation in report['violations']:
                print(f"  - {violation['message']}")
            return False


def main():
    """主函数"""
    agent = ComplianceAgent()
    success = agent.run_compliance_check()
    
    # 退出码：0表示成功，1表示失败
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
