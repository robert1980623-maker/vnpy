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
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account
import random
from logger import TaskLogger


class DailyTrading:
    """每日交易"""
    
    def __init__(self, account: AccountService):
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
        
        # 获取当前持仓
        positions = self.account.get_positions()
        position_dict = {pos.symbol: pos for pos in positions}
        
        # 1. 清空表现差的持仓
        for symbol, pos in position_dict.items():
            if symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                cost_rate = (current_price - pos.avg_cost) / pos.avg_cost * 100
                
                # 亏损超过 5% 卖出
                if cost_rate < -5:
                    sell_list.append({
                        'symbol': symbol,
                        'volume': pos.quantity,
                        'price': current_price,
                        'reason': f'亏损 {cost_rate:.2f}%'
                    })
        
        # 2. 选择表现最好的股票买入
        # 计算过去5天的收益率
        momentum_scores = {}
        for symbol, data in self.stock_data.items():
            if symbol not in position_dict:
                # 计算从开盘到收盘的收益率
                return_rate = (data['close'] - data['open']) / data['open'] * 100
                momentum_scores[symbol] = return_rate
        
        # 按收益率排序，选择前5只
        sorted_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        top_symbols = [s[0] for s in sorted_symbols[:5]]
        
        # 每只买入 1000 股
        for symbol in top_symbols:
            if symbol not in position_dict:
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
        
        # 获取交易历史
        trade_history = self.account.get_trade_history()
        
        # 执行卖出
        for trade in sell_list:
            # 检查是否已经卖出
            if not any(t.symbol == trade['symbol'] and t.direction.value == 'sell' and t.trade_date == self.today 
                      for t in trade_history):
                revenue = trade['price'] * trade['volume']
                total_revenue += revenue
                self.account.sell(trade['symbol'], trade['price'], trade['volume'], trade['reason'])
                print(f"  卖出 {trade['symbol']} {trade['volume']}股 @ {trade['price']:.2f} ({trade['reason']})")
            else:
                print(f"  ⚠️  {trade['symbol']} 今日已卖出，跳过")
        
        # 执行买入
        for trade in buy_list:
            # 检查是否已经买入
            if not any(t.symbol == trade['symbol'] and t.direction.value == 'buy' and t.trade_date == self.today 
                      for t in trade_history):
                cost = trade['price'] * trade['volume']
                total_cost += cost
                self.account.buy(trade['symbol'], "", trade['price'], trade['volume'], trade['reason'])
                print(f"  买入 {trade['symbol']} {trade['volume']}股 @ {trade['price']:.2f} ({trade['reason']})")
            else:
                print(f"  ⚠️  {trade['symbol']} 今日已买入，跳过")
        
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
        balance = self.account.get_balance()
        positions = self.account.get_positions()
        
        print(f"\n  账户状态:")
        print(f"    现金: ¥{balance.cash:.2f}")
        print(f"    持仓: {len(positions)} 只")
        print(f"    总市值: ¥{balance.total_assets:.2f}")


def main():
    """主函数"""
    print("=" * 50)
    print("                    每日自动交易")
    print("=" * 50)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载账户
    db = AccountDB()
    if not db.get_account("virtual_2026"):
        db.create_account(Account(
            account_id="virtual_2026",
            account_name="虚拟账户",
            account_type="virtual",
            initial_capital=50000,
            cash=50000,
            currency="CNY",
            status="active",
            risk_level="moderate",
        ))
    
    account = AccountService("virtual_2026")
    
    balance = account.get_balance()
    positions = account.get_positions()
    trades = account.get_trade_history()
    
    print(f"\n✅ 加载账户：virtual_2026")
    print(f"   现金：¥{balance.cash:.2f}")
    print(f"   持仓：{len(positions)} 只")
    print(f"   交易：{len(trades)} 笔")
    
    # 运行每日交易
    daily_trading = DailyTrading(account)
    daily_trading.run_daily()
    
    print(f"\n✅ 账户已保存")


if __name__ == '__main__':
    main()
