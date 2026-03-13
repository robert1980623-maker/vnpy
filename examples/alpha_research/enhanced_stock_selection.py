#!/usr/bin/env python3
"""
增强版选股系统
- 选股前自动检查并更新数据
- 显示股票名称
- 整合四大维度：基本面 + 消息面 + 时政 + 国际形势 + 未来展望
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from tushare_fundamental_fetcher import TushareFundamentalFetcher
from stock_name_utils import StockNameCache, get_stock_name
from comprehensive_analyzer import ComprehensiveAnalyzer

class EnhancedStockSelector:
    """增强版选股系统"""
    
    def __init__(self):
        self.data_dir = Path('./data/akshare/bars')
        self.report_dir = Path('./reports')
        self.cache_dir = Path('./cache/fundamental')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化
        self.fundamental_fetcher = TushareFundamentalFetcher()
        self.name_cache = StockNameCache()
        self.comprehensive_analyzer = ComprehensiveAnalyzer()
    
    def check_and_update_data(self, max_age_hours=24):
        """检查数据新鲜度，如果滞后则自动更新"""
        print("\n" + "="*70)
        print("📊 数据新鲜度检查")
        print("="*70)
        
        if not self.data_dir.exists():
            print("❌ 数据目录不存在，触发更新...")
            self.trigger_data_download()
            return True
        
        # 检查最新数据文件时间
        csv_files = list(self.data_dir.glob('*.csv'))
        if not csv_files:
            print("❌ 没有数据文件，触发更新...")
            self.trigger_data_download()
            return True
        
        latest_time = max(f.stat().st_mtime for f in csv_files)
        latest_dt = datetime.fromtimestamp(latest_time)
        age = datetime.now() - latest_dt
        
        print(f"最新数据时间：{latest_dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"距今：{int(age.total_seconds() / 3600)}小时前")
        
        if age > timedelta(hours=max_age_hours):
            print(f"⚠️ 数据滞后超过{max_age_hours}小时，触发更新...")
            self.trigger_data_download()
            return True
        else:
            print("✅ 数据新鲜，无需更新")
            return False
    
    def trigger_data_download(self):
        """触发数据下载"""
        print("\n🔄 执行数据下载...")
        
        try:
            result = subprocess.run(
                ['bash', 'download_data_akshare.sh'],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                print("✅ 数据下载成功")
            else:
                print(f"⚠️ 数据下载部分失败：{result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print("⚠️ 数据下载超时，继续选股流程")
        except Exception as e:
            print(f"⚠️ 数据下载失败：{e}")
    
    def load_stocks(self):
        """加载股票池"""
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem.replace('_', '.') for f in csv_files]
        print(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
    
    def get_real_fundamentals(self, symbols):
        """获取真实财务数据"""
        print("\n" + "="*70)
        print("📈 获取财务数据 (Tushare)")
        print("="*70)
        
        fundamentals = self.fundamental_fetcher.get_batch_fundamentals(symbols)
        return fundamentals
    
    def get_comprehensive_analysis(self, symbols, fundamentals):
        """获取综合分析（四大维度）"""
        print("\n" + "="*70)
        print("🔍 综合分析（基本面 + 消息面 + 时政 + 国际形势）")
        print("="*70)
        
        try:
            results = []
            for i, symbol in enumerate(symbols[:20], 1):
                data = fundamentals.get(symbol, {})
                if not data.get('pe'):
                    continue
                
                # 获取综合分析
                analysis = self.comprehensive_analyzer.analyze_single(symbol, data)
                if analysis:
                    results.append(analysis)
                    print(f"[{i}/20] ✅ {symbol} - 综合评分：{analysis.get('comprehensive_score', 0):.1f}")
            
            return results
        except Exception as e:
            print(f"⚠️ 综合分析失败：{e}")
            return []
    
    def multi_strategy_selection(self, symbols, fundamentals, target_count=100):
        """多策略选股（整合四大维度）"""
        print("\n" + "="*70)
        print("🏆 多策略选股")
        print("="*70)
        
        selected = []
        
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            if not data.get('pe'):
                continue
            
            reasons = []
            strategies = []
            score = 0
            
            # 1. 价值股策略
            pe = data.get('pe', 100)
            roe = data.get('roe', 0)
            if (pe or 100) < 20 and (roe or 0) > 10:
                strategies.append("价值")
                reasons.append(f"PE={pe:.1f}, ROE={roe:.1f}%")
                score += 3
            
            # 2. 成长股策略
            revenue_growth = data.get('revenue_growth', 0)
            profit_growth = data.get('profit_growth', 0)
            if (revenue_growth or 0) > 25 or (profit_growth or 0) > 30:
                strategies.append("成长")
                reasons.append(f"营收增长={revenue_growth:.1f}%, 利润增长={profit_growth:.1f}%")
                score += 2
            
            # 3. 质量股策略
            if (roe or 0) > 15:
                strategies.append("质量")
                score += 2
            
            # 4. 高息股策略
            dividend_yield = data.get('dividend_yield', 0)
            if (dividend_yield or 0) > 3:
                strategies.append("高息")
                reasons.append(f"股息率={dividend_yield:.1f}%")
                score += 2
            elif (dividend_yield or 0) > 2:
                score += 1
            
            if strategies:
                # 获取股票名称
                name = get_stock_name(symbol, self.name_cache)
                
                selected.append({
                    'symbol': symbol,
                    'name': name,
                    'strategies': strategies,
                    'score': score,
                    'reasons': reasons,
                    'pe': round(pe, 2) if pe else None,
                    'roe': round(roe, 2) if roe else None,
                    'dividend_yield': round(dividend_yield, 2) if dividend_yield else None,
                    'revenue_growth': round(revenue_growth, 2) if revenue_growth else None,
                    'profit_growth': round(profit_growth, 2) if profit_growth else None,
                    'fundamentals': data
                })
        
        # 按评分排序
        selected.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n✅ 选股完成：{len(selected)}只")
        
        # 显示 Top 10（带名称）
        print("\n🏆 Top 10:")
        for i, stock in enumerate(selected[:10], 1):
            strategies_str = '+'.join(stock['strategies'])
            print(f"  {i}. {stock['symbol']} ({stock['name']}) - {strategies_str} (评分：{stock['score']})")
            print(f"     {', '.join(stock['reasons'][:2])}")
        
        return selected[:target_count]
    
    def generate_report(self, selected_stocks, comprehensive_results):
        """生成选股报告（包含综合分析）"""
        report_file = self.report_dir / f"stock_selection_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        # 整合综合分析结果
        comprehensive_dict = {r['symbol']: r for r in comprehensive_results}
        
        for stock in selected_stocks:
            symbol = stock['symbol']
            if symbol in comprehensive_dict:
                comp = comprehensive_dict[symbol]
                stock['comprehensive'] = {
                    'score': comp.get('comprehensive_score', 0),
                    'fundamental_score': comp.get('fundamental_score', 0),
                    'news_score': comp.get('news_score', 0),
                    'policy_score': comp.get('policy_score', 0),
                    'geopolitics_score': comp.get('geopolitics_score', 0),
                    'sector': comp.get('sector', ''),
                    'policy_impacts': comp.get('policy_impacts', [])[:3],
                    'geopolitics_impacts': comp.get('geopolitics_impacts', [])[:3],
                    'outlook': comp.get('outlook', '')
                }
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'total_count': len(selected_stocks),
            'stocks': selected_stocks[:50]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{report_file}")
        
        return report
    
    def run(self, target_count=100):
        """运行完整选股流程"""
        print("\n" + "="*70)
        print(f"🚀 增强版选股系统 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 检查并更新数据
        self.check_and_update_data(max_age_hours=24)
        
        # 步骤 2: 加载股票池
        print("\n" + "="*70)
        print("📋 读取股票池")
        print("="*70)
        symbols = self.load_stocks()
        
        if not symbols:
            print("❌ 股票池为空")
            return []
        
        # 步骤 3: 获取财务数据
        fundamentals = self.get_real_fundamentals(symbols)
        
        # 步骤 4: 多策略选股
        selected = self.multi_strategy_selection(symbols, fundamentals, target_count)
        
        if not selected:
            print("\n⚠️ 没有选出符合条件的股票")
            return []
        
        # 步骤 5: 综合分析（前 20 只）
        comprehensive = self.get_comprehensive_analysis(symbols, fundamentals)
        
        # 步骤 6: 生成报告
        report = self.generate_report(selected, comprehensive)
        
        print("\n" + "="*70)
        print("✅ 选股完成")
        print("="*70)
        print(f"选股：{len(selected)}只")
        print(f"综合分析：{len(comprehensive)}只")
        
        return selected


if __name__ == '__main__':
    selector = EnhancedStockSelector()
    selector.run(target_count=100)
