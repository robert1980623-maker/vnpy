#!/usr/bin/env python3
"""
涨停龙头策略测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.limit_up_leader import (
    LimitUpLeaderStrategy,
    StockInfo,
    LimitUpStock,
    StrategySignal,
)


class TestLimitUpLeaderStrategy:
    """涨停龙头策略测试类"""
    
    @pytest.fixture
    def strategy(self):
        """创建策略实例"""
        return LimitUpLeaderStrategy()
    
    def test_initialization(self, strategy):
        """测试初始化"""
        assert strategy.config is not None
        assert 'min_limit_up_days' in strategy.config
        assert strategy.config['min_limit_up_days'] == 2
        assert strategy.limit_up_stocks == []
        assert strategy.leader_candidates == []
    
    def test_stock_info_creation(self):
        """测试股票信息创建"""
        stock = StockInfo(
            symbol='000001',
            name='平安银行',
            price=10.5,
            change_pct=10.0,
            volume=1000000,
            amount=10500000,
            turnover_rate=2.5,
            pe_ratio=5.0,
            pb_ratio=0.8,
            market_cap=200e8,
            industry='银行',
            concept='金融',
        )
        
        assert stock.symbol == '000001'
        assert stock.name == '平安银行'
        assert stock.change_pct == 10.0
    
    def test_limit_up_stock_creation(self):
        """测试涨停股票信息创建"""
        stock = LimitUpStock(
            symbol='000001',
            name='平安银行',
            limit_up_days=3,
            first_limit_up_date='20260315',
            last_limit_up_date='20260318',
            industry='银行',
            concept='金融',
            volume_ratio=2.5,
            amount=10500000,
            market_cap=200e8,
        )
        
        assert stock.limit_up_days == 3
        assert stock.volume_ratio == 2.5
        assert stock.score == 0.0  # 初始评分为 0
    
    def test_calculate_industry_effect(self, strategy):
        """测试板块效应计算"""
        stocks = [
            StockInfo('000001', '股票 1', 10, 10, 0, 0, 0, 0, 0, 0, '科技', 'AI'),
            StockInfo('000002', '股票 2', 20, 10, 0, 0, 0, 0, 0, 0, '科技', '芯片'),
            StockInfo('000003', '股票 3', 30, 10, 0, 0, 0, 0, 0, 0, '金融', '银行'),
        ]
        
        # 科技板块有 2 只涨停
        effect = strategy.calculate_industry_effect('科技', stocks)
        assert effect == 2
        
        # AI 概念有 1 只涨停
        effect = strategy.calculate_industry_effect('AI', stocks)
        assert effect == 1
        
        # 不存在的板块
        effect = strategy.calculate_industry_effect('不存在', stocks)
        assert effect == 0
    
    def test_calculate_leader_score_basic(self, strategy):
        """测试龙头评分计算 (基础)"""
        stock = LimitUpStock(
            symbol='000001',
            name='测试股票',
            limit_up_days=3,
            first_limit_up_date='',
            last_limit_up_date='20260318',
            industry='科技',
            concept='AI',
            volume_ratio=2.0,
            amount=10000000,
            market_cap=100e8,
        )
        
        stocks = [
            StockInfo('000001', '测试 1', 10, 10, 0, 0, 0, 0, 0, 0, '科技', 'AI'),
            StockInfo('000002', '测试 2', 20, 10, 0, 0, 0, 0, 0, 0, '科技', 'AI'),
        ]
        
        score = strategy.calculate_leader_score(stock, stocks)
        
        # 评分应该在 0-100 之间
        assert 0 <= score <= 100
        
        # 3 连板应该有不错的分数
        assert score > 50
    
    def test_calculate_leader_score_high_continuous(self, strategy):
        """测试高连续涨停的评分"""
        stock_3days = LimitUpStock(
            symbol='000001',
            name='3 连板',
            limit_up_days=3,
            first_limit_up_date='',
            last_limit_up_date='20260318',
            industry='科技',
            concept='AI',
            volume_ratio=2.0,
            amount=10000000,
            market_cap=100e8,
        )
        
        stock_5days = LimitUpStock(
            symbol='000002',
            name='5 连板',
            limit_up_days=5,
            first_limit_up_date='',
            last_limit_up_date='20260318',
            industry='科技',
            concept='AI',
            volume_ratio=2.0,
            amount=10000000,
            market_cap=100e8,
        )
        
        stocks = []
        
        score_3 = strategy.calculate_leader_score(stock_3days, stocks)
        score_5 = strategy.calculate_leader_score(stock_5days, stocks)
        
        # 5 连板应该比 3 连板分数高
        assert score_5 > score_3
    
    def test_strategy_signal_creation(self):
        """测试交易信号创建"""
        signal = StrategySignal(
            symbol='000001',
            action='buy',
            price=10.5,
            quantity=1000,
            reason='龙头候选，评分 85',
            confidence=0.85,
            timestamp='2026-03-18T17:00:00',
        )
        
        assert signal.action == 'buy'
        assert signal.confidence == 0.85
        assert signal.quantity == 1000
    
    def test_config_customization(self):
        """测试自定义配置"""
        custom_config = {
            'min_limit_up_days': 3,
            'max_position_count': 3,
            'stop_loss_pct': -5.0,
        }
        
        strategy = LimitUpLeaderStrategy(custom_config)
        
        assert strategy.config['min_limit_up_days'] == 3
        assert strategy.config['max_position_count'] == 3
        assert strategy.config['stop_loss_pct'] == -5.0
        
        # 默认配置应该保留
        assert 'take_profit_pct' in strategy.config
    
    def test_get_daily_report_structure(self, strategy):
        """测试每日报告结构"""
        report = strategy.get_daily_report('20260318')
        
        # 检查报告结构
        assert 'date' in report
        assert 'total_limit_up' in report
        assert 'leader_candidates' in report
        assert 'current_positions' in report
        assert 'leaders' in report
        assert 'positions' in report
        assert 'config' in report
        
        assert report['date'] == '20260318'
        assert isinstance(report['leaders'], list)
        assert isinstance(report['positions'], list)


class TestLimitUpLeaderStrategyIntegration:
    """集成测试"""
    
    @pytest.mark.skip(reason="需要真实数据源")
    def test_fetch_limit_up_stocks_real(self):
        """测试获取真实涨停数据"""
        strategy = LimitUpLeaderStrategy()
        
        # 获取最近交易日的数据
        stocks = strategy.fetch_limit_up_stocks()
        
        # 应该有数据
        assert len(stocks) > 0
        
        # 检查数据结构
        for stock in stocks:
            assert stock.symbol != ''
            assert stock.name != ''
            assert stock.change_pct >= 9.5  # 涨停
    
    @pytest.mark.skip(reason="需要真实数据源")
    def test_select_leaders_real(self):
        """测试真实筛选龙头"""
        strategy = LimitUpLeaderStrategy()
        
        leaders = strategy.select_leaders()
        
        # 应该有龙头候选
        assert len(leaders) > 0
        
        # 检查龙头质量
        for leader in leaders:
            assert leader.limit_up_days >= 2
            assert leader.volume_ratio >= 1.5
            assert 0 <= leader.score <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
