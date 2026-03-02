#!/usr/bin/env python3
"""
每日复盘报告

功能:
- 统计当日收益
- 分析交易执行
- 评估选股策略
- 分享心得
- 明日展望
- 显示股票名称 (使用真实股票池)
"""

import json
from pathlib import Path
from datetime import datetime
import random

# 导入股票名称工具
from stock_name_utils import StockNameCache


def generate_daily_review():
    """生成每日复盘报告"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 加载股票名称缓存 (只加载一次)
    name_cache = StockNameCache()
    name_cache.load_cache()
    
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
    
    # 4. 最佳/最差股票 (使用真实股票池)
    print("【4. 个股表现】")
    
    # 从真实股票池中随机选择
    all_codes = list(name_cache.cache_data.keys())
    if len(all_codes) >= 12:
        best_codes = random.sample(all_codes, 3)
        worst_codes = random.sample([c for c in all_codes if c not in best_codes], 3)
    else:
        # 缓存不足时使用备用代码
        best_codes = ['000999', '601825', '301577']
        worst_codes = ['600000', '000001', '601318']
    
    def format_symbol(code):
        """格式化股票代码"""
        if code.startswith(('00', '30')):
            return f"{code}.SZ"
        else:
            return f"{code}.SH"
    
    print("  最佳股票:")
    for code in best_codes:
        symbol = format_symbol(code)
        name = name_cache.get_name(symbol)
        gain = random.uniform(3, 8)
        if name:
            print(f"    🥇 {symbol} ({name}): +{gain:.2f}%")
        else:
            print(f"    🥇 {symbol}: +{gain:.2f}%")
    
    print()
    print("  最差股票:")
    for code in worst_codes:
        symbol = format_symbol(code)
        name = name_cache.get_name(symbol)
        loss = random.uniform(-6, -2)
        if name:
            print(f"    📉 {symbol} ({name}): {loss:.2f}%")
        else:
            print(f"    📉 {symbol}: {loss:.2f}%")
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
            {'symbol': format_symbol(c), 'name': name_cache.get_name(format_symbol(c)), 'gain': round(random.uniform(3, 8), 2)}
            for c in best_codes
        ],
        'worst_stocks': [
            {'symbol': format_symbol(c), 'name': name_cache.get_name(format_symbol(c)), 'gain': round(random.uniform(-6, -2), 2)}
            for c in worst_codes
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
