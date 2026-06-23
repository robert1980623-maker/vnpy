#!/usr/bin/env python3
"""
快速选股脚本（简化版 - 使用 daily_basic 数据）
用于在财务缓存缺失时快速生成选股报告
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent.parent))

from tushare_fundamental_fetcher_v2 import TushareBatchFetcher
from stock_name_utils import StockNameCache


def quick_selection():
    """快速选股"""
    print("=" * 70)
    print(" " * 20 + "快速选股系统（简化版）")
    print("=" * 70)
    
    # 初始化
    fetcher = TushareBatchFetcher()
    name_cache = StockNameCache()
    
    # 获取今日交易日
    today = datetime.now().strftime('%Y%m%d')
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 交易日：{today}")
    
    # 获取全市场 daily_basic 数据
    print("\n📥 获取全市场数据...")
    daily_basic = fetcher._fetch_daily_basic(today)
    print(f"✅ 获取到 {len(daily_basic)} 只股票数据")
    
    # 简化选股策略（只使用 daily_basic 中的指标）
    selected = []
    
    for symbol, data in daily_basic.items():
        pe = data.get('pe')
        pb = data.get('pb')
        dividend_yield = data.get('dividend_yield')
        total_mv = data.get('total_mv')  # 总市值（亿）
        
        # 跳过数据不完整的
        if not pe or pe <= 0:
            continue
        
        strategies = []
        reasons = []
        score = 0
        
        # 策略 1: 低估值 (PE < 15)
        if pe < 15:
            strategies.append('低估值')
            reasons.append(f'PE={pe:.1f}')
            score += 2
        
        # 策略 2: 高股息 (股息率 > 3%)
        if dividend_yield and dividend_yield > 3:
            strategies.append('高股息')
            reasons.append(f'股息率={dividend_yield:.1f}%')
            score += 2
        
        # 策略 3: 小市值 (总市值 < 100 亿)
        if total_mv and total_mv < 100:
            strategies.append('小市值')
            reasons.append(f'市值={total_mv:.1f}亿')
            score += 1
        
        # 策略 4: 低 PB (PB < 2)
        if pb and pb < 2:
            strategies.append('低 PB')
            reasons.append(f'PB={pb:.2f}')
            score += 1
        
        # 如果满足至少一个策略，加入候选
        if strategies:
            name = name_cache.get_name(symbol)
            selected.append({
                'symbol': symbol,
                'name': name,
                'strategies': strategies,
                'reasons': reasons,
                'score': score,
                'pe': pe,
                'pb': pb,
                'dividend_yield': dividend_yield,
                'total_mv': total_mv
            })
    
    # 按评分排序
    selected.sort(key=lambda x: x['score'], reverse=True)
    
    # 限制数量
    if len(selected) > 20:
        selected = selected[:20]
    
    print(f"\n✅ 选股完成：{len(selected)} 只")
    
    # 显示 Top 10
    print("\n🏆 Top 10:")
    for i, stock in enumerate(selected[:10], 1):
        strategies_str = '+'.join(stock['strategies'])
        print(f"  {i}. {stock['symbol']} {stock['name']} - {strategies_str} (评分：{stock['score']}, PE={stock['pe']:.1f}, 股息率={stock['dividend_yield'] or 'N/A'})")
    
    # 生成报告
    report = {
        'date': today_str,
        'time': datetime.now().strftime('%H:%M:%S'),
        'total_count': len(selected),
        'strategy_distribution': {},
        'stocks': selected
    }
    
    # 统计策略分布
    for stock in selected:
        for strategy in stock['strategies']:
            report['strategy_distribution'][strategy] = report['strategy_distribution'].get(strategy, 0) + 1
    
    # 保存报告
    report_path = project_root / 'reports' / f'stock_selection_{today_str}.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存：{report_path}")
    
    # 生成交易计划（简化版）
    trading_plan = {
        'date': today_str,
        'buy': [{'symbol': s['symbol'], 'name': s['name'], 'reason': '+'.join(s['strategies'])} for s in selected[:5]],
        'sell': [],
        'notes': '简化版选股报告，基于 daily_basic 数据'
    }
    
    plan_path = project_root / 'reports' / f'trading_plan_{today_str}.json'
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(trading_plan, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 交易计划已保存：{plan_path}")
    
    # 统计信息
    print("\n" + "=" * 70)
    print("📊 选股统计")
    print("=" * 70)
    print(f"入选股票数量：{len(selected)}")
    print(f"策略分布：")
    for strategy, count in sorted(report['strategy_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {strategy}: {count}只")
    
    if selected:
        print(f"\n🎯 重点推荐标的:")
        for i, stock in enumerate(selected[:3], 1):
            print(f"  {i}. {stock['symbol']} {stock['name']} ({'+'.join(stock['strategies'])})")
    
    return report


if __name__ == '__main__':
    # 设置环境变量
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    quick_selection()
