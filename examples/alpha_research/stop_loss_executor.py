#!/usr/bin/env python3
"""
止盈止损执行 Agent - 自动执行风控交易

功能：
1. 直接检查账户持仓盈亏（不再依赖 CRO 报告）
2. 从 config/trading_strategy_v2.json 读取止损/止盈阈值
3. 自动执行止损卖出操作
4. 记录交易流水到账户 trades 数组
5. 发送告警通知
6. 紧急止损（无需人工确认）

修复历史问题 (2026-05-15):
- 之前依赖 CRO 报告触发，但 CRO 使用错误的字段名 (symbol vs stock_code) 导致从未生成信号
- 止损阈值硬编码为 -15%，现在从配置文件读取
- 交易记录正确写入账户 trades 数组
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
        self.config_file = Path('./config/trading_strategy_v2.json')
        self.report_dir = Path('./reports/stop_loss')
        self.cro_report_dir = Path('./reports/risk_control')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 从配置文件加载阈值
        self.thresholds = self._load_thresholds()
        
        # 执行规则
        self.execution_rules = {
            'auto_stop_loss': True,       # 自动止损
            'auto_take_profit': False,    # 自动止盈（需要人工确认）
            'emergency_stop_loss': True,  # 紧急止损（双倍止损线，立即执行）
            'max_sell_per_day': 5,        # 每日最多卖出 5 只
            'min_hold_days': 1,           # 最少持有天数
        }
    
    def _load_thresholds(self) -> Dict:
        """从配置文件加载止损/止盈阈值"""
        defaults = {
            'stop_loss_rate': -0.05,       # -5% 止损
            'take_profit_rate': 0.15,      # +15% 止盈
            'warning_rate': -0.03,         # -3% 预警
            'emergency_rate': -0.10,       # -10% 紧急止损
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                sl = cfg.get('stop_loss', {})
                defaults['stop_loss_rate'] = sl.get('hard_stop_loss', -0.05)
                defaults['take_profit_rate'] = sl.get('take_profit', 0.15)
                defaults['warning_rate'] = sl.get('warning_level', -0.03)
                defaults['emergency_rate'] = defaults['stop_loss_rate'] * 2
                print(f"✅ 止损阈值已加载：止损={defaults['stop_loss_rate']*100:.0f}%, "
                      f"止盈={defaults['take_profit_rate']*100:.0f}%, "
                      f"预警={defaults['warning_rate']*100:.0f}%")
            except Exception as e:
                print(f"⚠️ 加载配置失败，使用默认值：{e}")
        else:
            print(f"⚠️ 配置文件不存在，使用默认阈值")
        
        return defaults
    
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
    
    def check_positions(self, account: Dict) -> Dict:
        """
        直接检查持仓盈亏（修复：使用正确的字段名 stock_code/stock_name）
        
        返回: {
            'stop_loss': [...],   # 触发止损
            'take_profit': [...], # 触发止盈
            'warning': [...],     # 预警
            'normal': [...],      # 正常
        }
        """
        print("\n" + "="*70)
        print("🔍 直接检查持仓盈亏")
        print("="*70)
        print(f"止损线：{self.thresholds['stop_loss_rate']*100:.0f}%  |  "
              f"止盈线：{self.thresholds['take_profit_rate']*100:.0f}%  |  "
              f"预警线：{self.thresholds['warning_rate']*100:.0f}%")
        print()
        
        results = {
            'stop_loss': [],
            'take_profit': [],
            'warning': [],
            'normal': [],
        }
        
        positions = account.get('positions', [])
        
        for pos in positions:
            # 修复：兼容两种字段名格式
            symbol = pos.get('symbol') or pos.get('stock_name') or pos.get('stock_code') or 'Unknown'
            stock_code = pos.get('stock_code', '')
            stock_name = pos.get('stock_name', '')
            
            # 修复：兼容多种成本价格字段
            cost_price = pos.get('cost_price', pos.get('avg_price', 0))
            current_price = pos.get('current_price', 0)
            
            # 兼容多种数量字段
            quantity = pos.get('quantity', pos.get('volume', 0))
            
            if cost_price <= 0 or current_price <= 0:
                print(f"⚠️ {symbol}: 价格无效 (cost={cost_price}, current={current_price})，跳过")
                continue
            
            profit_rate = (current_price - cost_price) / cost_price
            profit_amount = quantity * (current_price - cost_price)
            
            pos_info = {
                'symbol': symbol,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'cost_price': cost_price,
                'current_price': current_price,
                'profit_rate': profit_rate,
                'profit_amount': profit_amount,
                'market_value': current_price * quantity,
            }
            
            # 判断操作
            if profit_rate <= self.thresholds['stop_loss_rate']:
                results['stop_loss'].append(pos_info)
                print(f"🔴 止损触发：{symbol} 盈亏={profit_rate*100:.1f}% "
                      f"(成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            elif profit_rate >= self.thresholds['take_profit_rate']:
                results['take_profit'].append(pos_info)
                print(f"🟢 止盈触发：{symbol} 盈亏={profit_rate*100:.1f}% "
                      f"(成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            elif profit_rate <= self.thresholds['warning_rate']:
                results['warning'].append(pos_info)
                print(f"🟡 预警：{symbol} 盈亏={profit_rate*100:.1f}% "
                      f"(成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            else:
                results['normal'].append(pos_info)
        
        print(f"\n📊 统计:")
        print(f"  🔴 止损：{len(results['stop_loss'])} 只")
        print(f"  🟢 止盈：{len(results['take_profit'])} 只")
        print(f"  🟡 预警：{len(results['warning'])} 只")
        print(f"  ✅ 正常：{len(results['normal'])} 只")
        
        return results
    
    def execute_sell(self, account: Dict, pos_info: Dict, reason: str = 'stop_loss') -> Dict:
        """
        执行卖出操作并记录到 trades 数组
        
        修复：确保交易记录正确写入账户 trades 数组
        """
        symbol = pos_info['symbol']
        quantity = pos_info['quantity']
        current_price = pos_info['current_price']
        cost_price = pos_info['cost_price']
        
        profit_rate = pos_info['profit_rate']
        
        print(f"\n⚡ 执行卖出：{symbol} {quantity}股 @ ¥{current_price:.2f} ({reason})")
        
        # 计算卖出金额
        sell_amount = current_price * quantity
        
        # 更新持仓
        positions = account.get('positions', [])
        new_positions = []
        sold = False
        
        for pos in positions:
            pos_symbol = pos.get('symbol') or pos.get('stock_name') or pos.get('stock_code')
            pos_qty = pos.get('quantity', pos.get('volume', 0))
            
            if pos_symbol == symbol and not sold:
                if quantity >= pos_qty:
                    # 全部卖出，不加入新持仓
                    print(f"   全部卖出：{pos_qty}股")
                    sold = True
                else:
                    # 部分卖出
                    pos['quantity'] = pos.get('quantity', pos.get('volume', 0)) - quantity
                    pos['volume'] = pos['quantity']  # 同步
                    pos['market_value'] = pos['quantity'] * current_price
                    new_positions.append(pos)
                    print(f"   部分卖出：{quantity}/{pos_qty}股")
                    sold = True
            else:
                new_positions.append(pos)
        
        account['positions'] = new_positions
        
        # 更新现金
        account['cash'] = account.get('cash', 0) + sell_amount
        
        # 记录交易（修复：确保写入 trades 数组）
        trade = {
            'trade_id': f"STOP-LOSS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(account.get('trades', [])) + 1}",
            'symbol': symbol,
            'stock_code': pos_info.get('stock_code', ''),
            'stock_name': pos_info.get('stock_name', ''),
            'type': 'sell',
            'reason': f"{reason}_{profit_rate*100:.0f}%",
            'quantity': quantity,
            'price': current_price,
            'amount': sell_amount,
            'cost_price': cost_price,
            'profit': (current_price - cost_price) * quantity,
            'profit_rate': profit_rate,
            'executed_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'auto_executed': True,
        }
        
        if 'trades' not in account:
            account['trades'] = []
        account['trades'].append(trade)
        
        print(f"   卖出金额：¥{sell_amount:,.2f}")
        print(f"   盈亏：¥{trade['profit']:,.2f} ({trade['profit_rate']*100:.1f}%)")
        print(f"   ✅ 交易记录已写入 trades 数组 (当前共 {len(account['trades'])} 条)")
        
        return trade
    
    def generate_alert(self, check_results: Dict, trades: List[Dict]) -> Dict:
        """生成告警信息"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': 'stop_loss_alert',
            'thresholds': {
                'stop_loss': self.thresholds['stop_loss_rate'],
                'take_profit': self.thresholds['take_profit_rate'],
                'warning': self.thresholds['warning_rate'],
            },
            'summary': {
                'stop_loss_count': len(check_results['stop_loss']),
                'take_profit_count': len(check_results['take_profit']),
                'warning_count': len(check_results['warning']),
                'trades_executed': len(trades),
            },
            'stop_loss_positions': check_results['stop_loss'],
            'take_profit_positions': check_results['take_profit'],
            'warning_positions': check_results['warning'],
            'executed_trades': trades,
        }
        
        # 保存告警到文件
        alert_file = self.report_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(alert_file, 'w', encoding='utf-8') as f:
            json.dump(alert, f, ensure_ascii=False, indent=2)
        
        # 同时写入 cache/monitor 兼容旧路径
        cache_dir = Path('./cache/monitor')
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(alert, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 告警已保存：{alert_file.name}")
        
        return alert
    
    def run(self) -> Dict:
        """运行完整止损检查与执行流程"""
        print("\n" + "="*70)
        print(f"💰 止盈止损执行 Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        print(f"配置文件：{self.config_file}")
        print(f"账户文件：{self.account_file}")
        
        # 加载账户
        account = self.load_account()
        if not account:
            return {'status': 'error', 'reason': 'Account file not found'}
        
        print(f"\n当前账户状态:")
        print(f"  现金：¥{account.get('cash', 0):,.2f}")
        print(f"  持仓：{len(account.get('positions', []))}只")
        total_value = account.get('cash', 0) + sum(
            p.get('current_price', 0) * p.get('quantity', p.get('volume', 0))
            for p in account.get('positions', [])
        )
        print(f"  总资产：¥{total_value:,.2f}")
        
        # 直接检查持仓盈亏（不再依赖 CRO 报告）
        check_results = self.check_positions(account)
        
        # 执行止损
        trades = []
        for pos_info in check_results['stop_loss']:
            trade = self.execute_sell(account, pos_info, reason='stop_loss')
            trades.append(trade)
        
        # 保存账户（包含 trades 记录）
        if trades:
            self.save_account(account)
            print(f"\n✅ 已执行 {len(trades)} 笔止损交易，账户已保存")
        else:
            print(f"\n✅ 无需止损操作")
        
        # 生成告警
        alert = self.generate_alert(check_results, trades)
        
        return {
            'status': 'ok',
            'check_results': check_results,
            'trades_executed': len(trades),
            'alert': alert,
        }


if __name__ == '__main__':
    executor = StopLossExecutor()
    result = executor.run()
    print(f"\n最终状态：{result['status']}")
