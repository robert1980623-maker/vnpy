#!/usr/bin/env python3
"""
严格止盈止损执行器

规则:
- 止损：-15% 强制卖出
- 止盈：+30% 建议卖出（可分批）
- 预警：-10% 提醒关注
"""

import json
from pathlib import Path
from datetime import datetime
import csv


class StrictStopLoss:
    """严格止盈止损"""
    
    def __init__(self, account_file: str = './accounts/virtual_2026_account.json'):
        self.account_file = Path(account_file)
        self.config_file = Path('./config/trading_strategy_v2.json')
        self.data_dir = Path('./data/akshare/bars')
        self._load_thresholds()
        self.actions = {
            'stop_loss': [],
            'take_profit': [],
            'warning': [],
            'hold': []
        }
    
    def _load_thresholds(self):
        """从配置文件加载止损/止盈阈值，修复：之前硬编码为-15%/+30%"""
        defaults = {
            'stop_loss_threshold': -0.05,   # 止损 -5%（从-15%修复）
            'take_profit_threshold': 0.15,  # 止盈 +15%（从30%修复）
            'warning_threshold': -0.03,     # 预警 -3%（新增）
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                sl = cfg.get('stop_loss', {})
                defaults['stop_loss_threshold'] = sl.get('hard_stop_loss', -0.05)
                defaults['take_profit_threshold'] = sl.get('take_profit', 0.15)
                defaults['warning_threshold'] = sl.get('warning_level', -0.03)
            except:
                pass
        self.stop_loss_threshold = defaults['stop_loss_threshold']
        self.take_profit_threshold = defaults['take_profit_threshold']
        self.warning_threshold = defaults['warning_threshold']
        print(f"✅ 严格止损阈值：止损={self.stop_loss_threshold*100:.0f}%, "
              f"止盈={self.take_profit_threshold*100:.0f}%, 预警={self.warning_threshold*100:.0f}%")
        
    def load_account(self):
        """加载账户"""
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_current_prices(self):
        """获取最新价格"""
        prices = {}
        today = datetime.now().strftime('%Y-%m-%d')
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    # 获取最新价格
                    last_line = lines[-1].strip().split(',')
                    if len(last_line) >= 5:
                        prices[symbol] = float(last_line[4])  # close_price
        
        return prices
    
    def check_positions(self, account, prices):
        """检查持仓盈亏 — 修复：兼容 stock_code/cost_price 字段，显示动态阈值"""
        print("=" * 70)
        print(" " * 20 + "止盈止损检查")
        print("=" * 70)
        print(f"止损线：{self.stop_loss_threshold*100:.0f}%  |  "
              f"止盈线：{self.take_profit_threshold*100:.0f}%  |  "
              f"预警线：{self.warning_threshold*100:.0f}%")
        print()
        
        for pos in account['positions']:
            # 修复：兼容 symbol/stock_name/stock_code
            symbol = pos.get('symbol') or pos.get('stock_name') or pos.get('stock_code') or 'Unknown'
            # 修复：兼容 avg_price/cost_price
            cost_price = pos.get('avg_price') or pos.get('cost_price', 0)
            # 修复：兼容 current_price 字段
            current_price = prices.get(symbol, pos.get('current_price', 0))
            # 修复：兼容 volume/quantity
            volume = pos.get('volume', pos.get('quantity', 0))
            
            # 判断操作
            if profit_rate <= self.stop_loss_threshold:
                # 触发止损
                self.actions['stop_loss'].append(pos_info)
                print(f"🔴 止损：{symbol} 盈亏={profit_rate*100:.1f}% (成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            elif profit_rate >= self.take_profit_threshold:
                # 触发止盈
                self.actions['take_profit'].append(pos_info)
                print(f"🟢 止盈：{symbol} 盈亏={profit_rate*100:.1f}% (成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            elif profit_rate <= self.warning_threshold:
                # 预警
                self.actions['warning'].append(pos_info)
                print(f"🟡 预警：{symbol} 盈亏={profit_rate*100:.1f}% (成本¥{cost_price:.2f} → 现价¥{current_price:.2f})")
            else:
                # 继续持有
                self.actions['hold'].append(pos_info)
        
        print()
        print(f"📊 统计:")
        print(f"  止损：{len(self.actions['stop_loss'])} 只")
        print(f"  止盈：{len(self.actions['take_profit'])} 只")
        print(f"  预警：{len(self.actions['warning'])} 只")
        print(f"  持有：{len(self.actions['hold'])} 只")
        
        return self.actions
    
    def execute_stop_loss(self, account):
        """执行止损卖出"""
        if not self.actions['stop_loss']:
            print("\n✅ 无需止损")
            return account
        
        print("\n" + "=" * 70)
        print(" " * 20 + "执行止损")
        print("=" * 70)
        
        prices = self.get_current_prices()
        
        for pos_info in self.actions['stop_loss']:
            symbol = pos_info['symbol']
            sell_price = prices.get(symbol, pos_info['current_price'])
            volume = pos_info['volume']
            sell_value = volume * sell_price
            
            print(f"  卖出 {symbol}: {volume} 股 × ¥{sell_price:.2f} = ¥{sell_value:,.2f}")
            print(f"    亏损：¥{pos_info['profit_amount']:,.2f} ({pos_info['profit_rate']*100:.1f}%)")
            
            # 更新账户
            account['cash'] += sell_value
            
            # 从持仓中移除（修复：兼容多种标识字段）
            account['positions'] = [
                p for p in account['positions']
                if (p.get('symbol') or p.get('stock_name') or p.get('stock_code')) != symbol
            ]
        
        print(f"\n✅ 止损完成：卖出 {len(self.actions['stop_loss'])} 只股票")
        return account
    
    def suggest_take_profit(self):
        """止盈建议"""
        if not self.actions['take_profit']:
            print("\n✅ 无止盈建议")
            return []
        
        print("\n" + "=" * 70)
        print(" " * 20 + "止盈建议")
        print("=" * 70)
        
        suggestions = []
        for pos in self.actions['take_profit']:
            suggestion = {
                'symbol': pos['symbol'],
                'action': '建议卖出 50% 或全部',
                'reason': f"盈利 {pos['profit_rate']*100:.1f}%，达到止盈线 (+30%)",
                'profit': pos['profit_amount'],
                'market_value': pos['market_value']
            }
            suggestions.append(suggestion)
            print(f"  💰 {pos['symbol']}: 盈利 ¥{pos['profit_amount']:,.2f} ({pos['profit_rate']*100:.1f}%)")
            print(f"     建议：卖出 50% 锁定利润，或继续持有博取更高收益")
        
        return suggestions
    
    def show_warnings(self):
        """显示预警"""
        if not self.actions['warning']:
            print("\n✅ 无预警股票")
            return
        
        print("\n" + "=" * 70)
        print(" " * 20 + "预警关注")
        print("=" * 70)
        
        for pos in self.actions['warning']:
            print(f"  ⚠️ {pos['symbol']}: 亏损 ¥{pos['profit_amount']:,.2f} ({pos['profit_rate']*100:.1f}%)")
            print(f"     距离止损线：{(self.stop_loss_threshold - pos['profit_rate'])*100:.1f}%")
            print(f"     建议：密切关注，如继续下跌准备止损")
    
    def save_report(self, account):
        """保存检查报告"""
        report = {
            'check_time': datetime.now().isoformat(),
            'stop_loss': self.actions['stop_loss'],
            'take_profit': self.actions['take_profit'],
            'warning': self.actions['warning'],
            'hold': self.actions['hold'],
            'account_snapshot': {
                'cash': account['cash'],
                'position_count': len(account['positions']),
                'total_market_value': sum(p.get('market_value', 0) for p in account['positions'])
            }
        }
        
        report_file = Path('./reports/stop_loss_check_' + datetime.now().strftime('%Y%m%d_%H%M') + '.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{report_file}")
        return report_file


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 18 + "严格止盈止损执行器 v1.0")
    print("=" * 70)
    
    executor = StrictStopLoss()
    
    # 加载账户
    account = executor.load_account()
    print(f"📊 账户：{account['account_id']}")
    print(f"   持仓：{len(account['positions'])} 只")
    print()
    
    # 获取最新价格
    prices = executor.get_current_prices()
    print(f"✅ 获取最新价格：{len(prices)} 只股票")
    print()
    
    # 检查持仓
    executor.check_positions(account, prices)
    
    # 执行止损
    account = executor.execute_stop_loss(account)
    
    # 止盈建议
    executor.suggest_take_profit()
    
    # 预警
    executor.show_warnings()
    
    # 保存报告
    executor.save_report(account)
    
    # 保存更新后的账户
    with open(executor.account_file, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 账户已更新")
    
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
