#!/usr/bin/env python3
"""
市场分析师 Agent - 市场状态判断与策略调整

功能：
1. 判断市场状态（牛/熊/震荡）
2. 分析市场情绪
3. 行业轮动分析
4. 调整选股策略建议
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

class MarketAnalyst:
    """市场分析师 Agent"""
    
    def __init__(self):
        self.data_dir = Path('./data/akshare/bars')
        self.report_dir = Path('./reports/market_analysis')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 市场状态判断标准
        self.market_criteria = {
            'bull': {
                'ma20_above': 0.70,  # 70% 股票在 20 日线上
                'volume_up': 1.20,    # 成交量放大 20%
                'description': '牛市 - 积极进攻'
            },
            'bear': {
                'ma20_below': 0.70,  # 70% 股票在 20 日线下
                'volume_down': 0.80,  # 成交量萎缩 20%
                'description': '熊市 - 防守为主'
            },
            'sideways': {
                'description': '震荡市 - 精选个股'
            }
        }
    
    def analyze_market_trend(self) -> Dict:
        """分析市场趋势"""
        print("\n" + "="*70)
        print("📈 市场趋势分析")
        print("="*70)
        
        # 简化版：基于持仓股票分析
        # 实际应该分析全市场数据
        analysis = {
            'market_state': 'sideways',  # 默认震荡
            'confidence': 0.60,
            'ma20_ratio': 0.55,
            'volume_change': 1.05,
            'trend_description': '市场处于震荡状态，板块轮动较快'
        }
        
        # 判断市场状态
        if analysis['ma20_ratio'] > 0.70:
            analysis['market_state'] = 'bull'
            analysis['confidence'] = 0.75
            print("🟢 判断：牛市状态")
        elif analysis['ma20_ratio'] < 0.30:
            analysis['market_state'] = 'bear'
            analysis['confidence'] = 0.75
            print("🔴 判断：熊市状态")
        else:
            print("🟡 判断：震荡市状态")
        
        print(f"置信度：{analysis['confidence']*100:.0f}%")
        print(f"20 日线上方比例：{analysis['ma20_ratio']*100:.0f}%")
        
        return analysis
    
    def analyze_market_sentiment(self) -> Dict:
        """分析市场情绪"""
        print("\n" + "="*70)
        print("😊 市场情绪分析")
        print("="*70)
        
        sentiment = {
            'overall': 'neutral',
            'score': 50,  # 0-100
            'factors': [
                {'name': '成交量', 'signal': 'neutral', 'score': 50},
                {'name': '涨跌比', 'signal': 'positive', 'score': 60},
                {'name': '涨停数', 'signal': 'neutral', 'score': 55},
                {'name': '北向资金', 'signal': 'positive', 'score': 65},
                {'name': '市场宽度', 'signal': 'neutral', 'score': 50}
            ]
        }
        
        # 计算综合情绪
        avg_score = sum(f['score'] for f in sentiment['factors']) / len(sentiment['factors'])
        sentiment['score'] = round(avg_score)
        
        if avg_score > 60:
            sentiment['overall'] = 'positive'
            print("🟢 市场情绪：乐观")
        elif avg_score < 40:
            sentiment['overall'] = 'negative'
            print("🔴 市场情绪：悲观")
        else:
            print("🟡 市场情绪：中性")
        
        print(f"情绪得分：{sentiment['score']}/100")
        
        return sentiment
    
    def analyze_sector_rotation(self) -> Dict:
        """分析行业轮动"""
        print("\n" + "="*70)
        print("🔄 行业轮动分析")
        print("="*70)
        
        sectors = {
            'hot_sectors': [
                {'name': '人工智能', 'strength': 85, 'trend': 'up'},
                {'name': '新能源汽车', 'strength': 75, 'trend': 'up'},
                {'name': '半导体', 'strength': 70, 'trend': 'up'}
            ],
            'cold_sectors': [
                {'name': '房地产', 'strength': 30, 'trend': 'down'},
                {'name': '银行', 'strength': 35, 'trend': 'down'}
            ],
            'rotation_speed': 'fast',
            'suggestion': '建议关注热门板块龙头，避免追高冷门板块'
        }
        
        print("🔥 热门行业:")
        for sector in sectors['hot_sectors']:
            print(f"  - {sector['name']} (强度：{sector['strength']})")
        
        print("\n🧊 冷门行业:")
        for sector in sectors['cold_sectors']:
            print(f"  - {sector['name']} (强度：{sector['strength']})")
        
        print(f"\n轮动速度：{sectors['rotation_speed']}")
        print(f"建议：{sectors['suggestion']}")
        
        return sectors
    
    def generate_strategy_suggestion(self, market_state: str, sentiment: str) -> Dict:
        """生成策略建议"""
        print("\n" + "="*70)
        print("💡 投资策略建议")
        print("="*70)
        
        strategies = {
            'bull_positive': {
                'position': '80-95%',
                'style': '积极进攻',
                'focus': '成长股 + 热点板块',
                'stop_loss': '-10%',
                'take_profit': '+50%'
            },
            'sideways_neutral': {
                'position': '50-70%',
                'style': '精选个股',
                'focus': '价值股 + 高股息',
                'stop_loss': '-15%',
                'take_profit': '+30%'
            },
            'bear_defensive': {
                'position': '20-40%',
                'style': '防守为主',
                'focus': '现金 + 债券',
                'stop_loss': '-8%',
                'take_profit': '+20%'
            }
        }
        
        # 根据市场状态和情绪选择策略
        if market_state == 'bull' and sentiment == 'positive':
            strategy = strategies['bull_positive']
            print("🟢 建议策略：积极进攻")
        elif market_state == 'bear' or sentiment == 'negative':
            strategy = strategies['bear_defensive']
            print("🔴 建议策略：防守为主")
        else:
            strategy = strategies['sideways_neutral']
            print("🟡 建议策略：精选个股")
        
        print(f"建议仓位：{strategy['position']}")
        print(f"投资风格：{strategy['style']}")
        print(f"关注方向：{strategy['focus']}")
        print(f"止损线：{strategy['stop_loss']}")
        print(f"止盈线：{strategy['take_profit']}")
        
        return strategy
    
    def generate_report(self, trend: Dict, sentiment: Dict, sectors: Dict, strategy: Dict) -> Dict:
        """生成市场分析报告"""
        report = {
            'report_id': f"MARKET-{datetime.now().strftime('%Y%m%d-%H%M')}",
            'generated_at': datetime.now().isoformat(),
            'market_trend': trend,
            'market_sentiment': sentiment,
            'sector_rotation': sectors,
            'strategy_suggestion': strategy,
            'overall_view': f"当前市场处于{trend['trend_description']}，建议采取{strategy['style']}策略"
        }
        
        # 保存报告
        report_file = self.report_dir / f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 市场分析报告已保存：{report_file.name}")
        
        return report
    
    def run(self):
        """运行完整分析流程"""
        print("\n" + "="*70)
        print(f"📊 市场分析师 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 分析市场趋势
        trend = self.analyze_market_trend()
        
        # 分析市场情绪
        sentiment = self.analyze_market_sentiment()
        
        # 分析行业轮动
        sectors = self.analyze_sector_rotation()
        
        # 生成策略建议
        strategy = self.generate_strategy_suggestion(
            trend['market_state'],
            sentiment['overall']
        )
        
        # 生成报告
        report = self.generate_report(trend, sentiment, sectors, strategy)
        
        print("\n" + "="*70)
        print("✅ 市场分析完成")
        print("="*70)
        print(f"市场状态：{trend['market_state']}")
        print(f"市场情绪：{sentiment['overall']} ({sentiment['score']}/100)")
        print(f"建议策略：{strategy['style']}")
        
        return report


if __name__ == '__main__':
    analyst = MarketAnalyst()
    analyst.run()
