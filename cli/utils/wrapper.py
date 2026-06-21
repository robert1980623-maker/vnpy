"""Wrapper for calling legacy scripts from CLI commands.

Provides backward compatibility by allowing new CLI commands to invoke
old scripts without modification.
"""
from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

from .errors import DependencyError, ValidationError
from .logging import get_current_trace_id, get_logger


logger = get_logger(__name__)

# Legacy scripts directory (examples/alpha_research/)
LEGACY_SCRIPTS_DIR = Path(__file__).parent.parent.parent / 'examples' / 'alpha_research'


def run_legacy(
    script_name: str,
    *,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a legacy script as a subprocess.

    Args:
        script_name: Script filename (e.g., 'download_data_akshare.py').
        args: Command-line arguments to pass.
        env: Additional environment variables (merged with current env).
        cwd: Working directory (default: examples/alpha_research/).
        check: If True, raise on non-zero exit code.

    Returns:
        CompletedProcess instance.

    Raises:
        DependencyError: If script not found or execution fails.
    """
    script_path = LEGACY_SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise DependencyError(
            f"Legacy script not found: {script_name}",
            details={'path': str(script_path)},
        )

    # Build environment with trace_id propagation
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    run_env['TRACEPARENT'] = get_current_trace_id()

    # Build command
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    # Working directory
    run_cwd = cwd or LEGACY_SCRIPTS_DIR

    logger.info(
        f"Running legacy script: {script_name}",
        extra={'command': ' '.join(cmd), 'cwd': str(run_cwd)},
    )

    try:
        result = subprocess.run(
            cmd,
            cwd=run_cwd,
            env=run_env,
            check=False,  # We handle errors ourselves
        )
        if check and result.returncode != 0:
            raise DependencyError(
                f"Legacy script failed with exit code {result.returncode}",
                details={
                    'script': script_name,
                    'exit_code': result.returncode,
                },
            )
        return result
    except FileNotFoundError as e:
        raise DependencyError(
            f"Failed to execute script: {e}",
            details={'script': script_name},
        )
    except Exception as e:
        raise DependencyError(
            f"Unexpected error running script: {e}",
            details={'script': script_name},
        )


def run_legacy_import(
    script_name: str,
    *,
    run_name: str = '__main__',
) -> dict[str, Any]:
    """Run a legacy script via runpy (in-process).

    Use this when you need to import symbols from the script.
    Prefer run_legacy() for simple execution.

    Args:
        script_name: Script filename.
        run_name: Module name to use (default: '__main__').

    Returns:
        Module globals dict.
    """
    script_path = LEGACY_SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise DependencyError(
            f"Legacy script not found: {script_name}",
            details={'path': str(script_path)},
        )

    logger.info(f"Importing legacy script: {script_name}")
    try:
        return runpy.run_path(str(script_path), run_name=run_name)
    except SystemExit as e:
        # Script called sys.exit()
        if e.code and e.code != 0:
            raise DependencyError(
                f"Legacy script exited with code {e.code}",
                details={'script': script_name, 'exit_code': e.code},
            )
        return {}
    except Exception as e:
        raise DependencyError(
            f"Failed to import legacy script: {e}",
            details={'script': script_name},
        )


def legacy_command(
    script_name: str,
    *,
    help_text: str | None = None,
    hidden: bool = False,
):
    """Decorator: wrap a legacy script as a Click command.

    Example:
        @legacy_command('realtime_monitor.py', help_text='实时监控 (兼容旧脚本)')
        def monitor_realtime(**kwargs):
            pass
    """
    def decorator(func):
        @click.command(
            name=func.__name__.replace('_', '-'),
            help=help_text or func.__doc__,
            hidden=hidden,
        )
        @click.pass_context
        def wrapper(ctx, *args, **kwargs):
            # Extract Click options from kwargs, pass rest as script args
            script_args = []
            for key, val in kwargs.items():
                if val is None:
                    continue
                arg_name = f"--{key.replace('_', '-')}"
                if isinstance(val, bool):
                    if val:
                        script_args.append(arg_name)
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        script_args.extend([arg_name, str(item)])
                else:
                    script_args.extend([arg_name, str(val)])

            try:
                result = run_legacy(script_name, args=script_args)
                ctx.exit(result.returncode or 0)
            except DependencyError as e:
                ctx.fail(e.message)

        # Preserve original function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
