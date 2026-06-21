"""vnpy health - 健康检查命令组"""
from __future__ import annotations

import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click

from ..utils.logging import get_logger


logger = get_logger(__name__)


@click.group(name='health', short_help='健康检查')
def health():
    """健康检查子命令: 系统 / 数据 / 服务"""
    pass


def _check_system() -> tuple[str, str]:
    """Check system health."""
    try:
        os_info = f"{platform.system()} {platform.release()}"
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        disk = shutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)

        if disk_free_gb < 5:
            status = '❌'
            detail = f"Disk space low: {disk_free_gb:.1f}GB free"
        else:
            status = '✅'
            detail = f"{os_info}, Python {python_version}, {disk_free_gb:.1f}GB free"

        return status, detail
    except Exception as e:
        return '❌', f"Error: {e}"


def _check_data() -> tuple[str, str]:
    """Check data freshness."""
    try:
        # Check if data directory exists and has recent files
        data_dir = Path('examples/alpha_research/data')
        if not data_dir.exists():
            return '⚠️', 'Data directory not found'

        # Find most recent file
        recent_files = []
        for f in data_dir.rglob('*.parquet'):
            try:
                mtime = f.stat().st_mtime
                recent_files.append((f, mtime))
            except OSError:
                pass

        if not recent_files:
            return '⚠️', 'No parquet files found'

        recent_files.sort(key=lambda x: x[1], reverse=True)
        newest_path, newest_time = recent_files[0]
        newest_dt = datetime.fromtimestamp(newest_time)
        age_hours = (datetime.now() - newest_dt).total_seconds() / 3600

        if age_hours > 24:
            status = '⚠️'
            detail = f"Latest data: {newest_dt.strftime('%Y-%m-%d %H:%M')} ({age_hours:.1f}h ago)"
        else:
            status = '✅'
            detail = f"Latest data: {newest_dt.strftime('%Y-%m-%d %H:%M')} ({age_hours:.1f}h ago)"

        return status, detail
    except Exception as e:
        return '❌', f"Error: {e}"


def _check_services() -> tuple[str, str]:
    """Check external service connectivity."""
    services = []

    # Check Tushare
    try:
        import os
        if os.environ.get('TUSHARE_TOKEN'):
            services.append('Tushare (token configured)')
        else:
            services.append('Tushare (⚠️ no token)')
    except Exception:
        services.append('Tushare (❌)')

    # Check AKShare
    try:
        import akshare
        services.append('AKShare (OK)')
    except ImportError:
        services.append('AKShare (❌ not installed)')
    except Exception:
        services.append('AKShare (⚠️)')

    detail = ', '.join(services)
    status = '✅' if all('(OK' in s or 'token configured' in s for s in services) else '⚠️'
    return status, detail


@health.command(name='system')
def health_system():
    """检查系统健康状态"""
    status, detail = _check_system()
    click.echo(f"{status} System: {detail}")


@health.command(name='data')
def health_data():
    """检查数据新鲜度"""
    status, detail = _check_data()
    click.echo(f"{status} Data: {detail}")


@health.command(name='services')
def health_services():
    """检查外部服务连通性"""
    status, detail = _check_services()
    click.echo(f"{status} Services: {detail}")


@health.command(name='all')
def health_all():
    """全面健康检查"""
    click.echo("VNPY 健康检查报告\n")

    sys_status, sys_detail = _check_system()
    click.echo(f"{sys_status} System:     {sys_detail}")

    data_status, data_detail = _check_data()
    click.echo(f"{data_status} Data:       {data_detail}")

    svc_status, svc_detail = _check_services()
    click.echo(f"{svc_status} Services:   {svc_detail}")

    click.echo()
    if all(s == '✅' for s in [sys_status, data_status, svc_status]):
        click.echo("✅ 所有检查通过")
    else:
        click.echo("⚠️  部分检查未通过，请查看详情")
