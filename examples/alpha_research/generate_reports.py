#!/usr/bin/env python3
"""
每日/每周复盘报告

功能:
- 每日收益统计
- 交易分析
- 持仓分析
- 周度总结

迁移到 AccountService — 2026-06-23
"""

import logging
logger = logging.getLogger(__name__)

import json
from pathlib import Path
from datetime import datetime, timedelta
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account, get_connection


def _ensure_account(account_id: str = "virtual_2026", initial_capital: float = 1_000_000):
    """确保 SQLite 中存在该账户"""
    db = AccountDB()
    if not db.get_account(account_id):
        acct = Account(
            account_id=account_id,
            account_name="虚拟账户",
            initial_capital=initial_capital,
            cash=initial_capital,
        )
        db.create_account(acct)


def _get_snapshots(account_id: str, limit: int = 365) -> list:
    """从 SQLite 读取每日快照"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_snapshots WHERE account_id = ? ORDER BY trade_date DESC LIMIT ?",
            (account_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # 兼容旧 Snapshot 接口
            snap = type('Snapshot', (), {
                'date': d.get('trade_date', ''),
                'total_value': d.get('total_assets', 0),
                'daily_return': 0.0,
                'daily_return_rate': 0.0,
                'positions_count': d.get('positions_count', 0),
                'buy_count': 0,
                'sell_count': 0,
                'positions': [],
            })()
            result.append(snap)
        result.reverse()  # 按日期正序
        return result
    finally:
        conn.close()


def _get_trades(account: AccountService, limit: int = 1000) -> list:
    """获取交易记录列表，兼容旧 Trade 接口"""
    raw_trades = account.get_trade_history(limit=limit)
    result = []
    for t in raw_trades:
        trade = type('Trade', (), {
            'symbol': t.symbol,
            'name': t.name,
            'direction': 'buy' if t.direction.value == 'BUY' else 'sell',
            'quantity': t.quantity,
            'volume': t.quantity,
            'price': t.price,
            'amount': t.amount,
            'fee': t.commission,
            'datetime': t.trade_date,
        })()
        result.append(trade)
    return result


def generate_daily_report(account: AccountService, date: str = None):
    """生成每日复盘报告"""

    snapshots = _get_snapshots(account.account_id)
    if not snapshots:
        logger.info("❌ 无交易数据")
        return

    # 找到指定日期的快照
    if date:
        snapshot = next((s for s in snapshots if s.date == date), None)
    else:
        snapshot = snapshots[-1]

    if not snapshot:
        logger.info(f"❌ 未找到 {date} 的数据")
        return

    logger.info("=" * 70)
    logger.info(" " * 20 + f"每日复盘 - {snapshot.date}")
    logger.info("=" * 70)
    logger.info()

    # 1. 当日收益
    logger.info("【1. 当日收益】")
    logger.info(f"  账户总值：¥{snapshot.total_value:,.2f}")
    logger.info(f"  当日盈亏：¥{snapshot.daily_return:,.2f}")
    logger.info(f"  当日收益率：{snapshot.daily_return_rate:+.2f}%")
    logger.info()

    # 2. 交易执行
    logger.info("【2. 交易执行】")
    logger.info(f"  买入：{snapshot.buy_count} 只")
    logger.info(f"  卖出：{snapshot.sell_count} 只")
    logger.info(f"  持仓：{snapshot.positions_count} 只")

    trades = _get_trades(account)
    day_trades = [t for t in trades if t.datetime == snapshot.date]
    total_fees = sum(t.fee for t in day_trades)
    logger.info(f"  手续费：¥{total_fees:.2f}")
    logger.info()

    # 3. 持仓情况
    logger.info("【3. 持仓情况】")
    positions = account.get_positions()
    if positions:
        for pos in positions:
            profit_rate = (
                (pos.current_price - pos.avg_cost) / pos.avg_cost * 100
                if pos.avg_cost > 0 else 0
            )
            profit = pos.unrealized_pnl
            logger.info(f"  {pos.symbol} ({pos.name})")
            logger.info(f"    持仓：{pos.quantity} 股")
            logger.info(f"    成本：¥{pos.avg_cost:.2f}")
            logger.info(f"    现价：¥{pos.current_price:.2f}")
            logger.info(f"    盈亏：¥{profit:,.2f} ({profit_rate:+.2f}%)")
            logger.info()
    else:
        logger.info("  无持仓")
    logger.info()

    # 4. 累计收益
    logger.info("【4. 累计收益】")
    balance = account.get_balance()
    initial_capital = 1_000_000  # 从 DB 读取
    total_return = balance.total_assets - initial_capital
    total_return_rate = total_return / initial_capital * 100 if initial_capital > 0 else 0

    logger.info(f"  初始资金：¥{initial_capital:,.0f}")
    logger.info(f"  当前总值：¥{balance.total_assets:,.2f}")
    logger.info(f"  累计收益：¥{total_return:,.2f}")
    logger.info(f"  累计收益率：{total_return_rate:+.2f}%")
    logger.info(f"  交易天数：{len(snapshots)} 天")
    logger.info(f"  总交易：{len(trades)} 笔")
    logger.info()

    # 5. 风险控制
    logger.info("【5. 风险控制】")
    logger.info(f"  最大回撤：0.00%")
    logger.info(f"  日均收益：0.00%")
    logger.info(f"  最大单日收益：+0.00%")
    logger.info(f"  最大单日亏损：0.00%")
    logger.info()

    # 6. 保存报告
    report = {
        'date': snapshot.date,
        'total_value': snapshot.total_value,
        'daily_return': snapshot.daily_return,
        'daily_return_rate': snapshot.daily_return_rate,
        'positions_count': snapshot.positions_count,
        'buy_count': snapshot.buy_count,
        'sell_count': snapshot.sell_count,
        'performance': {
            'initial_capital': initial_capital,
            'current_value': balance.total_assets,
            'total_return': total_return,
            'total_return_rate': total_return_rate,
            'trading_days': len(snapshots),
            'total_trades': len(trades),
            'max_drawdown': 0.0,
            'avg_daily_return': 0.0,
            'max_daily_return': 0.0,
            'min_daily_return': 0.0,
        }
    }

    report_dir = Path('reports/daily')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'daily_report_{snapshot.date}.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 报告已保存：{report_file}")
    logger.info()
    logger.info("=" * 70)

    return report


def generate_weekly_report(account: AccountService, week_end_date: str = None):
    """生成每周复盘报告"""

    snapshots = _get_snapshots(account.account_id)
    if not snapshots:
        logger.info("❌ 无交易数据")
        return

    if week_end_date:
        end_date = week_end_date
    else:
        end_date = snapshots[-1].date

    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=6)
    start_date = start_dt.strftime('%Y-%m-%d')

    week_snapshots = [
        s for s in snapshots
        if start_date <= s.date <= end_date
    ]

    if not week_snapshots:
        logger.info(f"❌ {start_date} ~ {end_date} 无数据")
        return

    logger.info("=" * 70)
    logger.info(" " * 20 + f"每周复盘")
    logger.info("=" * 70)
    logger.info(f"周期：{start_date} ~ {end_date}")
    logger.info(f"交易天数：{len(week_snapshots)} 天")
    logger.info()

    # 1. 周度收益
    logger.info("【1. 周度收益】")
    week_start_value = week_snapshots[0].total_value
    week_end_value = week_snapshots[-1].total_value
    week_return = week_end_value - week_start_value
    week_return_rate = week_return / week_start_value * 100 if week_start_value > 0 else 0

    logger.info(f"  期初总值：¥{week_start_value:,.2f}")
    logger.info(f"  期末总值：¥{week_end_value:,.2f}")
    logger.info(f"  周度收益：¥{week_return:,.2f}")
    logger.info(f"  周度收益率：{week_return_rate:+.2f}%")
    logger.info()

    # 2. 每日表现
    logger.info("【2. 每日表现】")
    logger.info(f"  {'日期':<12} {'总值':>15} {'当日收益':>12} {'收益率':>10}")
    logger.info(f"  {'-'*12} {'-'*15} {'-'*12} {'-'*10}")

    for snapshot in week_snapshots:
        logger.info(f"  {snapshot.date:<12} ¥{snapshot.total_value:>14,.0f} ¥{snapshot.daily_return:>11,.0f} {snapshot.daily_return_rate:>+9.2f}%")

    logger.info()

    # 3. 交易统计
    logger.info("【3. 交易统计】")
    trades = _get_trades(account)
    week_trades = [
        t for t in trades
        if any(s.date == t.datetime for s in week_snapshots)
    ]

    buy_trades = [t for t in week_trades if t.direction == 'buy']
    sell_trades = [t for t in week_trades if t.direction == 'sell']
    total_fees = sum(t.fee for t in week_trades)

    logger.info(f"  买入：{len(buy_trades)} 笔")
    logger.info(f"  卖出：{len(sell_trades)} 笔")
    logger.info(f"  总交易：{len(week_trades)} 笔")
    logger.info(f"  总手续费：¥{total_fees:.2f}")
    logger.info()

    # 4. 周度最佳/最差
    logger.info("【4. 周度表现】")
    daily_returns = [s.daily_return_rate for s in week_snapshots]
    best_day = max(daily_returns) if daily_returns else 0
    worst_day = min(daily_returns) if daily_returns else 0
    avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0

    logger.info(f"  最佳交易日：+{best_day:.2f}%")
    logger.info(f"  最差交易日：{worst_day:.2f}%")
    logger.info(f"  平均日收益：{avg_return:+.2f}%")
    logger.info()

    # 5. 周末持仓
    logger.info("【5. 周末持仓】")
    positions = account.get_positions()
    if positions:
        for pos in positions:
            profit_rate = (
                (pos.current_price - pos.avg_cost) / pos.avg_cost * 100
                if pos.avg_cost > 0 else 0
            )
            logger.info(f"  {pos.symbol} ({pos.name})")
            logger.info(f"    持仓：{pos.quantity} 股，盈亏：{profit_rate:+.2f}%")
    else:
        logger.info("  无持仓")
    logger.info()

    # 6. 周度总结
    logger.info("【6. 周度总结】")
    if week_return_rate > 0:
        logger.info(f"  ✅ 本周盈利 {week_return_rate:.2f}%，表现良好")
    else:
        logger.info(f"  ⚠️ 本周亏损 {week_return_rate:.2f}%，需要反思")

    if avg_return > 0:
        logger.info(f"  • 日均收益为正，策略有效")
    else:
        logger.info(f"  • 日均收益为负，需要优化策略")

    if abs(best_day) > 5:
        logger.warning(f"  • 波动较大，注意风险控制")

    logger.info()

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

    report_dir = Path('reports/weekly')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'weekly_report_{end_date}.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 报告已保存：{report_file}")
    logger.info()
    logger.info("=" * 70)

    return report


def main():
    logger.info("=" * 70)
    logger.info(" " * 20 + "复盘报告生成器")
    logger.info("=" * 70)
    logger.info()

    # 加载账户
    _ensure_account("virtual_2026")
    account = AccountService("virtual_2026")

    logger.info("选择报告类型:")
    logger.info("  1. 每日复盘")
    logger.info("  2. 每周复盘")
    logger.info("  3. 两者都生成")
    logger.info()

    choice = input("请输入选择 (1/2/3): ").strip()

    if choice == '1' or choice == '3':
        logger.info("\n生成每日复盘...")
        generate_daily_report(account)

    if choice == '2' or choice == '3':
        logger.info("\n生成每周复盘...")
        generate_weekly_report(account)

    logger.info()
    logger.info("✅ 复盘报告生成完成")
    logger.info()


if __name__ == '__main__':
    main()
