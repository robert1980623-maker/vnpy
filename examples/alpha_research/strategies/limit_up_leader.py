"""
涨停龙头策略

策略逻辑:
1. 识别涨停股票 (10% 或 20% 涨幅)
2. 筛选龙头特征 (连续涨停、板块效应、成交量放大)
3. 在龙头确立后介入，享受溢价
4. 严格止损，控制风险

核心指标:
- 涨停强度：连续涨停天数
- 板块效应：同板块涨停股票数量
- 成交量：相对前期放大倍数
- 市场情绪：涨停家数/跌停家数
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import akshare as ak
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StockInfo:
    """股票信息"""
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    turnover_rate: float
    pe_ratio: float
    pb_ratio: float
    market_cap: float
    industry: str
    concept: str


@dataclass
class LimitUpStock:
    """涨停股票信息"""
    symbol: str
    name: str
    limit_up_days: int  # 连续涨停天数
    first_limit_up_date: str
    last_limit_up_date: str
    industry: str
    concept: str
    volume_ratio: float  # 成交量放大倍数
    amount: float
    market_cap: float
    score: float = 0.0  # 龙头评分


@dataclass
class StrategySignal:
    """交易信号"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    price: float
    quantity: int
    reason: str
    confidence: float  # 0-1
    timestamp: str


class LimitUpLeaderStrategy:
    """
    涨停龙头策略
    
    核心逻辑:
    1. 每日收盘后识别所有涨停股票
    2. 计算龙头评分 (连续涨停 + 板块效应 + 成交量 + 市值)
    3. 选择评分最高的前 N 只作为龙头候选
    4. 次日开盘根据竞价情况决定是否介入
    5. 持有期间监控，破板或达到目标位止盈
    """
    
    # 配置参数
    CONFIG = {
        'min_limit_up_days': 2,  # 最小连续涨停天数
        'max_position_count': 5,  # 最大持仓数量
        'stop_loss_pct': -8.0,  # 止损百分比
        'take_profit_pct': 20.0,  # 止盈百分比
        'volume_ratio_threshold': 1.5,  # 成交量放大阈值
        'min_market_cap': 50e8,  # 最小市值 (50 亿)
        'max_market_cap': 500e8,  # 最大市值 (500 亿)
        'leader_score_weights': {
            'limit_up_days': 0.4,  # 连续涨停权重
            'industry_effect': 0.25,  # 板块效应权重
            'volume_ratio': 0.2,  # 成交量权重
            'market_cap': 0.15,  # 市值权重 (偏好中小盘)
        }
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化策略"""
        self.config = {**self.CONFIG, **(config or {})}
        self.limit_up_stocks: List[LimitUpStock] = []
        self.leader_candidates: List[LimitUpStock] = []
        self.positions: Dict[str, Dict] = {}  # 持仓信息
        self.trade_history: List[Dict] = []
        
        # 数据缓存路径
        self.cache_dir = Path(__file__).parent.parent / 'cache' / 'limit_up_strategy'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"涨停龙头策略初始化完成，配置：{self.config}")
    
    def fetch_limit_up_stocks(self, date: Optional[str] = None) -> List[StockInfo]:
        """
        获取指定日期的涨停股票列表
        
        Args:
            date: 日期，格式 YYYY-MM-DD，默认为昨日
            
        Returns:
            涨停股票信息列表
        """
        if date is None:
            # 获取最近交易日
            date = self._get_last_trading_date()
        
        try:
            # 使用 AKShare 获取涨停池数据
            logger.info(f"获取 {date} 的涨停股票数据...")
            
            # 获取沪深 A 股涨停数据
            df = ak.stock_zt_pool_em(date=date)
            
            if df.empty:
                logger.warning(f"{date} 没有涨停股票数据")
                return []
            
            stocks = []
            for _, row in df.iterrows():
                stock = StockInfo(
                    symbol=row.get('代码', ''),
                    name=row.get('名称', ''),
                    price=row.get('最新价', 0),
                    change_pct=row.get('涨跌幅', 0),
                    volume=row.get('成交量', 0),
                    amount=row.get('成交额', 0),
                    turnover_rate=row.get('换手率', 0),
                    pe_ratio=row.get('市盈率', 0),
                    pb_ratio=row.get('市净率', 0),
                    market_cap=row.get('总市值', 0),
                    industry=row.get('行业', ''),
                    concept=row.get('概念', ''),
                )
                stocks.append(stock)
            
            logger.info(f"获取到 {len(stocks)} 只涨停股票")
            return stocks
            
        except Exception as e:
            logger.error(f"获取涨停股票失败：{e}")
            return []
    
    def analyze_continuous_limit_up(self, symbol: str, end_date: str) -> int:
        """
        分析股票连续涨停天数
        
        Args:
            symbol: 股票代码
            end_date: 结束日期
            
        Returns:
            连续涨停天数
        """
        try:
            # 获取历史行情
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                   end_date=end_date, adjust="qfq")
            
            if df.empty:
                return 0
            
            # 计算每日涨跌幅
            df['pct_change'] = df['涨跌幅'].astype(float)
            
            # 从后往前统计连续涨停天数
            continuous_days = 0
            for i in range(len(df) - 1, -1, -1):
                pct = df.iloc[i]['pct_change']
                # 判断是否涨停 (考虑 10% 和 20% 两种情况)
                if pct >= 9.5:  # 留一点容差
                    continuous_days += 1
                else:
                    break
            
            return continuous_days
            
        except Exception as e:
            logger.error(f"分析 {symbol} 连续涨停天数失败：{e}")
            return 0
    
    def calculate_volume_ratio(self, symbol: str, date: str) -> float:
        """
        计算成交量放大倍数 (当日成交量 / 前 5 日平均成交量)
        
        Args:
            symbol: 股票代码
            date: 日期
            
        Returns:
            成交量放大倍数
        """
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                   end_date=date, adjust="qfq")
            
            if len(df) < 6:
                return 1.0
            
            # 当日成交量
            current_volume = df.iloc[-1]['成交量']
            
            # 前 5 日平均成交量
            prev_5_avg = df.iloc[-6:-1]['成交量'].mean()
            
            if prev_5_avg == 0:
                return 1.0
            
            return current_volume / prev_5_avg
            
        except Exception as e:
            logger.error(f"计算 {symbol} 成交量倍数失败：{e}")
            return 1.0
    
    def calculate_industry_effect(self, industry: str, limit_up_stocks: List[StockInfo]) -> int:
        """
        计算板块效应 (同板块涨停股票数量)
        
        Args:
            industry: 行业/概念
            limit_up_stocks: 涨停股票列表
            
        Returns:
            同板块涨停数量
        """
        if not industry:
            return 0
        
        count = 0
        for stock in limit_up_stocks:
            if industry in (stock.industry or '') or industry in (stock.concept or ''):
                count += 1
        
        return count
    
    def calculate_leader_score(self, stock: LimitUpStock, 
                               limit_up_stocks: List[StockInfo]) -> float:
        """
        计算龙头评分
        
        评分维度:
        1. 连续涨停天数 (越高越好)
        2. 板块效应 (同板块涨停数量，越高越好)
        3. 成交量放大 (适度放大最好)
        4. 市值 (中小盘偏好)
        
        Args:
            stock: 涨停股票信息
            limit_up_stocks: 所有涨停股票
            
        Returns:
            综合评分 (0-100)
        """
        weights = self.config['leader_score_weights']
        
        # 1. 连续涨停评分 (0-40 分)
        limit_up_score = min(stock.limit_up_days * 10, 40)
        
        # 2. 板块效应评分 (0-25 分)
        industry_count = self.calculate_industry_effect(stock.industry, limit_up_stocks)
        industry_score = min(industry_count * 5, 25)
        
        # 3. 成交量评分 (0-20 分)
        # 成交量放大 1.5-3 倍最佳
        if 1.5 <= stock.volume_ratio <= 3.0:
            volume_score = 20
        elif stock.volume_ratio < 1.5:
            volume_score = stock.volume_ratio / 1.5 * 20
        else:
            volume_score = max(0, 20 - (stock.volume_ratio - 3.0) * 5)
        
        # 4. 市值评分 (0-15 分)
        # 50-200 亿最佳
        market_cap = stock.market_cap / 1e8  # 转换为亿
        if 50 <= market_cap <= 200:
            market_score = 15
        elif market_cap < 50:
            market_score = market_cap / 50 * 15
        else:
            market_score = max(0, 15 - (market_cap - 200) / 300 * 15)
        
        # 加权总分
        total_score = (
            limit_up_score * weights['limit_up_days'] / 0.4 +
            industry_score * weights['industry_effect'] / 0.25 +
            volume_score * weights['volume_ratio'] / 0.2 +
            market_score * weights['market_cap'] / 0.15
        )
        
        return round(total_score, 2)
    
    def select_leaders(self, date: Optional[str] = None) -> List[LimitUpStock]:
        """
        筛选龙头股票
        
        Args:
            date: 日期，默认昨日
            
        Returns:
            龙头候选列表 (按评分排序)
        """
        # 1. 获取涨停股票
        stocks = self.fetch_limit_up_stocks(date)
        if not stocks:
            return []
        
        # 2. 分析每只股票，构建 LimitUpStock 对象
        limit_up_stocks = []
        for stock in stocks:
            # 分析连续涨停天数
            continuous_days = self.analyze_continuous_limit_up(stock.symbol, date)
            
            # 跳过不满足最小天数的
            if continuous_days < self.config['min_limit_up_days']:
                continue
            
            # 计算成交量放大倍数
            volume_ratio = self.calculate_volume_ratio(stock.symbol, date)
            
            # 跳过成交量不足的
            if volume_ratio < self.config['volume_ratio_threshold']:
                continue
            
            # 检查市值范围
            if stock.market_cap < self.config['min_market_cap']:
                continue
            if stock.market_cap > self.config['max_market_cap']:
                continue
            
            limit_up_stock = LimitUpStock(
                symbol=stock.symbol,
                name=stock.name,
                limit_up_days=continuous_days,
                first_limit_up_date='',  # TODO: 实现
                last_limit_up_date=date,
                industry=stock.industry,
                concept=stock.concept,
                volume_ratio=volume_ratio,
                amount=stock.amount,
                market_cap=stock.market_cap,
            )
            
            # 计算龙头评分
            limit_up_stock.score = self.calculate_leader_score(limit_up_stock, stocks)
            
            limit_up_stocks.append(limit_up_stock)
        
        # 3. 按评分排序
        limit_up_stocks.sort(key=lambda x: x.score, reverse=True)
        
        # 4. 保存结果
        self.limit_up_stocks = limit_up_stocks
        self.leader_candidates = limit_up_stocks[:self.config['max_position_count']]
        
        # 5. 缓存到文件
        self._cache_leaders(date)
        
        logger.info(f"筛选出 {len(self.leader_candidates)} 只龙头候选")
        for leader in self.leader_candidates:
            logger.info(f"  {leader.symbol} {leader.name}: 评分={leader.score}, "
                       f"连板={leader.limit_up_days}, 量比={leader.volume_ratio:.2f}")
        
        return self.leader_candidates
    
    def generate_signals(self, current_prices: Dict[str, float]) -> List[StrategySignal]:
        """
        生成交易信号
        
        Args:
            current_prices: 当前价格字典 {symbol: price}
            
        Returns:
            交易信号列表
        """
        signals = []
        
        # 1. 检查持仓，生成卖出信号
        for symbol, position in list(self.positions.items()):
            cost_price = position['cost_price']
            current_price = current_prices.get(symbol, 0)
            
            if current_price == 0:
                continue
            
            # 计算盈亏比例
            pnl_pct = (current_price - cost_price) / cost_price * 100
            
            # 止损检查
            if pnl_pct <= self.config['stop_loss_pct']:
                signal = StrategySignal(
                    symbol=symbol,
                    action='sell',
                    price=current_price,
                    quantity=position['quantity'],
                    reason=f'止损：盈亏{pnl_pct:.2f}%',
                    confidence=0.9,
                    timestamp=datetime.now().isoformat(),
                )
                signals.append(signal)
                logger.warning(f"触发止损：{symbol}, 盈亏={pnl_pct:.2f}%")
                continue
            
            # 止盈检查
            if pnl_pct >= self.config['take_profit_pct']:
                signal = StrategySignal(
                    symbol=symbol,
                    action='sell',
                    price=current_price,
                    quantity=position['quantity'],
                    reason=f'止盈：盈亏{pnl_pct:.2f}%',
                    confidence=0.85,
                    timestamp=datetime.now().isoformat(),
                )
                signals.append(signal)
                logger.info(f"触发止盈：{symbol}, 盈亏={pnl_pct:.2f}%")
                continue
            
            # 检查是否还是龙头 (不在候选列表中则卖出)
            is_leader = any(l.symbol == symbol for l in self.leader_candidates)
            if not is_leader and len(self.leader_candidates) > 0:
                signal = StrategySignal(
                    symbol=symbol,
                    action='sell',
                    price=current_price,
                    quantity=position['quantity'],
                    reason='不再是龙头候选',
                    confidence=0.7,
                    timestamp=datetime.now().isoformat(),
                )
                signals.append(signal)
                logger.info(f"龙头地位丧失：{symbol}")
        
        # 2. 检查龙头候选，生成买入信号
        current_positions = len(self.positions)
        available_slots = self.config['max_position_count'] - current_positions
        
        for leader in self.leader_candidates:
            if available_slots <= 0:
                break
            
            # 已持仓则跳过
            if leader.symbol in self.positions:
                continue
            
            # 检查是否有价格
            current_price = current_prices.get(leader.symbol, 0)
            if current_price == 0:
                continue
            
            # 生成买入信号
            signal = StrategySignal(
                symbol=leader.symbol,
                action='buy',
                price=current_price,
                quantity=0,  # TODO: 根据仓位计算
                reason=f'龙头候选：评分={leader.score}, 连板={leader.limit_up_days}',
                confidence=leader.score / 100,
                timestamp=datetime.now().isoformat(),
            )
            signals.append(signal)
            available_slots -= 1
            
            logger.info(f"生成买入信号：{leader.symbol}, 评分={leader.score}")
        
        return signals
    
    def execute_signal(self, signal: StrategySignal) -> bool:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            是否执行成功
        """
        try:
            if signal.action == 'buy':
                # 买入逻辑
                self.positions[signal.symbol] = {
                    'cost_price': signal.price,
                    'quantity': signal.quantity,
                    'entry_date': signal.timestamp,
                    'symbol': signal.symbol,
                    'name': '',  # TODO: 补充
                }
                
                logger.info(f"买入：{signal.symbol}, 价格={signal.price}, "
                           f"数量={signal.quantity}, 原因={signal.reason}")
                
            elif signal.action == 'sell':
                # 卖出逻辑
                if signal.symbol in self.positions:
                    position = self.positions[signal.symbol]
                    pnl = (signal.price - position['cost_price']) * position['quantity']
                    
                    # 记录交易历史
                    self.trade_history.append({
                        'symbol': signal.symbol,
                        'action': 'sell',
                        'price': signal.price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'exit_date': signal.timestamp,
                        'entry_date': position['entry_date'],
                        'reason': signal.reason,
                    })
                    
                    # 清除持仓
                    del self.positions[signal.symbol]
                    
                    logger.info(f"卖出：{signal.symbol}, 价格={signal.price}, "
                               f"数量={signal.quantity}, 盈亏={pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行信号失败：{e}")
            return False
    
    def _get_last_trading_date(self) -> str:
        """获取最近交易日"""
        # 简单实现：返回昨日
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime('%Y%m%d')
    
    def _cache_leaders(self, date: str):
        """缓存龙头候选到文件"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        cache_file = self.cache_dir / f'leaders_{date}.json'
        
        data = {
            'date': date,
            'leaders': [
                {
                    'symbol': l.symbol,
                    'name': l.name,
                    'score': l.score,
                    'limit_up_days': l.limit_up_days,
                    'volume_ratio': l.volume_ratio,
                    'industry': l.industry,
                    'market_cap': l.market_cap,
                }
                for l in self.leader_candidates
            ],
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"龙头候选已缓存：{cache_file}")
    
    def get_daily_report(self, date: Optional[str] = None) -> Dict:
        """
        生成每日策略报告
        
        Args:
            date: 日期
            
        Returns:
            报告字典
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        report = {
            'date': date,
            'total_limit_up': len(self.limit_up_stocks),
            'leader_candidates': len(self.leader_candidates),
            'current_positions': len(self.positions),
            'today_signals': 0,  # TODO: 统计
            'leaders': [
                {
                    'symbol': l.symbol,
                    'name': l.name,
                    'score': l.score,
                    'limit_up_days': l.limit_up_days,
                    'volume_ratio': l.volume_ratio,
                }
                for l in self.leader_candidates
            ],
            'positions': [
                {
                    'symbol': p['symbol'],
                    'cost_price': p['cost_price'],
                    'quantity': p['quantity'],
                    'entry_date': p['entry_date'],
                }
                for p in self.positions.values()
            ],
            'config': self.config,
        }
        
        return report


# 快捷函数
def run_daily_strategy(date: Optional[str] = None) -> Dict:
    """
    运行每日策略
    
    Args:
        date: 日期，默认昨日
        
    Returns:
        策略报告
    """
    strategy = LimitUpLeaderStrategy()
    strategy.select_leaders(date)
    return strategy.get_daily_report(date)


if __name__ == '__main__':
    # 测试运行
    logging.basicConfig(level=logging.INFO)
    
    report = run_daily_strategy()
    print(json.dumps(report, ensure_ascii=False, indent=2))
