"""vnpy download - 数据下载命令组"""
from __future__ import annotations

from datetime import datetime

import click

from ..utils.logging import get_logger


logger = get_logger(__name__)


@click.group(name='download', short_help='数据下载')
def download():
    """数据下载子命令: akshare / tushare / baostock / 政策/新闻"""
    pass


@download.command(name='akshare')
@click.option('--end', type=click.DateTime(formats=['%Y-%m-%d']),
              help='结束日期 (默认: 今日)')
@click.option('--max', 'max_stocks', type=int, default=20,
              help='最大下载股票数')
@click.option('--force', is_flag=True, help='强制重新下载')
@click.option('--workers', type=int, default=4, help='并行线程数')
@click.option('--validate', is_flag=True, help='下载后自动校验数据质量')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_akshare(end, max_stocks, force, workers, validate, dry_run):
    """下载 A 股日 K 线数据 (via AKShare)"""
    end_date = end or datetime.now()
    logger.info("download.akshare", extra={
        'end': end_date.strftime('%Y-%m-%d'),
        'max': max_stocks,
        'force': force,
        'workers': workers,
        'validate': validate,
    })

    args = ['--end', end_date.strftime('%Y-%m-%d'),
            '--max', str(max_stocks)]
    if force:
        args.append('--force')
    if validate:
        args.append('--validate')

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: download_data_akshare.py {' '.join(args)}")
        return

    from ..utils.wrapper import run_legacy
    run_legacy('download_data_akshare.py', args=args)
    click.echo("✅ AKShare 数据下载完成")

    if validate:
        _run_post_download_validation()


@download.command(name='tushare')
@click.option('--symbols', type=str, help='股票代码列表 (逗号分隔)')
@click.option('--force', is_flag=True, help='强制重新下载')
@click.option('--validate', is_flag=True, help='下载后自动校验数据质量')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_tushare(symbols, force, validate, dry_run):
    """下载 A 股数据 (via Tushare Pro)"""
    from ..utils.wrapper import run_legacy

    args = []
    if symbols:
        args.extend(['--symbols', symbols])
    if force:
        args.append('--force')
    if validate:
        args.append('--validate')

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: tushare_pro_downloader.py {' '.join(args)}")
        return

    run_legacy('tushare_pro_downloader.py', args=args)
    click.echo("✅ Tushare 数据下载完成")

    if validate:
        _run_post_download_validation()


@download.command(name='policy')
@click.option('--days', type=int, default=7, help='回溯天数')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_policy(days, dry_run):
    """下载政策面数据"""
    from ..utils.wrapper import run_legacy

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: download_policy_data.py --days {days}")
        return

    run_legacy('download_policy_data.py', args=['--days', str(days)])
    click.echo("✅ 政策面数据下载完成")


@download.command(name='geopolitics')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_geopolitics(dry_run):
    """下载国际形势数据"""
    from ..utils.wrapper import run_legacy

    if dry_run:
        click.echo("[DRY-RUN] Would run: download_geopolitics_data.py")
        return

    run_legacy('download_geopolitics_data.py')
    click.echo("✅ 国际形势数据下载完成")


@download.command(name='news')
@click.option('--session', type=click.Choice(['morning', 'evening', 'all']),
              default='all', help='时段')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_news(session, dry_run):
    """下载财经新闻数据"""
    from ..utils.wrapper import run_legacy

    args = ['--session', session]

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: download_news_data.py {' '.join(args)}")
        return

    run_legacy('download_news_data.py', args=args)
    click.echo("✅ 新闻数据下载完成")


@download.command(name='all')
@click.option('--parallel', is_flag=True, help='并行下载')
@click.option('--validate', is_flag=True, help='下载后自动校验数据质量')
@click.option('--dry-run', is_flag=True, help='只检查参数, 不实际下载')
def download_all(parallel, validate, dry_run):
    """下载所有数据源 (汇总调用)"""
    if dry_run:
        click.echo("[DRY-RUN] Would run all download subcommands")
        return

    ctx = click.get_current_context()
    for cmd_name in ['akshare', 'policy', 'geopolitics', 'news']:
        click.echo(f"\n--- Running: {cmd_name} ---")
        try:
            ctx.invoke(download.commands[cmd_name], dry_run=False, validate=validate)
        except TypeError:
            # Some subcommands don't have --validate
            ctx.invoke(download.commands[cmd_name], dry_run=False)
        except Exception as e:
            click.echo(f"❌ {cmd_name} failed: {e}", err=True)

    click.echo("\n✅ 全部下载任务完成")


# ---------------------------------------------------------------------------
# Helper: post-download validation
# ---------------------------------------------------------------------------

def _run_post_download_validation():
    """下载完成后对数据目录中的 CSV 运行校验"""
    import sys
    from pathlib import Path

    # 确保 alpha_research 在 sys.path 中
    ar_dir = Path(__file__).resolve().parent.parent.parent / 'examples' / 'alpha_research'
    if str(ar_dir) not in sys.path:
        sys.path.insert(0, str(ar_dir))

    try:
        from data_validator import DataValidator
        validator = DataValidator()

        data_dir = Path('./data/akshare/bars')
        if not data_dir.exists():
            click.echo("⚠️  数据目录不存在，跳过校验")
            return

        csv_files = sorted(data_dir.glob('*.csv'))
        if not csv_files:
            click.echo("⚠️  数据目录为空，跳过校验")
            return

        click.echo(f"\n🔍 校验 {len(csv_files)} 个数据文件...")
        passed, failed, errors = 0, 0, 0

        for csv_file in csv_files:
            symbol = csv_file.stem.replace('_', '.')
            try:
                df = pd.read_csv(csv_file)
                result = validator.validate(df, symbol)
                if result.passed:
                    passed += 1
                else:
                    failed += 1
                    click.echo(f"  ❌ {symbol}: {result.summary()}")
            except Exception as e:
                errors += 1
                click.echo(f"  ⚠️  {symbol}: 校验异常 - {e}")

        click.echo(f"\n✅ 校验完成: 通过 {passed}, 失败 {failed}, 异常 {errors}")

    except ImportError as e:
        click.echo(f"⚠️  无法加载 data_validator: {e}")
    except Exception as e:
        click.echo(f"⚠️  校验过程出错: {e}")


# 导入 pandas（post-validation 使用）
try:
    import pandas as pd
except ImportError:
    pd = None
