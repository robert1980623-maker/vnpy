#!/usr/bin/env python3
"""
基于真实数据的每日复盘

功能:
- 使用真实股票数据
- 计算真实收益
- 分析真实交易
- 显示真实股票名称
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from stock_name_utils import StockNameCache


def load_backtest_results() -> dict:
    """加载回测结果"""
    reports_dir = Path('reports')
    
    # 找到最新的回测账户文件
    account_files = sorted(reports_dir.glob('backtest_accounts_*.json'))
    trades_files = sorted(reports_dir.glob('backtest_trades_*.json'))
    
    if not account_files or not trades_files:
        print("❌ 未找到回测结果文件")
        print("请先运行：python3 simulated_trading.py")
        return None
    
    with open(account_files[-1], 'r', encoding='utf-8') as f:
        accounts = json.load(f)
    
    with open(trades_files[-1], 'r', encoding='utf-8') as f:
        trades = json.load(f)
    
    return {
        'accounts': accounts,
        'trades': trades,
        'accounts_file': str(account_files[-1]),
        'trades_file': str(trades_files[-1])
    }


def generate_daily_review_from_backtest(target_date: str = '2024-12-31'):
    """从回测数据生成每日复盘"""
    
    print("=" * 70)
    print(" " * 20 + f"每日复盘 - {target_date}")
    print("=" * 70)
    print()
    
    # 加载回测结果
    data = load_backtest_results()
    if not data:
        return
    
    accounts = data['accounts']
    trades = data['trades']
    
    # 加载股票名称
    name_cache = StockNameCache()
    name_cache.load_cache()
    
    # 找到目标日期的账户
    target_account = None
    prev_account = None
    
    for acc in accounts:
        if acc['date'] == target_date:
            target_account = acc
        elif acc['date'] < target_date:
            prev_account = acc
    
    if not target_account:
        print(f"❌ 未找到 {target_date} 的账户数据")
        return
    
    # 1. 当日收益
    print("【1. 当日收益】")
    initial_value = accounts[0]['total_value'] if accounts else 1000000
    prev_value = prev_account['total_value'] if prev_account else initial_value
    current_value = target_account['total_value']
    daily_return = target_account['daily_return']
    
    print(f"  初始资金：¥{initial_value:,.0f}")
    print(f"  当前总值：¥{current_value:,.2f}")
    print(f"  当日盈亏：¥{current_value - prev_value:,.2f}")
    print(f"  当日收益率：{daily_return:+.2f}%")
    print()
    
    # 2. 交易执行
    print("【2. 交易执行】")
    day_trades = [t for t in trades if t['datetime'] == target_date]
    buy_trades = [t for t in day_trades if t['direction'] == 'buy']
    sell_trades = [t for t in day_trades if t['direction'] == 'sell']
    
    print(f"  买入：{len(buy_trades)} 只")
    print(f"  卖出：{len(sell_trades)} 只")
    print(f"  成交：{len(day_trades)} 笔")
    
    total_fees = sum(t['fee'] for t in day_trades)
    print(f"  手续费：¥{total_fees:.2f}")
    print()
    
    # 3. 选股策略评估 (简化)
    print("【3. 选股策略评估】")
    print("  (基于持仓表现)")
    
    # 计算持仓股票的当日表现
    positions = target_account.get('positions', {})
    if positions:
        print(f"  持仓数量：{len(positions)} 只")
        print(f"  持仓市值：¥{sum(p.get('volume', 0) * p.get('avg_price', 0) for p in positions.values()):,.2f}")
    print()
    
    # 4. 个股表现
    print("【4. 个股表现】")
    
    # 最佳股票 (当日买入的)
    if buy_trades:
        print("  买入股票:")
        for trade in buy_trades[:3]:
            symbol = trade['symbol']
            name = name_cache.get_name(symbol)
            volume = trade['volume']
            amount = trade['amount']
            
            if name:
                print(f"    🥇 {symbol} ({name})")
            else:
                print(f"    🥇 {symbol}")
            
            print(f"       买入 {volume} 股，¥{trade['price']:.2f}，金额 ¥{amount:,.2f}")
    
    print()
    
    # 卖出股票
    if sell_trades:
        print("  卖出股票:")
        for trade in sell_trades[:3]:
            symbol = trade['symbol']
            name = name_cache.get_name(symbol)
            volume = trade['volume']
            amount = trade['amount']
            
            if name:
                print(f"    📉 {symbol} ({name})")
            else:
                print(f"    📉 {symbol}")
            
            print(f"       卖出 {volume} 股，¥{trade['price']:.2f}，金额 ¥{amount:,.2f}")
    
    print()
    
    # 5. 最终持仓
    print("【5. 当前持仓】")
    if positions:
        for symbol, pos in positions.items():
            name = name_cache.get_name(symbol)
            volume = pos.get('volume', 0) if isinstance(pos, dict) else pos.volume
            avg_price = pos.get('avg_price', 0) if isinstance(pos, dict) else pos.avg_price
            cost = pos.get('cost', 0) if isinstance(pos, dict) else pos.cost
            
            if name:
                print(f"  {symbol} ({name})")
            else:
                print(f"  {symbol}")
            
            print(f"    持仓：{volume} 股，均价 ¥{avg_price:.2f}，市值 ¥{volume * avg_price:,.2f}")
    else:
        print("  无持仓")
    print()
    
    # 6. 累计收益
    print("【6. 累计收益】")
    total_return = (current_value - initial_value) / initial_value * 100
    print(f"  初始资金：¥{initial_value:,.0f}")
    print(f"  当前总值：¥{current_value:,.2f}")
    print(f"  累计收益：¥{current_value - initial_value:,.2f}")
    print(f"  累计收益率：{total_return:+.2f}%")
    
    # 统计交易
    total_trades = len(trades)
    total_fees_all = sum(t['fee'] for t in trades)
    print(f"  总交易：{total_trades} 笔")
    print(f"  总手续费：¥{total_fees_all:,.2f}")
    print()
    
    # 7. 保存报告
    report = {
        'date': target_date,
        'initial_value': initial_value,
        'current_value': current_value,
        'daily_return': daily_return,
        'total_return': round(total_return, 2),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'positions_count': len(positions),
        'total_trades': total_trades,
        'total_fees': round(total_fees_all, 2),
    }
    
    report_dir = Path('reports/daily')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'daily_review_{target_date}_real.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_file}")
    print()
    
    print("=" * 70)
    
    return report


def main():
    print("=" * 70)
    print(" " * 15 + "基于真实数据的每日复盘")
    print("=" * 70)
    print()
    
    # 默认复盘最后一个交易日
    target_date = '2024-12-31'
    
    print(f"复盘日期：{target_date}")
    print()
    
    generate_daily_review_from_backtest(target_date)


if __name__ == '__main__':
    main()
