#!/usr/bin/env python3
"""
每日自动交易

功能:
- 读取当日股票数据
- 执行交易策略
- 更新持仓
- 生成交易日志
"""

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from virtual_account import VirtualAccount, Position
import random
from logger import TaskLogger


class DailyTrading:
    """每日交易"""
    
    def __init__(self, account: VirtualAccount):
        self.account = account
        self.data_dir = Path('./data/akshare/bars')
        self.today = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 加载股票数据
        self.stock_data: dict = {}
        self.current_prices: dict = {}
        
    def load_today_data(self, target_date: str = None):
        """加载当日数据"""
        if target_date:
            self.today = target_date
        
        print(f"【加载数据】{self.today}")
        
        csv_files = list(self.data_dir.glob('*.csv'))
        loaded = 0
        
        for csv_file in csv_files:
            symbol = csv_file.stem.replace('_', '.')
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['datetime'] == self.today:
                        # Handle both column name formats
                        open_price = row.get('open_price') or row.get('open')
                        high_price = row.get('high_price') or row.get('high')
                        low_price = row.get('low_price') or row.get('low')
                        close_price = row.get('close_price') or row.get('close')
                        volume = row.get('volume')
                        
                        self.stock_data[symbol] = {
                            'open': float(open_price),
                            'high': float(high_price),
                            'low': float(low_price),
                            'close': float(close_price),
                            'volume': float(volume)
                        }
                        self.current_prices[symbol] = float(close_price)
                        loaded += 1
                        break
        
        print(f"  加载 {loaded} 只股票")
        return loaded
    
    def simple_momentum_strategy(self) -> tuple:
        """简单动量策略"""
        buy_list = []
        sell_list = []
        
        # 1. 清空表现差的持仓
        for symbol, pos in list(self.account.positions.items()):
            if symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                cost_rate = (current_price - pos.avg_price) / pos.avg_price * 100
                
                # 亏损超过 5% 卖出
                if cost_rate < -5:
                    sell_list.append({
                        'symbol': symbol,
                        'volume': pos.volume,
                        'price': current_price,
                        'reason': f'亏损 {cost_rate:.2f}%'
                    })
        
        # 2. 选择表现最好的股票买入
        # 计算过去5天的收益率
        momentum_scores = {}
        for symbol, data in self.stock_data.items():
            if symbol not in self.account.positions:
                # 计算从开盘到收盘的收益率
                return_rate = (data['close'] - data['open']) / data['open'] * 100
                momentum_scores[symbol] = return_rate
        
        # 按收益率排序，选择前5只
        sorted_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        top_symbols = [s[0] for s in sorted_symbols[:5]]
        
        # 每只买入 1000 股
        for symbol in top_symbols:
            if symbol not in self.account.positions:
                buy_list.append({
                    'symbol': symbol,
                    'volume': 1000,
                    'price': self.current_prices[symbol],
                    'reason': f'动量 {momentum_scores[symbol]:.2f}%'
                })
        
        return buy_list, sell_list
    
    def execute_trades(self, buy_list, sell_list):
        """执行交易"""
        total_cost = 0
        total_revenue = 0
        
        # 执行卖出
        for trade in sell_list:
            revenue = trade['price'] * trade['volume']
            total_revenue += revenue
            self.account.sell(trade['symbol'], trade['price'], trade['volume'], self.today, trade['reason'])
            print(f"  卖出 {trade['symbol']} {trade['volume']}股 @ {trade['price']:.2f} ({trade['reason']})")
        
        # 执行买入
        for trade in buy_list:
            cost = trade['price'] * trade['volume']
            total_cost += cost
            self.account.buy(trade['symbol'], trade['price'], trade['volume'], self.today, trade['reason'])
            print(f"  买入 {trade['symbol']} {trade['volume']}股 @ {trade['price']:.2f} ({trade['reason']})")
        
        print(f"\n  交易成本: ¥{total_cost:.2f}")
        print(f"  交易收入: ¥{total_revenue:.2f}")
        print(f"  净额: ¥{total_revenue - total_cost:.2f}")
    
    def run_daily(self):
        """运行每日交易"""
        print(f"  每日交易 - {self.today}")
        
        # 加载数据
        loaded = self.load_today_data()
        if loaded == 0:
            print(f"  ⚠️  未找到 {self.today} 的数据")
            return
        
        # 执行策略
        buy_list, sell_list = self.simple_momentum_strategy()
        
        # 执行交易
        if buy_list or sell_list:
            self.execute_trades(buy_list, sell_list)
        else:
            print("  无交易")
        
        # 显示账户状态
        print(f"\n  账户状态:")
        print(f"    现金: ¥{self.account.cash:.2f}")
        print(f"    持仓: {len(self.account.positions)} 只")
        print(f"    总市值: ¥{self.account.get_total_value():.2f}")


def main():
    """主函数"""
    print("=" * 50)
    print("                    每日自动交易")
    print("=" * 50)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载账户
    account = VirtualAccount(initial_capital=50000, account_id='virtual_2026')
    print(f"\n✅ 加载账户：virtual_2026")
    print(f"   现金：¥{account.cash:.2f}")
    print(f"   持仓：{len(account.positions)} 只")
    print(f"   交易：{len(account.trades)} 笔")
    
    # 运行每日交易
    daily_trading = DailyTrading(account)
    daily_trading.run_daily()
    
    # 保存账户
    account._save_account()
    print(f"\n✅ 账户已保存")


if __name__ == '__main__':
    main()
