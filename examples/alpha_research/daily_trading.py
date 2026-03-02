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


class DailyTrading:
    """每日交易"""
    
    def __init__(self, account: VirtualAccount):
        self.account = account
        self.data_dir = Path('./data/akshare/bars')
        self.today = datetime.now().strftime('%Y-%m-%d')
        
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
                        self.stock_data[symbol] = {
                            'open': float(row['open_price']),
                            'high': float(row['high_price']),
                            'low': float(row['low_price']),
                            'close': float(row['close_price']),
                            'volume': float(row['volume'])
                        }
                        self.current_prices[symbol] = float(row['close_price'])
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
                        'reason': f'止损 ({cost_rate:.1f}%)'
                    })
        
        # 2. 选择新股票买入
        # 按价格排序，选前 10 只
        sorted_stocks = sorted(
            self.current_prices.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # 排除已持仓
        holding_symbols = set(self.account.positions.keys())
        for symbol, price in sorted_stocks:
            if symbol not in holding_symbols and len(buy_list) < 5:
                buy_list.append({
                    'symbol': symbol,
                    'price': price,
                    'reason': '动量选股'
                })
        
        return buy_list, sell_list
    
    def execute_trades(self, buy_list: list, sell_list: list):
        """执行交易"""
        print(f"\n【执行交易】")
        
        buy_count = 0
        sell_count = 0
        
        # 先卖出
        for trade_info in sell_list:
            trade = self.account.sell(
                symbol=trade_info['symbol'],
                price=trade_info['price'],
                volume=trade_info['volume'],
                date=self.today,
                reason=trade_info['reason']
            )
            
            if trade:
                print(f"  卖出 {trade_info['symbol']} ({trade.name})")
                print(f"    {trade.volume} 股 @ ¥{trade.price:.2f}")
                sell_count += 1
        
        # 再买入
        if buy_list:
            # 计算可用资金
            available_cash = self.account.cash * 0.9  # 留 10% 现金
            position_size = available_cash / len(buy_list)
            
            for trade_info in buy_list:
                volume = int(position_size / trade_info['price'] / 100) * 100
                if volume >= 100:
                    trade = self.account.buy(
                        symbol=trade_info['symbol'],
                        price=trade_info['price'],
                        volume=volume,
                        date=self.today,
                        reason=trade_info['reason']
                    )
                    
                    if trade:
                        print(f"  买入 {trade_info['symbol']} ({trade.name})")
                        print(f"    {trade.volume} 股 @ ¥{trade.price:.2f}")
                        buy_count += 1
        
        return buy_count, sell_count
    
    def update_portfolio(self):
        """更新组合"""
        self.account.update_positions(self.current_prices)
    
    def generate_snapshot(self, buy_count: int, sell_count: int):
        """生成每日快照"""
        snapshot = self.account.generate_daily_snapshot(
            date=self.today,
            buy_count=buy_count,
            sell_count=sell_count
        )
        
        print(f"\n【账户快照】")
        print(f"  日期：{snapshot.date}")
        print(f"  现金：¥{snapshot.cash:,.2f}")
        print(f"  总值：¥{snapshot.total_value:,.2f}")
        print(f"  市值：¥{snapshot.market_value:,.2f}")
        print(f"  当日收益：¥{snapshot.daily_return:,.2f} ({snapshot.daily_return_rate:+.2f}%)")
        print(f"  持仓：{snapshot.positions_count} 只")
        
        return snapshot
    
    def run_daily(self, target_date: str = None):
        """运行每日交易"""
        print("=" * 70)
        print(f"  每日交易 - {self.today if not target_date else target_date}")
        print("=" * 70)
        print()
        
        # 1. 加载数据
        loaded = self.load_today_data(target_date)
        if loaded == 0:
            print("❌ 无当日数据，跳过")
            return None
        
        # 2. 执行策略
        buy_list, sell_list = self.simple_momentum_strategy()
        
        # 3. 执行交易
        buy_count, sell_count = self.execute_trades(buy_list, sell_list)
        
        # 4. 更新组合
        self.update_portfolio()
        
        # 5. 生成快照
        snapshot = self.generate_snapshot(buy_count, sell_count)
        
        # 6. 保存账户
        self.account._save_account()
        
        print()
        print("=" * 70)
        
        return snapshot


def main():
    print("=" * 70)
    print(" " * 20 + "每日自动交易")
    print("=" * 70)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载虚拟账户
    account = VirtualAccount(
        initial_capital=1000000,
        account_id="virtual_2026"
    )
    
    # 创建每日交易
    daily_trading = DailyTrading(account)
    
    # 运行每日交易
    # 可以指定日期，默认今天
    daily_trading.run_daily()
    
    print()
    print("✅ 每日交易完成")
    print()


if __name__ == '__main__':
    main()
