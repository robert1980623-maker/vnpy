#!/usr/bin/env python3
"""
VNPY 统一配置管理

所有配置集中在此模块，通过 get_config() 获取。
配置来源: vnpy_config.yaml
"""

from pathlib import Path
from typing import Any, Optional
import yaml

_config_cache: Optional[dict[str, Any]] = None


def get_config() -> dict[str, Any]:
    """
    获取全局配置（单例模式，配置加载一次后缓存）。
    
    Returns:
        配置字典，结构如下:
        {
            'delta_consumer': {'max_retries': 3, 'max_history': 100, 'poll_interval': 30},
            'manager': {'default_timeout_minutes': 30, 'max_retries': 3, 'poll_interval': 5},
            'alert': {'notify_threshold': 3, 'channels': [...]},
            'error_analyzer': {'timeout': 30, 'fallback_confidence': 0.5, ...},
            'scheduler': {'max_retries': 5, ...},
        }
    """
    global _config_cache
    if _config_cache is None:
        config_path = Path(__file__).parent / "vnpy_config.yaml"
        with open(config_path, encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def get_delta_consumer_config() -> dict[str, Any]:
    """获取 delta_consumer 配置"""
    return get_config().get("delta_consumer", {})


def get_manager_config() -> dict[str, Any]:
    """获取 manager 配置"""
    return get_config().get("manager", {})


def get_alert_config() -> dict[str, Any]:
    """获取 alert 配置"""
    return get_config().get("alert", {})


def get_error_analyzer_config() -> dict[str, Any]:
    """获取 error_analyzer 配置"""
    return get_config().get("error_analyzer", {})


def get_scheduler_config() -> dict[str, Any]:
    """获取 scheduler 配置"""
    return get_config().get("scheduler", {})


# ============================================================
# 便捷访问器（供现有代码直接替换常量用）
# ============================================================

# delta_consumer
MAX_RETRIES = get_delta_consumer_config().get("max_retries", 3)
MAX_HISTORY = get_delta_consumer_config().get("max_history", 100)
DELTA_POLL_INTERVAL = get_delta_consumer_config().get("poll_interval", 30)

# manager
MANAGER_DEFAULT_TIMEOUT_MINUTES = get_manager_config().get("default_timeout_minutes", 30)
MANAGER_MAX_RETRIES = get_manager_config().get("max_retries", 3)
MANAGER_POLL_INTERVAL = get_manager_config().get("poll_interval", 5)

# alert
NOTIFY_THRESHOLD = get_alert_config().get("notify_threshold", 3)
ALERT_CHANNELS = get_alert_config().get("channels", [])

# error_analyzer
ERROR_ANALYZER_TIMEOUT = get_error_analyzer_config().get("timeout", 30)
ERROR_ANALYZER_FALLBACK_CONFIDENCE = get_error_analyzer_config().get("fallback_confidence", 0.5)
ERROR_ANALYZER_MODEL_URL = get_error_analyzer_config().get("model_url", "http://localhost:1234/v1/chat/completions")
ERROR_ANALYZER_MODEL_NAME = get_error_analyzer_config().get("model_name", "qwen/qwen3.6-35b-a3b")

# scheduler
SCHEDULER_MAX_RETRIES = get_scheduler_config().get("max_retries", 5)
SCHEDULER_RETRY_INTERVAL_SECONDS = get_scheduler_config().get("retry_interval_seconds", 60)
FEISHU_GROUP_ID = get_scheduler_config().get("feishu_group_id", "")
