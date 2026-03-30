#!/usr/bin/env python3
"""
交易执行脚本 - 更新版

功能：
1. 读取交易计划
2. 执行虚拟账户买入/卖出
3. 同步交易记录、账户资金、持仓到飞书多维表格
4. 生成交易执行报告

用法：
    python3 execute_trading.py [--date 2026-03-27] [--dry-run]
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')

from virtual_account import VirtualAccount
from openclaw_lark import feishu_bitable_app_table_record

# 配置
REPORTS_DIR = Path(__file__).parent / "reports"
EXECUTION_LOG_DIR = Path(__file__).parent / "logs"
FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
FEISHU_TRADE_TABLE = "tbl4n14ZYANQtI26"  # 交易日志表
FEISHU_ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
FEISHU_POSITION_TABLE = "tblLHrg7fFOcN0to"  # 持仓记录表


def load_trading_plan(date=None):
    """加载交易计划"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    plan_file = REPORTS_DIR / f"trading_plan_{date}.json"
    
    if not plan_file.exists():
        print(f"❌ 交易计划文件不存在：{plan_file}")
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
                    print(f"   参考价格：{estimated_price:.2f} 元 (PE={pe})")
                    return estimated_price
    
    print(f"   ⚠️ 使用默认价格：10.00 元")
    return 10.0


def calculate_buy_quantity(symbol, price, max_position_ratio=0.3):
    """计算买入数量"""
    account = VirtualAccount()
    available_cash = account.get_available_cash()
    total_asset = account.get_total_asset()
    
    max_amount_by_cash = available_cash * 0.95
    max_amount_by_position = total_asset * max_position_ratio
    
    buy_amount = min(max_amount_by_cash, max_amount_by_position)
    
    if buy_amount <= 0:
        return 0
    
    quantity = int(buy_amount / price / 100) * 100
    
    if quantity < 100:
        quantity = 100
    
    return quantity


def sync_to_feishu(trade_records, account):
    """
    同步交易记录、账户、持仓到飞书
    
    Args:
        trade_records: 交易记录列表
        account: VirtualAccount 实例
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # 1. 同步交易记录
    print("\n📱 同步交易记录到飞书...")
    for trade in trade_records:
        try:
            fields = {
                "多行文本": f"{trade.get('symbol')} - {trade.get('direction')}",
                "股票代码": trade.get("symbol"),
                "股票名称": trade.get("name", ""),
                "Trade ID": trade.get("trade_id"),
                "方向": trade.get("direction"),
                "价格": trade.get("price", 0),
                "数量": trade.get("quantity", 0),
                "状态": "filled",
                "Agent ID": trade.get("agent_id", "Q-Trade"),
                "备注": trade.get("reason", "")
            }
            
            if trade.get("direction") == "买":
                fields["建仓时间"] = timestamp
            
            feishu_bitable_app_table_record(
                action='create',
                app_token=FEISHU_APP_TOKEN,
                table_id=FEISHU_TRADE_TABLE,
                fields=fields
            )
            print(f"   ✅ {trade.get('trade_id')}")
        except Exception as e:
            print(f"   ⚠️ {trade.get('trade_id')} 失败：{e}")
    
    # 2. 同步账户资金
    print("\n📱 同步账户资金到飞书...")
    try:
        feishu_bitable_app_table_record(
            action='update',
            app_token=FEISHU_APP_TOKEN,
            table_id=FEISHU_ACCOUNT_TABLE,
            record_id='recveSFVVfD6EJ',
            fields={
                "当前资金": account.get_available_cash(),
                "更新时间": timestamp
            }
        )
        print(f"   ✅ 当前资金：{account.get_available_cash():,.2f} 元")
    except Exception as e:
        print(f"   ⚠️ 账户同步失败：{e}")
    
    # 3. 同步持仓
    print("\n📱 同步持仓到飞书...")
    positions = account.get_positions()
    for pos in positions:
        try:
            fields = {
                "股票代码": pos["symbol"],
                "股票名称": pos["name"],
                "持仓数量": pos["quantity"],
                "持仓成本": pos["cost"],
                "平均成本": pos["avg_price"],
                "建仓日期": timestamp,
                "当前价": pos["avg_price"],
                "持仓市值": pos["cost"],
                "浮盈": 0,
                "收益率": 0,
                "状态": "持仓中",
                "更新时间": timestamp,
                "Agent ID": "Q-Trade"
            }
            
            feishu_bitable_app_table_record(
                action='create',
                app_token=FEISHU_APP_TOKEN,
                table_id=FEISHU_POSITION_TABLE,
                fields=fields
            )
            print(f"   ✅ {pos['symbol']} {pos['quantity']} 股")
        except Exception as e:
            print(f"   ⚠️ {pos['symbol']} 失败：{e}")


def execute_trading(date=None, dry_run=False):
    """执行交易"""
    print("=" * 70)
    print(" " * 25 + "交易执行")
    print("=" * 70)
    print(f"日期：{date or datetime.now().strftime('%Y-%m-%d')}")
    print(f"时间：{datetime.now().strftime('%H:%M:%S')}")
    print(f"模式：{'模拟' if dry_run else '实盘'}")
    print("=" * 70)
    
    # 加载交易计划
    plan = load_trading_plan(date)
    if plan is None:
        return {"success": False, "error": "交易计划加载失败"}
    
    print(f"\n📊 交易计划:")
    print(f"  买入：{len(plan.get('buy', []))} 只")
    print(f"  卖出：{len(plan.get('sell', []))} 只")
    
    # 初始化虚拟账户
    account = VirtualAccount()
    account.print_summary()
    
    executed_trades = []
    failed_trades = []
    
    # 执行买入
    print("\n" + "=" * 70)
    print(" " * 25 + "执行买入")
    print("=" * 70)
    
    for stock in plan.get("buy", []):
        symbol = stock.get("symbol")
        name = stock.get("name", "")
        reason = stock.get("reason", "")
        score = stock.get("score", 0)
        
        print(f"\n【买入】{symbol} {name} (评分：{score}, 理由：{reason})")
        
        try:
            price = get_current_price(symbol)
            quantity = calculate_buy_quantity(symbol, price)
            
            if quantity <= 0:
                raise ValueError("计算买入数量失败")
            
            cost = price * quantity
            print(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{cost:,.2f} 元")
            
            if dry_run:
                print(f"   [模拟] 买入成功")
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
                trade_record = account.buy(
                    symbol=symbol,
                    name=name,
                    price=price,
                    quantity=quantity,
                    reason=reason
                )
                executed_trades.append(trade_record)
        
        except Exception as e:
            print(f"   ❌ 买入失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })
    
    # 执行卖出
    print("\n" + "=" * 70)
    print(" " * 25 + "执行卖出")
    print("=" * 70)
    
    for stock in plan.get("sell", []):
        symbol = stock.get("symbol")
        name = stock.get("name", "")
        reason = stock.get("reason", "")
        
        print(f"\n【卖出】{symbol} {name} (理由：{reason})")
        
        try:
            price = get_current_price(symbol)
            positions = account.get_positions()
            position = next((p for p in positions if p["symbol"] == symbol), None)
            
            if not position:
                raise ValueError("没有持仓")
            
            quantity = position["quantity"]
            proceeds = price * quantity
            
            print(f"   价格：{price:.2f} 元，数量：{quantity} 股，金额：{proceeds:,.2f} 元")
            
            if dry_run:
                print(f"   [模拟] 卖出成功")
            else:
                account.sell(symbol=symbol, price=price, quantity=quantity, reason=reason)
        
        except Exception as e:
            print(f"   ❌ 卖出失败：{e}")
            failed_trades.append({
                "symbol": symbol,
                "name": name,
                "reason": str(e)
            })
    
    # 打印执行后摘要
    if not dry_run:
        account.print_summary()
    
    # 同步到飞书
    if not dry_run and executed_trades:
        sync_to_feishu(executed_trades, account)
    
    # 生成执行报告
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
            "cash": account.get_available_cash(),
            "position_value": account.get_position_value(),
            "total_asset": account.get_total_asset(),
            "position_ratio": account.get_position_ratio()
        } if not dry_run else None
    }
    
    # 保存执行报告
    EXECUTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_file = EXECUTION_LOG_DIR / f"execution_{date or datetime.now().strftime('%Y-%m-%d')}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 执行报告已保存：{report_file}")
    
    # 打印总结
    print("\n" + "=" * 70)
    print(" " * 25 + "执行总结")
    print("=" * 70)
    print(f"计划买入：{report['summary']['total_buy']} 只")
    print(f"实际买入：{report['summary']['executed_buy']} 只")
    print(f"失败：{report['summary']['failed']} 只")
    
    if executed_trades:
        print("\n执行成功的交易:")
        for trade in executed_trades:
            direction = "买入" if trade.get("direction") == "买" else "卖出"
            print(f"  ✅ {trade.get('symbol')} {direction} {trade.get('quantity')} 股 @ {trade.get('price'):.2f} 元")
    
    print("=" * 70)
    
    return report


def main():
    parser = argparse.ArgumentParser(description='交易执行脚本')
    parser.add_argument('--date', type=str, help='交易日期 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行')
    
    args = parser.parse_args()
    
    report = execute_trading(date=args.date, dry_run=args.dry_run)
    sys.exit(0 if report.get("summary", {}).get("failed", 0) == 0 else 1)


if __name__ == "__main__":
    main()
