#!/usr/bin/env python3
"""
使用真实数据测试回测
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy, create_cross_sectional_engine

# 使用本地定义的 Interval
class Interval:
    DAILY = "daily"

print('=' * 70)
print(' ' * 20 + '使用真实数据测试回测引擎')
print('=' * 70)
print()

# 创建实验室
lab = AlphaLab('./lab/real_data_test')

# 创建引擎
engine = create_cross_sectional_engine(lab, initial_capital=1_000_000)

# 设置参数
engine.set_parameters(
    vt_symbols=['000630.SZ', '000807.SZ', '000975.SZ', '000999.SZ', '002028.SZ'],
    interval=Interval.DAILY,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        'max_pe': 20,
        'min_roe': 10,
        'min_dividend_yield': 2.0
    }
)

print('✅ 回测引擎配置成功')
print(f'   股票代码：5 只')
print(f'   回测周期：2024-01-01 到 2024-12-31')
print()

# 加载数据
print('加载真实市场数据...')
try:
    engine.load_data()
    print('✅ 数据加载成功')
    
    # 检查加载的数据
    if hasattr(engine, '_bars_dict'):
        total_bars = sum(len(bars) for bars in engine._bars_dict.values())
        print(f'   加载 K 线数据：{total_bars} 条')
        print(f'   覆盖股票：{len(engine._bars_dict)} 只')
    
    print()
    print('数据示例:')
    for symbol, bars in list(engine._bars_dict.items())[:2]:
        if bars:
            first_bar = bars[0]
            last_bar = bars[-1]
            print(f'   {symbol}:')
            print(f'     首条：{first_bar.datetime} - 收盘：{first_bar.close_price}')
            print(f'     末条：{last_bar.datetime} - 收盘：{last_bar.close_price}')
            print(f'     总条数：{len(bars)}')
    
except Exception as e:
    print(f'⚠️ 数据加载问题：{e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 70)
print(' ' * 25 + '真实数据测试完成！')
print('=' * 70)
