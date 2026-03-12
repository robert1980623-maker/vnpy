#!/usr/bin/env python3
"""
每日选股和交易计划生成 (v2 - 使用真实 Tushare 数据)

功能:
1. 多策略选股 (使用真实财务数据)
2. 生成交易计划
3. 发送钉钉通知
4. 保存选股报告
5. 显示股票名称
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
from stock_name_utils import StockNameCache, format_symbol_with_name
from tushare_fundamental_fetcher import TushareFundamentalFetcher
from logger import TaskLogger


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
        # 加载股票名称缓存
        self.name_cache = StockNameCache()
        # 初始化 Tushare 财务数据获取器
        self.fundamental_fetcher = TushareFundamentalFetcher()
        
    def load_stocks(self):
        """加载股票池"""
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem.replace('_', '.') for f in csv_files]
        print(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
        
    def get_real_fundamentals(self, symbols):
        """从 Tushare 获取真实财务数据"""
        print("\n" + "=" * 70)
        print(" " * 20 + "获取财务数据 (Tushare)")
        print("=" * 70)
        
        fundamentals = self.fundamental_fetcher.get_batch_fundamentals(symbols)
        return fundamentals
        
    def multi_strategy_selection(self, symbols, fundamentals, target_count=100):
        """多策略选股"""
        print("\n" + "=" * 70)
        print(" " * 20 + "多策略选股")
        print("=" * 70)
        
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            
            # 跳过数据不完整的股票
            if not data.get('pe') or not data.get('roe'):
                continue
            
            strategies = []
            reasons = []
            
            # 策略 1: 价值股 (PE<20, ROE>10%, 股息率>2%)
            if data.get('pe', 100) < 20 and data.get('roe', 0) > 10 and (data.get('dividend_yield') or 0) > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, ROE={data['roe']:.1f}%, 股息率={data['dividend_yield']:.1f}%")
            
            # 策略 2: 成长股 (营收增长>25%, 利润增长>30%)
            if data.get('revenue_growth', 0) > 25 and data.get('profit_growth', 0) > 30:
                strategies.append('成长')
                reasons.append(f"营收增长={data['revenue_growth']:.1f}%, 利润增长={data['profit_growth']:.1f}%")
            
            # 策略 3: 质量股 (ROE>15%)
            if data.get('roe', 0) > 15:
                strategies.append('质量')
                reasons.append(f"ROE={data['roe']:.1f}%")
            
            # 策略 4: 高息股 (股息率>3%)
            if (data.get('dividend_yield') or 0) > 3:
                strategies.append('高息')
                reasons.append(f"股息率={data['dividend_yield']:.1f}%")
            
            # 计算评分
            score = len(strategies) * 2
            if len(strategies) >= 3:
                score += 1
            if len(strategies) == 4:
                score += 1
            
            # 如果满足至少一个策略，加入候选
            if strategies:
                self.selected_stocks.append((symbol, {
                    'strategies': strategies,
                    'reasons': reasons,
                    'score': score,
                    'fundamentals': data
                }))
        
        # 按评分排序
        self.selected_stocks.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # 限制数量
        if len(self.selected_stocks) > target_count:
            self.selected_stocks = self.selected_stocks[:target_count]
        
        print(f"\n✅ 选股完成：{len(self.selected_stocks)} 只")
        
        # 显示前 10 只
        print("\n🏆 Top 10:")
        for i, (symbol, data) in enumerate(self.selected_stocks[:10], 1):
            name = self.name_cache.get_name(symbol)
            strategies_str = '+'.join(data['strategies'])
            pe = data['fundamentals'].get('pe', 'N/A')
            roe = data['fundamentals'].get('roe', 'N/A')
            print(f"  {i}. {symbol} {name} - {strategies_str} (评分：{data['score']}, PE={pe}, ROE={roe}%)")
        
        return self.selected_stocks
    
    def generate_trading_plan(self, current_holdings=None):
        """生成交易计划"""
        print("\n" + "=" * 70)
        print(" " * 20 + "生成交易计划")
        print("=" * 70)
        
        if current_holdings is None:
            current_holdings = []
        
        # 目标持仓：选股结果中的股票
        target_symbols = set([s[0] for s in self.selected_stocks[:20]])  # 前 20 只
        
        # 计算调仓
        buy_list = [s for s in target_symbols if s not in current_holdings]
        sell_list = [s for s in current_holdings if s not in target_symbols]
        hold_list = [s for s in current_holdings if s in target_symbols]
        
        self.trading_plan['buy'] = list(buy_list)[:10]  # 最多买入 10 只
        self.trading_plan['sell'] = list(sell_list)[:10]  # 最多卖出 10 只
        self.trading_plan['hold'] = list(hold_list)
        
        print(f"\n买入：{len(self.trading_plan['buy'])} 只")
        for symbol in self.trading_plan['buy'][:5]:
            name = self.name_cache.get_name(symbol)
            print(f"  - {symbol} {name}")
        if len(self.trading_plan['buy']) > 5:
            print(f"  ... 还有 {len(self.trading_plan['buy']) - 5} 只")
        
        print(f"\n卖出：{len(self.trading_plan['sell'])} 只")
        for symbol in self.trading_plan['sell'][:5]:
            name = self.name_cache.get_name(symbol)
            print(f"  - {symbol} {name}")
        if len(self.trading_plan['sell']) > 5:
            print(f"  ... 还有 {len(self.trading_plan['sell']) - 5} 只")
        
        return self.trading_plan
    
    def save_reports(self, output_dir: str = './reports'):
        """保存选股报告和交易计划"""
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
                'name': self.name_cache.get_name(symbol),
                'strategies': data['strategies'],
                'score': data['score'],
                'reasons': data['reasons'],
                'pe': round(data['fundamentals'].get('pe', 0), 2),
                'roe': round(data['fundamentals'].get('roe', 0), 2),
                'dividend_yield': round(data['fundamentals'].get('dividend_yield', 0), 2),
                'revenue_growth': round(data['fundamentals'].get('revenue_growth', 0), 2),
                'profit_growth': round(data['fundamentals'].get('profit_growth', 0), 2),
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


def main():
    """主函数"""
    logger = TaskLogger(task_name='daily_stock_selection')
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info("任务开始执行")
        print("=" * 70)
        print(" " * 20 + "每日选股系统 v2")
        print("=" * 70)

        selector = DailyStockSelector()

        # 步骤 1: 加载股票池
        symbols = selector.load_stocks()

        # 步骤 2: 获取财务数据
        fundamentals = selector.get_real_fundamentals(symbols)

        # 步骤 3: 多策略选股
        selector.multi_strategy_selection(symbols, fundamentals, target_count=100)

        # 步骤 4: 生成交易计划
        # 模拟当前持仓（实际应从虚拟账户读取）
        current_holdings = ['600066.SH', '688169.SH', '000975.SZ']
        selector.generate_trading_plan(current_holdings)

        # 步骤 5: 保存报告
        selector.save_reports()

        print("\n" + "=" * 70)
        print(" " * 20 + "完成")
        print("=" * 70)
        print(f"选股：{len(selector.selected_stocks)} 只")
        print(f"买入：{len(selector.trading_plan['buy'])} 只")
        print(f"卖出：{len(selector.trading_plan['sell'])} 只")

        print("\n下一步:")
        print("  - 查看选股报告：cat reports/stock_selection_*.json")
        print("  - 查看交易计划：cat reports/trading_plan_*.json")
        print("  - 执行交易：python3 execute_trading.py")
    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)

if __name__ == '__main__':
    main()
