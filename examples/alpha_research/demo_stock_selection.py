#!/usr/bin/env python3
"""
模拟交易选股流程演示

展示完整的选股和交易信号生成流程
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.dataset import StockPool, FundamentalData

print('=' * 70)
print(' ' * 20 + '模拟交易 - 选股流程演示')
print('=' * 70)
print()

# 1. 创建实验室
print('【步骤 1】创建 AlphaLab...')
lab = AlphaLab('./lab/demo_trading')
print('✅ AlphaLab 创建成功')
print()

# 2. 创建股票池
print('【步骤 2】创建股票池...')
pool = StockPool('demo_pool')
for stock in ['000001.SZ', '600036.SH', '600519.SH', '000858.SZ', '002415.SZ']:
    pool.add(stock)
print(f'✅ 股票池创建成功：{pool.name}')
print(f'   股票数量：{pool.count()}')
print(f'   股票列表：{pool.get_stocks()[:5]}')
print()

# 3. 添加财务数据
print('【步骤 3】添加财务数据...')
fund_data = FundamentalData()
mock_data = {
    '000001.SZ': {'pe': 5.2, 'roe': 8.5, 'dividend_yield': 4.5, 'revenue_growth': 5.2, 'profit_growth': 6.8},
    '600036.SH': {'pe': 5.8, 'roe': 12.5, 'dividend_yield': 5.2, 'revenue_growth': 8.5, 'profit_growth': 10.2},
    '600519.SH': {'pe': 25.5, 'roe': 15.2, 'dividend_yield': 2.5, 'revenue_growth': 18.5, 'profit_growth': 22.3},
    '000858.SZ': {'pe': 15.2, 'roe': 12.8, 'dividend_yield': 3.2, 'revenue_growth': 12.5, 'profit_growth': 15.8},
    '002415.SZ': {'pe': 28.5, 'roe': 18.5, 'dividend_yield': 1.8, 'revenue_growth': 25.8, 'profit_growth': 32.5},
}
for symbol, data in mock_data.items():
    fund_data.add_indicator(symbol, 'pe', data['pe'])
    fund_data.add_indicator(symbol, 'roe', data['roe'])
    fund_data.add_indicator(symbol, 'dividend_yield', data['dividend_yield'])
print(f'✅ 财务数据添加成功：{len(mock_data)} 只股票')
print()

# 4. 运行选股策略
print('【步骤 4】运行价值股策略...')
print('   策略参数:')
print('     max_pe: 20')
print('     min_roe: 10%')
print('     min_dividend_yield: 2.0%')
print()

strategy = ValueStockStrategy(
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2.0
)

# 筛选股票
selected = []
for symbol in pool.stocks:
    try:
        pe = fund_data.get_latest_indicator(symbol, 'pe')
        roe = fund_data.get_latest_indicator(symbol, 'roe')
        div = fund_data.get_latest_indicator(symbol, 'dividend_yield')
        
        if pe and roe and div:
            if pe < 20 and roe > 10 and div > 2.0:
                selected.append(symbol)
                print(f'   ✅ {symbol}: PE={pe}, ROE={roe}%, 股息率={div}%')
            else:
                reason = []
                if pe >= 20: reason.append(f'PE={pe}≥20')
                if roe <= 10: reason.append(f'ROE={roe}%≤10%')
                if div <= 2.0: reason.append(f'股息率={div}%≤2%')
                print(f'   ❌ {symbol}: PE={pe}, ROE={roe}%, 股息率={div}% ({", ".join(reason)})')
    except Exception as e:
        print(f'   ⚠️ {symbol}: 数据获取失败')

print()
print(f'✅ 筛选结果：{len(selected)} 只股票')
print(f'   入选股票：{selected}')
print()

# 5. 生成交易信号
print('【步骤 5】生成交易信号...')
print('   假设当前持仓：[]')
print('   目标持仓：' + str(selected))
print()

# 计算买卖信号
current_holdings = []
buy_signals = [s for s in selected if s not in current_holdings]
sell_signals = [s for s in current_holdings if s not in selected]

print(f'   买入信号：{buy_signals}')
print(f'   卖出信号：{sell_signals}')
print()

# 6. 计算仓位
print('【步骤 6】计算仓位...')
initial_capital = 1_000_000
position_size = 0.03  # 3% 仓位
max_positions = 30

capital_per_stock = initial_capital * position_size
print(f'   初始资金：¥{initial_capital:,.0f}')
print(f'   单只仓位：{position_size * 100}%')
print(f'   单只金额：¥{capital_per_stock:,.0f}')
print()

# 模拟价格
prices = {
    '600036.SH': 35.2,
    '000858.SZ': 42.5,
}

for symbol in buy_signals:
    price = prices.get(symbol, 20.0)  # 默认价格
    volume = int(capital_per_stock / price / 100) * 100  # 100 股整数倍
    total = volume * price
    print(f'   {symbol}: 价格¥{price:.2f}, 买入{volume}股，金额¥{total:,.0f}')

print()
print('=' * 70)
print(' ' * 25 + '选股流程演示完成')
print('=' * 70)
print()
print('📋 总结:')
print('  1. ✅ 创建股票池')
print('  2. ✅ 添加财务数据')
print('  3. ✅ 运行选股策略')
print('  4. ✅ 生成交易信号')
print('  5. ✅ 计算仓位')
print()
print('🎯 下一步:')
print('  - 运行模拟交易：python3 start_trading.py --mode paper')
print('  - 查看配置：cat config/paper_config.yaml')
print('  - 查看文档：open docs/alpha/QUICK_START.md')
print()
