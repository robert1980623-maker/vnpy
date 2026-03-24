#!/usr/bin/env python3
"""
综合消息面分析器

整合:
- 个股新闻/公告
- 宏观政策
- 行业政策
- 国际形势 (中美关系、全球经济、地缘政治、行业竞争)

输出:
- 综合评分 (基本面 40% + 消息面 25% + 时政面 20% + 国际形势 15%)
- 投资建议
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from logger import TaskLogger


class ComprehensiveAnalyzer:
    """综合消息面分析器"""
    
    def __init__(self):
        self.data_dir = Path('./data')
        self.reports_dir = Path('./reports/comprehensive')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 权重配置
        self.weights = {
            'fundamental': 0.40,    # 基本面
            'news': 0.25,           # 消息面 (个股新闻)
            'policy': 0.20,         # 时政面 (政策)
            'geopolitics': 0.15     # 国际形势
        }
        
        # 行业映射
        self.sector_mapping = {
            '300750': '新能源汽车', '601456': '券商', '600027': '电力',
            '002422': '医药', '000975': '有色金属', '300418': '传媒',
            '603893': '半导体', '600161': '医药', '002384': '电子',
            '600000': '银行', '002600': '电子', '002594': '新能源汽车',
            '300476': '电子', '688472': '新能源', '601398': '银行',
            '601298': '港口', '300803': '金融科技', '000999': '医药',
            '600026': '航运', '600036': '银行', '600415': '商贸',
            '000651': '家电', '601825': '银行', '000630': '有色金属',
            '000001': '银行', '002028': '电力设备', '600482': '船舶',
            '601888': '旅游', '600160': '化工', '688169': '家电',
            '600522': '通信', '300251': '传媒', '601018': '港口',
            '302132': '军工', '600377': '交通', '601127': '汽车',
            '600066': '汽车', '688082': '半导体', '300442': '数据中心',
            '002463': '电子', '688009': '轨道交通', '603296': '电子',
            '002625': '军工', '001391': '物流', '000807': '有色金属',
            '000858': '白酒', '688506': '医药', '300866': '消费电子'
        }
    
    def load_policy_data(self, date=None):
        """加载政策数据"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        macro_file = self.data_dir / 'policy' / f'macro_policy_{date}.json'
        industry_file = self.data_dir / 'policy' / f'industry_policy_{date}.json'
        
        macro = []
        industry = []
        
        if macro_file.exists():
            with open(macro_file, 'r', encoding='utf-8') as f:
                macro = json.load(f)
        
        if industry_file.exists():
            with open(industry_file, 'r', encoding='utf-8') as f:
                industry = json.load(f)
        
        return {'macro': macro, 'industry': industry}
    
    def load_geopolitics_data(self, date=None):
        """加载国际形势数据"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        data = {
            'us_china': [],
            'global_economy': [],
            'geopolitics': [],
            'industry_competition': []
        }
        
        for key in data.keys():
            filepath = self.data_dir / 'geopolitics' / f'{key}_{date}.json'
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data[key] = json.load(f)
        
        return data
    
    def load_news_data(self, symbol, date=None):
        """加载个股新闻数据"""
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 尝试多个日期
        for d in [date, (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]:
            filepath = self.data_dir / 'news' / f'{symbol.split(".")[0]}_news_{d}.json'
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        return []
    
    def analyze_policy_impact(self, symbol, policy_data):
        """分析政策对股票的影响"""
        sector = self.sector_mapping.get(symbol.split('.')[0], '全行业')
        
        score = 50  # 基准分
        impacts = []
        
        # 宏观政策影响
        for policy in policy_data.get('macro', []):
            if policy.get('impact') == 'positive':
                score += 3
                impacts.append({
                    'type': 'macro',
                    'title': policy['title'],
                    'impact': 'positive',
                    'score_change': 3
                })
            elif policy.get('impact') == 'negative':
                score -= 3
                impacts.append({
                    'type': 'macro',
                    'title': policy['title'],
                    'impact': 'negative',
                    'score_change': -3
                })
        
        # 行业政策影响
        for policy in policy_data.get('industry', []):
            if sector in policy.get('sector', '') or policy.get('sector') == '全行业':
                if policy.get('impact') == 'positive':
                    score += 5
                    impacts.append({
                        'type': 'industry',
                        'title': policy['title'],
                        'impact': 'positive',
                        'score_change': 5,
                        'sector': sector
                    })
                elif policy.get('impact') == 'negative':
                    score -= 5
                    impacts.append({
                        'type': 'industry',
                        'title': policy['title'],
                        'impact': 'negative',
                        'score_change': -5,
                        'sector': sector
                    })
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'sector': sector,
            'impacts': impacts,
            'positive_count': len([i for i in impacts if i['impact'] == 'positive']),
            'negative_count': len([i for i in impacts if i['impact'] == 'negative'])
        }
    
    def analyze_geopolitics_impact(self, symbol, geo_data):
        """分析国际形势对股票的影响"""
        sector = self.sector_mapping.get(symbol.split('.')[0], '全行业')
        
        score = 50  # 基准分
        impacts = []
        
        # 中美关系影响
        for news in geo_data.get('us_china', []):
            if news.get('impact') == 'positive':
                score += 2
                impacts.append({
                    'type': 'us_china',
                    'title': news['title'],
                    'impact': 'positive',
                    'score_change': 2
                })
            elif news.get('impact') == 'negative':
                score -= 2
                impacts.append({
                    'type': 'us_china',
                    'title': news['title'],
                    'impact': 'negative',
                    'score_change': -2
                })
        
        # 全球经济影响
        for news in geo_data.get('global_economy', []):
            if news.get('impact') == 'positive':
                score += 1
                impacts.append({
                    'type': 'global_economy',
                    'title': news['title'],
                    'impact': 'positive',
                    'score_change': 1
                })
            elif news.get('impact') == 'negative':
                score -= 1
                impacts.append({
                    'type': 'global_economy',
                    'title': news['title'],
                    'impact': 'negative',
                    'score_change': -1
                })
        
        # 行业国际竞争影响
        for news in geo_data.get('industry_competition', []):
            if sector in news.get('sector', ''):
                if news.get('impact') == 'positive':
                    score += 4
                    impacts.append({
                        'type': 'industry_competition',
                        'title': news['title'],
                        'impact': 'positive',
                        'score_change': 4,
                        'sector': sector
                    })
                elif news.get('impact') == 'negative':
                    score -= 4
                    impacts.append({
                        'type': 'industry_competition',
                        'title': news['title'],
                        'impact': 'negative',
                        'score_change': -4,
                        'sector': sector
                    })
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'impacts': impacts,
            'positive_count': len([i for i in impacts if i['impact'] == 'positive']),
            'negative_count': len([i for i in impacts if i['impact'] == 'negative'])
        }
    
    def analyze_news_impact(self, symbol, news_data):
        """分析个股新闻影响"""
        score = 50  # 基准分
        impacts = []
        
        for news in news_data:
            # 简单关键词分析
            title = news.get('新闻标题', news.get('title', '')).lower()
            content = news.get('新闻内容', news.get('content', '')).lower()
            text = title + ' ' + content
            
            positive_keywords = ['回购', '增长', '盈利', '扩张', '获批', '中标', '合作', '创新']
            negative_keywords = ['下滑', '亏损', '处罚', '诉讼', '风险', '警告', '减持']
            
            pos_count = sum(1 for kw in positive_keywords if kw in text)
            neg_count = sum(1 for kw in negative_keywords if kw in text)
            
            if pos_count > neg_count:
                score += 3
                impacts.append({
                    'title': news.get('新闻标题', news.get('title', '')),
                    'impact': 'positive',
                    'score_change': 3
                })
            elif neg_count > pos_count:
                score -= 3
                impacts.append({
                    'title': news.get('新闻标题', news.get('title', '')),
                    'impact': 'negative',
                    'score_change': -3
                })
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'impacts': impacts,
            'positive_count': len([i for i in impacts if i['impact'] == 'positive']),
            'negative_count': len([i for i in impacts if i['impact'] == 'negative'])
        }
    
    def calculate_comprehensive_score(self, symbol, fundamental_score=50):
        """计算综合评分"""
        # 加载各类数据
        policy_data = self.load_policy_data()
        geo_data = self.load_geopolitics_data()
        news_data = self.load_news_data(symbol)
        
        # 分析各维度影响
        policy_analysis = self.analyze_policy_impact(symbol, policy_data)
        geo_analysis = self.analyze_geopolitics_impact(symbol, geo_data)
        news_analysis = self.analyze_news_impact(symbol, news_data)
        
        # 计算综合评分
        comprehensive_score = (
            fundamental_score * self.weights['fundamental'] +
            news_analysis['score'] * self.weights['news'] +
            policy_analysis['score'] * self.weights['policy'] +
            geo_analysis['score'] * self.weights['geopolitics']
        )
        
        return {
            'symbol': symbol,
            'fundamental_score': fundamental_score,
            'news_score': news_analysis['score'],
            'policy_score': policy_analysis['score'],
            'geopolitics_score': geo_analysis['score'],
            'comprehensive_score': round(comprehensive_score, 2),
            'sector': policy_analysis.get('sector', '未知'),
            'policy_impacts': policy_analysis['impacts'],
            'geopolitics_impacts': geo_analysis['impacts'],
            'news_impacts': news_analysis['impacts'],
            'recommendation': self._get_recommendation(comprehensive_score)
        }
    
    def _get_recommendation(self, score):
        """根据评分给出投资建议"""
        if score >= 80:
            return {'action': '强烈推荐', 'level': 5, 'icon': '⭐⭐⭐⭐⭐'}
        elif score >= 70:
            return {'action': '推荐', 'level': 4, 'icon': '⭐⭐⭐⭐'}
        elif score >= 60:
            return {'action': '谨慎推荐', 'level': 3, 'icon': '⭐⭐⭐'}
        elif score >= 50:
            return {'action': '观望', 'level': 2, 'icon': '⭐⭐'}
        else:
            return {'action': '回避', 'level': 1, 'icon': '⭐'}
    
    def analyze_stock(self, symbol, fundamental_data=None):
        """分析单只股票"""
        print(f"\n{'='*70}")
        print(f"  {symbol} 综合分析")
        print(f"{'='*70}")
        
        # 如果没有提供基本面数据，使用默认值
        if fundamental_data is None:
            fundamental_score = 50
        else:
            # 根据 PE/ROE 等计算基本面分数
            pe = fundamental_data.get('pe', 20)
            roe = fundamental_data.get('roe', 10)
            growth = fundamental_data.get('profit_growth', 10)
            
            fundamental_score = 50
            if pe < 20:
                fundamental_score += 15
            elif pe < 30:
                fundamental_score += 5
            if roe > 15:
                fundamental_score += 20
            elif roe > 10:
                fundamental_score += 10
            if growth > 30:
                fundamental_score += 15
            elif growth > 15:
                fundamental_score += 5
            
            fundamental_score = min(100, fundamental_score)
        
        # 计算综合评分
        result = self.calculate_comprehensive_score(symbol, fundamental_score)
        
        # 打印结果
        print(f"\n📊 综合评分：{result['comprehensive_score']} / 100")
        print(f"   行业：{result['sector']}")
        print(f"   建议：{result['recommendation']['icon']} {result['recommendation']['action']}")
        
        print(f"\n📈 分项评分:")
        print(f"   基本面：{result['fundamental_score']} (权重 40%)")
        print(f"   消息面：{result['news_score']} (权重 25%)")
        print(f"   时政面：{result['policy_score']} (权重 20%)")
        print(f"   国际形势：{result['geopolitics_score']} (权重 15%)")
        
        if result['policy_impacts']:
            print(f"\n📋 政策影响 ({len(result['policy_impacts'])} 条):")
            for impact in result['policy_impacts'][:3]:
                sign = '+' if impact['score_change'] > 0 else ''
                print(f"   {sign}{impact['score_change']} {impact['title'][:40]}...")
        
        if result['geopolitics_impacts']:
            print(f"\n🌍 国际形势影响 ({len(result['geopolitics_impacts'])} 条):")
            for impact in result['geopolitics_impacts'][:3]:
                sign = '+' if impact['score_change'] > 0 else ''
                print(f"   {sign}{impact['score_change']} {impact['title'][:40]}...")
        
        if result['news_impacts']:
            print(f"\n📰 个股新闻影响 ({len(result['news_impacts'])} 条):")
            for impact in result['news_impacts'][:3]:
                sign = '+' if impact['score_change'] > 0 else ''
                print(f"   {sign}{impact['score_change']} {impact['title'][:40]}...")
        
        return result
    
    def analyze_multiple_stocks(self, stocks_with_fundamentals):
        """批量分析多只股票"""
        results = []
        
        for stock in stocks_with_fundamentals:
            symbol = stock['symbol']
            fundamental_data = stock.get('fundamentals', {})
            
            result = self.analyze_stock(symbol, fundamental_data)
            results.append(result)
        
        # 按综合评分排序
        results.sort(key=lambda x: x['comprehensive_score'], reverse=True)
        
        return results
    
    def save_report(self, results, date=None):
        """保存分析报告"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        report = {
            'date': date,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_stocks': len(results),
            'results': results,
            'summary': {
                'avg_score': round(sum(r['comprehensive_score'] for r in results) / len(results), 2),
                'max_score': max(r['comprehensive_score'] for r in results),
                'min_score': min(r['comprehensive_score'] for r in results),
                'recommendations': {
                    '强烈推荐': len([r for r in results if r['recommendation']['action'] == '强烈推荐']),
                    '推荐': len([r for r in results if r['recommendation']['action'] == '推荐']),
                    '谨慎推荐': len([r for r in results if r['recommendation']['action'] == '谨慎推荐']),
                    '观望': len([r for r in results if r['recommendation']['action'] == '观望']),
                    '回避': len([r for r in results if r['recommendation']['action'] == '回避'])
                }
            }
        }
        
        filepath = self.reports_dir / f'comprehensive_analysis_{date}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{filepath}")
        return filepath


def main():
    logger = TaskLogger(task_name='comprehensive_analysis')
    start_time = datetime.now()
    try:
        """测试分析器"""
        logger.task_start()
        logger.info("任务开始")
        print("=" * 70)
        print(" " * 18 + "综合消息面分析器")
        print("=" * 70)
    
        analyzer = ComprehensiveAnalyzer()
    
        # 测试分析几只股票
        test_stocks = [
            {'symbol': '300750.SZ', 'fundamentals': {'pe': 19.68, 'roe': 19.94, 'profit_growth': 54.4}},
            {'symbol': '601456.SH', 'fundamentals': {'pe': 18.5, 'roe': 16.2, 'profit_growth': 35.6}},
            {'symbol': '600519.SH', 'fundamentals': {'pe': 22.3, 'roe': 28.5, 'profit_growth': 18.2}}
        ]
    
        results = analyzer.analyze_multiple_stocks(test_stocks)
        analyzer.save_report(results)
    
        print("\n" + "=" * 70)
        print(" " * 20 + "分析完成")
        print("=" * 70)

    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)


if __name__ == '__main__':
    main()
