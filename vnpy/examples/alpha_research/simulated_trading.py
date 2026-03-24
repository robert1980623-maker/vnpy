#!/usr/bin/env python3
"""
模拟实盘回测

功能:
- 使用 2024 年真实股票数据
- 模拟真实交易流程
- 计算真实收益
- 生成交易记录
- 支持多策略
"""

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import random


@dataclass
class Position:
    """持仓"""
    symbol: str
    volume: int
    avg_price: float
    cost: float


@dataclass
class Trade:
    """交易记录"""
    symbol: str
    direction: str  # buy/sell
    volume: int
    price: float
    amount: float
    fee: float
    datetime: str


@dataclass
class DailyAccount:
    """每日账户"""
    date: str
    cash: float
    positions: Dict[str, Position]
    total_value: float
    daily_return: float


class SimulatedTrading:
    """模拟交易"""
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_accounts: List[DailyAccount] = []
        
        # 加载股票数据
        self.data_dir = Path('./data/akshare/bars')
        self.stock_data: Dict[str, List[dict]] = {}
        
        # 交易费率
        self.commission_rate = 0.0003  # 万三
        self.slippage_rate = 0.001     # 千一滑点
        
    def load_stock_data(self, symbols: Optional[List[str]] = None):
        """加载股票数据"""
        csv_files = list(self.data_dir.glob('*.csv'))
        
        if symbols:
            csv_files = [f for f in csv_files if f.stem.replace('_', '.') in symbols]
        
        for csv_file in csv_files:
            symbol = csv_file.stem.replace('_', '.')
            bars = []
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bars.append({
                        'datetime': row['datetime'],
                        'open': float(row['open_price']),
                        'high': float(row['high_price']),
                        'low': float(row['low_price']),
                        'close': float(row['close_price']),
                        'volume': float(row['volume']),
                        'turnover': float(row['turnover'])
                    })
            
            self.stock_data[symbol] = bars
        
        print(f"✅ 加载 {len(self.stock_data)} 只股票数据")
        
    def get_trading_dates(self) -> List[str]:
        """获取交易日期"""
        if not self.stock_data:
            return []
        
        # 从任意股票获取交易日期
        first_symbol = list(self.stock_data.keys())[0]
        return [bar['datetime'] for bar in self.stock_data[first_symbol]]
    
    def buy(self, symbol: str, price: float, volume: int, date: str) -> Optional[Trade]:
        """买入"""
        if symbol not in self.stock_data:
            return None
        
        # 计算滑点
        exec_price = price * (1 + self.slippage_rate)
        amount = exec_price * volume
        fee = max(5, amount * self.commission_rate)  # 最低 5 元
        total_cost = amount + fee
        
        if total_cost > self.cash:
            return None
        
        # 更新现金
        self.cash -= total_cost
        
        # 更新持仓
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_volume = pos.volume + volume
            total_cost = pos.cost + amount
            pos.avg_price = total_cost / total_volume
            pos.volume = total_volume
            pos.cost = total_cost
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                volume=volume,
                avg_price=exec_price,
                cost=amount
            )
        
        # 记录交易
        trade = Trade(
            symbol=symbol,
            direction='buy',
            volume=volume,
            price=exec_price,
            amount=amount,
            fee=fee,
            datetime=date
        )
        self.trades.append(trade)
        
        return trade
    
    def sell(self, symbol: str, price: float, volume: int, date: str) -> Optional[Trade]:
        """卖出"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        if pos.volume < volume:
            return None
        
        # 计算滑点
        exec_price = price * (1 - self.slippage_rate)
        amount = exec_price * volume
        fee = max(5, amount * self.commission_rate)
        net_amount = amount - fee
        
        # 更新现金
        self.cash += net_amount
        
        # 更新持仓
        pos.volume -= volume
        if pos.volume == 0:
            del self.positions[symbol]
        
        # 记录交易
        trade = Trade(
            symbol=symbol,
            direction='sell',
            volume=volume,
            price=exec_price,
            amount=amount,
            fee=fee,
            datetime=date
        )
        self.trades.append(trade)
        
        return trade
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """计算组合总值"""
        # 持仓市值
        market_value = sum(
            pos.volume * current_prices.get(pos.symbol, pos.avg_price)
            for pos in self.positions.values()
        )
        return self.cash + market_value
    
    def run_backtest(self, start_date: str = '2024-01-02', end_date: str = '2024-12-31'):
        """运行回测"""
        print("\n" + "=" * 70)
        print(" " * 20 + "模拟实盘回测")
        print("=" * 70)
        print(f"初始资金：¥{self.initial_capital:,.0f}")
        print(f"回测区间：{start_date} ~ {end_date}")
        print()
        
        trading_dates = self.get_trading_dates()
        trading_dates = [d for d in trading_dates if start_date <= d <= end_date]
        
        print(f"交易天数：{len(trading_dates)}")
        print()
        
        prev_value = self.initial_capital
        
        # 简化策略：每月初调仓
        last_month = None
        
        for date in trading_dates:
            current_month = date[:7]  # YYYY-MM
            
            # 获取当日收盘价
            current_prices = {}
            for symbol, bars in self.stock_data.items():
                for bar in bars:
                    if bar['datetime'] == date:
                        current_prices[symbol] = bar['close']
                        break
            
            # 计算账户总值
            total_value = self.get_portfolio_value(current_prices)
            daily_return = (total_value - prev_value) / prev_value * 100 if prev_value > 0 else 0
            
            # 记录每日账户
            account = DailyAccount(
                date=date,
                cash=round(self.cash, 2),
                positions={k: asdict(v) for k, v in self.positions.items()},
                total_value=round(total_value, 2),
                daily_return=round(daily_return, 2)
            )
            self.daily_accounts.append(account)
            prev_value = total_value
            
            # 每月初调仓 (简化策略)
            if current_month != last_month:
                last_month = current_month
                
                # 清空持仓
                for symbol in list(self.positions.keys()):
                    if symbol in current_prices:
                        price = current_prices[symbol]
                        pos = self.positions[symbol]
                        self.sell(symbol, price, pos.volume, date)
                
                # 选择股票买入 (简单动量策略)
                # 选择前 5 只涨幅最好的股票
                sorted_stocks = sorted(
                    current_prices.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                # 平均分配资金
                position_size = self.cash * 0.9 / len(sorted_stocks)
                
                for symbol, price in sorted_stocks:
                    volume = int(position_size / price / 100) * 100  # 100 股整数倍
                    if volume >= 100:
                        self.buy(symbol, price, volume, date)
        
        # 输出结果
        self.print_results()
        
        return self.daily_accounts
    
    def print_results(self):
        """打印回测结果"""
        print("\n" + "=" * 70)
        print(" " * 20 + "回测结果")
        print("=" * 70)
        
        if not self.daily_accounts:
            print("❌ 无回测数据")
            return
        
        final_account = self.daily_accounts[-1]
        total_return = (final_account.total_value - self.initial_capital) / self.initial_capital * 100
        
        print(f"\n初始资金：¥{self.initial_capital:,.0f}")
        print(f"最终总值：¥{final_account.total_value:,.2f}")
        print(f"总收益：¥{final_account.total_value - self.initial_capital:,.2f}")
        print(f"总收益率：{total_return:+.2f}%")
        print()
        
        # 交易统计
        buy_trades = [t for t in self.trades if t.direction == 'buy']
        sell_trades = [t for t in self.trades if t.direction == 'sell']
        
        print(f"交易次数：{len(self.trades)}")
        print(f"买入：{len(buy_trades)} 次")
        print(f"卖出：{len(sell_trades)} 次")
        print(f"总手续费：¥{sum(t.fee for t in self.trades):,.2f}")
        print()
        
        # 每日收益统计
        daily_returns = [acc.daily_return for acc in self.daily_accounts]
        avg_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
        max_daily_return = max(daily_returns) if daily_returns else 0
        min_daily_return = min(daily_returns) if daily_returns else 0
        
        print(f"日均收益：{avg_daily_return:+.2f}%")
        print(f"最大单日收益：+{max_daily_return:.2f}%")
        print(f"最大单日亏损：{min_daily_return:.2f}%")
        print()
        
        # 最终持仓
        print("最终持仓:")
        for symbol, pos in final_account.positions.items():
            if isinstance(pos, dict):
                print(f"  {symbol}: {pos['volume']} 股，均价 ¥{pos['avg_price']:.2f}")
            else:
                print(f"  {symbol}: {pos.volume} 股，均价 ¥{pos.avg_price:.2f}")
        
        print()
        print("=" * 70)
    
    def save_results(self, output_dir: str = 'reports'):
        """保存回测结果"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存每日账户
        accounts_file = output_path / f'backtest_accounts_{datetime.now().strftime("%Y%m%d")}.json'
        with open(accounts_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(acc) for acc in self.daily_accounts], f, ensure_ascii=False, indent=2)
        
        # 保存交易记录
        trades_file = output_path / f'backtest_trades_{datetime.now().strftime("%Y%m%d")}.json'
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(t) for t in self.trades], f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 结果已保存:")
        print(f"   每日账户：{accounts_file}")
        print(f"   交易记录：{trades_file}")


def main():
    print("=" * 70)
    print(" " * 15 + "模拟实盘回测系统")
    print("=" * 70)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建模拟交易
    sim = SimulatedTrading(initial_capital=1000000)
    
    # 加载股票数据
    print("\n【步骤 1】加载股票数据...")
    sim.load_stock_data()
    
    # 运行回测
    print("\n【步骤 2】运行回测...")
    sim.run_backtest(
        start_date='2024-01-02',
        end_date='2024-12-31'
    )
    
    # 保存结果
    print("\n【步骤 3】保存结果...")
    sim.save_results()
    
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
