#!/usr/bin/env python3
"""
虚拟账户模拟交易系统

功能:
- 虚拟账户管理 (初始资金可配置)
- 每日自动交易
- 实时持仓跟踪
- 每日/每周复盘
- 交易记录保存
- 收益曲线生成
"""

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
import random


@dataclass
class Position:
    """持仓"""
    symbol: str
    name: str
    volume: int
    avg_price: float
    cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    profit: float = 0.0
    profit_rate: float = 0.0


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    symbol: str
    name: str
    direction: str  # buy/sell
    volume: int
    price: float
    amount: float
    fee: float
    datetime: str
    reason: str = ""


@dataclass
class DailyAccount:
    """每日账户快照"""
    date: str
    cash: float
    total_value: float
    market_value: float
    daily_return: float
    daily_return_rate: float
    positions_count: int
    buy_count: int
    sell_count: int
    positions: List[Dict] = field(default_factory=list)


class VirtualAccount:
    """虚拟账户"""
    
    def __init__(self, initial_capital: float = 1000000, account_id: str = "default"):
        self.account_id = account_id
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_snapshots: List[DailyAccount] = []
        
        # 配置
        self.commission_rate = 0.0003  # 万三手续费
        self.slippage_rate = 0.001     # 千一滑点
        self.min_commission = 5        # 最低 5 元
        
        # 数据目录
        self.data_dir = Path('./data/akshare/bars')
        self.account_dir = Path('./accounts')
        self.account_dir.mkdir(parents=True, exist_ok=True)
        
        # 股票名称缓存
        self.stock_names: Dict[str, str] = {}
        self._load_stock_names()
        
        # 加载已有账户 (如果存在)
        self._load_account()
    
    def _load_stock_names(self):
        """加载股票名称"""
        name_file = Path('./data/akshare/stock_names.json')
        if name_file.exists():
            with open(name_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stock_names = {item['code']: item['name'] for item in data.get('stocks', [])}
    
    def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称"""
        code = symbol.split('.')[0]
        return self.stock_names.get(code, "")
    
    def _load_account(self):
        """加载已有账户"""
        account_file = self.account_dir / f'{self.account_id}_account.json'
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cash = data.get('cash', self.initial_capital)
                self.trades = [Trade(**t) for t in data.get('trades', [])]
                self.daily_snapshots = [DailyAccount(**s) for s in data.get('daily_snapshots', [])]
                
                # 恢复持仓
                for pos_data in data.get('positions', []):
                    pos = Position(**pos_data)
                    self.positions[pos.symbol] = pos
                
                print(f"✅ 加载账户：{self.account_id}")
                print(f"   现金：¥{self.cash:,.2f}")
                print(f"   持仓：{len(self.positions)} 只")
                print(f"   交易：{len(self.trades)} 笔")
    
    def _save_account(self):
        """保存账户"""
        account_file = self.account_dir / f'{self.account_id}_account.json'
        
        data = {
            'account_id': self.account_id,
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': [asdict(p) for p in self.positions.values()],
            'trades': [asdict(t) for t in self.trades],
            'daily_snapshots': [asdict(s) for s in self.daily_snapshots],
            'last_update': datetime.now().isoformat()
        }
        
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def buy(self, symbol: str, price: float, volume: int, date: str, reason: str = "") -> Optional[Trade]:
        """买入"""
        name = self._get_stock_name(symbol)
        
        # 计算滑点和费用
        exec_price = price * (1 + self.slippage_rate)
        amount = exec_price * volume
        fee = max(self.min_commission, amount * self.commission_rate)
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
                name=name,
                volume=volume,
                avg_price=exec_price,
                cost=amount
            )
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{len(self.trades)+1:06d}",
            symbol=symbol,
            name=name,
            direction='buy',
            volume=volume,
            price=exec_price,
            amount=amount,
            fee=fee,
            datetime=date,
            reason=reason
        )
        self.trades.append(trade)
        
        return trade
    
    def sell(self, symbol: str, price: float, volume: int, date: str, reason: str = "") -> Optional[Trade]:
        """卖出"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        if pos.volume < volume:
            return None
        
        name = pos.name
        
        # 计算滑点和费用
        exec_price = price * (1 - self.slippage_rate)
        amount = exec_price * volume
        fee = max(self.min_commission, amount * self.commission_rate)
        net_amount = amount - fee
        
        # 更新现金
        self.cash += net_amount
        
        # 更新持仓
        pos.volume -= volume
        if pos.volume == 0:
            del self.positions[symbol]
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{len(self.trades)+1:06d}",
            symbol=symbol,
            name=name,
            direction='sell',
            volume=volume,
            price=exec_price,
            amount=amount,
            fee=fee,
            datetime=date,
            reason=reason
        )
        self.trades.append(trade)
        
        return trade
    
    def update_positions(self, current_prices: Dict[str, float]):
        """更新持仓市值"""
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                pos.current_price = current_prices[symbol]
                pos.market_value = pos.volume * pos.current_price
                pos.profit = pos.market_value - pos.cost
                pos.profit_rate = pos.profit / pos.cost * 100 if pos.cost > 0 else 0
    
    def get_total_value(self) -> float:
        """计算账户总值"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + market_value
    
    def generate_daily_snapshot(self, date: str, buy_count: int = 0, sell_count: int = 0):
        """生成每日快照"""
        self.update_positions({})  # 更新持仓
        
        total_value = self.get_total_value()
        market_value = sum(pos.market_value for pos in self.positions.values())
        
        # 计算当日收益
        if self.daily_snapshots:
            prev_value = self.daily_snapshots[-1].total_value
            daily_return = total_value - prev_value
            daily_return_rate = daily_return / prev_value * 100 if prev_value > 0 else 0
        else:
            daily_return = total_value - self.initial_capital
            daily_return_rate = daily_return / self.initial_capital * 100 if self.initial_capital > 0 else 0
        
        snapshot = DailyAccount(
            date=date,
            cash=round(self.cash, 2),
            total_value=round(total_value, 2),
            market_value=round(market_value, 2),
            daily_return=round(daily_return, 2),
            daily_return_rate=round(daily_return_rate, 2),
            positions_count=len(self.positions),
            buy_count=buy_count,
            sell_count=sell_count,
            positions=[asdict(p) for p in self.positions.values()]
        )
        
        self.daily_snapshots.append(snapshot)
        self._save_account()
        
        return snapshot
    
    def get_performance(self) -> dict:
        """获取业绩统计"""
        if not self.daily_snapshots:
            return {}
        
        final = self.daily_snapshots[-1]
        total_return = final.total_value - self.initial_capital
        total_return_rate = total_return / self.initial_capital * 100
        
        daily_returns = [s.daily_return_rate for s in self.daily_snapshots]
        avg_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
        max_daily_return = max(daily_returns) if daily_returns else 0
        min_daily_return = min(daily_returns) if daily_returns else 0
        
        # 计算最大回撤
        peak = self.initial_capital
        max_drawdown = 0
        for snapshot in self.daily_snapshots:
            if snapshot.total_value > peak:
                peak = snapshot.total_value
            drawdown = (peak - snapshot.total_value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'initial_capital': self.initial_capital,
            'current_value': final.total_value,
            'total_return': round(total_return, 2),
            'total_return_rate': round(total_return_rate, 2),
            'trading_days': len(self.daily_snapshots),
            'avg_daily_return': round(avg_daily_return, 2),
            'max_daily_return': round(max_daily_return, 2),
            'min_daily_return': round(min_daily_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'total_trades': len(self.trades),
            'current_positions': len(self.positions)
        }


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "虚拟账户模拟交易系统")
    print("=" * 70)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建虚拟账户
    account = VirtualAccount(
        initial_capital=1000000,
        account_id="virtual_2026"
    )
    
    print(f"账户 ID: {account.account_id}")
    print(f"初始资金：¥{account.initial_capital:,.0f}")
    print(f"当前现金：¥{account.cash:,.2f}")
    print(f"当前持仓：{len(account.positions)} 只")
    print(f"总交易：{len(account.trades)} 笔")
    print()
    
    # 显示业绩
    perf = account.get_performance()
    if perf:
        print("【业绩统计】")
        print(f"  当前总值：¥{perf['current_value']:,.2f}")
        print(f"  总收益：¥{perf['total_return']:,.2f}")
        print(f"  总收益率：{perf['total_return_rate']:+.2f}%")
        print(f"  交易天数：{perf['trading_days']} 天")
        print(f"  最大回撤：{perf['max_drawdown']:.2f}%")
        print()
    
    # 保存账户
    account._save_account()
    print(f"✅ 账户已保存：accounts/{account.account_id}_account.json")
    print()
    
    print("=" * 70)


if __name__ == '__main__':
    main()
