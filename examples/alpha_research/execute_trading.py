#!/usr/bin/env python3
"""
交易执行脚本 - AccountService 版

功能：
1. 使用 AccountService 作为账户系统 (SQLite 唯一数据源)
2. FeishuSyncService 事件驱动同步飞书
3. 执行虚拟账户买入/卖出
4. 生成交易执行报告

迁移到 AccountService — 2026-06-23
原 FeishuVirtualAccount 内联类已删除，改用 AccountService + FeishuSyncService。

用法：
    python3 execute_trading.py [--date 2026-03-27] [--dry-run]
"""

import logging
logger = logging.getLogger(__name__)

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 账户系统 — Phase 3
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account
from accounts.feishu_sync import FeishuSyncService

# 配置
REPORTS_DIR = Path(__file__).parent / "reports"
EXECUTION_LOG_DIR = Path(__file__).parent / "logs"


def _ensure_account(account_id: str = "virtual_2026", initial_capital: float = 1_000_000):
    """确保 SQLite 中存在该账户"""
    db = AccountDB()
    if not db.get_account(account_id):
        acct = Account(
            account_id=account_id,
            account_name="王雅轩主账户",
            initial_capital=initial_capital,
            cash=initial_capital,
        )
        db.create_account(acct)


# ─────────────────────────────────────────────
#  交易计划
# ─────────────────────────────────────────────

def load_trading_plan(date=None):
    """加载交易计划"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    plan_file = REPORTS_DIR / f"trading_plan_{date}.json"

    if not plan_file.exists():
        logger.info(f"❌ 交易计划文件不存在：{plan_file}")
        return None

    with open(plan_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_current_price(symbol, date=None):
    """获取当前价格（从选股报告估算）"""
    selection_date = datetime.now().strftime("%Y-%m-%d") if date is None else date
    selection_file = REPORTS_DIR / f"stock_selection_{selection_date}.json"

    if selection_file.exists():
        with open(selection_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for stock in data.get("stocks", []):
                stock_symbol = str(stock.get("symbol", ""))
                target_symbol = str(symbol)

                if (stock_symbol == target_symbol or
                        stock_symbol.replace('.', '') == target_symbol.replace('.', '')):
                    pe = stock.get("pe", 20)
                    estimated_price = pe * 0.8
                    logger.info(f"   参考价格：{estimated_price:.2f} 元 (PE={pe})")
                    return estimated_price

    logger.info(f"   ⚠️ 使用默认价格：10.00 元")
    return 10.0


def calculate_buy_quantity(account: AccountService, symbol: str, price: float, max_position_ratio=0.3):
    """计算买入数量"""
    balance = account.get_balance()
    available_cash = balance.cash
    total_asset = balance.total_assets

    max_amount_by_cash = available_cash * 0.95
    max_amount_by_position = total_asset * max_position_ratio

    buy_amount = min(max_amount_by_cash, max_amount_by_position)

    if buy_amount <= 0:
        return 0

    quantity = int(buy_amount / price / 100) * 100

    if quantity < 100:
        quantity = 100

    return quantity


# ─────────────────────────────────────────────
#  主执行
# ─────────────────────────────────────────────

def execute_trading(date=None, dry_run=False):
    """执行交易"""
    logger.info("=" * 70)
    logger.info(" " * 25 + "交易执行")
    logger.info("=" * 70)
    logger.info(f"日期：{date or datetime.now().strftime('%Y-%m-%d')}")
    logger.info(f"时间：{datetime.now().strftime('%H:%M:%S')}")
    logger.info(f"模式：{'模拟' if dry_run else 'AccountService (SQLite)'}")
    logger.info("=" * 70)

    # 加载交易计划
    plan = load_trading_plan(date)
    if plan is None:
        return {"success": False, "error": "交易计划加载失败"}

    logger.info(f"\n📊 交易计划:")
    logger.info(f"  买入：{len(plan.get('buy', []))} 只")
    logger.info(f"  卖出：{len(plan.get('sell', []))} 只")

    # 初始化 AccountService + FeishuSyncService
    _ensure_account("virtual_2026")
    account = AccountService("virtual_2026")
    sync = FeishuSyncService(account, account.event_bus)

    # 打印摘要
    balance = account.get_balance()
    positions = account.get_positions()
    logger.info(f"\n💼 账户摘要:")
    logger.info(f"   现金: ¥{balance.cash:,.2f}")
    logger.info(f"   持仓: {len(positions)} 只")
    logger.info(f"   总资产: ¥{balance.total_assets:,.2f}")

    executed_trades = []
    failed_trades = []

    # 执行买入
    logger.info("\n" + "=" * 70)
    logger.info(" " * 25 + "执行买入")
    logger.info("=" * 70)

    for stock in plan.get("buy", []):
        symbol = stock.get("symbol")
        name = stock.get("name", "")
        reason = stock.get("reason", "")
        score = stock.get("score", 0)

        logger.info(f"\n【买入】{symbol} {name} (评分：{score}, 理由：{reason})")

        try:
            price = get_current_price(symbol)
            quantity = calculate_buy_quantity(account, symbol, price)

            if quantity <= 0:
                raise ValueError("计算买入数量失败")

            cost = price * quantity
            logger.info(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{cost:,.2f} 元")

            if dry_run:
                logger.info(f"   [模拟] 买入成功")
                trade_record = {
                    "trade_id": f"DRY_{datetime.now().strftime('%Y%m%d')}_{len(executed_trades)+1:03d}",
                    "symbol": symbol,
                    "name": name,
                    "direction": "买",
                    "price": price,
                    "quantity": quantity,
                    "cost": cost,
                    "reason": reason,
                    "status": "dry_run",
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": "Q-Trade"
                }
                executed_trades.append(trade_record)
            else:
                result = account.buy(
                    symbol=symbol,
                    name=name,
                    price=price,
                    quantity=quantity,
                    reason=reason,
                    source_module="execute_trading.py",
                )
                if result.success:
                    trade_record = {
                        "trade_id": result.trade_id,
                        "symbol": symbol,
                        "name": name,
                        "direction": "买",
                        "price": price,
                        "quantity": quantity,
                        "cost": cost,
                        "reason": reason,
                        "status": "filled",
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": "Q-Trade"
                    }
                    executed_trades.append(trade_record)
                else:
                    raise ValueError(result.message)

        except Exception as e:
            logger.error(f"   ❌ 买入失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })

    # 执行卖出
    logger.info("\n" + "=" * 70)
    logger.info(" " * 25 + "执行卖出")
    logger.info("=" * 70)

    for stock in plan.get("sell", []):
        # 兼容字符串和字典两种格式
        if isinstance(stock, str):
            symbol = stock
            name = ""
            reason = ""
        else:
            symbol = stock.get("symbol", "")
            name = stock.get("name", "")
            reason = stock.get("reason", "")

        logger.info(f"\n【卖出】{symbol} {name} (理由：{reason})")

        try:
            price = get_current_price(symbol)
            positions = account.get_positions()
            position = next((p for p in positions if p.symbol == symbol), None)

            if not position:
                raise ValueError("没有持仓")

            quantity = position.quantity
            proceeds = price * quantity

            logger.info(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{proceeds:,.2f} 元")

            if dry_run:
                logger.info(f"   [模拟] 卖出成功")
            else:
                result = account.sell(
                    symbol=symbol,
                    price=price,
                    quantity=quantity,
                    reason=reason,
                    source_module="execute_trading.py",
                )
                if not result.success:
                    raise ValueError(result.message)

        except Exception as e:
            logger.error(f"   ❌ 卖出失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })

    # 打印执行后摘要
    if not dry_run:
        balance = account.get_balance()
        positions = account.get_positions()
        logger.info(f"\n💼 执行后账户摘要:")
        logger.info(f"   现金: ¥{balance.cash:,.2f}")
        logger.info(f"   持仓: {len(positions)} 只")
        logger.info(f"   总资产: ¥{balance.total_assets:,.2f}")

    # 生成执行报告
    balance = account.get_balance()
    report = {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "summary": {
            "total_buy": len(plan.get("buy", [])),
            "total_sell": len(plan.get("sell", [])),
            "executed_buy": len([t for t in executed_trades if t.get("direction") == "买"]),
            "executed_sell": len([t for t in executed_trades if t.get("direction") == "卖"]),
            "failed": len(failed_trades)
        },
        "executed_trades": executed_trades,
        "failed_trades": failed_trades,
        "account_summary": {
            "cash": balance.cash,
            "position_value": balance.market_value,
            "total_asset": balance.total_assets,
            "position_ratio": balance.market_value / balance.total_assets * 100 if balance.total_assets > 0 else 0
        } if not dry_run else None
    }

    # 保存执行报告
    EXECUTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_file = EXECUTION_LOG_DIR / f"execution_{date or datetime.now().strftime('%Y-%m-%d')}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 执行报告已保存：{report_file}")

    # 打印总结
    logger.info("\n" + "=" * 70)
    logger.info(" " * 25 + "执行总结")
    logger.info("=" * 70)
    logger.info(f"计划买入：{report['summary']['total_buy']} 只")
    logger.info(f"实际买入：{report['summary']['executed_buy']} 只")
    logger.error(f"失败：{report['summary']['failed']} 只")

    if executed_trades:
        logger.info("\n执行成功的交易:")
        for trade in executed_trades:
            direction = "买入" if trade.get("direction") == "买" else "卖出"
            logger.info(f"  ✅ {trade.get('symbol')} {direction} {trade.get('quantity')} 股 @ {trade.get('price'):.2f} 元")

    logger.info("=" * 70)

    return report


def main():
    parser = argparse.ArgumentParser(description='交易执行脚本（AccountService 版）')
    parser.add_argument('--date', type=str, help='交易日期 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行')

    args = parser.parse_args()

    report = execute_trading(date=args.date, dry_run=args.dry_run)
    sys.exit(0 if report.get("summary", {}).get("failed", 0) == 0 else 1)


if __name__ == "__main__":
    main()
