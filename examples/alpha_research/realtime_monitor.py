#!/usr/bin/env python3
"""
实时监控系统 - 每小时检查

功能:
1. 每小时更新持仓价格
2. 检查止盈止损
3. 检查仓位比例
4. 发送告警通知
5. 确保数据最新
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
import time
import requests
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive


class RealtimeMonitor:
    @staticmethod
    def parse_date(date_str):
        """解析日期，支持多种格式"""
        if not date_str:
            return None
        # Try common formats
        for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        # If all fail, return None
        return None

    """实时监控系统"""
    
    def __init__(self, account_file: str = './accounts/virtual_2026_account.json'):
        self.account_file = Path(account_file)
        self.data_dir = Path("./cache")
        self.cache_dir = Path('./cache/monitor')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 监控配置
        self.check_interval = 3600  # 1 小时
        self.stop_loss_threshold = -0.15  # -15% 止损
        self.take_profit_threshold = 0.30  # +30% 止盈
        self.warning_threshold = -0.10  # -10% 预警
        self.max_position_ratio = 0.15  # 单只最大 15%
        self.min_cash_ratio = 0.05  # 最小现金 5%
        
        # 告警配置
        self.enable_dingtalk = False  # 配置钉钉 webhook
        self.enable_email = False  # 配置邮件
        
    def load_account(self):
        """加载账户"""
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_latest_prices(self, symbols):
        """获取最新价格（优先从最新数据文件读取）"""
        prices = {}
        today = datetime.now().strftime('%Y-%m-%d')
        
        for symbol in symbols:
            csv_file = self.data_dir / f"{symbol.replace('.', '_')}.csv"
            if csv_file.exists():
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        # Handle different CSV formats
                        # Format 1: vt_symbol,datetime,open,high,low,close,volume,turnover
                        # Format 2: date,open,high,low,close,volume
                        if len(last_line) >= 5:
                            # Try to find the date field (could be at index 0 or 1)
                            price_date = None
                            for i in range(min(2, len(last_line))):
                                # Check if this field looks like a date
                                try:
                                    # Try parsing as date
                                    datetime.strptime(last_line[i], '%Y-%m-%d')
                                    price_date = last_line[i]
                                    break
                                except ValueError:
                                    try:
                                        datetime.strptime(last_line[i], '%Y%m%d')
                                        price_date = last_line[i]
                                        break
                                    except ValueError:
                                        continue
                            
                            if price_date:
                                price = float(last_line[4])
                                prices[symbol] = {
                                    'price': price,
                                    'date': price_date,
                                    'is_latest': price_date == today
                                }
        
        return prices
    
    def check_data_freshness(self, prices):
        """检查数据新鲜度"""
        print("=" * 70)
        print(" " * 20 + "数据新鲜度检查")
        print("=" * 70)
        
        today = datetime.now().strftime('%Y-%m-%d')
        stale_data = []
        
        for symbol, data in prices.items():
            if not data['is_latest']:
                stale_data.append({
                    'symbol': symbol,
                    'last_date': data['date'],
                    'days_old': (datetime.now() - RealtimeMonitor.parse_date(data['date'])).days
                })
                print(f"  ⚠️ {symbol}: 数据滞后 {data['date']} ({(datetime.now() - RealtimeMonitor.parse_date(data['date'])).days} 天)")
        
        if not stale_data:
            print(f"  ✅ 所有数据均为最新 ({today})")
        else:
            print(f"\n  📊 统计：{len(stale_data)} 只股票数据滞后")
            print(f"  💡 建议：运行 python3 download_data_akshare.py 更新数据")
        
        return len(stale_data) == 0, stale_data
    
    def check_positions(self, account, prices):
        """检查持仓状态"""
        print("\n" + "=" * 70)
        print(" " * 20 + "持仓状态检查")
        print("=" * 70)
        
        alerts = {
            'stop_loss': [],
            'take_profit': [],
            'warning': [],
            'position_overweight': [],
            'cash_low': []
        }
        
        total_assets = account['cash'] + sum(p.get('market_value', 0) for p in account['positions'])
        
        for pos in account['positions']:
            symbol = pos['symbol']
            price_data = prices.get(symbol, {})
            current_price = price_data.get('price', pos['current_price'])
            cost_price = pos['avg_price']
            
            # 计算盈亏率
            profit_rate = (current_price - cost_price) / cost_price
            market_value = pos['volume'] * current_price
            position_ratio = market_value / total_assets if total_assets > 0 else 0
            
            # 止盈止损检查
            if profit_rate <= self.stop_loss_threshold:
                alerts['stop_loss'].append({
                    'symbol': symbol,
                    'profit_rate': profit_rate,
                    'current_price': current_price,
                    'cost_price': cost_price,
                    'action': '立即止损卖出'
                })
                print(f"  🔴 止损：{symbol} {profit_rate*100:.1f}% (¥{cost_price:.2f}→¥{current_price:.2f})")
            
            elif profit_rate >= self.take_profit_threshold:
                alerts['take_profit'].append({
                    'symbol': symbol,
                    'profit_rate': profit_rate,
                    'current_price': current_price,
                    'action': '建议止盈'
                })
                print(f"  🟢 止盈：{symbol} {profit_rate*100:.1f}%")
            
            elif profit_rate <= self.warning_threshold:
                alerts['warning'].append({
                    'symbol': symbol,
                    'profit_rate': profit_rate,
                    'distance_to_stop': (self.stop_loss_threshold - profit_rate) * 100
                })
                print(f"  🟡 预警：{symbol} {profit_rate*100:.1f}% (距止损 {(self.stop_loss_threshold - profit_rate)*100:.1f}%)")
            
            # 仓位检查
            if position_ratio > self.max_position_ratio:
                alerts['position_overweight'].append({
                    'symbol': symbol,
                    'ratio': position_ratio,
                    'market_value': market_value,
                    'excess': (position_ratio - self.max_position_ratio) * 100
                })
                print(f"  ⚠️ 超配：{symbol} {position_ratio*100:.1f}% (上限 15%，超 {position_ratio*100 - 15:.1f}%)")
        
        # 现金比例检查
        cash_ratio = account['cash'] / total_assets if total_assets > 0 else 0
        if cash_ratio < self.min_cash_ratio:
            alerts['cash_low'].append({
                'cash_ratio': cash_ratio,
                'cash': account['cash'],
                'min_required': total_assets * self.min_cash_ratio
            })
            print(f"  ⚠️ 现金不足：{cash_ratio*100:.1f}% (建议≥5%)")
        
        print(f"\n📊 统计:")
        print(f"  止损：{len(alerts['stop_loss'])} 只")
        print(f"  止盈：{len(alerts['take_profit'])} 只")
        print(f"  预警：{len(alerts['warning'])} 只")
        print(f"  超配：{len(alerts['position_overweight'])} 只")
        print(f"  现金不足：{len(alerts['cash_low'])} 次")
        
        return alerts
    
    def send_alert(self, alerts):
        """发送告警通知"""
        if not any(alerts.values()):
            print("\n✅ 无告警")
            return
        
        print("\n" + "=" * 70)
        print(" " * 20 + "告警通知")
        print("=" * 70)
        
        # 构建告警消息
        message = f"🚨 投资监控告警 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        if alerts['stop_loss']:
            message += "🔴 止损:\n"
            for a in alerts['stop_loss']:
                message += f"  - {a['symbol']}: {a['profit_rate']*100:.1f}% (建议立即卖出)\n"
            message += "\n"
        
        if alerts['take_profit']:
            message += "🟢 止盈:\n"
            for a in alerts['take_profit']:
                message += f"  - {a['symbol']}: {a['profit_rate']*100:.1f}% (建议考虑止盈)\n"
            message += "\n"
        
        if alerts['position_overweight']:
            message += "⚠️ 超配:\n"
            for a in alerts['position_overweight']:
                message += f"  - {a['symbol']}: {a['ratio']*100:.1f}% (建议减仓至 15%)\n"
            message += "\n"
        
        if alerts['cash_low']:
            message += "💰 现金不足:\n"
            message += f"  当前现金比例：{alerts['cash_low'][0]['cash_ratio']*100:.1f}%\n"
            message += f"  建议：保持至少 5% 现金\n"
        
        print(message)
        
        # 钉钉通知（如果配置）
        if self.enable_dingtalk:
            self._send_dingtalk(message)
        
        # 保存告警记录
        self._save_alert_record(alerts, message)
    
    def _send_dingtalk(self, message):
        """发送钉钉消息"""
        webhook = os.environ.get('DINGTALK_WEBHOOK', '')
        if not webhook:
            return
        
        try:
            data = {
                'msgtype': 'text',
                'text': {'content': message}
            }
            response = requests.post(webhook, json=data, timeout=10)
            if response.status_code == 200:
                print("  ✅ 钉钉通知已发送")
        except Exception as e:
            print(f"  ⚠️ 钉钉通知失败：{e}")
    
    def _save_alert_record(self, alerts, message):
        """保存告警记录"""
        record_file = self.cache_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        record = {
            'timestamp': datetime.now().isoformat(),
            'alerts': alerts,
            'message': message
        }
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 告警记录已保存：{record_file}")
    
    def update_account_prices(self, account, prices):
        """更新账户持仓价格"""
        print("\n" + "=" * 70)
        print(" " * 20 + "更新持仓价格")
        print("=" * 70)
        
        for pos in account['positions']:
            symbol = pos['symbol']
            if symbol in prices:
                old_price = pos['current_price']
                new_price = prices[symbol]['price']
                pos['current_price'] = new_price
                pos['market_value'] = pos['volume'] * new_price
                pos['profit'] = pos['market_value'] - pos['cost']
                pos['profit_rate'] = pos['profit'] / pos['cost'] if pos['cost'] > 0 else 0
                
                if abs(new_price - old_price) / old_price > 0.01:  # 变化超过 1%
                    print(f"  📈 {symbol}: ¥{old_price:.2f} → ¥{new_price:.2f} ({(new_price-old_price)/old_price*100:+.1f}%)")
        
        # 重新计算总资产
        total_market_value = sum(p.get('market_value', 0) for p in account['positions'])
        total_assets = account['cash'] + total_market_value
        
        print(f"\n💰 账户状态:")
        print(f"  现金：¥{account['cash']:,.2f}")
        print(f"  持仓市值：¥{total_market_value:,.2f}")
        print(f"  总资产：¥{total_assets:,.2f}")
        print(f"  收益率：{(total_assets - account['initial_capital'])/account['initial_capital']*100:+.1f}%")
        
        return account
    
    def save_account(self, account):
        """保存账户"""
        with open(self.account_file, 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 账户已保存")
    
    def save_monitor_report(self, data_fresh, stale_data, alerts):
        """保存监控报告"""
        report = {
            'check_time': datetime.now().isoformat(),
            'data_freshness': {
                'is_fresh': data_fresh,
                'stale_stocks': stale_data
            },
            'alerts': alerts,
            'summary': {
                'stop_loss_count': len(alerts.get('stop_loss', [])),
                'take_profit_count': len(alerts.get('take_profit', [])),
                'warning_count': len(alerts.get('warning', [])),
                'overweight_count': len(alerts.get('position_overweight', []))
            }
        }
        
        report_file = Path('./reports/monitor_' + datetime.now().strftime('%Y%m%d_%H%M') + '.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 监控报告已保存：{report_file}")
        return report_file
    
    def run_check(self):
        """执行一次完整检查"""
        print("=" * 70)
        print(" " * 16 + f"实时监控检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        
        # 加载账户
        account = self.load_account()
        print(f"📊 账户：{account['account_id']}")
        print(f"   持仓：{len(account['positions'])} 只")
        print()
        
        # 获取最新价格
        symbols = [p['symbol'] for p in account['positions']]
        prices = self.get_latest_prices(symbols)
        print(f"✅ 获取价格数据：{len(prices)} 只股票")
        print()
        
        # 检查数据新鲜度
        data_fresh, stale_data = self.check_data_freshness(prices)
        
        # 更新账户价格
        account = self.update_account_prices(account, prices)
        
        # 检查持仓状态
        alerts = self.check_positions(account, prices)
        
        # 发送告警
        self.send_alert(alerts)
        
        # 保存账户
        self.save_account(account)
        
        # 保存监控报告
        self.save_monitor_report(data_fresh, stale_data, alerts)
        
        print("\n" + "=" * 70)
        print(" " * 20 + "检查完成")
        print("=" * 70)
        
        return alerts


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='实时监控系统')
    parser.add_argument('--once', action='store_true', help='只执行一次检查')
    parser.add_argument('--interval', type=int, default=3600, help='检查间隔（秒），默认 3600 秒')
    args = parser.parse_args()
    
    # 设置无人值守模式
    setup_non_interactive_mode(args.non_interactive)
    
    monitor = RealtimeMonitor()
    
    if args.once:
        # 只执行一次
        monitor.run_check()
    else:
        # 持续监控
        print("=" * 70)
        print(" " * 18 + "实时监控系统启动")
        print("=" * 70)
        print(f"检查间隔：{args.interval} 秒 ({args.interval/60:.0f} 分钟)")
        print(f"止损线：-15%  |  止盈线：+30%  |  预警线：-10%")
        print(f"单只上限：15%  |  现金下限：5%")
        print()
        print("按 Ctrl+C 停止监控")
        print("=" * 70)
        
        try:
            while True:
                monitor.run_check()
                
                next_check = datetime.now() + timedelta(seconds=args.interval)
                print(f"\n⏰ 下次检查：{next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")


if __name__ == '__main__':
    main()
