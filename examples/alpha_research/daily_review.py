#!/usr/bin/env python3
"""
每日复盘报告

功能:
- 统计当日收益
- 分析交易执行
- 评估选股策略
- 分享心得
- 明日展望
- 显示股票名称
"""

import json
from pathlib import Path
from datetime import datetime
import random

# 导入股票名称工具
from stock_name_utils import StockNameCache, format_symbol_with_name


def generate_daily_review():
    """生成每日复盘报告"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 加载股票名称缓存
    name_cache = StockNameCache()
    
    print("=" * 70)
    print(" " * 20 + f"每日复盘 - {today}")
    print("=" * 70)
    print()
    
    # 模拟当日数据
    initial_value = 1000000
    current_value = initial_value + random.uniform(-5000, 15000)
    daily_return = (current_value - initial_value) / initial_value * 100
    
    # 1. 当日收益
    print("【1. 当日收益】")
    print(f"  初始资金：¥{initial_value:,.0f}")
    print(f"  当前总值：¥{current_value:,.2f}")
    print(f"  当日盈亏：¥{current_value - initial_value:,.2f}")
    print(f"  当日收益率：{daily_return:+.2f}%")
    print()
    
    # 2. 交易执行
    print("【2. 交易执行】")
    buy_count = random.randint(3, 10)
    sell_count = random.randint(2, 8)
    success_rate = random.uniform(85, 100)
    
    print(f"  买入：{buy_count} 只")
    print(f"  卖出：{sell_count} 只")
    print(f"  成交率：{success_rate:.1f}%")
    print(f"  滑点：{random.uniform(0.5, 1.5):.2f}%")
    print(f"  手续费：¥{random.uniform(50, 200):.2f}")
    print()
    
    # 3. 选股策略评估
    print("【3. 选股策略评估】")
    strategies = ['价值', '成长', '质量', '高息']
    for strategy in strategies:
        return_rate = random.uniform(-2, 5)
        print(f"  {strategy}策略：{return_rate:+.2f}%")
    print()
    
    # 4. 最佳/最差股票 (带名称)
    print("【4. 个股表现】")
    
    # 生成模拟数据 (实际应从交易记录获取)
    best_stocks = [
        ('604808.SZ', random.uniform(4, 6)),
        ('301577.SZ', random.uniform(5, 7)),
        ('608999.SZ', random.uniform(4, 6)),
    ]
    
    worst_stocks = [
        ('607981.SZ', random.uniform(-5, -3)),
        ('006670.SZ', random.uniform(-4, -2)),
        ('306813.SZ', random.uniform(-4, -2)),
    ]
    
    print("  最佳股票:")
    for symbol, gain in best_stocks:
        symbol_with_name = format_symbol_with_name(symbol)
        print(f"    🥇 {symbol_with_name}: +{gain:.2f}%")
    
    print()
    print("  最差股票:")
    for symbol, loss in worst_stocks:
        symbol_with_name = format_symbol_with_name(symbol)
        print(f"    📉 {symbol_with_name}: {loss:.2f}%")
    print()
    
    # 5. 心得分享
    print("【5. 今日心得】")
    insights = [
        "今日市场震荡，价值股表现稳健，高股息策略抗跌性较好。",
        "成长股波动较大，建议控制仓位，等待更好买点。",
        "选股策略中，质量因子表现突出，ROE>15% 的股票普遍跑赢大盘。",
        "交易执行方面，早盘买入时机较好，滑点控制在 1% 以内。",
        "明日关注成交量变化，若持续放量可适当增加仓位。",
    ]
    for insight in random.sample(insights, 3):
        print(f"  • {insight}")
    print()
    
    # 6. 明日展望
    print("【6. 明日展望】")
    print(f"  预计开盘：{'震荡' if random.random() > 0.5 else '小幅高开'}")
    print(f"  操作策略：{'逢低布局' if random.random() > 0.5 else '持股观望'}")
    print(f"  关注板块：{random.choice(['科技', '消费', '金融', '医药', '新能源'])}")
    print(f"  仓位建议：{random.randint(60, 80)}%")
    print()
    
    # 7. 保存报告
    report = {
        'date': today,
        'initial_value': initial_value,
        'current_value': current_value,
        'daily_return': round(daily_return, 2),
        'buy_count': buy_count,
        'sell_count': sell_count,
        'success_rate': round(success_rate, 2),
        'best_stocks': [
            {'symbol': s, 'gain': round(g, 2)} for s, g in best_stocks
        ],
        'worst_stocks': [
            {'symbol': s, 'gain': round(g, 2)} for s, g in worst_stocks
        ],
        'insights': random.sample(insights, 3),
    }
    
    report_dir = Path('reports/daily')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'daily_review_{today}.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_file}")
    print()
    
    return report


if __name__ == '__main__':
    generate_daily_review()
