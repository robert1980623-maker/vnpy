#!/usr/bin/env python3
"""
精选股票选股器 - 简化版（按基本面排序）
"""

import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent.parent))

from stock_name_utils import StockNameCache
from tushare_fundamental_fetcher import TushareFundamentalFetcher

class EliteStockSelector:
    def __init__(self, target_count=5):
        self.target_count = target_count
        self.data_dir = Path('./data/akshare/bars')
        self.name_cache = StockNameCache()
        self.fundamental_fetcher = TushareFundamentalFetcher()
        self.selected_stocks = []
        
    def load_stock_symbols(self):
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem.replace('_', '.') for f in csv_files]
        print(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
        
    def get_fundamentals(self, symbols):
        print("\n" + "=" * 70)
        print(" " * 20 + "获取财务数据 (Tushare)")
        print("=" * 70)
        return self.fundamental_fetcher.get_batch_fundamentals(symbols)
    
    def multi_strategy_filter(self, symbols, fundamentals):
        print("\n" + "=" * 70)
        print(" " * 20 + "多策略筛选")
        print("=" * 70)
        
        candidates = []
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            if not data.get('pe') or not data.get('roe'):
                continue
            
            strategies = []
            reasons = []
            
            if data.get('pe', 100) < 20 and data.get('roe', 0) > 10 and data.get('dividend_yield', 0) > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, ROE={data['roe']:.1f}%, 股息率={data['dividend_yield']:.1f}%")
            
            if data.get('revenue_growth', 0) > 25 and data.get('profit_growth', 0) > 30:
                strategies.append('成长')
                reasons.append(f"营收增长={data['revenue_growth']:.1f}%, 利润增长={data['profit_growth']:.1f}%")
            
            if data.get('roe', 0) > 15:
                strategies.append('质量')
                reasons.append(f"ROE={data['roe']:.1f}%")
            
            if data.get('dividend_yield', 0) > 3:
                strategies.append('高息')
                reasons.append(f"股息率={data['dividend_yield']:.1f}%")
            
            base_score = len(strategies) * 2
            if len(strategies) >= 3:
                base_score += 1
            if len(strategies) == 4:
                base_score += 1
            
            if len(strategies) >= 2:
                candidates.append({
                    'symbol': symbol,
                    'fundamentals': data,
                    'strategies': strategies,
                    'reasons': reasons,
                    'base_score': base_score
                })
        
        candidates.sort(key=lambda x: (x['base_score'], x['fundamentals'].get('roe', 0)), reverse=True)
        
        print(f"\n✅ 筛选完成：{len(candidates)} 只股票")
        print(f"\n🏆 Top 10:")
        for i, c in enumerate(candidates[:10], 1):
            name = self.name_cache.get_name(c['symbol'])
            print(f"  {i}. {c['symbol']} {name} - {'+'.join(c['strategies'])} (评分：{c['base_score']}, ROE:{c['fundamentals'].get('roe', 0):.1f}%)")
        
        return candidates
    
    def select_elite(self, candidates):
        print("\n" + "=" * 70)
        print(" " * 20 + "精选 Top 5")
        print("=" * 70)
        
        self.selected_stocks = candidates[:self.target_count]
        
        print(f"\n✅ 精选完成：{len(self.selected_stocks)} 只股票")
        print(f"\n🏆 精英组合:")
        for i, stock in enumerate(self.selected_stocks, 1):
            name = self.name_cache.get_name(stock['symbol'])
            print(f"\n  {i}. {stock['symbol']} {name}")
            print(f"     策略：{'+'.join(stock['strategies'])} (评分：{stock['base_score']})")
            print(f"     PE: {stock['fundamentals'].get('pe', 'N/A')}, ROE: {stock['fundamentals'].get('roe', 'N/A')}%")
            print(f"     股息率：{stock['fundamentals'].get('dividend_yield', 'N/A')}%")
            print(f"     营收增长：{stock['fundamentals'].get('revenue_growth', 'N/A')}%")
            print(f"     利润增长：{stock['fundamentals'].get('profit_growth', 'N/A')}%")
        
        return self.selected_stocks
    
    def save_report(self, output_dir='./reports'):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'elite_selection_simple',
            'target_count': self.target_count,
            'selected_count': len(self.selected_stocks),
            'stocks': []
        }
        
        for stock in self.selected_stocks:
            stock_info = {
                'symbol': stock['symbol'],
                'name': self.name_cache.get_name(stock['symbol']),
                'strategies': stock['strategies'],
                'base_score': stock['base_score'],
                'fundamentals': {
                    'pe': round(stock['fundamentals'].get('pe', 0), 2),
                    'roe': round(stock['fundamentals'].get('roe', 0), 2),
                    'dividend_yield': round(stock['fundamentals'].get('dividend_yield', 0), 2),
                    'revenue_growth': round(stock['fundamentals'].get('revenue_growth', 0), 2),
                    'profit_growth': round(stock['fundamentals'].get('profit_growth', 0), 2),
                }
            }
            report['stocks'].append(stock_info)
        
        report_file = output_path / f'elite_selection_{report["date"]}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{report_file}")
        return report_file

def main():
    print("=" * 70)
    print(" " * 20 + "精选股票选股器 v1.0 (简化版)")
    print("=" * 70)
    
    selector = EliteStockSelector(target_count=5)
    symbols = selector.load_stock_symbols()
    fundamentals = selector.get_fundamentals(symbols)
    candidates = selector.multi_strategy_filter(symbols, fundamentals)
    selector.select_elite(candidates)
    selector.save_report()
    
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)

if __name__ == '__main__':
    main()
