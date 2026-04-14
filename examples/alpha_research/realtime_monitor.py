#!/usr/bin/env python3
"""
实时监控系统 - 每小时检查

功能:
1. 每小时更新持仓价格
2. 检查止盈止损
3. 检查仓位比例
4. 发送告警通知
5. 确保数据最新
6. 自动上报 Issue 到 Manager (P0-1 修复)
"""

import json
import csv
import os
from pathlib import Path
from agent_report import create_report
from report_templates import create_monitoring_report
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
        
        # P0-1 修复：Manager 接口和去重机制
        self.manager = None
        self.reported_issues = {}  # 用于去重：{issue_key: last_reported_time}
        self.dedup_window = 1800  # 30 分钟内不重复上报
    
    def _get_manager(self):
        """懒加载 Manager 实例"""
        if self.manager is None:
            try:
                from manager_interface import QuantManager
                self.manager = QuantManager()
                print("✅ Manager 接口已初始化")
            except Exception as e:
                print(f"⚠️  Manager 初始化失败：{e}")
                self.manager = False  # 标记为失败，避免重复尝试
        return self.manager if self.manager else None
    
    def _get_issue_key(self, issue_type: str, context: dict) -> str:
        """生成 Issue 去重键"""
        # 根据问题类型和关键上下文生成唯一键
        if issue_type == 'data_quality':
            stock_code = context.get('stock_code', '')
            return f"data_quality:{stock_code}"
        elif issue_type == 'trading_error':
            stock_code = context.get('stock_code', '')
            return f"trading_error:{stock_code}"
        elif issue_type == 'system_alert':
            return f"system_alert:{context.get('title', '')}"
        return f"{issue_type}:{json.dumps(context, sort_keys=True)}"
    
    def _should_report(self, issue_key: str) -> bool:
        """检查是否应该上报（去重检查）"""
        now = time.time()
        if issue_key in self.reported_issues:
            last_reported = self.reported_issues[issue_key]
            if now - last_reported < self.dedup_window:
                return False
        self.reported_issues[issue_key] = now
        return True
    
    def report_to_manager(self, issue_type: str, severity: str, title: str,
                         description: str, context: dict = None):
        """
        P0-1 修复：上报问题到 Manager
        
        Args:
            issue_type: data_quality | trading_error | system_alert
            severity: critical | high | medium | low
            title: 简洁描述
            description: 详细信息
            context: 上下文信息
        """
        # 去重检查
        issue_key = self._get_issue_key(issue_type, context or {})
        if not self._should_report(issue_key):
            print(f"  ⏭️  跳过重复上报：{title}")
            return None
        
        manager = self._get_manager()
        if not manager:
            print(f"  ⚠️  Manager 不可用，跳过上报：{title}")
            return None
        
        try:
            # 构建 Issue 数据结构
            issue_data = {
                "type": issue_type,
                "severity": severity,
                "title": title,
                "description": description,
                "source": "realtime_monitor",
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            }
            
            # 创建 Issue
            from issue_queue import Issue
            issue = Issue(
                id="",
                agent="realtime_monitor",
                severity=severity.upper() if severity in ['critical', 'high', 'medium', 'low'] else "P2",
                error_type=issue_type,
                error_message=description[:200],
                details=issue_data
            )
            
            # 上报到 Manager
            task = manager.handle_error_report(issue)
            issue_id = task.get('issue_id', 'unknown')
            
            print(f"  ✅ 已上报 Issue 到 Manager: {issue_id}")
            print(f"     类型：{issue_type}, 严重性：{severity}")
            print(f"     标题：{title}")
            
            return issue_id
            
        except Exception as e:
            print(f"  ❌ 上报失败：{e}")
            return None
            
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
                days_old = (datetime.now() - RealtimeMonitor.parse_date(data['date'])).days
                stale_data.append({
                    'symbol': symbol,
                    'last_date': data['date'],
                    'days_old': days_old
                })
                print(f"  ⚠️ {symbol}: 数据滞后 {data['date']} ({days_old} 天)")
                
                # P0-1 修复：数据滞后超过 2 天时自动上报
                if days_old >= 2:
                    self.report_to_manager(
                        issue_type='data_quality',
                        severity='high' if days_old >= 5 else 'medium',
                        title=f'{symbol} 数据滞后 {days_old} 天',
                        description=f'{symbol} 最新数据日期为 {data["date"]}，已滞后 {days_old} 天，可能影响交易决策',
                        context={
                            'stock_code': symbol,
                            'last_date': data['date'],
                            'days_old': days_old,
                            'expected': today
                        }
                    )
        
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
            cost_price = pos.get('avg_price') or pos.get('avg_cost', 0)
            
            # 计算盈亏率
            profit_rate = (current_price - cost_price) / cost_price
            market_value = pos.get('quantity', 0) * current_price
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
                
                # P0-1 修复：止损触发时自动上报
                self.report_to_manager(
                    issue_type='trading_error',
                    severity='critical',
                    title=f'{symbol} 触发止损',
                    description=f'{symbol} 当前跌幅 {profit_rate*100:.1f}%，已触及止损线 {self.stop_loss_threshold*100:.0f}%，建议立即卖出',
                    context={
                        'stock_code': symbol,
                        'profit_rate': profit_rate,
                        'current_price': current_price,
                        'cost_price': cost_price,
                        'stop_loss_threshold': self.stop_loss_threshold
                    }
                )
            
            elif profit_rate >= self.take_profit_threshold:
                alerts['take_profit'].append({
                    'symbol': symbol,
                    'profit_rate': profit_rate,
                    'current_price': current_price,
                    'action': '建议止盈'
                })
                print(f"  🟢 止盈：{symbol} {profit_rate*100:.1f}%")
                
                # P0-1 修复：止盈触发时自动上报
                self.report_to_manager(
                    issue_type='trading_error',
                    severity='high',
                    title=f'{symbol} 触发止盈',
                    description=f'{symbol} 当前涨幅 {profit_rate*100:.1f}%，已触及止盈线 {self.take_profit_threshold*100:.0f}%，建议考虑止盈',
                    context={
                        'stock_code': symbol,
                        'profit_rate': profit_rate,
                        'current_price': current_price,
                        'take_profit_threshold': self.take_profit_threshold
                    }
                )
            
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
                
                # P0-1 修复：仓位超配时自动上报
                self.report_to_manager(
                    issue_type='system_alert',
                    severity='medium',
                    title=f'{symbol} 仓位超配',
                    description=f'{symbol} 当前仓位 {position_ratio*100:.1f}%，超过上限 {self.max_position_ratio*100:.0f}%',
                    context={
                        'stock_code': symbol,
                        'position_ratio': position_ratio,
                        'max_ratio': self.max_position_ratio,
                        'market_value': market_value
                    }
                )
        
        # 现金比例检查
        cash_ratio = account['cash'] / total_assets if total_assets > 0 else 0
        if cash_ratio < self.min_cash_ratio:
            alerts['cash_low'].append({
                'cash_ratio': cash_ratio,
                'cash': account['cash'],
                'min_required': total_assets * self.min_cash_ratio
            })
            print(f"  ⚠️ 现金不足：{cash_ratio*100:.1f}% (建议≥5%)")
            
            # P0-1 修复：现金不足时自动上报
            self.report_to_manager(
                issue_type='system_alert',
                severity='medium',
                title='现金比例不足',
                description=f'当前现金比例 {cash_ratio*100:.1f}%，低于最低要求 {self.min_cash_ratio*100:.0f}%',
                context={
                    'cash_ratio': cash_ratio,
                    'cash': account['cash'],
                    'min_required': self.min_cash_ratio
                }
            )
        
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
                pos['market_value'] = pos.get('quantity', 0) * new_price
                pos['profit'] = pos['market_value'] - pos.get('cost_basis', 0)
                pos['profit_rate'] = pos['profit'] / pos.get('cost_basis', 1) if pos.get('cost_basis', 0) > 0 else 0
                
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
    parser.add_argument('--non-interactive', action='store_true', help='无人值守模式：禁用所有交互式提示，使用默认值')
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
