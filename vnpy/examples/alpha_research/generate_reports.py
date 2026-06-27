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

from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account


def _get_snapshots(account_id: str):
    """从数据库获取每日快照列表"""
    db = AccountDB()
    conn = db._conn
    try:
        rows = conn.execute(
            "SELECT * FROM daily_snapshots WHERE account_id = ? ORDER BY trade_date DESC",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        pass


def generate_daily_report(account: AccountService, date: str = None):
    """生成每日复盘报告"""
    
    snapshots = _get_snapshots(account.account_id)
    if not snapshots:
        print("❌ 无交易数据")
        return
    
    # 找到指定日期的快照
    if date:
        snapshot = next((s for s in snapshots if s['trade_date'] == date or s['trade_date'] == date.replace('-', '')), None)
    else:
        snapshot = snapshots[0]  # 最新的快照
    
    if not snapshot:
        print(f"❌ 未找到 {date} 的数据")
        return
    
    print("=" * 70)
    print(" " * 20 + f"每日复盘 - {snapshot['trade_date']}")
    print("=" * 70)
    print()
    
    # 1. 当日收益
    print("【1. 当日收益】")
    print(f"  账户总值：¥{snapshot['total_assets']:,.2f}")
    
    # 计算当日收益
    daily_return = 0
    daily_return_rate = 0
    if len(snapshots) > 1:
        prev_snapshot = snapshots[1]
        daily_return = snapshot['total_assets'] - prev_snapshot['total_assets']
        daily_return_rate = daily_return / prev_snapshot['total_assets'] * 100 if prev_snapshot['total_assets'] > 0 else 0
    
    print(f"  当日盈亏：¥{daily_return:,.2f}")
    print(f"  当日收益率：{daily_return_rate:+.2f}%")
    print()
    
    # 2. 交易执行
    print("【2. 交易执行】")
    print(f"  持仓：{snapshot['positions_count']} 只")
    
    # 计算当日交易费用
    trade_date = snapshot['trade_date']
    all_trades = account.get_trade_history()
    day_trades = [t for t in all_trades if t.trade_date == trade_date]
    total_fees = sum(t.commission for t in day_trades)
    buy_count = sum(1 for t in day_trades if t.direction.value == 'buy')
    sell_count = sum(1 for t in day_trades if t.direction.value == 'sell')
    print(f"  买入：{buy_count} 只")
    print(f"  卖出：{sell_count} 只")
    print(f"  手续费：¥{total_fees:.2f}")
    print()
    
    # 3. 持仓情况
    print("【3. 持仓情况】")
    positions = account.get_positions()
    if positions:
        for pos in positions:
            profit_rate = (pos.current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            profit = (pos.current_price - pos.avg_cost) * pos.quantity
            print(f"  {pos.symbol} ({pos.name})")
            print(f"    持仓：{pos.quantity} 股")
            print(f"    成本：¥{pos.avg_cost:.2f}")
            print(f"    现价：¥{pos.current_price:.2f}")
            print(f"    盈亏：¥{profit:,.2f} ({profit_rate:+.2f}%)")
            print()
    else:
        print("  无持仓")
    print()
    
    # 4. 累计收益
    print("【4. 累计收益】")
    balance = account.get_balance()
    db = AccountDB()
    acct = db.get_account(account.account_id)
    initial_capital = acct.initial_capital if acct else 1000000
    total_return = balance.total_assets - initial_capital
    total_return_rate = total_return / initial_capital * 100 if initial_capital > 0 else 0
    trading_days = len(snapshots)
    total_trades = len(all_trades)
    
    print(f"  初始资金：¥{initial_capital:,.0f}")
    print(f"  当前总值：¥{balance.total_assets:,.2f}")
    print(f"  累计收益：¥{total_return:,.2f}")
    print(f"  累计收益率：{total_return_rate:+.2f}%")
    print(f"  交易天数：{trading_days} 天")
    print(f"  总交易：{total_trades} 笔")
    print()
    
    # 5. 风险控制
    print("【5. 风险控制】")
    # 计算最大回撤和日均收益
    max_drawdown = 0.0
    daily_returns = []
    peak = 0
    for snap in snapshots:
        total_assets = snap['total_assets']
        if total_assets > peak:
            peak = total_assets
        drawdown = (peak - total_assets) / peak * 100 if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        if len(snapshots) > 1:
            idx = snapshots.index(snap)
            if idx < len(snapshots) - 1:
                prev_assets = snapshots[idx + 1]['total_assets']
                if prev_assets > 0:
                    daily_ret = (total_assets - prev_assets) / prev_assets * 100
                    daily_returns.append(daily_ret)
    
    avg_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
    max_daily_return = max(daily_returns) if daily_returns else 0
    min_daily_return = min(daily_returns) if daily_returns else 0
    
    print(f"  最大回撤：{max_drawdown:.2f}%")
    print(f"  日均收益：{avg_daily_return:+.2f}%")
    print(f"  最大单日收益：+{max_daily_return:.2f}%")
    print(f"  最大单日亏损：{min_daily_return:.2f}%")
    print()
    
    # 6. 保存报告
    report = {
        'date': snapshot['trade_date'],
        'total_value': snapshot['total_assets'],
        'daily_return': daily_return,
        'daily_return_rate': daily_return_rate,
        'positions_count': snapshot['positions_count'],
        'buy_count': buy_count,
        'sell_count': sell_count,
    }
    
    report_dir = Path('vnpy/examples/alpha_research/reports/daily')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"daily_report_{snapshot['trade_date']}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_file}")
    print()
    print("=" * 70)
    
    return report


def generate_weekly_report(account: AccountService, week_end_date: str = None):
    """生成每周复盘报告"""
    
    snapshots = _get_snapshots(account.account_id)
    if not snapshots:
        print("❌ 无交易数据")
        return
    
    # 确定周结束日期
    if week_end_date:
        end_date = week_end_date
    else:
        end_date = snapshots[0]['trade_date']
    
    # 处理 YYYYMMDD 格式
    if len(end_date) == 8:
        end_dt = datetime.strptime(end_date, '%Y%m%d')
    else:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=6)
    start_date = start_dt.strftime('%Y-%m-%d')
    
    # 筛选本周数据
    week_snapshots = [
        s for s in snapshots
        if start_date <= s['trade_date'] <= end_date or 
           start_date.replace('-', '') <= s['trade_date'] <= end_date.replace('-', '')
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
    week_start_value = week_snapshots[-1]['total_assets']
    week_end_value = week_snapshots[0]['total_assets']
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
        total_val = snapshot['total_assets']
        # 找到前一天的快照计算当日收益
        idx = week_snapshots.index(snapshot)
        if idx < len(week_snapshots) - 1:
            prev_val = week_snapshots[idx + 1]['total_assets']
            day_return = total_val - prev_val
            day_return_rate = day_return / prev_val * 100 if prev_val > 0 else 0
        else:
            day_return = 0
            day_return_rate = 0
        print(f"  {snapshot['trade_date']:<12} ¥{total_val:>14,.0f} ¥{day_return:>11,.0f} {day_return_rate:>+9.2f}%")
    
    print()
    
    # 3. 交易统计
    print("【3. 交易统计】")
    all_trades = account.get_trade_history()
    week_trades = [
        t for t in all_trades
        if any(s['trade_date'] == t.trade_date for s in week_snapshots)
    ]
    
    buy_trades = [t for t in week_trades if t.direction.value == 'buy']
    sell_trades = [t for t in week_trades if t.direction.value == 'sell']
    total_fees = sum(t.commission for t in week_trades)
    
    print(f"  买入：{len(buy_trades)} 笔")
    print(f"  卖出：{len(sell_trades)} 笔")
    print(f"  总交易：{len(week_trades)} 笔")
    print(f"  总手续费：¥{total_fees:.2f}")
    print()
    
    # 4. 周度最佳/最差
    print("【4. 周度表现】")
    daily_returns = []
    for i, snap in enumerate(week_snapshots):
        if i < len(week_snapshots) - 1:
            prev = week_snapshots[i + 1]['total_assets']
            curr = snap['total_assets']
            if prev > 0:
                daily_returns.append((curr - prev) / prev * 100)
    
    best_day = max(daily_returns) if daily_returns else 0
    worst_day = min(daily_returns) if daily_returns else 0
    avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
    
    print(f"  最佳交易日：+{best_day:.2f}%")
    print(f"  最差交易日：{worst_day:.2f}%")
    print(f"  平均日收益：{avg_return:+.2f}%")
    print()
    
    # 5. 周末持仓
    print("【5. 周末持仓】")
    positions = account.get_positions()
    if positions:
        for pos in positions:
            profit_rate = (pos.current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            print(f"  {pos.symbol} ({pos.name})")
            print(f"    持仓：{pos.quantity} 股，盈亏：{profit_rate:+.2f}%")
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
        'positions_count': len(positions)
    }
    
    report_dir = Path('vnpy/examples/alpha_research/reports/weekly')
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
    
    # 初始化账户
    db = AccountDB()
    if not db.get_account("virtual_2026"):
        db.create_account(Account(
            account_id="virtual_2026",
            account_name="虚拟账户",
            account_type="virtual",
            initial_capital=1000000,
            cash=1000000,
            currency="CNY",
            status="active",
            risk_level="moderate",
        ))
    
    account = AccountService("virtual_2026")
    
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
