"""vnpy trade - 交易执行命令组"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
import click

from ..utils.logging import get_logger


logger = get_logger(__name__)


def log_audit_entry(account_id: str, operation: str, symbol: str = None,
                   quantity: int = None, price: float = None, amount: float = None,
                   cash_before: float = None, cash_after: float = None,
                   agent_id: str = "cli", source_module: str = "cli.trade.execute",
                   details: dict = None):
    """
    记录审计日志到数据库

    Args:
        account_id: 账户ID
        operation: 操作类型
        symbol: 证券代码
        quantity: 数量
        price: 价格
        amount: 金额
        cash_before: 操作前资金
        cash_after: 操作后资金
        agent_id: 操作者ID
        source_module: 操作来源模块
        details: 其他详细信息
    """
    import sqlite3

    # 创建一个虚拟账户用于审计日志记录（在真实账户系统完善之前）
    # 在真实的实现中，应该从环境变量或其他地方获取账户ID
    if details is None:
        details = {}

    # 为审计日志生成唯一的审计ID
    audit_id = f"AUDIT-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"

    # 记录审计日志到文件（临时实现，直到账户系统完全建立）
    audit_log_entry = {
        "audit_id": audit_id,
        "account_id": account_id,
        "operation": operation,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "amount": amount,
        "cash_before": cash_before,
        "cash_after": cash_after,
        "agent_id": agent_id,
        "source_module": source_module,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }

    # 保存到审计日志文件
    import os
    from pathlib import Path

    log_dir = Path(os.getcwd()) / "logs"
    log_dir.mkdir(exist_ok=True)
    audit_log_path = log_dir / "audit.log"

    with open(audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_log_entry, ensure_ascii=False) + "\n")

    logger.info(f"审计日志已记录: {audit_id} - {operation} - {details.get('reason', 'N/A')}")


@click.group(name='trade', short_help='交易执行')
def trade():
    """交易执行子命令: 模拟交易 / 调仓 / 止盈止损"""
    pass


@trade.command(name='paper')
@click.option('--stocks', type=str, help='股票代码列表 (逗号分隔)')
@click.option('--capital', type=float, default=1000000, help='初始资金')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际执行')
def trade_paper(stocks, capital, dry_run):
    """模拟交易"""
    from ..utils.wrapper import run_legacy

    args = ['--capital', str(capital)]
    if stocks:
        args.extend(['--stocks', stocks])

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: paper_trading.py {' '.join(args)}")
        return

    run_legacy('paper_trading.py', args=args)
    click.echo("✅ 模拟交易完成")


@trade.command(name='rebalance')
@click.option('--target', type=int, default=5, help='目标持仓数')
@click.option('--execute', is_flag=True, help='实际执行 (默认只预览)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际执行')
def trade_rebalance(target, execute, dry_run):
    """每日调仓"""
    from ..utils.wrapper import run_legacy

    args = ['--target', str(target)]
    if execute:
        args.append('--execute')

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: rebalance_portfolio.py {' '.join(args)}")
        return

    run_legacy('rebalance_portfolio.py', args=args)
    click.echo("✅ 调仓完成")


@trade.command(name='stop-loss')
@click.option('--threshold', type=float, default=0.05, help='止盈止损阈值')
@click.option('--execute', is_flag=True, help='实际执行 (默认只预览)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际执行')
def trade_stop_loss(threshold, execute, dry_run):
    """止盈止损"""
    from ..utils.wrapper import run_legacy

    args = ['--threshold', str(threshold)]
    if execute:
        args.append('--execute')

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: strict_stop_loss.py {' '.join(args)}")
        return

    run_legacy('strict_stop_loss.py', args=args)
    click.echo("✅ 止盈止损执行完成")


@trade.command(name='execute')
@click.option('--action', type=click.Choice(['close-all', 'close-position']),
              required=True, help='操作类型')
@click.option('--reason', type=str, required=True, help='操作原因 (必填)')
@click.option('--confirm', is_flag=True, help='显式确认执行操作 (必填)')
@click.option('--account-id', type=str, default='default_account', help='账户ID (用于审计)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际执行')
def trade_execute(action, reason, confirm, account_id, dry_run):
    """紧急交易执行 - 需要二次确认和审计日志记录"""
    from ..utils.wrapper import run_legacy

    # 必须提供--confirm标志才能执行
    if not confirm:
        click.echo("❌ 错误: 必须使用 --confirm 标志确认操作")
        click.echo("💡 提示: 使用 --confirm 标志显式确认此操作")
        return

    # 特别对close-all操作增加确认提示（在dry-run模式下显示警告，在非dry-run模式下进行实际确认）
    if action == 'close-all':
        if dry_run:
            click.echo("🚨 特别警告: close-all 是清仓操作，将关闭所有持仓")
        else:
            click.confirm("🚨 特别警告: close-all 是清仓操作，将关闭所有持仓，确定继续吗？", abort=True)
            # 双重确认，增加输入字符串确认
            confirm_text = click.prompt("请再次输入 'CONFIRM_CLOSE_ALL' 以确认清仓操作", type=str)
            if confirm_text != 'CONFIRM_CLOSE_ALL':
                click.echo("❌ 清仓操作已取消 - 输入未匹配确认字符串")
                return

    # 记录审计日志
    audit_details = {
        "reason": reason,
        "dry_run": dry_run,
        "user_confirmed": confirm,
        "command_line": " ".join(["trade", "execute", "--action", action, "--reason", reason]),
        "execution_environment": "dry_run" if dry_run else "live"
    }

    log_audit_entry(
        account_id=account_id,
        operation=action.upper(),
        agent_id="cli_user",
        source_module="cli.trade.execute",
        details=audit_details
    )

    args = ['--action', action, '--reason', reason]

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: execute_rebalance_today.py {' '.join(args)}")
        click.echo(f"📊 审计日志已记录: 操作={action}, 账户={account_id}, 原因='{reason}'")
        return

    run_legacy('execute_rebalance_today.py', args=args)
    click.echo(f"✅ 交易执行完成: {action}")
