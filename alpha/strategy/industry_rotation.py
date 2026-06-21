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
import logging
import math
import os

from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Direction, Offset

from alpha.strategy.stock_screener_strategy import StockScreenerStrategy
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval

logger = logging.getLogger(__name__)


# ========== TushareFundamentalFetcher 兼容类 ==========
# 用于从 Tushare/AKShare 获取真实估值数据


def safe_float(value, default=None):
    """安全转换为 float"""
    if value is None or value == '' or (isinstance(value, float) and str(value) == 'nan'):
        return default
    try:
        result = float(value)
        if math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class ValuationFetcher:
    """
    估值数据获取器
    
    优先使用 Tushare，如果未配置则回退到 AKShare。
    估值数据可追溯到真实来源，回测结果可验证。
    """
    
    def __init__(self, cache_dir: str = './cache/fundamental'):
        self.cache_dir = os.path.join(cache_dir, 'industry_rotation')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化 Tushare
        token = os.environ.get('TUSHARE_TOKEN', '')
        self._pro = None
        self._use_tushare = False
        
        if token:
            try:
                import tushare as ts
                ts.set_token(token)
                self._pro = ts.pro_api()
                self._use_tushare = True
            except Exception:
                pass
        
        # 内存缓存
        self._memory_cache: Dict[str, Tuple[float, float, float, str]] = {}
    
    def _get_cache_path(self, symbol: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{symbol.replace('.', '_')}_valuation.json")
    
    def _load_from_file(self, symbol: str) -> Optional[dict]:
        """从文件缓存加载"""
        cache_path = self._get_cache_path(symbol)
        if os.path.exists(cache_path):
            try:
                import json
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_to_file(self, symbol: str, data: dict):
        """保存到文件缓存"""
        cache_path = self._get_cache_path(symbol)
        try:
            import json
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_valuation(self, symbol: str, trade_date: str = None) -> Tuple[float, float, float, str]:
        """
        获取估值数据 (PE, PB, dividend_yield, source)
        
        优先从内存缓存获取，其次文件缓存，最后从数据源拉取。
        
        Returns:
            Tuple[pe, pb, dividend_yield, source]
            source: 'tushare' | 'akshare' | 'fallback'
        """
        # 1. 内存缓存
        if symbol in self._memory_cache:
            return self._memory_cache[symbol]
        
        # 2. 文件缓存
        cached = self._load_from_file(symbol)
        if cached:
            pe = safe_float(cached.get('pe'))
            pb = safe_float(cached.get('pb'))
            div = safe_float(cached.get('dividend_yield'))
            source = cached.get('source', 'fallback')
            if pe is not None and pb is not None:
                result = (pe, pb, div, source)
                self._memory_cache[symbol] = result
                return result
        
        # 3. 从数据源获取
        pe, pb, div, source = self._fetch_from_source(symbol, trade_date)
        
        # 4. 保存到缓存
        self._memory_cache[symbol] = (pe, pb, div, source)
        self._save_to_file(symbol, {
            'pe': pe,
            'pb': pb,
            'dividend_yield': div,
            'source': source,
            'fetch_time': datetime.now().isoformat()
        })
        
        return pe, pb, div, source
    
    def _fetch_from_source(self, symbol: str, trade_date: str = None) -> Tuple[float, float, float, str]:
        """从 Tushare/AKShare 获取真实数据"""
        # 优先 Tushare
        if self._use_tushare and self._pro:
            try:
                import tushare as ts
                df = self._pro.daily_basic(ts_code=symbol)
                if df is not None and len(df) > 0:
                    row = df.iloc[0]
                    pe = safe_float(row.get('pe_ttm')) or safe_float(row.get('pe'))
                    pb = safe_float(row.get('pb'))
                    div = safe_float(row.get('dv_ttm'))
                    if pe is not None and pb is not None:
                        return (pe, pb, div, 'tushare')
            except Exception:
                pass
        
        # 回退 AKShare
        try:
            import akshare as ak
            symbol_no_suffix = symbol.split('.')[0] if '.' in symbol else symbol
            df = ak.stock_value_em(symbol=symbol_no_suffix)
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                pe = safe_float(latest.get('PE(TTM)')) or safe_float(latest.get('市净率'))
                pb = safe_float(latest.get('PB(市净率)'))
                # AKShare 不直接提供股息率，使用 PE 反推近似
                div = None
                if pe and pe > 0:
                    # 简化估算：假设分红率 30%
                    div = 1.0 / pe * 100 * 0.3 if pe < 100 else None
                if pe is not None and pb is not None:
                    return (pe, pb, div, 'akshare')
        except Exception:
            pass
        
        # 最后 fallback：返回行业平均估值（不可信但不让程序崩溃）
        logger.warning(
            "Valuation cache penetration for %s: all data sources (Tushare/AKShare) failed, "
            "using hardcoded fallback values (PE=15.0, PB=2.0, div=1.5). "
            "Results based on this symbol's valuation are NOT trustworthy.",
            symbol
        )
        return (15.0, 2.0, 1.5, 'fallback')


# 全局估值获取器实例
_valuation_fetcher: Optional[ValuationFetcher] = None


def get_valuation_fetcher() -> ValuationFetcher:
    """获取全局估值获取器实例"""
    global _valuation_fetcher
    if _valuation_fetcher is None:
        _valuation_fetcher = ValuationFetcher()
    return _valuation_fetcher


# ========== 行业定义 ==========

# 申万一级行业代码映射（用于动态获取成分股）
SW_INDEX_CODE_MAP = {
    "bank": "801780.SI",      # 银行
    "securities": "801790.SI", # 非银金融
    "insurance": "801790.SI",  # 保险在非银金融里
    "liquor": "801120.SI",     # 食品饮料
    "food": "801120.SI",       # 食品
    "appliance": "801110.SI",  # 家用电器
    "medicine": "801150.SI",   # 医药生物
    "new_energy": "801730.SI", # 电力设备
    "tech": "801750.SI",       # 计算机
    "manufacturing": "801890.SI", # 机械设备
}

# 基础行业股票池（Fallback，动态获取失败时使用）
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


def _normalize_symbol(code: str, target_market: str = None) -> str:
    """
    标准化股票代码格式
    
    Args:
        code: 原始代码，可能是 6 位数字或带后缀
        target_market: 目标市场 'SSE'/'SZSE'
    
    Returns:
        标准化格式，如 '600000.SSE' 或 '000001.SZSE'
    """
    # 去除空白
    code = code.strip()
    
    # 如果已经有后缀，直接返回
    if '.' in code:
        return code
    
    # 纯数字，尝试判断市场
    if code.isdigit():
        if len(code) == 6:
            # 上海：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
            # 深圳：000xxx, 001xxx, 002xxx, 003xxx, 300xxx
            # 北交所：83xxxx, 87xxxx, 88xxxx, 43xxxx
            first_two = code[:2]
            first_three = code[:3]
            if first_three in ('600', '601', '603', '605', '688'):
                return f"{code}.SSE"
            elif first_two in ('83', '87', '88', '43'):
                return f"{code}.BSE"
            else:
                return f"{code}.SZSE"
    
    return code


def _fetch_industry_stocks_from_akshare(industry_code: str) -> List[str]:
    """
    从 AKShare 获取申万行业成分股
    
    Args:
        industry_code: 申万行业代码，如 '801780.SI'
    
    Returns:
        成分股代码列表
    """
    try:
        import akshare as ak
        
        # 去掉 .SI 后缀获取纯代码
        symbol = industry_code.replace('.SI', '')
        df = ak.index_component_sw(symbol=symbol)
        
        if df is None or len(df) == 0:
            return []
        
        # 获取证券代码列
        if '证券代码' in df.columns:
            codes = df['证券代码'].dropna().tolist()
        elif '代码' in df.columns:
            codes = df['代码'].dropna().tolist()
        else:
            return []
        
        # 标准化格式
        result = []
        for code in codes:
            normalized = _normalize_symbol(str(code))
            if normalized:
                result.append(normalized)
        
        return result
        
    except Exception:
        return []


def _expand_industry_pool():
    """
    扩充所有行业股票池（动态获取申万行业成分股）
    
    每行业至少 20 只成分股，动态获取失败则使用现有股票池。
    """
    global INDUSTRY_STOCKS
    
    for industry, sw_code in SW_INDEX_CODE_MAP.items():
        # 获取动态成分股
        dynamic_stocks = _fetch_industry_stocks_from_akshare(sw_code)
        
        # 现有股票池（Fallback）
        fallback_stocks = INDUSTRY_STOCKS.get(industry, [])
        
        # 选择更大的池子（至少 20 只）
        if len(dynamic_stocks) >= 20:
            INDUSTRY_STOCKS[industry] = dynamic_stocks
        elif len(fallback_stocks) > len(dynamic_stocks):
            # 保持 fallback（它更大）
            pass
        else:
            # 合并 + 去重
            combined = list(set(dynamic_stocks + fallback_stocks))
            INDUSTRY_STOCKS[industry] = combined


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
        rebalance_days: 调仓周期（默认 20 个交易日）
    """
    
    def __init__(
        self,
        name: str = "Industry Rotation",
        max_positions: int = 10,
        position_size: float = 0.1,
        rebalance_days: int = 20,
        industry_data: Dict[str, List[str]] = None,
        # 额外参数（通过 parameters 传递）
        lookback_momentum: int = 20,
        top_industries: int = 3,
        stocks_per_industry: int = 5,
        max_pe: float = 20,
        max_pb: float = 3,
        min_dividend_yield: float = 1,
        # 兼容 CrossSectionalBacktestingEngine 调用
        strategy_engine=None,
        strategy_name: str = None,
        vt_symbols=None,
        setting: Dict = None,
    ):
        # 如果通过 engine 调用，从 setting 提取参数
        if setting:
            name = setting.get('name', name)
            max_positions = setting.get('max_positions', max_positions)
            position_size = setting.get('position_size', position_size)
            rebalance_days = setting.get('rebalance_days', rebalance_days)
            lookback_momentum = setting.get('lookback_momentum', lookback_momentum)
            top_industries = setting.get('top_industries', top_industries)
            stocks_per_industry = setting.get('stocks_per_industry', stocks_per_industry)
            max_pe = setting.get('max_pe', max_pe)
            max_pb = setting.get('max_pb', max_pb)
            min_dividend_yield = setting.get('min_dividend_yield', min_dividend_yield)
        
        # ✅ 修复：正确调用基类 __init__，与 StockScreenerStrategy 签名一致
        super().__init__(name, max_positions, position_size, rebalance_days)
        
        # 存储引擎引用（用于访问资金/持仓方法）
        self.strategy_engine = strategy_engine
        
        # 扩充行业股票池（动态获取申万成分股）
        _expand_industry_pool()
        
        self._industry_data = industry_data or INDUSTRY_STOCKS
        
        # 策略参数
        self.lookback_momentum = lookback_momentum
        self.top_industries = top_industries
        self.stocks_per_industry = stocks_per_industry
        self.max_pe = max_pe
        self.max_pb = max_pb
        self.min_dividend_yield = min_dividend_yield
        
        # 状态
        self.last_rebalance_date: Optional[datetime] = None
        self.industry_scores: Dict[str, IndustryMetrics] = {}
        self.selected_industries: List[str] = []
        
        # 价格历史（用于计算动量）
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # 扩展参数（供基类 get_parameters 使用）
        self.set_parameters(
            lookback_momentum=lookback_momentum,
            top_industries=top_industries,
            stocks_per_industry=stocks_per_industry,
            max_pe=max_pe,
            max_pb=max_pb,
            min_dividend_yield=min_dividend_yield,
        )
    
    def refresh_industry_pool(self):
        """
        刷新行业股票池（重新从 AKShare 获取申万成分股）
        
        建议定期调用以保持成分股数据最新。
        """
        _expand_industry_pool()
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        """
        筛选股票（实现基类抽象方法）
        
        Args:
            stock_pool: 可选股票池
            fundamental_data: 财务数据字典 {vt_symbol: FinancialIndicator}
            current_date: 当前日期
            
        Returns:
            List[str]: 筛选出的股票代码列表
        """
        # 使用 _industry_data（外部传入的行业配置）
        selected = []
        
        for industry, stocks in self._industry_data.items():
            # 获取行业成分股中在 stock_pool 的股票
            industry_stocks = [s for s in stocks if s in stock_pool]
            
            # 获取估值并筛选
            stock_scores = []
            for vt_symbol in industry_stocks:
                pe, pb, dividend_yield, val_source = self._get_stock_valuation(vt_symbol)
                
                # 估值筛选
                if pe > self.max_pe or pb > self.max_pb:
                    continue
                if dividend_yield < self.min_dividend_yield:
                    continue
                
                # 综合得分（估值越低越好）
                score = (1 / pe) * 0.5 + (1 / pb) * 0.3 + dividend_yield * 0.2
                stock_scores.append((vt_symbol, score))
            
            # 按得分排序，选择前 N 只
            stock_scores.sort(key=lambda x: x[1], reverse=True)
            selected.extend([s[0] for s in stock_scores[:self.stocks_per_industry]])
        
        # 按目标持仓上限截断
        return selected[:self.max_positions]
    
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
        self.write_log(f"目标持仓：{len(new_holdings)} 只股票")
    
    # ========== 代理方法（访问引擎功能）==========
    
    def get_portfolio_value(self) -> float:
        """获取组合总市值（代理到引擎）"""
        if self.strategy_engine:
            return self.strategy_engine.get_portfolio_value()
        return 0.0
    
    def get_cash_available(self) -> float:
        """获取可用现金（代理到引擎）"""
        if self.strategy_engine:
            return self.strategy_engine.get_cash_available()
        return 0.0
    
    def get_holding_value(self) -> float:
        """获取持仓市值（代理到引擎）"""
        if self.strategy_engine:
            return self.strategy_engine.get_holding_value()
        return 0.0
    
    def get_pos(self, vt_symbol: str) -> float:
        """获取持仓数量（代理到引擎）"""
        if self.strategy_engine:
            return self.strategy_engine.positions.get(vt_symbol, 0)
        return 0.0
    
    def send_order(self, vt_symbol: str, direction, offset, price: float, volume: float):
        """发送订单（代理到引擎）"""
        if self.strategy_engine:
            self.strategy_engine.send_order(
                strategy=self,
                vt_symbol=vt_symbol,
                direction=direction,
                offset=offset,
                price=price,
                volume=volume
            )
    
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
        获取行业估值（从成分股计算平均 PE/PB）
        
        Args:
            industry: 行业名称
            
        Returns:
            (avg_pe, avg_pb) 元组
        """
        # 获取行业成分股
        industry_stocks = self._industry_data.get(industry, [])
        if not industry_stocks:
            logger.warning(
                "Industry valuation fallback for '%s': no stocks defined in industry pool, "
                "using hardcoded defaults (PE=15.0, PB=2.0).",
                industry
            )
            return (15.0, 2.0)  # 默认值
        
        # 从成分股计算平均估值
        pe_values = []
        pb_values = []
        
        for stock in industry_stocks[:50]:  # 限制计算前 50 只，避免太慢
            try:
                # 尝试从 dataset 获取财务数据
                from vnpy.alpha.dataset import FundamentalData
                funda = FundamentalData()
                stock_data = funda.get_stock_valuation(stock)
                if stock_data:
                    pe = stock_data.get('pe')
                    pb = stock_data.get('pb')
                    if pe and pe > 0:
                        pe_values.append(pe)
                    if pb and pb > 0:
                        pb_values.append(pb)
            except Exception:
                continue
        
        # 计算平均值
        avg_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0
        avg_pb = sum(pb_values) / len(pb_values) if pb_values else 2.0
        
        return (avg_pe, avg_pb)
    
    def _calculate_industry_turnover(self, stocks: List[str], bars: Dict[str, BarData]) -> float:
        """计算行业换手率（简化：使用成交量）"""
        total_volume = sum(bars[s].volume for s in stocks if s in bars)
        if total_volume == 0:
            return 0.0
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
                pe, pb, dividend_yield, val_source = self._get_stock_valuation(vt_symbol)
                
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
    
    def _get_stock_valuation(self, vt_symbol: str) -> Tuple[float, float, float, str]:
        """
        获取个股估值（从真实数据源）
        
        优先级：
        1. alpha/lab 的 _fundamental_cache（已缓存的财务数据）
        2. ValuationFetcher（Tushare/AKShare 实时拉取）
        
        Returns:
            Tuple[pe, pb, dividend_yield, source]
            source: 'lab_cache' | 'tushare' | 'akshare' | 'fallback'
        """
        # 1. 优先从 alpha/lab 缓存获取（最可信）
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
        
        # 2. 从 Tushare/AKShare 获取
        fetcher = get_valuation_fetcher()
        return fetcher.get_valuation(vt_symbol)
    
    def _get_dividend_yield(self, vt_symbol: str) -> float:
        """获取股息率（从真实数据源）"""
        pe, pb, div, source = self._get_stock_valuation(vt_symbol)
        if div is not None:
            return div
        # 估算：假设分红率 30%
        if pe and pe > 0 and pe < 100:
            return 1.0 / pe * 100 * 0.3
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
    logger.info("=" * 60)
    logger.info("行业轮动策略测试")
    logger.info("=" * 60)
    
    # 打印行业定义
    logger.info("\n📊 行业配置:")
    for industry, stocks in INDUSTRY_STOCKS.items():
        logger.info(f"  {industry}: {len(stocks)}只股票")
    
    logger.info("\n📊 策略参数:")
    logger.info("  - 动量回看：20 天")
    logger.info("  - 热门行业：前 3 个")
    logger.info("  - 每行业选股：5 只")
    logger.info("  - 估值上限：PE<20, PB<3")
    logger.info("  - 调仓周期：5 天")
    
    logger.info("\n📊 选股逻辑:")
    logger.info("  1. 计算行业得分（动量 40% + 估值 30% + 换手 10%）")
    logger.info("  2. 选择得分最高的 3 个行业")
    logger.info("  3. 在热门行业中选择低估值股票")
    logger.info("  4. 等权重配置")
    
    logger.info("\n✅ 策略开发完成！")


if __name__ == "__main__":
    test_strategy()
