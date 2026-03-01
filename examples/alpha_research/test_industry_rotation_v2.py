"""
行业轮动策略 V2 - 优化版

改进：
1. 放宽估值筛选（使用相对估值）
2. 增加动量权重
3. 优化调仓逻辑
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random

import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


# 行业定义
INDUSTRY_STOCKS = {
    "bank": ["600000.SSE", "600016.SSE", "600036.SSE", "601166.SSE", "601288.SSE"],
    "securities": ["600030.SSE", "601066.SSE", "601688.SSE"],
    "liquor": ["600519.SSE", "000568.SZSE", "000858.SZSE"],
    "food": ["000895.SZSE", "600887.SSE"],
    "appliance": ["000333.SZSE", "000651.SZSE", "600690.SSE"],
    "medicine": ["000538.SZSE", "002007.SZSE", "600276.SSE"],
    "new_energy": ["002594.SZSE", "300750.SZSE", "601012.SSE"],
    "tech": ["000063.SZSE", "002230.SZSE", "300059.SZSE"],
}


class IndustryRotationStrategyV2:
    """
    行业轮动策略 V2
    
    核心逻辑：
    1. 选择动量最强的 3 个行业
    2. 在热门行业中选择相对低估值股票（行业内比较）
    3. 等权重配置
    4. 每 5 天调仓
    """
    
    def __init__(self, setting: dict = None):
        self.setting = setting or {}
        self.lookback = self.setting.get("lookback", 20)
        self.top_industries = self.setting.get("top_industries", 3)
        self.stocks_per_industry = self.setting.get("stocks_per_industry", 3)
        self.rebalance_days = self.setting.get("rebalance_days", 5)
        
        self.last_rebalance: Optional[datetime] = None
        self.holdings: List[str] = []
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def should_rebalance(self, current_date: datetime) -> bool:
        if self.last_rebalance is None:
            return True
        days = (current_date - self.last_rebalance).days
        return days >= self.rebalance_days
    
    def update_price_history(self, bars: Dict[str, BarData]):
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            self.price_history[vt_symbol].append((bar.datetime, bar.close_price))
            if len(self.price_history[vt_symbol]) > 60:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-60:]
    
    def calculate_momentum(self, vt_symbol: str) -> float:
        """计算个股动量"""
        if vt_symbol not in self.price_history:
            return 0.0
        history = self.price_history[vt_symbol]
        if len(history) < self.lookback:
            return 0.0
        
        old_price = history[-self.lookback][1]
        current_price = history[-1][1]
        
        if old_price > 0:
            return (current_price - old_price) / old_price * 100
        return 0.0
    
    def calculate_industry_momentum(self, industry: str) -> float:
        """计算行业动量"""
        stocks = INDUSTRY_STOCKS.get(industry, [])
        returns = []
        
        for vt_symbol in stocks:
            ret = self.calculate_momentum(vt_symbol)
            returns.append(ret)
        
        return sum(returns) / len(returns) if returns else 0.0
    
    def select_hot_industries(self, bars: Dict[str, BarData]) -> List[str]:
        """选择热门行业（纯动量排序）"""
        industry_momentum = []
        
        for industry in INDUSTRY_STOCKS.keys():
            momentum = self.calculate_industry_momentum(industry)
            industry_momentum.append((industry, momentum))
        
        # 按动量排序
        industry_momentum.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 个
        return [ind[0] for ind in industry_momentum[:self.top_industries]]
    
    def select_stocks_in_industry(self, industry: str, bars: Dict[str, BarData]) -> List[str]:
        """
        在行业内选择股票
        
        逻辑：
        1. 计算行业内相对估值（PE/PB 分位数）
        2. 结合动量排序
        3. 选择综合得分最高的
        """
        stocks = INDUSTRY_STOCKS.get(industry, [])
        candidates = []
        
        for vt_symbol in stocks:
            if vt_symbol not in bars:
                continue
            
            # 动量
            momentum = self.calculate_momentum(vt_symbol)
            
            # 相对估值（简化：使用随机模拟，实际应从财务数据获取）
            random.seed(hash(vt_symbol) % 1000)
            pe_percentile = random.uniform(0.2, 0.8)  # PE 分位数（越低越好）
            
            # 综合得分：动量 50% + 估值 50%
            score = momentum * 0.5 + (1 - pe_percentile) * 30 * 0.5
            
            candidates.append((vt_symbol, score, momentum, pe_percentile))
        
        # 按得分排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 只
        return [c[0] for c in candidates[:self.stocks_per_industry]]
    
    def on_bars(self, bars: Dict[str, BarData], current_date: datetime) -> List[str]:
        self.update_price_history(bars)
        
        if not self.should_rebalance(current_date):
            return self.holdings
        
        # 选择热门行业
        hot_industries = self.select_hot_industries(bars)
        
        # 在每个热门行业中选股
        selected = []
        for industry in hot_industries:
            stocks = self.select_stocks_in_industry(industry, bars)
            selected.extend(stocks)
        
        self.holdings = selected
        self.last_rebalance = current_date
        
        return selected


class SimpleBacktestEngine:
    def __init__(self, capital: float = 1_000_000):
        self.capital = capital
        self.cash = capital
        self.positions: Dict[str, float] = {}
        self.daily_values = []
        self.datetime: Optional[datetime] = None
        self.trades = []
    
    def get_pos(self, vt_symbol: str) -> float:
        return self.positions.get(vt_symbol, 0.0)
    
    def get_portfolio_value(self) -> float:
        global history_data
        stock_value = 0.0
        for vt_symbol, volume in self.positions.items():
            if volume > 0 and self.datetime:
                key = (self.datetime, vt_symbol)
                if key in history_data:
                    stock_value += history_data[key].close_price * volume
        return self.cash + stock_value
    
    def rebalance_to(self, target_holdings: List[str], bars: Dict[str, BarData]):
        if not target_holdings:
            return
        
        portfolio_value = self.get_portfolio_value()
        target_per_stock = portfolio_value / len(target_holdings)
        
        for vt_symbol in target_holdings:
            if vt_symbol not in bars:
                continue
            
            bar = bars[vt_symbol]
            target_volume = target_per_stock / bar.close_price
            current_pos = self.get_pos(vt_symbol)
            
            if target_volume > current_pos * 1.05:
                volume = target_volume - current_pos
                cost = bar.close_price * volume
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[vt_symbol] = target_volume
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "买入",
                        "volume": volume,
                        "price": bar.close_price
                    })
            
            elif target_volume < current_pos * 0.95:
                volume = current_pos - target_volume
                if volume > 0:
                    revenue = bar.close_price * volume
                    self.cash += revenue
                    self.positions[vt_symbol] = target_volume
                    self.trades.append({
                        "datetime": self.datetime,
                        "vt_symbol": vt_symbol,
                        "direction": "卖出",
                        "volume": volume,
                        "price": bar.close_price
                    })
    
    def record_daily_value(self, bars: Dict[str, BarData]):
        if not self.datetime:
            return
        
        stock_value = sum(
            bars[vt_symbol].close_price * volume
            for vt_symbol, volume in self.positions.items()
            if vt_symbol in bars and volume > 0
        )
        
        self.daily_values.append({
            "datetime": self.datetime,
            "total_value": self.cash + stock_value
        })


def load_data(data_path: Path):
    print("\n📊 加载数据...")
    daily_path = data_path / "daily"
    
    vt_symbols = []
    history = {}
    dts = set()
    
    for file_path in daily_path.glob("*.parquet"):
        df = pl.read_parquet(file_path)
        vt_symbol = df["vt_symbol"][0]
        vt_symbols.append(vt_symbol)
        
        for row in df.iter_rows(named=True):
            dt = row["datetime"]
            dts.add(dt)
            exchange = Exchange.SSE if "SSE" in vt_symbol else Exchange.SZSE
            
            bar = BarData(
                symbol=vt_symbol.split(".")[0],
                exchange=exchange,
                datetime=dt,
                interval=Interval.DAILY,
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=0,
                gateway_name="MOCK"
            )
            
            history[(dt, vt_symbol)] = bar
    
    print(f"  股票数量：{len(vt_symbols)}")
    print(f"  交易日数：{len(dts)}")
    
    return vt_symbols, history, dts


history_data = {}


def run_backtest():
    print("=" * 60)
    print("行业轮动策略 V2（动量 + 相对估值）")
    print("=" * 60)
    
    data_path = Path("./data_real")
    vt_symbols, history_data_g, dts = load_data(data_path)
    
    global history_data
    history_data = history_data_g
    
    print("\n📊 策略参数:")
    print(f"  动量回看：20 天")
    print(f"  热门行业：前 3 个")
    print(f"  每行业选股：3 只")
    print(f"  调仓周期：5 天")
    
    strategy = IndustryRotationStrategyV2(setting={
        "lookback": 20,
        "top_industries": 3,
        "stocks_per_industry": 3,
        "rebalance_days": 5
    })
    
    engine = SimpleBacktestEngine(capital=1_000_000)
    
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 100 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if bars:
            target_holdings = strategy.on_bars(bars, dt)
            engine.rebalance_to(target_holdings, bars)
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if engine.daily_values:
        initial = engine.daily_values[0]["total_value"]
        final = engine.daily_values[-1]["total_value"]
        total_return = (final - initial) / initial * 100
        
        max_dd = 0
        peak = initial
        for daily in engine.daily_values:
            value = daily["total_value"]
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        years = len(sorted_dts) / 240
        annual_return = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        print(f"  初始资金：{initial:,.0f}")
        print(f"  最终价值：{final:,.0f}")
        print(f"  总收益率：{total_return:.2f}%")
        print(f"  年化收益率：{annual_return:.2f}%")
        print(f"  最大回撤：{max_dd:.2f}%")
        print(f"  交易次数：{len(engine.trades)}")
        
        final_holdings = [k for k, v in engine.positions.items() if v > 0]
        print(f"  最终持仓：{len(final_holdings)}只")
    
    print("=" * 60)
    return engine


if __name__ == "__main__":
    run_backtest()
