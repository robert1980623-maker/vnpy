#!/usr/bin/env python3
"""
每日/每周复盘报告

功能:
- 每日收益统计
- 交易分析
- 持仓分析
- 周度总结
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from virtual_account import VirtualAccount


def generate_daily_report(account: VirtualAccount, date: str = None):
    """生成每日复盘报告"""
    
    if not account.daily_snapshots:
        print("❌ 无交易数据")
        return
    
    # 找到指定日期的快照
    if date:
        snapshot = next((s for s in account.daily_snapshots if s.date == date), None)
    else:
        snapshot = account.daily_snapshots[-1]
    
    if not snapshot:
        print(f"❌ 未找到 {date} 的数据")
        return
    
    print("=" * 70)
    print(" " * 20 + f"每日复盘 - {snapshot.date}")
    print("=" * 70)
    print()
    
    # 1. 当日收益
    print("【1. 当日收益】")
    print(f"  账户总值：¥{snapshot.total_value:,.2f}")
    print(f"  当日盈亏：¥{snapshot.daily_return:,.2f}")
    print(f"  当日收益率：{snapshot.daily_return_rate:+.2f}%")
    print()
    
    # 2. 交易执行
    print("【2. 交易执行】")
    print(f"  买入：{snapshot.buy_count} 只")
    print(f"  卖出：{snapshot.sell_count} 只")
    print(f"  持仓：{snapshot.positions_count} 只")
    
    # 计算当日交易费用
    day_trades = [t for t in account.trades if t.datetime == snapshot.date]
    total_fees = sum(t.fee for t in day_trades)
    print(f"  手续费：¥{total_fees:.2f}")
    print()
    
    # 3. 持仓情况
    print("【3. 持仓情况】")
    if snapshot.positions:
        for pos in snapshot.positions:
            profit_rate = pos.get('profit_rate', 0)
            profit = pos.get('profit', 0)
            print(f"  {pos['symbol']} ({pos.get('name', '')})")
            print(f"    持仓：{pos['volume']} 股")
            print(f"    成本：¥{pos['avg_price']:.2f}")
            print(f"    现价：¥{pos.get('current_price', 0):.2f}")
            print(f"    盈亏：¥{profit:,.2f} ({profit_rate:+.2f}%)")
            print()
    else:
        print("  无持仓")
    print()
    
    # 4. 累计收益
    print("【4. 累计收益】")
    perf = account.get_performance()
    print(f"  初始资金：¥{perf['initial_capital']:,.0f}")
    print(f"  当前总值：¥{perf['current_value']:,.2f}")
    print(f"  累计收益：¥{perf['total_return']:,.2f}")
    print(f"  累计收益率：{perf['total_return_rate']:+.2f}%")
    print(f"  交易天数：{perf['trading_days']} 天")
    print(f"  总交易：{perf['total_trades']} 笔")
    print()
    
    # 5. 风险控制
    print("【5. 风险控制】")
    print(f"  最大回撤：{perf['max_drawdown']:.2f}%")
    print(f"  日均收益：{perf['avg_daily_return']:+.2f}%")
    print(f"  最大单日收益：+{perf['max_daily_return']:.2f}%")
    print(f"  最大单日亏损：{perf['min_daily_return']:.2f}%")
    print()
    
    # 6. 保存报告
    report = {
        'date': snapshot.date,
        'total_value': snapshot.total_value,
        'daily_return': snapshot.daily_return,
        'daily_return_rate': snapshot.daily_return_rate,
        'positions_count': snapshot.positions_count,
        'buy_count': snapshot.buy_count,
        'sell_count': snapshot.sell_count,
        'performance': perf
    }
    
    report_dir = Path('reports/daily')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'daily_report_{snapshot.date}.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_file}")
    print()
    print("=" * 70)
    
    return report


def generate_weekly_report(account: VirtualAccount, week_end_date: str = None):
    """生成每周复盘报告"""
    
    if not account.daily_snapshots:
        print("❌ 无交易数据")
        return
    
    # 确定周结束日期
    if week_end_date:
        end_date = week_end_date
    else:
        end_date = account.daily_snapshots[-1].date
    
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=6)
    start_date = start_dt.strftime('%Y-%m-%d')
    
    # 筛选本周数据
    week_snapshots = [
        s for s in account.daily_snapshots
        if start_date <= s.date <= end_date
    ]
    
    if not week_snapshots:
        print(f"❌ {start_date} ~ {end_date} 无数据")
        return
    
    print("=" * 70)
    print(" " * 20 + f"每周复盘")
    print("=" * 70)
    print(f"周期：{start_date} ~ {end_date}")
    print(f"交易天数：{len(week_snapshots)} 天")
    print()
    
    # 1. 周度收益
    print("【1. 周度收益】")
    week_start_value = week_snapshots[0].total_value
    week_end_value = week_snapshots[-1].total_value
    week_return = week_end_value - week_start_value
    week_return_rate = week_return / week_start_value * 100 if week_start_value > 0 else 0
    
    print(f"  期初总值：¥{week_start_value:,.2f}")
    print(f"  期末总值：¥{week_end_value:,.2f}")
    print(f"  周度收益：¥{week_return:,.2f}")
    print(f"  周度收益率：{week_return_rate:+.2f}%")
    print()
    
    # 2. 每日表现
    print("【2. 每日表现】")
    print(f"  {'日期':<12} {'总值':>15} {'当日收益':>12} {'收益率':>10}")
    print(f"  {'-'*12} {'-'*15} {'-'*12} {'-'*10}")
    
    for snapshot in week_snapshots:
        print(f"  {snapshot.date:<12} ¥{snapshot.total_value:>14,.0f} ¥{snapshot.daily_return:>11,.0f} {snapshot.daily_return_rate:>+9.2f}%")
    
    print()
    
    # 3. 交易统计
    print("【3. 交易统计】")
    week_trades = [
        t for t in account.trades
        if any(s.date == t.datetime for s in week_snapshots)
    ]
    
    buy_trades = [t for t in week_trades if t.direction == 'buy']
    sell_trades = [t for t in week_trades if t.direction == 'sell']
    total_fees = sum(t.fee for t in week_trades)
    
    print(f"  买入：{len(buy_trades)} 笔")
    print(f"  卖出：{len(sell_trades)} 笔")
    print(f"  总交易：{len(week_trades)} 笔")
    print(f"  总手续费：¥{total_fees:.2f}")
    print()
    
    # 4. 周度最佳/最差
    print("【4. 周度表现】")
    daily_returns = [s.daily_return_rate for s in week_snapshots]
    best_day = max(daily_returns)
    worst_day = min(daily_returns)
    avg_return = sum(daily_returns) / len(daily_returns)
    
    print(f"  最佳交易日：+{best_day:.2f}%")
    print(f"  最差交易日：{worst_day:.2f}%")
    print(f"  平均日收益：{avg_return:+.2f}%")
    print()
    
    # 5. 周末持仓
    print("【5. 周末持仓】")
    final_snapshot = week_snapshots[-1]
    if final_snapshot.positions:
        for pos in final_snapshot.positions:
            profit_rate = pos.get('profit_rate', 0)
            print(f"  {pos['symbol']} ({pos.get('name', '')})")
            print(f"    持仓：{pos['volume']} 股，盈亏：{profit_rate:+.2f}%")
    else:
        print("  无持仓")
    print()
    
    # 6. 周度总结
    print("【6. 周度总结】")
    if week_return_rate > 0:
        print(f"  ✅ 本周盈利 {week_return_rate:.2f}%，表现良好")
    else:
        print(f"  ⚠️ 本周亏损 {week_return_rate:.2f}%，需要反思")
    
    # 简单分析
    if avg_return > 0:
        print(f"  • 日均收益为正，策略有效")
    else:
        print(f"  • 日均收益为负，需要优化策略")
    
    if abs(best_day) > 5:
        print(f"  • 波动较大，注意风险控制")
    
    print()
    
    # 7. 保存报告
    report = {
        'week_start': start_date,
        'week_end': end_date,
        'week_start_value': week_start_value,
        'week_end_value': week_end_value,
        'week_return': round(week_return, 2),
        'week_return_rate': round(week_return_rate, 2),
        'trading_days': len(week_snapshots),
        'total_trades': len(week_trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'total_fees': round(total_fees, 2),
        'best_day': round(best_day, 2),
        'worst_day': round(worst_day, 2),
        'avg_return': round(avg_return, 2),
        'positions_count': len(final_snapshot.positions)
    }
    
    report_dir = Path('reports/weekly')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'weekly_report_{end_date}.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_file}")
    print()
    print("=" * 70)
    
    return report


def main():
    print("=" * 70)
    print(" " * 20 + "复盘报告生成器")
    print("=" * 70)
    print()
    
    # 加载虚拟账户
    account = VirtualAccount(
        initial_capital=1000000,
        account_id="virtual_2026"
    )
    
    print("选择报告类型:")
    print("  1. 每日复盘")
    print("  2. 每周复盘")
    print("  3. 两者都生成")
    print()
    
    choice = input("请输入选择 (1/2/3): ").strip()
    
    if choice == '1' or choice == '3':
        print("\n生成每日复盘...")
        generate_daily_report(account)
    
    if choice == '2' or choice == '3':
        print("\n生成每周复盘...")
        generate_weekly_report(account)
    
    print()
    print("✅ 复盘报告生成完成")
    print()


if __name__ == '__main__':
    main()
