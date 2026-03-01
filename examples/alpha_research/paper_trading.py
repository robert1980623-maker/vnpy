"""
股票模拟交易组合管理

功能：
- 模拟股票交易（买入/卖出）
- 持仓管理
- 盈亏计算
- 交易记录
- 绩效统计
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class Position:
    """持仓信息"""
    vt_symbol: str
    volume: float = 0.0
    avg_price: float = 0.0  # 平均成本价
    frozen_volume: float = 0.0  # 冻结数量（挂单中）
    
    @property
    def available_volume(self) -> float:
        """可用数量"""
        return self.volume - self.frozen_volume
    
    @property
    def cost(self) -> float:
        """持仓成本"""
        return self.volume * self.avg_price


@dataclass
class Order:
    """委托订单"""
    order_id: str
    vt_symbol: str
    direction: str  # "buy" or "sell"
    price: float
    volume: float
    timestamp: datetime
    status: str = "pending"  # pending, filled, cancelled, rejected
    filled_volume: float = 0.0
    filled_price: float = 0.0
    message: str = ""


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    vt_symbol: str
    direction: str
    price: float
    volume: float
    timestamp: datetime
    commission: float = 0.0  # 手续费


class PaperTradingAccount:
    """模拟交易账户"""
    
    def __init__(self, initial_capital: float = 1_000_000.0, 
                 data_dir: str = "./data/akshare/bars",
                 commission_rate: float = 0.0003,  # 万分之三
                 slippage: float = 0.01):  # 1% 滑点
        """
        Args:
            initial_capital: 初始资金
            data_dir: K 线数据目录
            commission_rate: 手续费率
            slippage: 滑点（0-1 之间）
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.data_dir = Path(data_dir)
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # 数据缓存
        self.price_cache: Dict[str, pd.DataFrame] = {}
        
        # 持仓、委托、成交
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        
        # 计数器
        self.order_counter = 0
        self.trade_counter = 0
        
        # 交易日期
        self.current_date: Optional[datetime] = None
        
        print(f"✓ 模拟交易账户已初始化")
        print(f"  初始资金：¥{initial_capital:,.2f}")
        print(f"  手续费率：{commission_rate*100:.2f}%")
        print(f"  滑点：{slippage*100:.1f}%")
    
    def load_price_data(self, vt_symbol: str, start_date: datetime = None, end_date: datetime = None):
        """加载 K 线数据"""
        # 扩大默认日期范围
        if start_date is None:
            start_date = datetime(2024, 1, 1)
        if end_date is None:
            end_date = datetime(2026, 12, 31)
        
        # 查找数据文件（支持两种路径）
        symbol = vt_symbol.split(".")[0]
        
        # 尝试多个可能的路径
        possible_paths = [
            self.data_dir / f"{symbol}.csv",
            self.data_dir / "bars" / f"{symbol}.csv",
            Path("./data/mock") / f"{symbol}.csv",
        ]
        
        data_file = None
        for path in possible_paths:
            if path.exists():
                data_file = path
                break
        
        if data_file is None:
            print(f"⚠️ 数据文件不存在：{symbol}.csv")
            return None
        
        try:
            df = pd.read_csv(data_file)
            
            # 自动检测列名格式
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'date' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'])
            
            # 筛选日期范围
            if len(df) > 0 and 'datetime' in df.columns:
                df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
            
            if len(df) > 0:
                self.price_cache[vt_symbol] = df
                print(f"✓ 加载 {vt_symbol} 数据：{len(df)} 条")
                return df
            else:
                print(f"✗ {vt_symbol} 数据为空")
                return None
        except Exception as e:
            print(f"✗ 加载数据失败：{e}")
            return None
    
    def get_current_price(self, vt_symbol: str) -> Optional[float]:
        """获取当前价格（最新收盘价）"""
        if vt_symbol not in self.price_cache:
            self.load_price_data(vt_symbol)
        
        if vt_symbol in self.price_cache:
            df = self.price_cache[vt_symbol]
            if len(df) > 0:
                return df.iloc[-1]['close_price']
        return None
    
    def get_price_on_date(self, vt_symbol: str, date: datetime) -> Optional[float]:
        """获取指定日期的价格"""
        if vt_symbol not in self.price_cache:
            self.load_price_data(vt_symbol)
        
        if vt_symbol in self.price_cache:
            df = self.price_cache[vt_symbol]
            df_date = df[df['datetime'].dt.date == date.date()]
            if len(df_date) > 0:
                return df_date.iloc[-1]['close_price']
        return None
    
    def buy(self, vt_symbol: str, volume: float, price: float = None, 
            order_type: str = "market") -> Optional[str]:
        """
        买入委托
        
        Args:
            vt_symbol: 股票代码
            volume: 数量（股）
            price: 价格（市价单可不填）
            order_type: 订单类型 (market/limit)
            
        Returns:
            order_id: 委托编号
        """
        # 检查数据
        if vt_symbol not in self.price_cache:
            self.load_price_data(vt_symbol)
        
        # 获取价格
        if price is None:
            price = self.get_current_price(vt_symbol)
            if price is None:
                print(f"✗ 无法获取 {vt_symbol} 价格")
                return None
        
        # 计算成交价格（考虑滑点）
        if order_type == "market":
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price
        
        # 计算总成本
        total_cost = fill_price * volume * (1 + self.commission_rate)
        
        # 检查资金
        if total_cost > self.capital:
            print(f"✗ 资金不足：需要 ¥{total_cost:,.2f}, 可用 ¥{self.capital:,.2f}")
            return None
        
        # 创建委托
        self.order_counter += 1
        order_id = f"BUY{self.order_counter:06d}"
        
        order = Order(
            order_id=order_id,
            vt_symbol=vt_symbol,
            direction="buy",
            price=price,
            volume=volume,
            timestamp=datetime.now(),
            status="filled",
            filled_volume=volume,
            filled_price=fill_price
        )
        
        self.orders[order_id] = order
        
        # 创建成交记录
        self.trade_counter += 1
        trade_id = f"TRADE{self.trade_counter:06d}"
        commission = fill_price * volume * self.commission_rate
        
        trade = Trade(
            trade_id=trade_id,
            order_id=order_id,
            vt_symbol=vt_symbol,
            direction="buy",
            price=fill_price,
            volume=volume,
            timestamp=datetime.now(),
            commission=commission
        )
        
        self.trades.append(trade)
        
        # 更新持仓
        if vt_symbol not in self.positions:
            self.positions[vt_symbol] = Position(vt_symbol=vt_symbol)
        
        pos = self.positions[vt_symbol]
        old_cost = pos.cost
        new_cost = fill_price * volume * (1 + self.commission_rate)
        
        pos.volume += volume
        pos.avg_price = (old_cost + new_cost) / pos.volume
        
        # 更新资金
        self.capital -= total_cost
        
        print(f"✓ 买入 {vt_symbol}: {volume}股 @ ¥{fill_price:.2f} (滑点后)")
        print(f"  手续费：¥{commission:.2f}")
        print(f"  总成本：¥{total_cost:,.2f}")
        print(f"  剩余资金：¥{self.capital:,.2f}")
        
        return order_id
    
    def sell(self, vt_symbol: str, volume: float, price: float = None,
             order_type: str = "market") -> Optional[str]:
        """
        卖出委托
        
        Args:
            vt_symbol: 股票代码
            volume: 数量（股）
            price: 价格
            order_type: 订单类型
            
        Returns:
            order_id: 委托编号
        """
        # 检查持仓
        if vt_symbol not in self.positions:
            print(f"✗ 无 {vt_symbol} 持仓")
            return None
        
        pos = self.positions[vt_symbol]
        if pos.available_volume < volume:
            print(f"✗ 可用数量不足：可用 {pos.available_volume}, 需要 {volume}")
            return None
        
        # 获取价格
        if price is None:
            price = self.get_current_price(vt_symbol)
            if price is None:
                print(f"✗ 无法获取 {vt_symbol} 价格")
                return None
        
        # 计算成交价格（考虑滑点）
        if order_type == "market":
            fill_price = price * (1 - self.slippage)
        else:
            fill_price = price
        
        # 计算收入
        total_income = fill_price * volume * (1 - self.commission_rate)
        
        # 创建委托
        self.order_counter += 1
        order_id = f"SELL{self.order_counter:06d}"
        
        order = Order(
            order_id=order_id,
            vt_symbol=vt_symbol,
            direction="sell",
            price=price,
            volume=volume,
            timestamp=datetime.now(),
            status="filled",
            filled_volume=volume,
            filled_price=fill_price
        )
        
        self.orders[order_id] = order
        
        # 创建成交记录
        self.trade_counter += 1
        trade_id = f"TRADE{self.trade_counter:06d}"
        commission = fill_price * volume * self.commission_rate
        
        trade = Trade(
            trade_id=trade_id,
            order_id=order_id,
            vt_symbol=vt_symbol,
            direction="sell",
            price=fill_price,
            volume=volume,
            timestamp=datetime.now(),
            commission=commission
        )
        
        self.trades.append(trade)
        
        # 更新持仓
        pos.volume -= volume
        if pos.volume == 0:
            pos.avg_price = 0
        
        # 更新资金
        self.capital += total_income
        
        print(f"✓ 卖出 {vt_symbol}: {volume}股 @ ¥{fill_price:.2f} (滑点后)")
        print(f"  手续费：¥{commission:.2f}")
        print(f"  总收入：¥{total_income:,.2f}")
        print(f"  剩余资金：¥{self.capital:,.2f}")
        
        return order_id
    
    def get_position(self, vt_symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(vt_symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions
    
    def get_portfolio_value(self) -> float:
        """计算组合总市值"""
        total = self.capital
        
        for vt_symbol, pos in self.positions.items():
            if pos.volume > 0:
                current_price = self.get_current_price(vt_symbol)
                if current_price:
                    total += current_price * pos.volume
        
        return total
    
    def get_portfolio_summary(self) -> dict:
        """获取组合概览"""
        total_value = self.get_portfolio_value()
        total_profit = total_value - self.initial_capital
        total_return = (total_profit / self.initial_capital) * 100
        
        positions_info = []
        for vt_symbol, pos in self.positions.items():
            if pos.volume > 0:
                current_price = self.get_current_price(vt_symbol)
                if current_price:
                    market_value = current_price * pos.volume
                    cost = pos.cost
                    profit = market_value - cost
                    return_pct = (profit / cost) * 100 if cost > 0 else 0
                    
                    positions_info.append({
                        'vt_symbol': vt_symbol,
                        'volume': pos.volume,
                        'avg_price': pos.avg_price,
                        'current_price': current_price,
                        'market_value': market_value,
                        'cost': cost,
                        'profit': profit,
                        'return_pct': return_pct
                    })
        
        return {
            'total_value': total_value,
            'capital': self.capital,
            'total_profit': total_profit,
            'total_return_pct': total_return,
            'positions': positions_info,
            'position_count': len(positions_info)
        }
    
    def print_portfolio_summary(self):
        """打印组合概览"""
        summary = self.get_portfolio_summary()
        
        print("\n" + "=" * 70)
        print("模拟交易组合概览")
        print("=" * 70)
        print(f"初始资金：¥{self.initial_capital:,.2f}")
        print(f"当前总值：¥{summary['total_value']:,.2f}")
        print(f"可用资金：¥{summary['capital']:,.2f}")
        print(f"总盈亏：¥{summary['total_profit']:,.2f} ({summary['total_return_pct']:+.2f}%)")
        print(f"持仓数量：{summary['position_count']}")
        
        if summary['positions']:
            print("\n持仓明细:")
            print(f"{'代码':<12} {'数量':>10} {'成本':>10} {'现价':>10} {'市值':>12} {'盈亏':>12} {'收益率':>10}")
            print("-" * 70)
            
            for pos in summary['positions']:
                print(f"{pos['vt_symbol']:<12} {pos['volume']:>10.0f} {pos['avg_price']:>10.2f} "
                      f"{pos['current_price']:>10.2f} {pos['market_value']:>12.2f} "
                      f"{pos['profit']:>+12.2f} {pos['return_pct']:>+9.2f}%")
        
        print("=" * 70)
    
    def get_trade_history(self) -> pd.DataFrame:
        """获取成交历史"""
        if not self.trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.trades:
            data.append({
                'trade_id': trade.trade_id,
                'order_id': trade.order_id,
                'vt_symbol': trade.vt_symbol,
                'direction': trade.direction,
                'price': trade.price,
                'volume': trade.volume,
                'timestamp': trade.timestamp,
                'commission': trade.commission
            })
        
        df = pd.DataFrame(data)
        return df
    
    def save_to_file(self, output_dir: str = "./paper_trading"):
        """保存交易记录到文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存持仓
        positions_file = output_dir / "positions.json"
        positions_data = {
            vt_symbol: {
                'volume': pos.volume,
                'avg_price': pos.avg_price
            }
            for vt_symbol, pos in self.positions.items()
        }
        with open(positions_file, 'w', encoding='utf-8') as f:
            json.dump(positions_data, f, ensure_ascii=False, indent=2)
        
        # 保存成交记录
        trades_file = output_dir / "trades.csv"
        df = self.get_trade_history()
        if len(df) > 0:
            df.to_csv(trades_file, index=False)
        
        # 保存组合概览
        summary_file = output_dir / "portfolio_summary.json"
        summary = self.get_portfolio_summary()
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✓ 交易记录已保存到：{output_dir}")
        print(f"  - 持仓：{positions_file}")
        print(f"  - 成交：{trades_file}")
        print(f"  - 概览：{summary_file}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 70)
    print("股票模拟交易测试")
    print("=" * 70)
    
    # 1. 创建模拟账户
    account = PaperTradingAccount(
        initial_capital=1_000_000.0,
        data_dir="./data/akshare/bars",
        commission_rate=0.0003,
        slippage=0.01
    )
    
    # 2. 加载数据
    print("\n加载数据...")
    account.load_price_data("000001.SZ")
    account.load_price_data("600036.SH")
    account.load_price_data("600519.SH")
    
    # 3. 执行交易
    print("\n执行交易...")
    account.buy("000001.SZ", volume=10000)  # 买入平安银行
    account.buy("600036.SH", volume=5000)   # 买入招商银行
    account.buy("600519.SH", volume=1000)   # 买入贵州茅台
    
    # 4. 查看持仓
    print("\n查看持仓...")
    account.print_portfolio_summary()
    
    # 5. 卖出部分持仓
    print("\n卖出部分持仓...")
    account.sell("000001.SZ", volume=5000)
    
    # 6. 最终概览
    account.print_portfolio_summary()
    
    # 7. 查看成交历史
    print("\n成交历史:")
    df = account.get_trade_history()
    if len(df) > 0:
        print(df[['vt_symbol', 'direction', 'price', 'volume', 'commission']].to_string())
    
    # 8. 保存记录
    account.save_to_file()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
