#!/usr/bin/env python3
"""
多策略组合选股系统

功能：
- 整合多种策略（价值/成长/质量/股息/平衡）
- 选出 100 只优质股票
- 说明选择原因和基于的策略
- 生成选股报告
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.alpha.dataset import StockPool, FundamentalData, FinancialIndicator
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy
)


class MultiStrategyScreener:
    """多策略选股器"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.pool = StockPool('all_stocks')
        self.fund_data = FundamentalData()
        self.selected_stocks = {}  # {symbol: {'strategies': [], 'reasons': []}}
        
        # 初始化策略
        self.strategies = {
            'value': ValueStockStrategy(max_pe=20, min_roe=10, min_dividend_yield=2.0),
            'growth': GrowthStockStrategy(min_revenue_growth=25, min_profit_growth=30),
            'quality': QualityStockStrategy(min_roe=15),
            'dividend': DividendStockStrategy(min_dividend_yield=3.0),
        }
        
    def load_stock_pool(self, max_stocks: int = 500):
        """从数据目录加载股票池"""
        csv_files = list(self.data_dir.glob('*.csv'))
        
        for csv_file in csv_files[:max_stocks]:
            symbol = csv_file.stem.replace('_', '.')
            self.pool.add(symbol)
        
        print(f"✅ 加载股票池：{self.pool.count()} 只股票")
        
    def load_fundamental_data(self):
        """加载财务数据（模拟）"""
        # 实际应用中应该从数据库或 API 获取
        # 这里使用模拟数据演示
        
        import random
        for symbol in self.pool.get_stocks():
            # 生成随机但合理的财务数据
            pe = random.uniform(5, 50)
            roe = random.uniform(5, 25)
            dividend_yield = random.uniform(0.5, 6)
            revenue_growth = random.uniform(-10, 50)
            profit_growth = random.uniform(-20, 60)
            profit_margin = random.uniform(5, 40)
            
            indicator = FinancialIndicator(
                vt_symbol=symbol,
                report_date='2024-12-31',
                pe=pe,
                roe=roe,
                dividend_yield=dividend_yield,
                revenue_growth=revenue_growth,
                profit_growth=profit_growth,
                profit_margin=profit_margin
            )
            self.fund_data.add(indicator)
        
        print(f"✅ 加载财务数据：{len(self.fund_data)} 只股票")
        
    def run_all_strategies(self):
        """运行所有策略"""
        print("\n" + "=" * 70)
        print(" " * 20 + "运行多策略选股")
        print("=" * 70)
        
        for strategy_name, strategy in self.strategies.items():
            print(f"\n【{strategy_name.upper()} 策略】")
            selected = self._run_strategy(strategy_name, strategy)
            print(f"  选出：{len(selected)} 只股票")
            
        # 合并结果
        self._merge_results()
        
    def _run_strategy(self, strategy_name: str, strategy) -> list:
        """运行单个策略"""
        selected = []
        
        for symbol in self.pool.get_stocks():
            indicator = self.fund_data.get_latest(symbol)
            if not indicator:
                continue
            
            # 根据策略类型进行筛选
            is_selected = False
            reasons = []
            
            if strategy_name == 'value':
                if indicator.pe and indicator.pe < strategy.max_pe:
                    reasons.append(f"PE={indicator.pe:.1f}<{strategy.max_pe}")
                    is_selected = True
                if indicator.roe and indicator.roe > strategy.min_roe:
                    reasons.append(f"ROE={indicator.roe:.1f}%>{strategy.min_roe}%")
                if indicator.dividend_yield and indicator.dividend_yield > strategy.min_dividend_yield:
                    reasons.append(f"股息率={indicator.dividend_yield:.1f}%>{strategy.min_dividend_yield}%")
                    
            elif strategy_name == 'growth':
                if indicator.revenue_growth and indicator.revenue_growth > strategy.min_revenue_growth:
                    reasons.append(f"营收增长={indicator.revenue_growth:.1f}%>{strategy.min_revenue_growth}%")
                    is_selected = True
                if indicator.profit_growth and indicator.profit_growth > strategy.min_profit_growth:
                    reasons.append(f"利润增长={indicator.profit_growth:.1f}%>{strategy.min_profit_growth}%")
                    
            elif strategy_name == 'quality':
                if indicator.roe and indicator.roe > strategy.min_roe:
                    reasons.append(f"ROE={indicator.roe:.1f}%>{strategy.min_roe}%")
                    is_selected = True
                if indicator.profit_margin and indicator.profit_margin > strategy.min_profit_margin:
                    reasons.append(f"净利率={indicator.profit_margin:.1f}%>{strategy.min_profit_margin}%")
                    
            elif strategy_name == 'dividend':
                if indicator.dividend_yield and indicator.dividend_yield > strategy.min_dividend_yield:
                    reasons.append(f"股息率={indicator.dividend_yield:.1f}%>{strategy.min_dividend_yield}%")
                    is_selected = True
                if indicator.pe and indicator.pe < strategy.max_pe:
                    reasons.append(f"PE={indicator.pe:.1f}<{strategy.max_pe}")
                    
            elif strategy_name == 'balanced':
                score = 0
                if indicator.pe and indicator.pe < strategy.max_pe:
                    score += 1
                    reasons.append(f"PE={indicator.pe:.1f}")
                if indicator.roe and indicator.roe > strategy.min_roe:
                    score += 1
                    reasons.append(f"ROE={indicator.roe:.1f}%")
                if indicator.dividend_yield and indicator.dividend_yield > strategy.min_dividend_yield:
                    score += 1
                    reasons.append(f"股息率={indicator.dividend_yield:.1f}%")
                if indicator.revenue_growth and indicator.revenue_growth > strategy.min_revenue_growth:
                    score += 1
                    reasons.append(f"营收增长={indicator.revenue_growth:.1f}%")
                if score >= 3:  # 至少满足 3 个条件
                    is_selected = True
            
            if is_selected:
                selected.append(symbol)
                
                # 记录选股原因
                if symbol not in self.selected_stocks:
                    self.selected_stocks[symbol] = {'strategies': [], 'reasons': []}
                self.selected_stocks[symbol]['strategies'].append(strategy_name)
                self.selected_stocks[symbol]['reasons'].extend(reasons)
        
        return selected
        
    def _merge_results(self):
        """合并所有策略结果，选出 Top 100"""
        print("\n" + "=" * 70)
        print(" " * 20 + "合并策略结果")
        print("=" * 70)
        
        # 按策略匹配数排序
        sorted_stocks = sorted(
            self.selected_stocks.items(),
            key=lambda x: len(x[1]['strategies']),
            reverse=True
        )
        
        # 选出 Top 100
        top_100 = sorted_stocks[:100]
        
        print(f"\n总匹配股票：{len(self.selected_stocks)} 只")
        print(f"最终选出：{len(top_100)} 只")
        print()
        
        # 统计各策略贡献
        strategy_count = {}
        for symbol, data in top_100:
            for strategy in data['strategies']:
                strategy_count[strategy] = strategy_count.get(strategy, 0) + 1
        
        print("策略贡献:")
        for strategy, count in sorted(strategy_count.items()):
            print(f"  {strategy}: {count} 只")
        
        # 保存结果
        self.top_100 = top_100
        
    def generate_report(self, output_file: str = 'reports/daily_stock_selection.json'):
        """生成选股报告"""
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'total_stocks': self.pool.count(),
            'selected_count': len(self.top_100),
            'stocks': []
        }
        
        for symbol, data in self.top_100:
            indicator = self.fund_data.get_latest(symbol)
            
            stock_info = {
                'symbol': symbol,
                'strategies': data['strategies'],
                'strategy_count': len(data['strategies']),
                'reasons': list(set(data['reasons']))[:5],  # 去重，最多 5 个原因
                'indicators': {
                    'pe': round(indicator.pe, 2) if indicator.pe else None,
                    'roe': round(indicator.roe, 2) if indicator.roe else None,
                    'dividend_yield': round(indicator.dividend_yield, 2) if indicator.dividend_yield else None,
                    'revenue_growth': round(indicator.revenue_growth, 2) if indicator.revenue_growth else None,
                    'profit_growth': round(indicator.profit_growth, 2) if indicator.profit_growth else None,
                }
            }
            report['stocks'].append(stock_info)
        
        # 保存 JSON
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{output_file}")
        
        # 打印前 10 只股票
        print("\n" + "=" * 70)
        print(" " * 20 + "Top 10 股票")
        print("=" * 70)
        print(f"{'排名':<4} {'代码':<12} {'策略数':<6} {'策略':<25} {'PE':<8} {'ROE':<8} {'股息率':<8}")
        print("-" * 70)
        
        for i, (symbol, data) in enumerate(self.top_100[:10], 1):
            indicator = self.fund_data.get_latest(symbol)
            strategies = ', '.join([s[:3] for s in data['strategies']])
            pe = f"{indicator.pe:.1f}" if indicator.pe else 'N/A'
            roe = f"{indicator.roe:.1f}%" if indicator.roe else 'N/A'
            div = f"{indicator.dividend_yield:.1f}%" if indicator.dividend_yield else 'N/A'
            
            print(f"{i:<4} {symbol:<12} {len(data['strategies']):<6} {strategies:<25} {pe:<8} {roe:<8} {div:<8}")
        
        return report


def main():
    print("=" * 70)
    print(" " * 18 + "多策略组合选股系统")
    print("=" * 70)
    print()
    
    # 创建选股器
    screener = MultiStrategyScreener()
    
    # 1. 加载股票池
    print("【步骤 1】加载股票池...")
    screener.load_stock_pool()
    print()
    
    # 2. 加载财务数据
    print("【步骤 2】加载财务数据...")
    screener.load_fundamental_data()
    print()
    
    # 3. 运行所有策略
    print("【步骤 3】运行多策略选股...")
    screener.run_all_strategies()
    print()
    
    # 4. 生成报告
    print("【步骤 4】生成选股报告...")
    report = screener.generate_report()
    print()
    
    # 5. 总结
    print("=" * 70)
    print(" " * 20 + "选股完成")
    print("=" * 70)
    print(f"日期：{report['date']} {report['time']}")
    print(f"股票池：{report['total_stocks']} 只")
    print(f"选出：{report['selected_count']} 只")
    print()
    print("下一步:")
    print("  - 查看完整报告：cat reports/daily_stock_selection.json")
    print("  - 生成交易计划：python3 generate_trading_plan.py")
    print("  - 执行模拟交易：python3 start_trading.py --mode paper")
    print()


if __name__ == '__main__':
    main()
