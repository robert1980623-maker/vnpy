"""
行业轮动策略 - 独立测试版

不依赖 vnpy 完整环境，直接测试策略逻辑
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
import random

import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.object import BarData


# ========== 行业定义 ==========

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

# 行业估值基准
INDUSTRY_VALUATION = {
    "bank": (5.0, 0.6, 3.5),      # PE, PB, 股息率
    "securities": (12.0, 1.2, 2.0),
    "liquor": (25.0, 5.0, 1.5),
    "food": (20.0, 3.5, 2.0),
    "appliance": (12.0, 2.5, 2.5),
    "medicine": (30.0, 4.0, 1.0),
    "new_energy": (35.0, 5.5, 0.5),
    "tech": (40.0, 4.5, 0.8),
}


@dataclass
class IndustryMetrics:
    """行业指标"""
    name: str
    momentum: float
    avg_pe: float
    avg_pb: float
    dividend_yield: float
    score: float


class IndustryRotationStrategy:
    """
    行业轮动策略（独立版）
    
    逻辑：
    1. 计算行业动量（过去 20 日收益率）
    2. 选择动量最强的 3 个行业
    3. 在热门行业中选择低估值股票（PE<20, PB<3）
    4. 等权重配置
    5. 每 5 天调仓
    """
    
    def __init__(self, setting: dict = None):
        self.setting = setting or {}
        self.lookback = self.setting.get("lookback", 20)
        self.top_industries = self.setting.get("top_industries", 3)
        self.stocks_per_industry = self.setting.get("stocks_per_industry", 5)
        self.max_pe = self.setting.get("max_pe", 20)
        self.max_pb = self.setting.get("max_pb", 3)
        self.rebalance_days = self.setting.get("rebalance_days", 5)
        
        self.last_rebalance: Optional[datetime] = None
        self.holdings: List[str] = []
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def should_rebalance(self, current_date: datetime) -> bool:
        """检查是否需要调仓"""
        if self.last_rebalance is None:
            return True
        days = (current_date - self.last_rebalance).days
        return days >= self.rebalance_days
    
    def update_price_history(self, bars: Dict[str, BarData]):
        """更新价格历史"""
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            self.price_history[vt_symbol].append((bar.datetime, bar.close_price))
            if len(self.price_history[vt_symbol]) > 60:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-60:]
    
    def calculate_industry_momentum(self, industry: str) -> float:
        """计算行业动量"""
        stocks = INDUSTRY_STOCKS.get(industry, [])
        returns = []
        
        for vt_symbol in stocks:
            if vt_symbol not in self.price_history:
                continue
            history = self.price_history[vt_symbol]
            if len(history) < self.lookback:
                continue
            
            old_price = history[-self.lookback][1]
            current_price = history[-1][1]
            
            if old_price > 0:
                ret = (current_price - old_price) / old_price * 100
                returns.append(ret)
        
        return sum(returns) / len(returns) if returns else 0.0
    
    def get_industry_valuation(self, industry: str) -> Tuple[float, float, float]:
        """获取行业估值"""
        return INDUSTRY_VALUATION.get(industry, (15.0, 2.0, 1.5))
    
    def select_hot_industries(self, bars: Dict[str, BarData]) -> List[str]:
        """选择热门行业"""
        industry_scores = []
        
        for industry in INDUSTRY_STOCKS.keys():
            momentum = self.calculate_industry_momentum(industry)
            pe, pb, div = self.get_industry_valuation(industry)
            
            # 综合得分：动量 60% + 估值 40%
            momentum_score = momentum / 10  # 标准化
            valuation_score = (1 / pe) * 50 + (1 / pb) * 10
            
            score = momentum_score * 0.6 + valuation_score * 0.4
            
            industry_scores.append(IndustryMetrics(
                name=industry,
                momentum=momentum,
                avg_pe=pe,
                avg_pb=pb,
                dividend_yield=div,
                score=score
            ))
        
        # 按得分排序
        industry_scores.sort(key=lambda x: x.score, reverse=True)
        
        # 返回前 N 个
        return [ind.name for ind in industry_scores[:self.top_industries]]
    
    def select_stocks(self, industry: str, bars: Dict[str, BarData]) -> List[str]:
        """在行业中选择低估值股票"""
        stocks = INDUSTRY_STOCKS.get(industry, [])
        candidates = []
        
        pe_base, pb_base, div_base = self.get_industry_valuation(industry)
        
        for vt_symbol in stocks:
            if vt_symbol not in bars:
                continue
            
            # 添加个股差异
            random.seed(hash(vt_symbol))
            pe = pe_base * (0.7 + random.random() * 0.6)
            pb = pb_base * (0.7 + random.random() * 0.6)
            div = div_base * (0.8 + random.random() * 0.4)
            
            # 估值筛选
            if pe > self.max_pe or pb > self.max_pb:
                continue
            
            # 得分（估值越低越好）
            score = (1 / pe) * 0.5 + (1 / pb) * 0.3 + div * 0.2
            candidates.append((vt_symbol, score))
        
        # 按得分排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 只
        return [c[0] for c in candidates[:self.stocks_per_industry]]
    
    def on_bars(self, bars: Dict[str, BarData], current_date: datetime) -> List[str]:
        """处理 K 线数据，返回目标持仓"""
        # 更新价格历史
        self.update_price_history(bars)
        
        # 检查调仓
        if not self.should_rebalance(current_date):
            return self.holdings
        
        # 选择热门行业
        hot_industries = self.select_hot_industries(bars)
        
        # 在每个热门行业中选股
        selected = []
        for industry in hot_industries:
            stocks = self.select_stocks(industry, bars)
            selected.extend(stocks)
        
        self.holdings = selected
        self.last_rebalance = current_date
        
        return selected


class SimpleBacktestEngine:
    """简化回测引擎"""
    
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
        stock_value = 0.0
        for vt_symbol, volume in self.positions.items():
            if volume > 0 and self.datetime:
                key = (self.datetime, vt_symbol)
                if key in history_data:
                    stock_value += history_data[key].close_price * volume
        return self.cash + stock_value
    
    def rebalance_to(self, target_holdings: List[str], bars: Dict[str, BarData]):
        """调仓到目标持仓"""
        if not target_holdings:
            return
        
        # 计算目标仓位
        portfolio_value = self.get_portfolio_value()
        target_per_stock = portfolio_value / len(target_holdings)
        
        # 调整持仓
        for vt_symbol in target_holdings:
            if vt_symbol not in bars:
                continue
            
            bar = bars[vt_symbol]
            target_volume = target_per_stock / bar.close_price
            current_pos = self.get_pos(vt_symbol)
            
            if target_volume > current_pos * 1.05:
                # 买入
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
                # 卖出
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
        """记录每日净值"""
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


def load_data(data_path: Path) -> Tuple[List[str], Dict, set]:
    """加载数据"""
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
    print(f"  总记录数：{len(history)}")
    
    return vt_symbols, history, dts


# 全局变量（供引擎使用）
history_data = {}


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("行业轮动策略回测（热门行业 + 低估值）")
    print("=" * 60)
    
    # 1. 加载数据
    data_path = Path("./data_real")
    vt_symbols, history_data_g, dts = load_data(data_path)
    
    global history_data
    history_data = history_data_g
    
    # 2. 创建策略
    print("\n📊 创建策略...")
    strategy = IndustryRotationStrategy(setting={
        "lookback": 20,
        "top_industries": 3,
        "stocks_per_industry": 3,
        "max_pe": 20,
        "max_pb": 3,
        "rebalance_days": 5
    })
    
    print(f"  动量回看：20 天")
    print(f"  热门行业：前 3 个")
    print(f"  每行业选股：3 只")
    print(f"  估值上限：PE<20, PB<3")
    print(f"  调仓周期：5 天")
    
    # 3. 创建引擎
    print("\n📊 创建回测引擎...")
    engine = SimpleBacktestEngine(capital=1_000_000)
    
    # 4. 运行回测
    print("\n📊 运行回测...")
    sorted_dts = sorted(dts)
    
    for i, dt in enumerate(sorted_dts):
        if i % 100 == 0:
            print(f"  进度：{i}/{len(sorted_dts)} ({i/len(sorted_dts)*100:.1f}%)")
        
        engine.datetime = dt
        
        # 获取当日 K 线
        bars = {}
        for vt_symbol in vt_symbols:
            key = (dt, vt_symbol)
            if key in history_data:
                bars[vt_symbol] = history_data[key]
        
        if bars:
            # 策略逻辑
            target_holdings = strategy.on_bars(bars, dt)
            
            # 调仓
            engine.rebalance_to(target_holdings, bars)
            
            # 记录净值
            engine.record_daily_value(bars)
    
    print(f"  ✅ 回测完成：{len(sorted_dts)} 个交易日")
    
    # 5. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if engine.daily_values:
        initial = engine.daily_values[0]["total_value"]
        final = engine.daily_values[-1]["total_value"]
        total_return = (final - initial) / initial * 100
        
        # 最大回撤
        max_dd = 0
        peak = initial
        for daily in engine.daily_values:
            value = daily["total_value"]
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 年化收益
        years = len(sorted_dts) / 240
        annual_return = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        print(f"  初始资金：{initial:,.0f}")
        print(f"  最终价值：{final:,.0f}")
        print(f"  总收益率：{total_return:.2f}%")
        print(f"  年化收益率：{annual_return:.2f}%")
        print(f"  最大回撤：{max_dd:.2f}%")
        print(f"  交易次数：{len(engine.trades)}")
        
        # 最终持仓
        final_holdings = [k for k, v in engine.positions.items() if v > 0]
        print(f"  最终持仓：{len(final_holdings)}只")
        
        if final_holdings:
            print(f"  持仓：{', '.join(final_holdings[:5])}...")
    
    print("=" * 60)
    return engine


if __name__ == "__main__":
    engine = run_backtest()
