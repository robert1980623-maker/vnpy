#!/usr/bin/env python3
"""
止盈止损执行 Agent - 自动执行风控交易

功能：
1. 接收 CRO 的止损/止盈信号
2. 执行虚拟账户卖出操作
3. 记录交易流水
4. 发送执行报告
5. 紧急止损（无需人工确认）
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class StopLossExecutor:
    """止盈止损执行 Agent"""
    
    def __init__(self):
        self.account_file = Path('./accounts/virtual_2026_account.json')
        self.report_dir = Path('./reports/stop_loss')
        self.cro_report_dir = Path('./reports/risk_control')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行规则
        self.execution_rules = {
            'auto_stop_loss': True,      # 自动止损（-15%）
            'auto_take_profit': False,   # 自动止盈（需要人工确认）
            'emergency_stop_loss': True, # 紧急止损（-20%，立即执行）
            'max_sell_per_day': 5,       # 每日最多卖出 5 只
            'min_hold_days': 1           # 最少持有天数（避免频繁交易）
        }
    
    def load_account(self) -> Optional[Dict]:
        """加载账户数据"""
        if not self.account_file.exists():
            print("❌ 账户文件不存在")
            return None
        
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_account(self, account: Dict):
        """保存账户数据"""
        account['last_update'] = datetime.now().isoformat()
        
        with open(self.account_file, 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        
        print("✅ 账户数据已保存")
    
    def load_cro_signals(self) -> List[Dict]:
        """加载 CRO 的风险信号"""
        print("\n" + "="*70)
        print("📥 加载 CRO 风险信号")
        print("="*70)
        
        signals = []
        
        # 查找最新的 CRO 报告
        cro_reports = sorted(self.cro_report_dir.glob('risk_report_*.json'), reverse=True)
        
        if not cro_reports:
            print("⚠️ 未找到 CRO 报告")
            return signals
        
        latest_report = cro_reports[0]
        print(f"加载报告：{latest_report.name}")
        
        with open(latest_report, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        # 提取需要执行的信号
        actions = report.get('actions', [])
        
        for action in actions:
            if action.get('type') == 'stop_loss' and action.get('level') == 'critical':
                signals.append({
                    **action,
                    'priority': 'high',
                    'auto_execute': True
                })
                print(f"🔴 止损信号：{action.get('symbol')} ({action.get('profit_rate', 'N/A')})")
            
            elif action.get('type') == 'take_profit':
                # 止盈需要人工确认
                signals.append({
                    **action,
                    'priority': 'medium',
                    'auto_execute': self.execution_rules['auto_take_profit']
                })
                print(f"🟢 止盈信号：{action.get('symbol')} ({action.get('profit_rate', 'N/A')}) [待确认]")
        
        return signals
    
    def execute_sell(self, account: Dict, signal: Dict) -> Dict:
        """执行卖出操作"""
        symbol = signal.get('symbol', 'Unknown')
        quantity = signal.get('quantity', 0)
        action_type = signal.get('type', 'unknown')
        
        print(f"\n⚡ 执行卖出：{symbol} {quantity}股 ({action_type})")
        
        # 查找持仓
        positions = account.get('positions', [])
        position = None
        position_idx = -1
        
        for i, pos in enumerate(positions):
            if pos.get('symbol') == symbol:
                position = pos
                position_idx = i
                break
        
        if not position:
            print(f"❌ 未找到 {symbol} 的持仓")
            return {
                'symbol': symbol,
                'status': 'failed',
                'reason': 'Position not found'
            }
        
        # 获取当前价格
        current_price = position.get('current_price', 0)
        cost_price = position.get('cost_price', 0)
        
        if current_price <= 0:
            print(f"❌ 无效价格：{current_price}")
            return {
                'symbol': symbol,
                'status': 'failed',
                'reason': 'Invalid price'
            }
        
        # 计算卖出金额
        sell_amount = current_price * quantity
        
        # 更新持仓
        current_quantity = position.get('quantity', 0)
        
        if quantity >= current_quantity:
            # 全部卖出
            print(f"   全部卖出：{current_quantity}股")
            positions.pop(position_idx)
        else:
            # 部分卖出
            print(f"   部分卖出：{quantity}/{current_quantity}股")
            position['quantity'] = current_quantity - quantity
            position['market_value'] = position['quantity'] * current_price
        
        # 更新现金
        account['cash'] = account.get('cash', 0) + sell_amount
        
        # 记录交易
        trade = {
            'trade_id': f"SELL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'symbol': symbol,
            'type': 'sell',
            'reason': action_type,
            'quantity': quantity,
            'price': current_price,
            'amount': sell_amount,
            'cost_price': cost_price,
            'profit': (current_price - cost_price) * quantity,
            'profit_rate': (current_price - cost_price) / cost_price if cost_price > 0 else 0,
            'executed_at': datetime.now().isoformat(),
            'auto_executed': signal.get('auto_execute', False)
        }
        
        if 'trades' not in account:
            account['trades'] = []
        account['trades'].append(trade)
        
        print(f"   卖出价格：¥{current_price:.2f}")
        print(f"   卖出金额：¥{sell_amount:.2f}")
        print(f"   盈亏：¥{trade['profit']:.2f} ({trade['profit_rate']*100:.1f}%)")
        
        return {
            **trade,
            'status': 'executed'
        }
    
    def execute_all_signals(self, account: Dict, signals: List[Dict]) -> List[Dict]:
        """执行所有信号"""
        print("\n" + "="*70)
        print("⚡ 批量执行交易信号")
        print("="*70)
        
        results = []
        executed_count = 0
        
        for signal in signals:
            # 检查是否自动执行
            if not signal.get('auto_execute', False):
                print(f"⏳ 跳过（待确认）：{signal.get('symbol')}")
                results.append({
                    **signal,
                    'status': 'pending_approval'
                })
                continue
            
            # 检查每日卖出上限
            if executed_count >= self.execution_rules['max_sell_per_day']:
                print(f"⏳ 跳过（达到每日上限）：{signal.get('symbol')}")
                results.append({
                    **signal,
                    'status': 'daily_limit_reached'
                })
                continue
            
            # 执行卖出
            result = self.execute_sell(account, signal)
            results.append(result)
            
            if result.get('status') == 'executed':
                executed_count += 1
        
        print(f"\n✅ 执行完成：{executed_count}/{len(signals)}")
        
        return results
    
    def generate_report(self, execution_results: List[Dict]) -> Dict:
        """生成执行报告"""
        report = {
            'report_id': f"EXEC-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_signals': len(execution_results),
                'executed': len([r for r in execution_results if r.get('status') == 'executed']),
                'pending': len([r for r in execution_results if r.get('status') == 'pending_approval']),
                'failed': len([r for r in execution_results if r.get('status') == 'failed']),
                'skipped': len([r for r in execution_results if r.get('status') in ['daily_limit_reached', 'skipped']])
            },
            'trades': [r for r in execution_results if r.get('status') == 'executed'],
            'pending_trades': [r for r in execution_results if r.get('status') == 'pending_approval'],
            'failed_trades': [r for r in execution_results if r.get('status') == 'failed']
        }
        
        # 计算总盈亏
        total_profit = sum(t.get('profit', 0) for t in report['trades'])
        report['summary']['total_profit'] = total_profit
        
        # 保存报告
        report_file = self.report_dir / f"execution_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 执行报告已保存：{report_file.name}")
        
        # 打印汇总
        print("\n" + "="*70)
        print("📊 执行汇总")
        print("="*70)
        print(f"总信号数：{report['summary']['total_signals']}")
        print(f"已执行：{report['summary']['executed']}")
        print(f"待确认：{report['summary']['pending']}")
        print(f"失败：{report['summary']['failed']}")
        print(f"总盈亏：¥{total_profit:.2f}")
        
        return report
    
    def run(self):
        """运行完整执行流程"""
        print("\n" + "="*70)
        print(f"💰 止盈止损执行 Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 加载账户
        account = self.load_account()
        if not account:
            return None
        
        print(f"\n当前账户状态:")
        print(f"  现金：¥{account.get('cash', 0):,.2f}")
        print(f"  持仓：{len(account.get('positions', []))}只")
        print(f"  总资产：¥{account.get('cash', 0) + sum(p.get('market_value', 0) for p in account.get('positions', [])):,.2f}")
        
        # 加载 CRO 信号
        signals = self.load_cro_signals()
        
        if not signals:
            print("\n✅ 无需执行的信号")
            return {'status': 'no_signals'}
        
        # 执行交易
        execution_results = self.execute_all_signals(account, signals)
        
        # 保存账户
        self.save_account(account)
        
        # 生成报告
        report = self.generate_report(execution_results)
        
        print("\n" + "="*70)
        print("✅ 执行流程完成")
        print("="*70)
        
        return report


if __name__ == '__main__':
    executor = StopLossExecutor()
    executor.run()
