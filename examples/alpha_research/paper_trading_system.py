#!/usr/bin/env python3
"""
VNPy 模拟交易系统

功能：
- 记录买卖操作
- 跟踪交易绩效
- 基于真实市场数据
- 生成交易报告
"""

import tushare as ts
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
import pandas as pd

# 初始化 Tushare
ts.set_token('612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5')
pro = ts.pro_api()


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    order_id: str
    ts_code: str
    stock_name: str
    direction: str  # buy/sell
    price: float
    volume: int
    timestamp: str
    commission: float
    trade_date: str
    
    @property
    def amount(self) -> float:
        return self.price * self.volume
    
    @property
    def total_cost(self) -> float:
        return self.amount + self.commission if self.direction == 'buy' else self.amount - self.commission


@dataclass
class Position:
    """持仓记录"""
    ts_code: str
    stock_name: str
    volume: int
    avg_price: float
    cost_basis: float
    current_price: float
    market_value: float
    profit: float
    return_pct: float


@dataclass
class PortfolioSnapshot:
    """账户快照"""
    date: str
    total_value: float
    cash: float
    position_value: float
    total_profit: float
    total_return_pct: float
    position_count: int


class PaperTradingAccount:
    """模拟交易账户"""
    
    def __init__(self, initial_cash: float = 1000000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.trades: List[Trade] = []
        self.positions: dict = {}  # ts_code -> Position
        self.snapshots: List[PortfolioSnapshot] = []
        self.trade_counter = 0
        self.order_counter = 0
        
        # 加载已有数据
        self.load_state()
    
    def load_state(self):
        """加载账户状态"""
        state_file = self._get_state_file()
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.cash = state.get('cash', self.initial_cash)
            self.positions = state.get('positions', {})
            self.trade_counter = state.get('trade_counter', 0)
            self.order_counter = state.get('order_counter', 0)
            
            # 加载交易记录
            trades_file = self._get_trades_file()
            if trades_file.exists():
                with open(trades_file, 'r', encoding='utf-8') as f:
                    trades_data = json.load(f)
                self.trades = [Trade(**t) for t in trades_data]
    
    def save_state(self):
        """保存账户状态"""
        state_dir = Path('paper_trading_demo')
        state_dir.mkdir(exist_ok=True)
        
        # 保存状态
        state = {
            'cash': self.cash,
            'positions': self.positions,
            'trade_counter': self.trade_counter,
            'order_counter': self.order_counter,
            'last_update': datetime.now().isoformat()
        }
        
        with open(self._get_state_file(), 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        # 保存交易记录
        trades_data = [asdict(t) for t in self.trades]
        with open(self._get_trades_file(), 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, indent=2, ensure_ascii=False)
    
    def _get_state_file(self) -> Path:
        return Path('paper_trading_demo/account_state.json')
    
    def _get_trades_file(self) -> Path:
        return Path('paper_trading_demo/trades_history.json')
    
    def get_latest_price(self, ts_code: str) -> tuple:
        """获取最新价格"""
        try:
            # 获取最近 5 天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df.empty:
                print(f"⚠️ 无法获取 {ts_code} 的价格数据")
                return None, None
            
            latest = df.iloc[0]
            return latest['close'], latest['trade_date']
        except Exception as e:
            print(f"❌ 获取价格失败：{e}")
            return None, None
    
    def buy(self, ts_code: str, volume: int, price: Optional[float] = None, 
            order_id: Optional[str] = None, trade_date: Optional[str] = None) -> Optional[Trade]:
        """买入操作"""
        if price is None:
            price, trade_date = self.get_latest_price(ts_code)
            if price is None:
                return None
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 获取股票名称
        try:
            basic = pro.stock_basic(ts_code=ts_code, fields='ts_code,name')
            stock_name = basic.iloc[0]['name'] if not basic.empty else ts_code
        except:
            stock_name = ts_code
        
        # 计算手续费（万分之三，最低 5 元）
        commission = max(5.0, price * volume * 0.0003)
        
        # 检查资金是否足够
        total_cost = price * volume + commission
        if total_cost > self.cash:
            print(f"❌ 资金不足！需要 ¥{total_cost:,.2f}, 可用 ¥{self.cash:,.2f}")
            return None
        
        # 创建交易记录
        self.trade_counter += 1
        self.order_counter += 1
        
        trade = Trade(
            trade_id=f"T{self.trade_counter:06d}",
            order_id=order_id or f"B{self.order_counter:06d}",
            ts_code=ts_code,
            stock_name=stock_name,
            direction='buy',
            price=price,
            volume=volume,
            timestamp=datetime.now().isoformat(),
            commission=commission,
            trade_date=trade_date
        )
        
        # 更新账户
        self.cash -= total_cost
        self.trades.append(trade)
        
        # 更新持仓
        if ts_code in self.positions:
            pos = self.positions[ts_code]
            total_cost = pos['volume'] * pos['avg_price'] + trade.total_cost
            total_volume = pos['volume'] + volume
            pos['avg_price'] = total_cost / total_volume
            pos['volume'] = total_volume
            pos['cost_basis'] = total_cost
        else:
            self.positions[ts_code] = {
                'ts_code': ts_code,
                'stock_name': stock_name,
                'volume': volume,
                'avg_price': price,
                'cost_basis': trade.total_cost
            }
        
        self.save_state()
        
        print(f"✅ 买入 {stock_name} ({ts_code}): {volume}股 @ ¥{price:.2f}, 手续费 ¥{commission:.2f}")
        return trade
    
    def sell(self, ts_code: str, volume: int, price: Optional[float] = None,
             order_id: Optional[str] = None, trade_date: Optional[str] = None) -> Optional[Trade]:
        """卖出操作"""
        if ts_code not in self.positions:
            print(f"❌ 不持有 {ts_code}")
            return None
        
        pos = self.positions[ts_code]
        if pos['volume'] < volume:
            print(f"❌ 持仓不足！持有 {pos['volume']}股，卖出 {volume}股")
            return None
        
        if price is None:
            price, trade_date = self.get_latest_price(ts_code)
            if price is None:
                return None
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 计算手续费
        commission = max(5.0, price * volume * 0.0003)
        commission += price * volume * 0.001  # 印花税千分之一
        
        # 创建交易记录
        self.trade_counter += 1
        self.order_counter += 1
        
        trade = Trade(
            trade_id=f"T{self.trade_counter:06d}",
            order_id=order_id or f"S{self.order_counter:06d}",
            ts_code=ts_code,
            stock_name=pos['stock_name'],
            direction='sell',
            price=price,
            volume=volume,
            timestamp=datetime.now().isoformat(),
            commission=commission,
            trade_date=trade_date
        )
        
        # 更新账户
        self.cash += (price * volume - commission)
        self.trades.append(trade)
        
        # 更新持仓
        pos['volume'] -= volume
        if pos['volume'] == 0:
            del self.positions[ts_code]
        else:
            pos['cost_basis'] = pos['avg_price'] * pos['volume']
        
        self.save_state()
        
        print(f"✅ 卖出 {pos['stock_name']} ({ts_code}): {volume}股 @ ¥{price:.2f}, 手续费 ¥{commission:.2f}")
        return trade
    
    def update_positions(self) -> dict:
        """更新持仓盈亏"""
        updated = {}
        
        for ts_code, pos in self.positions.items():
            current_price, trade_date = self.get_latest_price(ts_code)
            if current_price is None:
                continue
            
            market_value = current_price * pos['volume']
            profit = market_value - pos['cost_basis']
            return_pct = profit / pos['cost_basis'] * 100
            
            updated[ts_code] = {
                **pos,
                'current_price': current_price,
                'market_value': market_value,
                'profit': profit,
                'return_pct': return_pct,
                'trade_date': trade_date
            }
        
        return updated
    
    def get_portfolio_summary(self) -> dict:
        """获取账户汇总"""
        positions = self.update_positions()
        
        position_value = sum(p['market_value'] for p in positions.values())
        total_cost = sum(p['cost_basis'] for p in positions.values())
        total_profit = sum(p['profit'] for p in positions.values())
        total_value = self.cash + position_value
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'position_value': position_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_return_pct': (total_value - self.initial_cash) / self.initial_cash * 100,
            'position_count': len(positions),
            'positions': list(positions.values()),
            'trade_count': len(self.trades),
            'update_time': datetime.now().isoformat()
        }
    
    def create_snapshot(self):
        """创建账户快照"""
        summary = self.get_portfolio_summary()
        
        snapshot = PortfolioSnapshot(
            date=datetime.now().strftime('%Y%m%d'),
            total_value=summary['total_value'],
            cash=summary['cash'],
            position_value=summary['position_value'],
            total_profit=summary['total_profit'],
            total_return_pct=summary['total_return_pct'],
            position_count=summary['position_count']
        )
        
        self.snapshots.append(snapshot)
        self.save_state()
        
        return snapshot
    
    def print_report(self):
        """打印交易报告"""
        print("=" * 80)
        print(" " * 30 + "📊 模拟交易账户报告")
        print("=" * 80)
        print()
        
        summary = self.get_portfolio_summary()
        
        print("【账户总览】")
        print(f"  初始资金：  ¥{self.initial_cash:>14,.2f}")
        print(f"  总资产：    ¥{summary['total_value']:>14,.2f}")
        print(f"  可用现金：  ¥{summary['cash']:>14,.2f}")
        print(f"  持仓市值：  ¥{summary['position_value']:>14,.2f}")
        print(f"  累计盈亏：  ¥{summary['total_profit']:>14,.2f}")
        print(f"  累计收益率：{summary['total_return_pct']:>+13.2f}%")
        print(f"  持仓数量：  {summary['position_count']:>14} 只")
        print(f"  交易笔数：  {summary['trade_count']:>14} 笔")
        print()
        
        print("【持仓明细】")
        if summary['positions']:
            for pos in summary['positions']:
                print(f"\n  {pos['stock_name']} ({pos['ts_code']})")
                print(f"    持仓：  {pos['volume']:>10,} 股")
                print(f"    成本：  ¥{pos['avg_price']:>10.2f}")
                print(f"    现价：  ¥{pos['current_price']:>10.2f}")
                print(f"    市值：  ¥{pos['market_value']:>12,.2f}")
                print(f"    盈亏：  ¥{pos['profit']:>12,.2f} ({pos['return_pct']:>+6.2f}%)")
        else:
            print("  无持仓")
        print()
        
        print("【最近交易】")
        if self.trades:
            for trade in self.trades[-5:]:
                direction = "买入" if trade.direction == 'buy' else "卖出"
                print(f"  {trade.trade_date} {direction} {trade.stock_name} {trade.volume}股 @ ¥{trade.price:.2f}")
        else:
            print("  无交易记录")
        print()
        
        print("=" * 80)


def main():
    """主函数 - 演示模拟交易"""
    print("=" * 80)
    print(" " * 25 + "VNPy 模拟交易系统")
    print("=" * 80)
    print()
    
    # 创建模拟账户
    account = PaperTradingAccount(initial_cash=1000000.0)
    
    # 打印当前状态
    account.print_report()
    
    # 保存汇总到文件
    summary = account.get_portfolio_summary()
    output_file = Path('paper_trading_demo/portfolio_summary.json')
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 账户汇总已保存到：{output_file}")


if __name__ == "__main__":
    main()
