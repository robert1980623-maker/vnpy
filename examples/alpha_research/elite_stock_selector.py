#!/usr/bin/env python3
"""
精选股票选股器 - 5 只精英组合

功能:
1. 从多策略选股中精选 Top 5
2. 整合基本面 + 消息面 + 时政面 + 国际形势
3. 严格评分阈值，宁缺毋滥
"""

import sys
import json
from pathlib import Path
from agent_report import create_report
from datetime import datetime
import time
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent.parent))

from stock_name_utils import StockNameCache
from tushare_fundamental_fetcher import TushareFundamentalFetcher
from comprehensive_analyzer import ComprehensiveAnalyzer


class EliteStockSelector:
    """精选股票选股器"""
    
    def __init__(self, target_count: int = 5):
        self.target_count = target_count
        self.data_dir = Path('./data/akshare/bars')
        self.name_cache = StockNameCache()
        self.fundamental_fetcher = TushareFundamentalFetcher()
        self.comprehensive_analyzer = ComprehensiveAnalyzer()
        self.selected_stocks = []
        
    def load_stock_symbols(self):
        """加载股票池"""
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem.replace('_', '.') for f in csv_files]
        print(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
        
    def get_fundamentals(self, symbols):
        """获取财务数据"""
        print("\n" + "=" * 70)
        print(" " * 20 + "获取财务数据 (Tushare)")
        print("=" * 70)
        return self.fundamental_fetcher.get_batch_fundamentals(symbols)
    
    def multi_strategy_filter(self, symbols, fundamentals):
        """多策略初筛"""
        print("\n" + "=" * 70)
        print(" " * 20 + "多策略初筛")
        print("=" * 70)
        
        candidates = []
        
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            
            # 跳过数据不完整的股票
            if not data.get('pe') or not data.get('roe'):
                continue
            
            strategies = []
            reasons = []
            
            # 策略 1: 价值股 (PE<20, ROE>10%, 股息率>2%)
            if (data.get('pe') or 100) < 20 and (data.get('roe') or 0) > 10 and (data.get('dividend_yield') or 0) > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, ROE={data['roe']:.1f}%, 股息率={data['dividend_yield']:.1f}%")
            
            # 策略 2: 成长股 (营收增长>25%, 利润增长>30%)
            if (data.get('revenue_growth') or 0) > 25 and (data.get('profit_growth') or 0) > 30:
                strategies.append('成长')
                reasons.append(f"营收增长={data['revenue_growth']:.1f}%, 利润增长={data['profit_growth']:.1f}%")
            
            # 策略 3: 质量股 (ROE>15%)
            if (data.get('roe') or 0) > 15:
                strategies.append('质量')
                reasons.append(f"ROE={data['roe']:.1f}%")
            
            # 策略 4: 高息股 (股息率>3%)
            if (data.get('dividend_yield') or 0) > 3:
                strategies.append('高息')
                reasons.append(f"股息率={data['dividend_yield']:.1f}%")
            
            # 计算基本面评分
            base_score = len(strategies) * 2
            if len(strategies) >= 3:
                base_score += 1
            if len(strategies) == 4:
                base_score += 1
            
            # 只保留至少满足 2 个策略的股票
            if len(strategies) >= 2:
                candidates.append({
                    'symbol': symbol,
                    'fundamentals': data,
                    'strategies': strategies,
                    'reasons': reasons,
                    'base_score': base_score
                })
        
        # 按基本面评分排序
        candidates.sort(key=lambda x: x['base_score'], reverse=True)
        
        print(f"\n✅ 初筛完成：{len(candidates)} 只股票进入候选")
        print(f"\n🏆 Top 10 (基本面):")
        for i, c in enumerate(candidates[:10], 1):
            name = self.name_cache.get_name(c['symbol'])
            print(f"  {i}. {c['symbol']} {name} - {'+'.join(c['strategies'])} (评分：{c['base_score']})")
        
        return candidates
    
    def comprehensive_analysis(self, candidates):
        """综合消息面分析"""
        print("\n" + "=" * 70)
        print(" " * 20 + "综合消息面分析")
        print("=" * 70)
        
        # 取基本面 Top 15 进行综合分析（减少 API 调用）
        top_candidates = candidates[:15]
        
        analyzed = []
        for i, candidate in enumerate(top_candidates, 1):
            symbol = candidate['symbol']
            print(f"\n[{i}/{len(top_candidates)}] 分析 {symbol}...")
            
            # 调用综合分析器
            try:
                result = self.comprehensive_analyzer.analyze_stock(symbol)
                
                if result:
                    candidate['comprehensive'] = {
                        'fundamental_score': result.get('fundamental_score', 0),
                        'news_score': result.get('news_score', 0),
                        'policy_score': result.get('policy_score', 0),
                        'geopolitics_score': result.get('geopolitics_score', 0),
                        'comprehensive_score': result.get('comprehensive_score', 0),
                        'sector': result.get('sector', '未知'),
                        'recommendation': result.get('recommendation', {})
                    }
                    
                    # 综合评分 = 基本面 40% + 消息面 25% + 时政面 20% + 国际形势 15%
                    candidate['final_score'] = (
                        result.get('fundamental_score', 0) * 0.4 +
                        result.get('news_score', 0) * 0.25 +
                        result.get('policy_score', 0) * 0.20 +
                        result.get('geopolitics_score', 0) * 0.15
                    )
                    
                    print(f"  ✓ 综合评分：{candidate['final_score']:.1f}")
                    analyzed.append(candidate)
                else:
                    print(f"  ⚠️ 分析失败")
            except Exception as e:
                print(f"  ✗ 错误：{e}")
            
            # API 限流
            time.sleep(1.0)
        
        # 按综合评分排序
        analyzed.sort(key=lambda x: x['final_score'], reverse=True)
        
        return analyzed
    
    def select_elite(self, candidates):
        """精选 Top 5"""
        print("\n" + "=" * 70)
        print(" " * 20 + "精选 Top 5")
        print("=" * 70)
        
        # 筛选条件：综合评分 >= 70
        qualified = [c for c in candidates if c['final_score'] >= 70]
        
        if len(qualified) < self.target_count:
            print(f"⚠️ 仅 {len(qualified)} 只股票满足阈值 (>=52 分)，降低标准到>=52 分...")
            # 降低阈值到 52
            qualified = [c for c in candidates if c['final_score'] >= 65]
        
        if len(qualified) < self.target_count:
            print(f"⚠️ 仍不足 {self.target_count} 只，取前 {min(len(qualified), self.target_count)} 只")
        
        # 取 Top 5
        self.selected_stocks = qualified[:self.target_count]
        
        print(f"\n✅ 精选完成：{len(self.selected_stocks)} 只股票")
        print(f"\n🏆 精英组合 (按基本面评分排序):")
        for i, stock in enumerate(self.selected_stocks, 1):
            name = self.name_cache.get_name(stock['symbol'])
            print(f"\n  {i}. {stock['symbol']} {name}")
            print(f"     策略：{'+'.join(stock['strategies'])} (基础评分：{stock['base_score']})")
            print(f"     PE: {stock['fundamentals'].get('pe', 'N/A')}, ROE: {stock['fundamentals'].get('roe', 'N/A')}%")
            print(f"     股息率：{stock['fundamentals'].get('dividend_yield', 'N/A')}%")
            print(f"     营收增长：{stock['fundamentals'].get('revenue_growth', 'N/A')}%")
            print(f"     利润增长：{stock['fundamentals'].get('profit_growth', 'N/A')}%")
        
        return self.selected_stocks
    
    def save_report(self, output_dir: str = './reports'):
        """保存选股报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'elite_selection',
            'target_count': self.target_count,
            'selected_count': len(self.selected_stocks),
            'stocks': []
        }
        
        for stock in self.selected_stocks:
            comp = stock['comprehensive']
            stock_info = {
                'symbol': stock['symbol'],
                'name': self.name_cache.get_name(stock['symbol']),
                'sector': comp.get('sector', 'N/A'),
                'strategies': stock['strategies'],
                'base_score': stock['base_score'],
                'comprehensive_score': comp['comprehensive_score'],
                'final_score': round(stock['final_score'], 2),
                'scores': {
                    'fundamental': comp['fundamental_score'],
                    'news': comp['news_score'],
                    'policy': comp['policy_score'],
                    'geopolitics': comp['geopolitics_score']
                },
                'fundamentals': {
                    'pe': round(stock['fundamentals'].get('pe', 0), 2),
                    'roe': round(stock['fundamentals'].get('roe', 0), 2),
                    'dividend_yield': round(stock['fundamentals'].get('dividend_yield', 0), 2),
                    'revenue_growth': round(stock['fundamentals'].get('revenue_growth', 0), 2),
                    'profit_growth': round(stock['fundamentals'].get('profit_growth', 0), 2),
                },
                'recommendation': comp['recommendation']
            }
            report['stocks'].append(stock_info)
        
        # 保存 JSON
        report_file = output_path / f'elite_selection_{report["date"]}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{report_file}")
        return report_file


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "精选股票选股器 v1.0")
    print("=" * 70)
    
    selector = EliteStockSelector(target_count=5)
    
    # 步骤 1: 加载股票池
    symbols = selector.load_stock_symbols()
    
    # 步骤 2: 获取财务数据
    fundamentals = selector.get_fundamentals(symbols)
    
    # 步骤 3: 多策略初筛
    candidates = selector.multi_strategy_filter(symbols, fundamentals)
    
    # 步骤 4: 综合消息面分析
    candidates = selector.comprehensive_analysis(candidates)
    
    # 步骤 5: 精选 Top 5
    selector.select_elite(candidates)
    
    # 步骤 6: 保存报告
    selector.save_report()
    
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)
    print(f"精选股票：{len(selector.selected_stocks)} 只")
    print("\n下一步:")
    print("  - 查看报告：cat reports/elite_selection_*.json")
    print("  - 执行调仓：python3 rebalance_portfolio.py")
    print("  - 设置监控：python3 realtime_monitor.py")


if __name__ == '__main__':
    main()
