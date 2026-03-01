#!/usr/bin/env python3
"""
每日选股和交易计划生成

功能:
1. 多策略选股 (100 只)
2. 生成交易计划
3. 发送钉钉通知
4. 保存选股报告
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent.parent))

from vnpy.alpha.dataset import StockPool, FundamentalData


class DailyStockSelector:
    """每日选股器"""
    
    def __init__(self):
        self.data_dir = Path('./data/akshare/bars')
        self.selected_stocks = []
        self.trading_plan = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'buy': [],
            'sell': [],
            'hold': []
        }
        
    def load_stocks(self):
        """加载股票池"""
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem.replace('_', '.') for f in csv_files]
        print(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
        
    def generate_mock_fundamentals(self, symbols):
        """生成模拟财务数据 (实际应从数据库获取)"""
        fundamentals = {}
        
        for symbol in symbols:
            # 生成合理范围的财务指标
            fundamentals[symbol] = {
                'pe': random.uniform(5, 50),
                'roe': random.uniform(5, 25),
                'dividend_yield': random.uniform(0.5, 6),
                'revenue_growth': random.uniform(-10, 50),
                'profit_growth': random.uniform(-20, 60),
            }
        
        return fundamentals
        
    def multi_strategy_selection(self, symbols, fundamentals, target_count=100):
        """多策略选股"""
        print("\n" + "=" * 70)
        print(" " * 20 + "多策略选股")
        print("=" * 70)
        
        selected = {}  # {symbol: {'strategies': [], 'score': 0, 'reasons': []}}
        
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            strategies = []
            reasons = []
            score = 0
            
            # 策略 1: 价值股 (PE<20, ROE>10%, 股息率>2%)
            if data.get('pe', 100) < 20 and data.get('roe', 0) > 10 and data.get('dividend_yield', 0) > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, ROE={data['roe']:.1f}%, 股息率={data['dividend_yield']:.1f}%")
                score += 3
            
            # 策略 2: 成长股 (营收增长>25%, 利润增长>30%)
            if data.get('revenue_growth', 0) > 25 and data.get('profit_growth', 0) > 30:
                strategies.append('成长')
                reasons.append(f"营收增长={data['revenue_growth']:.1f}%, 利润增长={data['profit_growth']:.1f}%")
                score += 3
            
            # 策略 3: 质量股 (ROE>15%)
            if data.get('roe', 0) > 15:
                strategies.append('质量')
                reasons.append(f"ROE={data['roe']:.1f}%")
                score += 2
            
            # 策略 4: 高股息 (股息率>3%)
            if data.get('dividend_yield', 0) > 3:
                strategies.append('高息')
                reasons.append(f"股息率={data['dividend_yield']:.1f}%")
                score += 2
            
            if strategies:
                selected[symbol] = {
                    'strategies': strategies,
                    'score': score,
                    'reasons': reasons,
                    'fundamentals': data
                }
        
        # 按得分排序，选出 Top 100
        sorted_stocks = sorted(selected.items(), key=lambda x: x[1]['score'], reverse=True)
        top_100 = sorted_stocks[:target_count]
        
        print(f"\n总匹配：{len(selected)} 只")
        print(f"选出：{len(top_100)} 只")
        print()
        
        # 统计策略分布
        strategy_dist = {}
        for symbol, data in top_100:
            for s in data['strategies']:
                strategy_dist[s] = strategy_dist.get(s, 0) + 1
        
        print("策略分布:")
        for strategy, count in sorted(strategy_dist.items()):
            print(f"  {strategy}: {count} 只")
        
        self.selected_stocks = top_100
        return top_100
        
    def generate_trading_plan(self, current_holdings=None):
        """生成交易计划"""
        if current_holdings is None:
            current_holdings = []
        
        print("\n" + "=" * 70)
        print(" " * 20 + "生成交易计划")
        print("=" * 70)
        
        # 从 100 只中选出 20-30 只作为目标持仓
        target_count = min(25, len(self.selected_stocks))
        target_holdings = [s[0] for s in self.selected_stocks[:target_count]]
        
        # 计算买卖信号
        buy_list = [s for s in target_holdings if s not in current_holdings]
        sell_list = [s for s in current_holdings if s not in target_holdings]
        hold_list = [s for s in target_holdings if s in current_holdings]
        
        self.trading_plan = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'buy': buy_list[:15],  # 最多 15 只
            'sell': sell_list,
            'hold': hold_list,
            'total_selected': len(self.selected_stocks),
            'target_positions': target_count
        }
        
        print(f"\n目标持仓：{target_count} 只")
        print(f"买入：{len(buy_list)} 只")
        print(f"卖出：{len(sell_list)} 只")
        print(f"持有：{len(hold_list)} 只")
        
        return self.trading_plan
        
    def save_report(self, output_dir='reports'):
        """保存选股报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存选股结果
        selection_report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'total_count': len(self.selected_stocks),
            'stocks': []
        }
        
        for symbol, data in self.selected_stocks:
            stock_info = {
                'symbol': symbol,
                'strategies': data['strategies'],
                'score': data['score'],
                'reasons': data['reasons'],
                'pe': round(data['fundamentals'].get('pe', 0), 2),
                'roe': round(data['fundamentals'].get('roe', 0), 2),
                'dividend_yield': round(data['fundamentals'].get('dividend_yield', 0), 2),
            }
            selection_report['stocks'].append(stock_info)
        
        # 保存 JSON
        selection_file = output_path / f'stock_selection_{selection_report["date"]}.json'
        with open(selection_file, 'w', encoding='utf-8') as f:
            json.dump(selection_report, f, ensure_ascii=False, indent=2)
        
        # 保存交易计划
        plan_file = output_path / f'trading_plan_{self.trading_plan["date"]}.json'
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(self.trading_plan, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存:")
        print(f"   选股报告：{selection_file}")
        print(f"   交易计划：{plan_file}")
        
        return selection_file, plan_file
        
    def print_top_stocks(self, top_n=10):
        """打印前 N 只股票"""
        print("\n" + "=" * 70)
        print(f" " * 18 + f"Top {top_n} 股票")
        print("=" * 70)
        print(f"{'排名':<4} {'代码':<12} {'得分':<6} {'策略':<20} {'原因':<40}")
        print("-" * 70)
        
        for i, (symbol, data) in enumerate(self.selected_stocks[:top_n], 1):
            strategies = ', '.join(data['strategies'])
            reason = data['reasons'][0] if data['reasons'] else ''
            if len(reason) > 38:
                reason = reason[:35] + '...'
            
            print(f"{i:<4} {symbol:<12} {data['score']:<6} {strategies:<20} {reason:<40}")


def main():
    print("=" * 70)
    print(" " * 15 + "每日选股和交易计划")
    print("=" * 70)
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建选股器
    selector = DailyStockSelector()
    
    # 1. 加载股票池
    print("【步骤 1】加载股票池...")
    symbols = selector.load_stocks()
    
    # 2. 生成财务数据
    print("\n【步骤 2】生成财务数据...")
    fundamentals = selector.generate_mock_fundamentals(symbols)
    
    # 3. 多策略选股
    print("\n【步骤 3】多策略选股...")
    selector.multi_strategy_selection(symbols, fundamentals, target_count=100)
    
    # 4. 打印 Top 10
    selector.print_top_stocks(top_n=10)
    
    # 5. 生成交易计划
    print("\n【步骤 4】生成交易计划...")
    # 模拟当前持仓 (实际应从交易系统获取)
    current_holdings = random.sample([s[0] for s in selector.selected_stocks], min(10, len(selector.selected_stocks)))
    plan = selector.generate_trading_plan(current_holdings)
    
    # 6. 打印交易计划
    print("\n" + "=" * 70)
    print(" " * 20 + "交易计划")
    print("=" * 70)
    print(f"\n买入 ({len(plan['buy'])}只):")
    for symbol in plan['buy'][:5]:
        print(f"  - {symbol}")
    if len(plan['buy']) > 5:
        print(f"  ... 还有 {len(plan['buy']) - 5} 只")
    
    print(f"\n卖出 ({len(plan['sell'])}只):")
    for symbol in plan['sell'][:5]:
        print(f"  - {symbol}")
    if len(plan['sell']) > 5:
        print(f"  ... 还有 {len(plan['sell']) - 5} 只")
    
    # 7. 保存报告
    print("\n【步骤 5】保存报告...")
    selector.save_report()
    
    # 8. 总结
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)
    print(f"选股：{len(selector.selected_stocks)} 只")
    print(f"买入：{len(plan['buy'])} 只")
    print(f"卖出：{len(plan['sell'])} 只")
    print()
    print("下一步:")
    print("  - 查看选股报告：cat reports/stock_selection_*.json")
    print("  - 查看交易计划：cat reports/trading_plan_*.json")
    print("  - 发送通知：python3 send_notification.py")
    print("  - 执行交易：python3 execute_trading.py")
    print()


if __name__ == '__main__':
    main()
