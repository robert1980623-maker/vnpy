"""vnpy report - 报告生成命令组"""
from __future__ import annotations

from datetime import datetime

import click

from ..utils.logging import get_logger


logger = get_logger(__name__)


@click.group(name='report', short_help='报告生成')
def report():
    """报告生成子命令: 日报 / 小时报 / 周报 / 复盘"""
    pass


@report.command(name='daily')
@click.option('--date', type=click.DateTime(formats=['%Y-%m-%d']),
              help='报告日期 (默认: 今日)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际生成')
def report_daily(date, dry_run):
    """生成日报"""
    from ..utils.wrapper import run_legacy

    report_date = date or datetime.now()

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: generate_daily_quality_report.py --date {report_date.strftime('%Y-%m-%d')}")
        return

    run_legacy('generate_daily_quality_report.py',
               args=['--date', report_date.strftime('%Y-%m-%d')])
    click.echo(f"✅ 日报已生成: {report_date.strftime('%Y-%m-%d')}")


@report.command(name='hourly')
@click.option('--date', type=click.DateTime(formats=['%Y-%m-%d']),
              help='报告日期 (默认: 今日)')
@click.option('--hour', type=int, help='小时 (默认: 当前小时)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际生成')
def report_hourly(date, hour, dry_run):
    """生成小时报"""
    from ..utils.wrapper import run_legacy

    report_date = date or datetime.now()
    report_hour = hour or datetime.now().hour

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: hourly_enhanced_report.py --date {report_date.strftime('%Y-%m-%d')} --hour {report_hour}")
        return

    run_legacy('hourly_enhanced_report.py',
               args=['--date', report_date.strftime('%Y-%m-%d'),
                     '--hour', str(report_hour)])
    click.echo(f"✅ 小时报已生成: {report_date.strftime('%Y-%m-%d')} {report_hour}:00")


@report.command(name='weekly')
@click.option('--week', type=int, help='周数 (默认: 当前周)')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际生成')
def report_weekly(week, dry_run):
    """生成周报"""
    from ..utils.wrapper import run_legacy

    report_week = week or datetime.now().isocalendar()[1]

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: generate_weekly_report.py --week {report_week}")
        return

    run_legacy('generate_weekly_report.py', args=['--week', str(report_week)])
    click.echo(f"✅ 周报已生成: 第 {report_week} 周")


@report.command(name='review')
@click.option('--date', type=click.DateTime(formats=['%Y-%m-%d']),
              help='复盘日期 (默认: 今日)')
@click.option('--model', type=str, help='AI 模型')
@click.option('--lang', type=click.Choice(['zh', 'en']), default='zh',
              help='语言')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际生成')
def report_review(date, model, lang, dry_run):
    """生成复盘报告 (带 AI 分析)"""
    from ..utils.wrapper import run_legacy

    report_date = date or datetime.now()

    args = ['--date', report_date.strftime('%Y-%m-%d'), '--lang', lang]
    if model:
        args.extend(['--model', model])

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: daily_review.py {' '.join(args)}")
        return

    run_legacy('daily_review.py', args=args)
    click.echo(f"✅ 复盘报告已生成: {report_date.strftime('%Y-%m-%d')}")
