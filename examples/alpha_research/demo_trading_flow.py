#!/usr/bin/env python3
"""
模拟交易流程演示 - 简化版

展示完整的选股和交易流程
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.alpha.dataset import StockPool, FundamentalData, FinancialIndicator

print('=' * 70)
print(' ' * 20 + '模拟交易 - 完整流程演示')
print('=' * 70)
print()

# 步骤 1: 创建股票池
print('【步骤 1】创建股票池...')
pool = StockPool('demo_pool')
for stock in ['000001.SZ', '600036.SH', '600519.SH', '000858.SZ', '002415.SZ']:
    pool.add(stock)
print(f'✅ 股票池：{pool.name}')
print(f'   股票数量：{pool.count()}')
print(f'   股票：{pool.get_stocks()}')
print()

# 步骤 2: 添加财务数据
print('【步骤 2】添加财务数据...')
fund_data = FundamentalData()

# 创建财务指标数据
indicators = [
    FinancialIndicator('000001.SZ', '2024-12-31', pe=5.2, roe=8.5, dividend_yield=4.5, revenue_growth=5.2, profit_growth=6.8),
    FinancialIndicator('600036.SH', '2024-12-31', pe=5.8, roe=12.5, dividend_yield=5.2, revenue_growth=8.5, profit_growth=10.2),
    FinancialIndicator('600519.SH', '2024-12-31', pe=25.5, roe=15.2, dividend_yield=2.5, revenue_growth=18.5, profit_growth=22.3),
    FinancialIndicator('000858.SZ', '2024-12-31', pe=15.2, roe=12.8, dividend_yield=3.2, revenue_growth=12.5, profit_growth=15.8),
    FinancialIndicator('002415.SZ', '2024-12-31', pe=28.5, roe=18.5, dividend_yield=1.8, revenue_growth=25.8, profit_growth=32.5),
]

for ind in indicators:
    fund_data.add(ind)

print(f'✅ 财务数据：{len(indicators)} 只股票')
print()

# 步骤 3: 运行选股策略
print('【步骤 3】运行价值股策略筛选...')
print('   条件：PE < 20, ROE > 10%, 股息率 > 2%')
print()

selected = []
for symbol in pool.get_stocks():
    ind = fund_data.get_latest(symbol)
    if ind:
        pe = ind.pe
        roe = ind.roe
        div = ind.dividend_yield
        
        if pe and roe and div:
            if pe < 20 and roe > 10 and div > 2.0:
                selected.append(symbol)
                print(f'   ✅ {symbol}: PE={pe}, ROE={roe}%, 股息率={div}% ✓')
            else:
                reasons = []
                if pe >= 20: reasons.append(f'PE 过高')
                if roe <= 10: reasons.append(f'ROE 过低')
                if div <= 2.0: reasons.append(f'股息率过低')
                print(f'   ❌ {symbol}: PE={pe}, ROE={roe}%, 股息率={div}% ({", ".join(reasons)})')

print()
print(f'✅ 筛选结果：{len(selected)} 只股票入选')
print(f'   入选列表：{selected}')
print()

# 步骤 4: 生成交易信号
print('【步骤 4】生成交易信号...')
current_holdings = []  # 假设当前空仓
target_positions = selected

buy_signals = [s for s in target_positions if s not in current_holdings]
sell_signals = [s for s in current_holdings if s not in target_positions]

print(f'   当前持仓：{current_holdings if current_holdings else "(空仓)"}')
print(f'   目标持仓：{target_positions if target_positions else "(空仓)"}')
print()
print(f'   📈 买入信号：{buy_signals if buy_signals else "(无)"}')
print(f'   📉 卖出信号：{sell_signals if sell_signals else "(无)"}')
print()

# 步骤 5: 计算仓位和订单
print('【步骤 5】计算仓位和订单...')
initial_capital = 1_000_000
position_ratio = 0.03  # 3% 仓位
capital_per_stock = initial_capital * position_ratio

print(f'   初始资金：¥{initial_capital:,.0f}')
print(f'   单只仓位：{position_ratio * 100}%')
print(f'   单只金额：¥{capital_per_stock:,.0f}')
print()

# 模拟价格
prices = {
    '600036.SH': 35.20,
    '000858.SZ': 42.50,
}

print('   订单计算:')
for symbol in buy_signals:
    price = prices.get(symbol, 20.00)
    volume = int(capital_per_stock / price / 100) * 100  # 100 股整数倍
    total = volume * price
    commission = total * 0.0003  # 万分之三手续费
    print(f'   📝 {symbol}:')
    print(f'      价格：¥{price:.2f}')
    print(f'      数量：{volume} 股')
    print(f'      金额：¥{total:,.0f}')
    print(f'      手续费：¥{commission:.2f}')
    print(f'      总计：¥{total + commission:,.2f}')
    print()

# 步骤 6: 模拟执行
print('【步骤 6】模拟交易执行...')
print()

cash = initial_capital
positions = {}

for symbol in buy_signals:
    price = prices.get(symbol, 20.00)
    volume = int(capital_per_stock / price / 100) * 100
    total = volume * price
    commission = total * 0.0003
    
    if cash >= total + commission:
        cash -= (total + commission)
        positions[symbol] = {'volume': volume, 'avg_price': price}
        print(f'   ✅ 买入 {symbol}: {volume}股 @ ¥{price:.2f}')
    else:
        print(f'   ❌ 资金不足：{symbol}')

print()

# 步骤 7: 持仓概览
print('【步骤 7】持仓概览...')
print()
print('=' * 70)
print('模拟交易组合')
print('=' * 70)
print(f'初始资金：¥{initial_capital:,.0f}')
print(f'当前资金：¥{cash:,.2f}')
print(f'持仓数量：{len(positions)}')
print()

if positions:
    print('持仓明细:')
    print(f'{"代码":<12} {"数量":>10} {"成本":>10} {"当前价":>10} {"市值":>12} {"盈亏":>10}')
    print('-' * 70)
    
    current_prices = {
        '600036.SH': 35.80,  # 上涨
        '000858.SZ': 41.50,  # 下跌
    }
    
    total_market_value = 0
    total_profit = 0
    
    for symbol, pos in positions.items():
        cost = pos['avg_price']
        volume = pos['volume']
        current = current_prices.get(symbol, cost)
        market_value = volume * current
        profit = (current - cost) * volume
        profit_rate = (current - cost) / cost * 100
        
        total_market_value += market_value
        total_profit += profit
        
        print(f'{symbol:<12} {volume:>10} {cost:>10.2f} {current:>10.2f} {market_value:>12,.0f} {profit:>10,.2f} ({profit_rate:>6.2f}%)')
    
    print('-' * 70)
    portfolio_value = cash + total_market_value
    total_return = portfolio_value - initial_capital
    total_return_rate = total_return / initial_capital * 100
    
    print(f'{"组合总值":<44} {portfolio_value:>12,.2f}')
    print(f'{"总盈亏":<44} {total_return:>10,.2f} ({total_return_rate:>6.2f}%)')

print('=' * 70)
print()

# 总结
print('📋 流程总结:')
print('  1. ✅ 创建股票池')
print('  2. ✅ 添加财务数据')
print('  3. ✅ 运行选股策略')
print('  4. ✅ 生成交易信号')
print('  5. ✅ 计算仓位订单')
print('  6. ✅ 模拟交易执行')
print('  7. ✅ 查看持仓概览')
print()
print('🎯 下一步:')
print('  - 运行真实模拟：python3 start_trading.py --mode paper')
print('  - 查看配置：cat config/paper_config.yaml')
print('  - 查看文档：open docs/alpha/QUICK_START.md')
print()
