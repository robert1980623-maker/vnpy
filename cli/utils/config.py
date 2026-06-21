"""Configuration loading and validation for VNPY CLI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATHS = [
    Path('config/cli_config.yaml'),
    Path('cli_config.yaml'),
    Path.home() / '.vnpy' / 'config.yaml',
]

# Default values when no config file is found
DEFAULT_CONFIG: dict[str, Any] = {
    'log': {
        'level': 'INFO',
        'format': 'text',
        'dir': './logs',
        'rotation': '100MB',
        'retention': 30,
    },
    'runtime': {
        'default_timeout': 600,
        'max_workers': 4,
        'trace_id_header': 'X-Trace-Id',
    },
    'legacy': {
        'scripts_dir': 'examples/alpha_research',
        'python': 'python3',
        'venv': 'venv/bin/activate',
        'cwd': 'examples/alpha_research',
    },
    'data_source': {
        'primary': 'tushare',
        'fallback': 'akshare',
        'circuit_breaker': {
            'failure_threshold': 3,
            'recovery_time': 300,
        },
    },
    'notification': {
        'feishu': {
            'enabled': False,
            'webhook_url': '',
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (mutates base)."""
    for key, val in override.items():
        if (key in base and isinstance(base[key], dict)
                and isinstance(val, dict)):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def _resolve_env_vars(data: Any) -> Any:
    """Recursively resolve ${VAR} patterns from environment."""
    if isinstance(data, str):
        if data.startswith('${') and data.endswith('}'):
            env_key = data[2:-1]
            return os.environ.get(env_key, data)
        # Handle embedded ${VAR} patterns
        import re
        def repl(match):
            return os.environ.get(match.group(1), match.group(0))
        return re.sub(r'\$\{([^}]+)\}', repl, data)
    elif isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_vars(item) for item in data]
    return data


def load_cli_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load CLI config from file with fallback to defaults.

    Priority: explicit path > config/cli_config.yaml > ~/.vnpy/config.yaml > defaults.
    Environment variables override file values when referenced as ${VAR}.
    """
    import copy
    config = copy.deepcopy(DEFAULT_CONFIG)

    path: Path | None = None
    if config_path:
        path = Path(config_path)
    else:
        for candidate in DEFAULT_CONFIG_PATHS:
            if candidate.exists():
                path = candidate
                break

    if path and path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
            _deep_merge(config, file_config)
        except yaml.YAMLError as e:
            from .errors import ConfigError
            raise ConfigError(
                f"Failed to parse config file {path}: {e}",
                details={'path': str(path)},
            )
        except OSError as e:
            from .errors import ConfigError
            raise ConfigError(
                f"Failed to read config file {path}: {e}",
                details={'path': str(path)},
            )

    config = _resolve_env_vars(config)

    # Make paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    if not os.path.isabs(config['log']['dir']):
        config['log']['dir'] = str(project_root / config['log']['dir'])
    if not os.path.isabs(config['legacy']['scripts_dir']):
        config['legacy']['scripts_dir'] = str(
            project_root / config['legacy']['scripts_dir'])
    if not os.path.isabs(config['legacy']['cwd']):
        config['legacy']['cwd'] = str(
            project_root / config['legacy']['cwd'])

    return config


def load_cron_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load cron_config.yaml with env var resolution."""
    path: Path | None = None
    if config_path:
        path = Path(config_path)
    else:
        candidates = [
            Path('config/cron_config.yaml'),
            Path('cron_config.yaml'),
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break

    if not path or not path.exists():
        from .errors import ConfigError
        raise ConfigError(
            "cron_config.yaml not found",
            details={'searched': [str(c) for c in [
                Path('config/cron_config.yaml'),
                Path('cron_config.yaml'),
            ]]},
        )

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}

    config = _resolve_env_vars(config)
    return config
