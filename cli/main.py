"""VNPY 统一 CLI 入口"""
from __future__ import annotations

import os
import subprocess
import sys

import click

from .utils.config import load_cli_config
from .utils.logging import setup_logging
from .utils.logging import get_logger as _get_logger


def _ensure_tushare_token() -> str | None:
    """Ensure TUSHARE_TOKEN is loaded from environment or ~/.zshrc.

    Cron jobs run without an interactive shell, so ~/.zshrc is not sourced.
    This function attempts to source it when the token is missing.

    Returns the token source ('env', 'zshrc', '.env', or None).
    """
    import os as _os
    import subprocess as _subprocess

    # Already set via environment — nothing to do
    if _os.environ.get('TUSHARE_TOKEN'):
        logger = _get_logger(__name__)
        logger.debug("TUSHARE_TOKEN: loaded from environment")
        return 'env'

    logger = _get_logger(__name__)

    # Attempt 1: source ~/.zshrc and extract the token
    zshrc = _os.path.expanduser('~/.zshrc')
    if _os.path.exists(zshrc):
        try:
            result = _subprocess.run(
                ['zsh', '-c', f'source {zshrc} && env | grep TUSHARE_TOKEN'],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if line.startswith('TUSHARE_TOKEN='):
                    token = line.split('=', 1)[1].strip()
                    if token:
                        _os.environ['TUSHARE_TOKEN'] = token
                        logger.info(
                            f"TUSHARE_TOKEN: sourced from ~/.zshrc "
                            f"(masked: {token[:4]}...{token[-4:]})"
                        )
                        return 'zshrc'
        except Exception as e:
            logger.debug(f"Failed to source ~/.zshrc: {e}")

    # Attempt 2: check .env in project root
    project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    env_path = _os.path.join(project_root, '.env')
    if _os.path.exists(env_path):
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith('TUSHARE_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        if token:
                            _os.environ['TUSHARE_TOKEN'] = token
                            logger.info(
                                f"TUSHARE_TOKEN: loaded from .env "
                                f"(masked: {token[:4]}...{token[-4:]})"
                            )
                            return '.env'
        except Exception as e:
            logger.debug(f"Failed to read .env: {e}")

    logger.warning("TUSHARE_TOKEN: not found (env, ~/.zshrc, or .env)")
    return None


CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    max_content_width=120,
    show_default=True,
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='1.0.0', prog_name='vnpy')
@click.option('-v', '--verbose', count=True,
              help='增加日志详细度 (-v INFO, -vv DEBUG)')
@click.option('--config', 'config_path', type=click.Path(exists=True),
              help='CLI 配置文件路径 (默认: config/cli_config.yaml)')
@click.option('--log-format', type=click.Choice(['json', 'text']),
              default='text', help='日志格式')
@click.option('--log-dir', type=click.Path(), help='日志目录')
@click.option('--trace-id', help='手动指定 trace_id (用于跨进程关联)')
@click.pass_context
def cli(ctx: click.Context, verbose: int, config_path: str | None,
        log_format: str, log_dir: str | None, trace_id: str | None):
    """VNPY 量化交易系统统一 CLI

    提供数据下载、交易执行、报告生成、健康检查等功能。

    示例:
        vnpy download akshare --max 50
        vnpy trade rebalance --target 5
        vnpy health all
        vnpy cron list
    """
    # 1. Load config
    try:
        cfg = load_cli_config(config_path)
    except Exception as e:
        click.echo(f"Warning: Failed to load config: {e}", err=True)
        cfg = {}

    # 2. Initialize logging
    log_level = {0: 'WARNING', 1: 'INFO', 2: 'DEBUG'}.get(verbose, 'DEBUG')
    if verbose == 0:
        log_level = cfg.get('log', {}).get('level', 'INFO')

    setup_logging(
        level=log_level,
        fmt=log_format,
        log_dir=log_dir or cfg.get('log', {}).get('dir', './logs'),
        trace_id=trace_id,
    )

    # 3. Ensure TUSHARE_TOKEN is available (fix cron env issue)
    _ensure_tushare_token()

    # 4. Inject into context
    ctx.ensure_object(dict)
    ctx.obj['config'] = cfg
    ctx.obj['verbose'] = verbose


# Register subcommand groups
from .commands.download import download
from .commands.trade import trade
from .commands.report import report
from .commands.health import health
from .commands.cron import cron

cli.add_command(download)
cli.add_command(trade)
cli.add_command(report)
cli.add_command(health)
cli.add_command(cron)


def main():
    """console_scripts entry point."""
    try:
        cli(obj={})
    except click.UsageError as e:
        click.echo(f"Usage error: {e.format_message()}", err=True)
        sys.exit(2)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        from .utils.errors import handle_error
        code = handle_error(e)
        sys.exit(code)


if __name__ == '__main__':
    main()
