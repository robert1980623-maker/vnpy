"""vnpy cron - 定时任务管理命令组"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import click

from ..utils.cron_schema import CronConfig, load_and_validate_cron_config
from ..utils.errors import ConfigError
from ..utils.logging import get_logger


logger = get_logger(__name__)


@click.group(name='cron', short_help='定时任务管理')
@click.option('--config', 'config_path', type=click.Path(exists=True),
              help='cron 配置文件路径')
@click.pass_context
def cron(ctx, config_path):
    """定时任务管理: list / show / validate / install / export"""
    ctx.ensure_object(dict)
    ctx.obj['cron_config_path'] = config_path


def _load_config(ctx) -> CronConfig:
    """Load cron config from context or default path."""
    path = ctx.obj.get('cron_config_path')
    return load_and_validate_cron_config(path or 'config/cron_config.yaml')


@cron.command(name='list')
@click.option('--group', type=str, help='按分组过滤')
@click.option('--enabled-only', is_flag=True, help='只显示启用任务')
@click.pass_context
def cron_list(ctx, group, enabled_only):
    """列出所有 cron 任务"""
    config = _load_config(ctx)
    tasks = config.tasks

    if group:
        tasks = [t for t in tasks if t.group == group]
    if enabled_only:
        tasks = [t for t in tasks if t.enabled]

    if not tasks:
        click.echo("无任务")
        return

    # Print table header
    click.echo(f"{'ID':<35} {'SCHEDULE':<16} {'GROUP':<16} {'ENABLED'}")
    click.echo('-' * 75)

    for task in tasks:
        enabled = '✓' if task.enabled else '✗'
        click.echo(f"{task.id:<35} {task.schedule:<16} {task.group:<16} {enabled}")

    click.echo(f"\n共 {len(tasks)} 个任务")


@cron.command(name='show')
@click.argument('task_id')
@click.pass_context
def cron_show(ctx, task_id):
    """显示单个任务详情"""
    config = _load_config(ctx)
    task = config.get_task(task_id)

    if not task:
        click.echo(f"❌ 任务不存在: {task_id}", err=True)
        ctx.exit(1)

    click.echo(f"ID:        {task.id}")
    click.echo(f"Name:      {task.name}")
    click.echo(f"Group:     {task.group}")
    click.echo(f"Schedule:  {task.schedule} ({config.default_tz})")
    click.echo(f"Command:   {task.command}")
    click.echo(f"Timeout:   {task.timeout}s")
    if task.model:
        click.echo(f"Model:     {task.model}")
    if task.tags:
        click.echo(f"Tags:      {task.tags}")
    click.echo(f"Enabled:   {'true' if task.enabled else 'false'}")
    if task.depends_on:
        click.echo(f"Depends:   {task.depends_on}")
    else:
        click.echo("Depends:   (无)")


@cron.command(name='validate')
@click.pass_context
def cron_validate(ctx):
    """校验 cron 配置文件"""
    config = _load_config(ctx)

    click.echo("✅ 配置语法正确")
    click.echo("✅ 所有依赖关系合法")
    click.echo("✅ 无重复 task id")

    enabled = len(config.get_enabled_tasks())
    total = len(config.tasks)
    click.echo(f"\n📊 共 {total} 个任务 (启用 {enabled}, 禁用 {total - enabled})")


@cron.command(name='export')
@click.option('--output', '-o', type=click.Path(), default='./cron_jobs/',
              help='输出目录')
@click.pass_context
def cron_export(ctx, output):
    """导出为 OpenClaw cron JSON 配置"""
    config = _load_config(ctx)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for task in config.get_enabled_tasks():
        job = _to_openclaw_json(task, config)
        filename = f"{task.id}.json"
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=2)
        count += 1

    click.echo(f"✅ 已生成 {count} 个 OpenClaw cron 任务配置")
    click.echo(f"📁 输出目录: {output_dir}")


@cron.command(name='install')
@click.option('--dry-run', is_flag=True, help='只打印, 不实际安装')
@click.option('--yes', '-y', is_flag=True, help='跳过确认')
@click.pass_context
def cron_install(ctx, dry_run, yes):
    """安装 cron 任务到 OpenClaw"""
    config = _load_config(ctx)
    tasks = config.get_enabled_tasks()

    click.echo(f"将安装 {len(tasks)} 个任务...")

    if dry_run:
        for task in tasks:
            click.echo(f"  [DRY-RUN] {task.id} ({task.schedule})")
        click.echo(f"\n共 {len(tasks)} 个任务 (dry-run, 未实际安装)")
        return

    if not yes:
        if not click.confirm("是否继续?"):
            click.echo("已取消")
            return

    installed = 0
    failed = 0
    for task in tasks:
        job = _to_openclaw_json(task, config)
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'add', '--config',
                 json.dumps(job, ensure_ascii=False)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                click.echo(f"  ✅ {task.id}")
                installed += 1
            else:
                click.echo(f"  ❌ {task.id}: {result.stderr.strip()}")
                failed += 1
        except FileNotFoundError:
            click.echo("❌ openclaw 命令不可用, 请检查安装", err=True)
            ctx.exit(5)
        except Exception as e:
            click.echo(f"  ❌ {task.id}: {e}")
            failed += 1

    click.echo(f"\n✅ 已安装 {installed} 个任务"
               + (f", ❌ {failed} 个失败" if failed else ""))


@cron.command(name='enable')
@click.argument('task_id')
@click.pass_context
def cron_enable(ctx, task_id):
    """启用 cron 任务"""
    _set_task_enabled(ctx, task_id, True)
    click.echo(f"✅ 已启用: {task_id}")


@cron.command(name='disable')
@click.argument('task_id')
@click.pass_context
def cron_disable(ctx, task_id):
    """禁用 cron 任务"""
    _set_task_enabled(ctx, task_id, False)
    click.echo(f"✅ 已禁用: {task_id}")


@cron.command(name='run')
@click.argument('task_id')
@click.option('--dry-run', is_flag=True, help='只打印命令, 不实际执行')
@click.pass_context
def cron_run(ctx, task_id, dry_run):
    """立即运行指定任务"""
    config = _load_config(ctx)
    task = config.get_task(task_id)

    if not task:
        click.echo(f"❌ 任务不存在: {task_id}", err=True)
        ctx.exit(1)

    # Resolve vars in command
    command = _resolve_vars(task.command, config.vars)

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: {command}")
        return

    click.echo(f"[{task_id}] 正在执行: {command}")
    try:
        result = subprocess.run(
            command, shell=True, timeout=task.timeout,
            capture_output=False,
        )
        if result.returncode == 0:
            click.echo(f"✅ {task_id} 执行完成")
        else:
            click.echo(f"❌ {task_id} 执行失败 (exit code {result.returncode})")
            ctx.exit(result.returncode)
    except subprocess.TimeoutExpired:
        click.echo(f"❌ {task_id} 执行超时 ({task.timeout}s)")
        ctx.exit(6)


def _set_task_enabled(ctx, task_id: str, enabled: bool) -> None:
    """Set task enabled/disabled in the config file."""
    import yaml

    config_path = ctx.obj.get('cron_config_path') or 'config/cron_config.yaml'
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Config not found: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}

    tasks = raw.get('tasks', [])
    found = False
    for task in tasks:
        if task.get('id') == task_id:
            task['enabled'] = enabled
            found = True
            break

    if not found:
        click.echo(f"❌ 任务不存在: {task_id}", err=True)
        ctx.exit(1)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False,
                  sort_keys=False)


def _resolve_vars(command: str, vars_dict: dict[str, str]) -> str:
    """Resolve ${VAR} patterns in command string."""
    result = command
    for key, value in vars_dict.items():
        result = result.replace(f'${{{key}}}', value)
    # Also resolve from environment
    import re
    def repl(match):
        return os.environ.get(match.group(1), match.group(0))
    result = re.sub(r'\$\{([^}]+)\}', repl, result)
    return result


def _to_openclaw_json(task, config: CronConfig) -> dict:
    """Convert CronTask to OpenClaw cron JSON format."""
    job = {
        'id': task.id,
        'agentId': 'main',
        'name': task.name,
        'schedule': {
            'kind': 'cron',
            'expr': task.schedule,
            'tz': config.default_tz,
        },
        'payload': {
            'kind': 'prompt',
            'prompt': task.command,
        },
        'enabled': task.enabled,
        'sessionTarget': task.id,
    }
    if task.model:
        job['model'] = task.model
    elif config.default_model:
        job['model'] = config.default_model
    if task.notification:
        job['notify'] = {
            'onSuccess': task.notification.on_success,
            'onFailure': task.notification.on_failure,
        }
    elif config.notification:
        job['notify'] = {
            'onSuccess': config.notification.on_success,
            'onFailure': config.notification.on_failure,
        }
    return job
