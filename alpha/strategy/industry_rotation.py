"""
行业轮动策略 - 热门行业低估值选股

策略逻辑：
1. 识别热门行业（动量 + 资金流入）
2. 在热门行业中选择低估值股票
3. 定期调仓（周度/月度）

核心因子：
- 行业动量：过去 N 日行业指数收益率
- 行业估值：行业平均 PE/PB
- 个股估值：PE/PB/股息率
- 资金流向：北向资金/主力资金
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

from vnpy.alpha.strategy.stock_screener_strategy import StockScreenerStrategy
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval


# ========== 行业定义 ==========

INDUSTRY_STOCKS = {
    "bank": ["600000.SSE", "600016.SSE", "600036.SSE", "601166.SSE", "601288.SSE", "601328.SSE", "601398.SSE"],
    "securities": ["600030.SSE", "601066.SSE", "601211.SSE", "601688.SSE", "601881.SSE"],
    "insurance": ["601318.SSE", "601601.SSE", "601628.SSE"],
    "liquor": ["600519.SSE", "000568.SZSE", "000725.SZSE", "000858.SZSE", "600809.SSE"],
    "food": ["000895.SZSE", "600887.SSE", "603288.SSE"],
    "appliance": ["000333.SZSE", "000651.SZSE", "600690.SSE"],
    "medicine": ["000538.SZSE", "002007.SZSE", "300122.SZSE", "600276.SSE", "600436.SSE"],
    "new_energy": ["002594.SZSE", "300014.SZSE", "300274.SZSE", "300750.SZSE", "601012.SSE"],
    "tech": ["000063.SZSE", "002230.SZSE", "002415.SZSE", "300059.SZSE", "600570.SSE", "600745.SSE"],
    "manufacturing": ["000001.SZSE", "000002.SZSE", "600031.SSE", "601766.SSE"],
}


@dataclass
class IndustryMetrics:
    """行业指标"""
    name: str
    momentum_20d: float  # 20 日动量
    momentum_60d: float  # 60 日动量
    avg_pe: float  # 平均 PE
    avg_pb: float  # 平均 PB
    turnover_ratio: float  # 换手率
    score: float  # 综合得分


class IndustryRotationStrategy(StockScreenerStrategy):
    """
    行业轮动策略
    
    参数:
        lookback_momentum: 动量回看天数（默认 20）
        top_industries: 选择前 N 个热门行业（默认 3）
        stocks_per_industry: 每个行业选 N 只股票（默认 5）
        max_pe: 最大 PE（默认 20）
        max_pb: 最大 PB（默认 3）
        min_dividend_yield: 最小股息率（默认 1）
        rebalance_days: 调仓周期（默认 5 个交易日）
    """
    
    def __init__(self, strategy_engine, strategy_name: str, vt_symbols: List[str], setting: dict):
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        
        # 策略参数
        self.lookback_momentum = self.setting.get("lookback_momentum", 20)
        self.top_industries = self.setting.get("top_industries", 3)
        self.stocks_per_industry = self.setting.get("stocks_per_industry", 5)
        self.max_pe = self.setting.get("max_pe", 20)
        self.max_pb = self.setting.get("max_pb", 3)
        self.min_dividend_yield = self.setting.get("min_dividend_yield", 1)
        self.rebalance_days = self.setting.get("rebalance_days", 5)
        
        # 状态
        self.last_rebalance_date: Optional[datetime] = None
        self.industry_scores: Dict[str, IndustryMetrics] = {}
        self.selected_industries: List[str] = []
        
        # 价格历史（用于计算动量）
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def on_init(self):
        """初始化"""
        self.write_log("=== 行业轮动策略初始化 ===")
        self.write_log(f"动量回看：{self.lookback_momentum}天")
        self.write_log(f"热门行业：前{self.top_industries}个")
        self.write_log(f"每行业选股：{self.stocks_per_industry}只")
        self.write_log(f"估值上限：PE<{self.max_pe}, PB<{self.max_pb}")
        self.write_log(f"调仓周期：{self.rebalance_days}天")
    
    def on_bars(self, bars: Dict[str, BarData]):
        """K 线更新"""
        if not bars:
            return
        
        # 更新价格历史
        self._update_price_history(bars)
        
        # 检查是否需要调仓
        if not self._should_rebalance():
            return
        
        # 1. 计算行业得分
        self._calculate_industry_scores(bars)
        
        # 2. 选择热门行业
        self._select_hot_industries()
        
        # 3. 在热门行业中选股
        new_holdings = self._select_stocks_in_industries(bars)
        
        # 4. 调仓
        self._rebalance(new_holdings, bars)
        
        # 记录调仓日期
        self.last_rebalance_date = self.datetime
        
        # 输出日志
        self.write_log(f"\n=== 调仓完成 ({self.datetime.date()}) ===")
        self.write_log(f"热门行业：{', '.join(self.selected_industries)}")
        self.write_log(f"持仓数量：{len(self.holdings)}")
    
    def _update_price_history(self, bars: Dict[str, BarData]):
        """更新价格历史"""
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            
            self.price_history[vt_symbol].append((bar.datetime, bar.close_price))
            
            # 保留最近 120 天数据
            if len(self.price_history[vt_symbol]) > 120:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-120:]
    
    def _should_rebalance(self) -> bool:
        """检查是否需要调仓"""
        if not self.datetime:
            return True
        
        if self.last_rebalance_date is None:
            return True
        
        # 计算交易日间隔（简化处理）
        days_since_rebalance = (self.datetime - self.last_rebalance_date).days
        return days_since_rebalance >= self.rebalance_days
    
    def _calculate_industry_scores(self, bars: Dict[str, BarData]):
        """计算行业得分"""
        self.industry_scores = {}
        
        for industry_name, stocks in INDUSTRY_STOCKS.items():
            # 获取行业成分股
            industry_stocks = [s for s in stocks if s in bars]
            
            if not industry_stocks:
                continue
            
            # 计算行业动量
            momentum_20d = self._calculate_industry_momentum(industry_stocks, 20)
            momentum_60d = self._calculate_industry_momentum(industry_stocks, 60)
            
            # 计算行业估值（简化：使用固定值，实际应从财务数据获取）
            avg_pe, avg_pb = self._get_industry_valuation(industry_name)
            
            # 计算换手率（简化：使用成交量）
            turnover = self._calculate_industry_turnover(industry_stocks, bars)
            
            # 综合得分（动量 60% + 估值 30% + 换手 10%）
            score = (
                0.4 * self._normalize_momentum(momentum_20d) +
                0.2 * self._normalize_momentum(momentum_60d) +
                0.3 * self._normalize_valuation(avg_pe, avg_pb) +
                0.1 * self._normalize_turnover(turnover)
            )
            
            self.industry_scores[industry_name] = IndustryMetrics(
                name=industry_name,
                momentum_20d=momentum_20d,
                momentum_60d=momentum_60d,
                avg_pe=avg_pe,
                avg_pb=avg_pb,
                turnover_ratio=turnover,
                score=score
            )
    
    def _calculate_industry_momentum(self, stocks: List[str], days: int) -> float:
        """计算行业动量（成分股平均收益率）"""
        returns = []
        
        for vt_symbol in stocks:
            if vt_symbol not in self.price_history:
                continue
            
            history = self.price_history[vt_symbol]
            if len(history) < days:
                continue
            
            old_price = history[-days][1]
            current_price = history[-1][1]
            
            if old_price > 0:
                ret = (current_price - old_price) / old_price * 100
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        return sum(returns) / len(returns)
    
    def _get_industry_valuation(self, industry: str) -> Tuple[float, float]:
        """
        获取行业估值
        
        简化版本：返回固定估值范围
        实际应从财务数据获取
        """
        # 行业平均估值（近似值）
        valuations = {
            "bank": (5.0, 0.6),
            "securities": (12.0, 1.2),
            "insurance": (10.0, 1.0),
            "liquor": (25.0, 5.0),
            "food": (20.0, 3.5),
            "appliance": (12.0, 2.5),
            "medicine": (30.0, 4.0),
            "new_energy": (35.0, 5.5),
            "tech": (40.0, 4.5),
            "manufacturing": (15.0, 1.8),
        }
        
        return valuations.get(industry, (15.0, 2.0))
    
    def _calculate_industry_turnover(self, stocks: List[str], bars: Dict[str, BarData]) -> float:
        """计算行业换手率（简化：使用成交量）"""
        total_volume = sum(bars[s].volume for s in stocks if s in bars)
        return total_volume / 1_000_000  # 简化处理
    
    def _normalize_momentum(self, momentum: float) -> float:
        """动量标准化（0-1）"""
        # Sigmoid 函数
        return 1 / (1 + math.exp(-momentum / 10))
    
    def _normalize_valuation(self, pe: float, pb: float) -> float:
        """估值标准化（0-1，越低越好）"""
        # 估值越低得分越高
        pe_score = max(0, 1 - pe / 50)
        pb_score = max(0, 1 - pb / 10)
        return (pe_score + pb_score) / 2
    
    def _normalize_turnover(self, turnover: float) -> float:
        """换手率标准化（0-1）"""
        return min(1.0, turnover / 100)
    
    def _select_hot_industries(self):
        """选择热门行业"""
        if not self.industry_scores:
            return
        
        # 按得分排序
        sorted_industries = sorted(
            self.industry_scores.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        # 选择前 N 个
        self.selected_industries = [
            ind.name for ind in sorted_industries[:self.top_industries]
        ]
        
        # 输出行业得分
        for ind in sorted_industries[:5]:
            self.write_log(
                f"  {ind.name}: 得分={ind.score:.3f}, "
                f"动量 20d={ind.momentum_20d:.1f}%, "
                f"PE={ind.avg_pe:.1f}"
            )
    
    def _select_stocks_in_industries(self, bars: Dict[str, BarData]) -> List[str]:
        """在热门行业中选择低估值股票"""
        selected = []
        
        for industry in self.selected_industries:
            stocks = INDUSTRY_STOCKS.get(industry, [])
            
            # 获取行业内股票数据
            stock_data = []
            for vt_symbol in stocks:
                if vt_symbol not in bars:
                    continue
                
                # 获取估值数据（简化：使用固定值）
                pe, pb = self._get_stock_valuation(vt_symbol)
                dividend_yield = self._get_dividend_yield(vt_symbol)
                
                # 估值筛选
                if pe > self.max_pe or pb > self.max_pb:
                    continue
                if dividend_yield < self.min_dividend_yield:
                    continue
                
                # 计算综合得分（估值越低越好）
                score = (1 / pe) * 0.5 + (1 / pb) * 0.3 + dividend_yield * 0.2
                stock_data.append((vt_symbol, score))
            
            # 按得分排序，选择前 N 只
            stock_data.sort(key=lambda x: x[1], reverse=True)
            selected.extend([s[0] for s in stock_data[:self.stocks_per_industry]])
        
        return selected
    
    def _get_stock_valuation(self, vt_symbol: str) -> Tuple[float, float]:
        """获取个股估值（简化版本）"""
        # 根据股票代码生成近似估值
        symbol = vt_symbol.split(".")[0]
        
        # 根据行业和行业估值生成
        for industry, stocks in INDUSTRY_STOCKS.items():
            if vt_symbol in stocks:
                base_pe, base_pb = self._get_industry_valuation(industry)
                # 添加个股差异
                pe = base_pe * (0.8 + hash(symbol) % 40 / 100)
                pb = base_pb * (0.8 + hash(symbol) % 40 / 100)
                return (pe, pb)
        
        return (15.0, 2.0)
    
    def _get_dividend_yield(self, vt_symbol: str) -> float:
        """获取股息率（简化版本）"""
        # 根据行业生成
        for industry, stocks in INDUSTRY_STOCKS.items():
            if vt_symbol in stocks:
                if industry in ["bank", "securities", "insurance"]:
                    return 3.0 + hash(vt_symbol) % 30 / 10
                elif industry in ["liquor", "food", "appliance"]:
                    return 2.0 + hash(vt_symbol) % 20 / 10
                else:
                    return 1.0 + hash(vt_symbol) % 15 / 10
        
        return 1.5
    
    def _rebalance(self, new_holdings: List[str], bars: Dict[str, BarData]):
        """执行调仓"""
        if not new_holdings:
            return
        
        # 计算目标仓位
        target_weight = 1.0 / len(new_holdings)
        
        # 获取组合总价值
        portfolio_value = self.get_portfolio_value()
        available_cash = self.get_cash_available()
        
        # 调整持仓
        for vt_symbol in new_holdings:
            if vt_symbol not in bars:
                continue
            
            bar = bars[vt_symbol]
            target_value = portfolio_value * target_weight
            target_volume = target_value / bar.close_price
            
            current_pos = self.get_pos(vt_symbol)
            
            # 调仓
            if target_volume > current_pos * 1.05:  # 5% 阈值
                volume = target_volume - current_pos
                self.send_order(
                    vt_symbol=vt_symbol,
                    direction=Direction.LONG,
                    offset=Offset.OPEN,
                    price=bar.close_price,
                    volume=volume
                )
            elif target_volume < current_pos * 0.95:
                volume = current_pos - target_volume
                self.send_order(
                    vt_symbol=vt_symbol,
                    direction=Direction.SHORT,
                    offset=Offset.CLOSE,
                    price=bar.close_price,
                    volume=volume
                )
        
        # 更新持仓列表
        self.holdings = new_holdings


# ========== 测试函数 ==========

def test_strategy():
    """测试策略"""
    print("=" * 60)
    print("行业轮动策略测试")
    print("=" * 60)
    
    # 打印行业定义
    print("\n📊 行业配置:")
    for industry, stocks in INDUSTRY_STOCKS.items():
        print(f"  {industry}: {len(stocks)}只股票")
    
    print("\n📊 策略参数:")
    print("  - 动量回看：20 天")
    print("  - 热门行业：前 3 个")
    print("  - 每行业选股：5 只")
    print("  - 估值上限：PE<20, PB<3")
    print("  - 调仓周期：5 天")
    
    print("\n📊 选股逻辑:")
    print("  1. 计算行业得分（动量 40% + 估值 30% + 换手 10%）")
    print("  2. 选择得分最高的 3 个行业")
    print("  3. 在热门行业中选择低估值股票")
    print("  4. 等权重配置")
    
    print("\n✅ 策略开发完成！")


if __name__ == "__main__":
    test_strategy()
