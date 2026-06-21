"""Pydantic schema for cron_config.yaml validation."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RetryPolicy(BaseModel):
    """Retry policy for failed tasks."""
    max_attempts: int = Field(1, ge=1, le=10)
    backoff: Literal['fixed', 'exponential', 'linear'] = 'fixed'
    initial_delay: int = Field(60, ge=0)


class TaskNotification(BaseModel):
    """Per-task notification override."""
    on_success: bool = False
    on_failure: bool = True
    channel: str = 'feishu'
    target: str | None = None
    mention: bool = False


class CronTask(BaseModel):
    """A single cron task definition."""
    id: str = Field(..., pattern=r'^[a-z][a-z0-9_]*$')
    group: str
    name: str
    schedule: str  # cron expression "0 9 * * *"
    command: str
    timeout: int = 600
    enabled: bool = True
    priority: Literal['low', 'normal', 'high', 'critical'] = 'normal'
    model: str | None = None
    tags: list[str] = Field(default_factory=list)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    notification: TaskNotification | None = None
    depends_on: list[str] = Field(default_factory=list)
    trading_day_only: bool = False

    @field_validator('schedule')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(
                f"cron 表达式必须是 5 段: '{v}' (got {len(parts)} segments)")
        return v


class GlobalNotification(BaseModel):
    """Global notification defaults."""
    on_success: bool = False
    on_failure: bool = True
    channel: str = 'feishu'
    target: str | None = None
    mention: bool = False


class CronConfig(BaseModel):
    """Root cron configuration schema."""
    version: str = '1.0'
    default_tz: str = 'Asia/Shanghai'
    default_timeout: int = 600
    default_model: str | None = None
    vars: dict[str, str] = Field(default_factory=dict)
    notification: GlobalNotification | None = None
    groups: dict[str, dict] = Field(default_factory=dict)
    tasks: list[CronTask]

    @model_validator(mode='after')
    def check_unique_ids(self) -> 'CronConfig':
        ids = [t.id for t in self.tasks]
        dups = {x for x in ids if ids.count(x) > 1}
        if dups:
            raise ValueError(f"重复的 task id: {dups}")
        return self

    @model_validator(mode='after')
    def check_dependencies(self) -> 'CronConfig':
        ids = {t.id for t in self.tasks}
        for t in self.tasks:
            for dep in t.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"任务 {t.id} 依赖不存在的任务: {dep}")
        return self

    def get_enabled_tasks(self) -> list[CronTask]:
        return [t for t in self.tasks if t.enabled]

    def get_tasks_by_group(self, group: str) -> list[CronTask]:
        return [t for t in self.tasks if t.group == group]

    def get_task(self, task_id: str) -> CronTask | None:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None


def load_and_validate_cron_config(
    config_path: str,
) -> CronConfig:
    """Load and validate a cron config YAML file.

    Raises ConfigError on any validation failure.
    """
    import yaml
    from pathlib import Path
    from ..utils.errors import ConfigError

    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Cron config not found: {config_path}",
        )

    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error: {e}")

    try:
        return CronConfig(**raw)
    except Exception as e:
        raise ConfigError(
            f"Cron config validation failed: {e}",
            details={'path': config_path},
        )
