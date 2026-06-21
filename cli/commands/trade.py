"""vnpy trade - 交易执行命令组"""
from __future__ import annotations

import click

from ..utils.logging import get_logger


logger = get_logger(__name__)


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
@click.option('--reason', type=str, help='操作原因')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际执行')
def trade_execute(action, reason, dry_run):
    """紧急交易执行"""
    from ..utils.wrapper import run_legacy

    args = ['--action', action]
    if reason:
        args.extend(['--reason', reason])

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: execute_rebalance_today.py {' '.join(args)}")
        return

    run_legacy('execute_rebalance_today.py', args=args)
    click.echo(f"✅ 交易执行完成: {action}")
