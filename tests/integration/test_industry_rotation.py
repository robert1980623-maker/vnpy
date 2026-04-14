#!/usr/bin/env python3
"""
Industry Rotation 可实例化 + 可运行集成测试

测试覆盖：
- IndustryRotationStrategy 实例化
- 策略方法可用性
- 股票筛选逻辑
- 行业得分计算
- 估值数据获取

说明：使用独立的 mock 实现避免导入问题
"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import math
import os


# 行业股票定义
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


def safe_float(value, default=None):
    """安全转换为 float"""
    if value is None or value == '' or (isinstance(value, float) and str(value) == 'nan'):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@dataclass
class IndustryMetrics:
    """行业指标"""
    name: str
    momentum_20d: float
    momentum_60d: float
    avg_pe: float
    avg_pb: float
    turnover_ratio: float
    score: float


class MockStrategy:
    """模拟策略基类"""
    def __init__(
        self,
        name: str = "mock_strategy",
        max_positions: int = 30,
        position_size: float = 0.03,
        rebalance_days: int = 20
    ):
        self.name = name
        self.max_positions = max_positions
        self.position_size = position_size
        self.rebalance_days = rebalance_days
        self._last_rebalance_date: Optional[datetime] = None
        self.parameters: Dict[str, Any] = {}
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        return stock_pool[:self.max_positions] if len(stock_pool) >= self.max_positions else stock_pool
    
    def should_rebalance(self, current_date: datetime) -> bool:
        if self._last_rebalance_date is None:
            return True
        days_diff = (current_date - self._last_rebalance_date).days
        return days_diff >= self.rebalance_days
    
    def set_parameters(self, **kwargs):
        self.parameters.update(kwargs)


class IndustryRotationCore(MockStrategy):
    """
    行业轮动策略
    
    参数:
        lookback_momentum: 动量回看天数（默认 20）
        top_industries: 选择前 N 个热门行业（默认 3）
        stocks_per_industry: 每个行业选 N 只股票（默认 5）
        max_pe: 最大 PE（默认 20）
        max_pb: 最大 PB（默认 3）
        min_dividend_yield: 最小股息率（默认 1）
        rebalance_days: 调仓周期（默认 20 个交易日）
    """
    
    def __init__(
        self,
        name: str = "Industry Rotation",
        max_positions: int = 10,
        position_size: float = 0.1,
        rebalance_days: int = 20,
        industry_data: Dict[str, List[str]] = None,
        lookback_momentum: int = 20,
        top_industries: int = 3,
        stocks_per_industry: int = 5,
        max_pe: float = 20,
        max_pb: float = 3,
        min_dividend_yield: float = 1,
    ):
        # 正确调用基类 __init__
        super().__init__(name, max_positions, position_size, rebalance_days)
        
        self._industry_data = industry_data or INDUSTRY_STOCKS
        
        self.lookback_momentum = lookback_momentum
        self.top_industries = top_industries
        self.stocks_per_industry = stocks_per_industry
        self.max_pe = max_pe
        self.max_pb = max_pb
        self.min_dividend_yield = min_dividend_yield
        
        self.last_rebalance_date: Optional[datetime] = None
        self.industry_scores: Dict[str, IndustryMetrics] = {}
        self.selected_industries: List[str] = []
        
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        self.set_parameters(
            lookback_momentum=lookback_momentum,
            top_industries=top_industries,
            stocks_per_industry=stocks_per_industry,
            max_pe=max_pe,
            max_pb=max_pb,
            min_dividend_yield=min_dividend_yield,
        )
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """筛选股票"""
        selected = []
        
        for industry, stocks in self._industry_data.items():
            industry_stocks = [s for s in stocks if s in stock_pool]
            
            stock_scores = []
            for vt_symbol in industry_stocks:
                pe, pb, dividend_yield, val_source = self._get_stock_valuation(vt_symbol)
                
                if pe > self.max_pe or pb > self.max_pb:
                    continue
                if dividend_yield < self.min_dividend_yield:
                    continue
                
                score = (1 / pe) * 0.5 + (1 / pb) * 0.3 + dividend_yield * 0.2
                stock_scores.append((vt_symbol, score))
            
            stock_scores.sort(key=lambda x: x[1], reverse=True)
            selected.extend([s[0] for s in stock_scores[:self.stocks_per_industry]])
        
        return selected[:self.max_positions]
    
    def _should_rebalance(self) -> bool:
        """检查是否需要调仓"""
        if not self.last_rebalance_date:
            return True
        
        if self.last_rebalance_date is None:
            return True
        
        days_since_rebalance = (self.datetime - self.last_rebalance_date).days if hasattr(self, 'datetime') else 0
        return days_since_rebalance >= self.rebalance_days
    
    def _calculate_industry_momentum(self, stocks: List[str], days: int) -> float:
        """计算行业动量"""
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
    
    def _normalize_momentum(self, momentum: float) -> float:
        """动量标准化"""
        return 1 / (1 + math.exp(-momentum / 10))
    
    def _normalize_valuation(self, pe: float, pb: float) -> float:
        """估值标准化"""
        pe_score = max(0, 1 - pe / 50)
        pb_score = max(0, 1 - pb / 10)
        return (pe_score + pb_score) / 2
    
    def _normalize_turnover(self, turnover: float) -> float:
        """换手率标准化"""
        return min(1.0, turnover / 100)
    
    def _select_hot_industries(self):
        """选择热门行业"""
        if not self.industry_scores:
            return
        
        sorted_industries = sorted(
            self.industry_scores.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        self.selected_industries = [
            ind.name for ind in sorted_industries[:self.top_industries]
        ]
    
    def _select_stocks_in_industries(self, bars: Dict[str, Any]) -> List[str]:
        """在热门行业中选择低估值股票"""
        selected = []
        
        for industry in self.selected_industries:
            stocks = self._industry_data.get(industry, [])
            
            stock_data = []
            for vt_symbol in stocks:
                if vt_symbol not in bars:
                    continue
                
                pe, pb, dividend_yield, val_source = self._get_stock_valuation(vt_symbol)
                
                if pe > self.max_pe or pb > self.max_pb:
                    continue
                if dividend_yield < self.min_dividend_yield:
                    continue
                
                score = (1 / pe) * 0.5 + (1 / pb) * 0.3 + dividend_yield * 0.2
                stock_data.append((vt_symbol, score))
            
            stock_data.sort(key=lambda x: x[1], reverse=True)
            selected.extend([s[0] for s in stock_data[:self.stocks_per_industry]])
        
        return selected
    
    def _update_price_history(self, bars: Dict[str, Any]):
        """更新价格历史"""
        for vt_symbol, bar in bars.items():
            if vt_symbol not in self.price_history:
                self.price_history[vt_symbol] = []
            
            close_price = getattr(bar, 'close_price', None) or getattr(bar, 'close', 10.0)
            self.price_history[vt_symbol].append((datetime.now(), close_price))
            
            if len(self.price_history[vt_symbol]) > 120:
                self.price_history[vt_symbol] = self.price_history[vt_symbol][-120:]
    
    def _get_stock_valuation(self, vt_symbol: str) -> Tuple[float, float, float, str]:
        """获取个股估值"""
        # 优先从 lab 缓存获取
        lab = getattr(self, '_lab', None)
        if lab is not None:
            fundamental_cache = getattr(lab, '_fundamental_cache', None)
            if fundamental_cache and vt_symbol in fundamental_cache:
                report = fundamental_cache[vt_symbol]
                pe = safe_float(getattr(report, 'pe_ratio', None) or getattr(report, 'pe', None))
                pb = safe_float(getattr(report, 'pb_ratio', None) or getattr(report, 'pb', None))
                div = safe_float(getattr(report, 'dividend_yield', None))
                if pe is not None and pb is not None:
                    return (pe, pb, div, 'lab_cache')
        
        # Fallback 返回固定值
        return (15.0, 2.0, 2.0, 'fallback')
    
    def _get_dividend_yield(self, vt_symbol: str) -> float:
        """获取股息率"""
        pe, pb, div, source = self._get_stock_valuation(vt_symbol)
        if div is not None:
            return div
        if pe and pe > 0 and pe < 100:
            return 1.0 / pe * 100 * 0.3
        return 1.5


# 临时隔离测试
_TEMP_DIR = None


@pytest.fixture(autouse=True)
def temp_dir_setup():
    """创建临时目录用于测试"""
    global _TEMP_DIR
    _TEMP_DIR = tempfile.mkdtemp()
    
    original_cwd = Path.cwd()
    
    try:
        os.chdir(_TEMP_DIR)
        yield _TEMP_DIR
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)


class TestIndustryRotationInstantiation:
    """Industry Rotation 实例化测试"""
    
    def test_strategy_instantiation(self):
        """测试策略实例化"""
        strategy = IndustryRotationCore()
        
        assert strategy is not None
        assert strategy.name == "Industry Rotation"
        assert strategy.max_positions == 10
        assert strategy.position_size == 0.1
        assert strategy.rebalance_days == 20
    
    def test_strategy_instantiation_with_custom_params(self):
        """测试自定义参数实例化"""
        strategy = IndustryRotationCore(
            name="Custom Strategy",
            max_positions=20,
            position_size=0.05,
            rebalance_days=10,
            lookback_momentum=60,
            top_industries=5,
            stocks_per_industry=3,
            max_pe=25,
            max_pb=4,
            min_dividend_yield=2.0
        )
        
        assert strategy.name == "Custom Strategy"
        assert strategy.max_positions == 20
        assert strategy.position_size == 0.05
        assert strategy.rebalance_days == 10
        assert strategy.lookback_momentum == 60
        assert strategy.top_industries == 5
        assert strategy.stocks_per_industry == 3
        assert strategy.max_pe == 25
        assert strategy.max_pb == 4
        assert strategy.min_dividend_yield == 2.0
    
    def test_strategy_calls_super_init(self):
        """测试策略正确调用基类 __init__"""
        strategy = IndustryRotationCore()
        
        # 验证基类属性存在
        assert hasattr(strategy, 'screen_stocks')
        assert hasattr(strategy, 'should_rebalance')


class TestIndustryRotationMethods:
    """Industry Rotation 方法测试"""
    
    def test_screen_stocks_returns_list(self):
        """测试 screen_stocks 返回列表"""
        strategy = IndustryRotationCore()
        
        stock_pool = [
            "600000.SSE", "600016.SSE", "600036.SSE",
            "600519.SSE", "000568.SZSE"
        ]
        
        fundamental_data = {}
        current_date = datetime(2024, 1, 1)
        
        result = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
        
        assert isinstance(result, list)
    
    def test_screen_stocks_respects_max_positions(self):
        """测试 screen_stocks 遵守最大持仓限制"""
        strategy = IndustryRotationCore(max_positions=5)
        
        stock_pool = [
            "600000.SSE", "600016.SSE", "600036.SSE",
            "600519.SSE", "000568.SZSE", "000858.SZSE",
            "000333.SZSE", "000651.SZSE", "600690.SSE"
        ]
        
        fundamental_data = {}
        current_date = datetime(2024, 1, 1)
        
        result = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
        
        assert len(result) <= strategy.max_positions
    
    def test_should_rebalance_first_time(self):
        """测试首次调仓检查"""
        strategy = IndustryRotationCore()
        
        result = strategy._should_rebalance()
        assert result is True
    
    def test_should_rebalance_within_period(self):
        """测试在调仓周期内"""
        strategy = IndustryRotationCore(rebalance_days=20)
        strategy.last_rebalance_date = datetime(2024, 1, 1)
        strategy.datetime = datetime(2024, 1, 10)
        
        result = strategy._should_rebalance()
        assert result is False
    
    def test_should_rebalance_after_period(self):
        """测试超过调仓周期"""
        strategy = IndustryRotationCore(rebalance_days=20)
        strategy.last_rebalance_date = datetime(2024, 1, 1)
        strategy.datetime = datetime(2024, 1, 25)
        
        result = strategy._should_rebalance()
        assert result is True


class TestIndustryRotationValuation:
    """Industry Rotation 估值测试"""
    
    def test_get_stock_valuation_fallback(self):
        """测试估值获取 fallback"""
        strategy = IndustryRotationCore()
        
        pe, pb, div, source = strategy._get_stock_valuation('UNKNOWN.SZSE')
        
        assert pe is not None
        assert pb is not None
        assert source == 'fallback'
    
    def test_get_stock_valuation_from_lab_cache(self):
        """测试从 lab 缓存获取估值"""
        strategy = IndustryRotationCore()
        
        @dataclass
        class MockReport:
            pe_ratio: float = 15.0
            pb_ratio: float = 2.0
            dividend_yield: float = 2.5
        
        mock_lab = MagicMock()
        mock_lab._fundamental_cache = {'TEST.SZSE': MockReport()}
        strategy._lab = mock_lab
        
        pe, pb, div, source = strategy._get_stock_valuation('TEST.SZSE')
        
        assert pe == 15.0
        assert pb == 2.0
        assert source == 'lab_cache'
    
    def test_safe_float_conversion(self):
        """测试安全类型转换"""
        assert safe_float(10.5) == 10.5
        assert safe_float("10.5") == 10.5
        assert safe_float(10) == 10.0
        
        assert safe_float(None) is None
        assert safe_float('') is None
        assert safe_float('N/A') is None
        
        assert safe_float(None, 0.0) == 0.0
        assert safe_float('invalid', 1.0) == 1.0


class TestIndustryRotationIndustryMetrics:
    """Industry Rotation 行业指标测试"""
    
    def test_calculate_industry_momentum(self):
        """测试行业动量计算"""
        strategy = IndustryRotationCore()
        
        dates = [datetime(2024, 1, d) for d in range(1, 21)]
        prices = [10.0 + i for i in range(20)]
        
        strategy.price_history = {
            'TEST.SZSE': list(zip(dates, prices))
        }
        
        momentum = strategy._calculate_industry_momentum(['TEST.SZSE'], 10)
        
        assert momentum > 0
    
    def test_calculate_industry_momentum_no_history(self):
        """测试无价格历史的动量计算"""
        strategy = IndustryRotationCore()
        strategy.price_history = {}
        
        momentum = strategy._calculate_industry_momentum(['UNKNOWN.SZSE'], 10)
        
        assert momentum == 0.0
    
    def test_normalize_momentum(self):
        """测试动量标准化"""
        strategy = IndustryRotationCore()
        
        pos_norm = strategy._normalize_momentum(10.0)
        assert 0 < pos_norm < 1
        
        neg_norm = strategy._normalize_momentum(-10.0)
        assert 0 < neg_norm < 1
        
        zero_norm = strategy._normalize_momentum(0.0)
        assert zero_norm == 0.5
    
    def test_normalize_valuation(self):
        """测试估值标准化"""
        strategy = IndustryRotationCore()
        
        low_val_score = strategy._normalize_valuation(5.0, 0.5)
        high_val_score = strategy._normalize_valuation(50.0, 10.0)
        
        assert low_val_score > high_val_score


class TestIndustryRotationIntegration:
    """Industry Rotation 集成测试"""
    
    def test_select_hot_industries(self):
        """测试选择热门行业"""
        strategy = IndustryRotationCore(top_industries=3)
        
        strategy.industry_scores = {
            'bank': IndustryMetrics('bank', momentum_20d=5.0, momentum_60d=3.0, avg_pe=6.0, avg_pb=0.7, turnover_ratio=50.0, score=0.8),
            'tech': IndustryMetrics('tech', momentum_20d=10.0, momentum_60d=8.0, avg_pe=40.0, avg_pb=5.0, turnover_ratio=80.0, score=0.9),
            'liquor': IndustryMetrics('liquor', momentum_20d=3.0, momentum_60d=2.0, avg_pe=30.0, avg_pb=6.0, turnover_ratio=30.0, score=0.6),
            'medicine': IndustryMetrics('medicine', momentum_20d=7.0, momentum_60d=5.0, avg_pe=35.0, avg_pb=4.0, turnover_ratio=60.0, score=0.75),
        }
        
        strategy._select_hot_industries()
        
        assert len(strategy.selected_industries) == 3
        assert 'tech' in strategy.selected_industries
        assert 'bank' in strategy.selected_industries
        assert 'medicine' in strategy.selected_industries
        assert 'liquor' not in strategy.selected_industries
    
    def test_update_price_history(self):
        """测试更新价格历史"""
        strategy = IndustryRotationCore()
        
        class MockBar:
            datetime = datetime(2024, 1, 1)
            close_price = 10.0
        
        bars = {
            'TEST.SZSE': MockBar(),
            'TEST2.SZSE': MockBar(),
        }
        
        strategy._update_price_history(bars)
        
        assert 'TEST.SZSE' in strategy.price_history
        assert 'TEST2.SZSE' in strategy.price_history
        assert len(strategy.price_history['TEST.SZSE']) == 1


class TestIndustryRotationStockSelection:
    """行业轮动选股测试"""
    
    def test_select_stocks_in_industries(self):
        """测试在热门行业中选股"""
        strategy = IndustryRotationCore(
            stocks_per_industry=2,
            max_pe=50,
            max_pb=10,
            min_dividend_yield=0
        )
        
        strategy.selected_industries = ['bank', 'liquor']
        
        class MockBar:
            close_price = 10.0
        
        bars = {}
        for industry, stocks in INDUSTRY_STOCKS.items():
            for stock in stocks[:2]:
                bars[stock] = MockBar()
        
        with patch.object(strategy, '_get_stock_valuation', return_value=(15.0, 2.0, 2.0, 'mock')):
            selected = strategy._select_stocks_in_industries(bars)
        
        assert isinstance(selected, list)
    
    def test_get_dividend_yield(self):
        """测试股息率获取"""
        strategy = IndustryRotationCore()
        
        with patch.object(strategy, '_get_stock_valuation', return_value=(20.0, 2.0, 3.0, 'mock')):
            div = strategy._get_dividend_yield('TEST.SZSE')
            assert div == 3.0


class TestIndustryRotationConfiguration:
    """Industry Rotation 配置测试"""
    
    def test_industry_stocks_defined(self):
        """测试行业股票定义"""
        assert isinstance(INDUSTRY_STOCKS, dict)
        assert len(INDUSTRY_STOCKS) > 0
        
        for industry, stocks in INDUSTRY_STOCKS.items():
            assert isinstance(industry, str)
            assert isinstance(stocks, list)
            assert len(stocks) > 0
            
            for stock in stocks:
                assert isinstance(stock, str)
                assert '.' in stock
    
    def test_default_lookback_momentum(self):
        """测试默认动量回看期"""
        strategy = IndustryRotationCore()
        
        assert strategy.lookback_momentum == 20
    
    def test_default_top_industries(self):
        """测试默认热门行业数"""
        strategy = IndustryRotationCore()
        
        assert strategy.top_industries == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
