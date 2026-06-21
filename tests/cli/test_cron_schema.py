"""Tests for cron schema validation."""
import pytest
from pydantic import ValidationError as PydanticValidationError

from cli.utils.cron_schema import (
    CronTask, CronConfig, RetryPolicy, TaskNotification,
    load_and_validate_cron_config,
)
from cli.utils.errors import ConfigError


class TestRetryPolicy:
    def test_defaults(self):
        r = RetryPolicy()
        assert r.max_attempts == 1
        assert r.backoff == 'fixed'
        assert r.initial_delay == 60

    def test_custom(self):
        r = RetryPolicy(max_attempts=3, backoff='exponential', initial_delay=120)
        assert r.max_attempts == 3

    def test_invalid_max_attempts(self):
        with pytest.raises(PydanticValidationError):
            RetryPolicy(max_attempts=0)

    def test_max_attempts_upper_bound(self):
        with pytest.raises(PydanticValidationError):
            RetryPolicy(max_attempts=11)


class TestCronTask:
    def test_minimal(self):
        t = CronTask(
            id='test_task', group='g', name='n',
            schedule='0 9 * * *', command='echo',
        )
        assert t.id == 'test_task'
        assert t.enabled is True
        assert t.priority == 'normal'
        assert t.tags == []

    def test_full(self):
        t = CronTask(
            id='full_task', group='g', name='n',
            schedule='0 9 * * 1-5', command='echo hello',
            timeout=300, enabled=False, priority='high',
            model='test-model', tags=['a', 'b'],
            retry=RetryPolicy(max_attempts=3),
            notification=TaskNotification(on_failure=True),
            depends_on=['other_task'],
            trading_day_only=True,
        )
        assert t.priority == 'high'
        assert t.trading_day_only is True

    def test_invalid_id_pattern(self):
        with pytest.raises(PydanticValidationError):
            CronTask(
                id='Invalid-ID', group='g', name='n',
                schedule='0 9 * * *', command='echo',
            )

    def test_invalid_cron_expression(self):
        with pytest.raises(PydanticValidationError):
            CronTask(
                id='bad_cron', group='g', name='n',
                schedule='0 1 * *',  # Only 4 segments
                command='echo',
            )

    def test_invalid_priority(self):
        with pytest.raises(PydanticValidationError):
            CronTask(
                id='bad_prio', group='g', name='n',
                schedule='0 9 * * *', command='echo',
                priority='ultra',
            )


class TestCronConfig:
    def test_minimal(self):
        c = CronConfig(tasks=[
            CronTask(id='t1', group='g', name='n',
                     schedule='0 9 * * *', command='echo'),
        ])
        assert c.version == '1.0'
        assert len(c.tasks) == 1

    def test_duplicate_ids(self):
        with pytest.raises(PydanticValidationError, match='重复'):
            CronConfig(tasks=[
                CronTask(id='dup', group='g', name='n',
                         schedule='0 9 * * *', command='echo'),
                CronTask(id='dup', group='g', name='n',
                         schedule='0 10 * * *', command='echo'),
            ])

    def test_bad_dependency(self):
        with pytest.raises(PydanticValidationError, match='依赖不存在'):
            CronConfig(tasks=[
                CronTask(id='t1', group='g', name='n',
                         schedule='0 9 * * *', command='echo',
                         depends_on=['nonexistent']),
            ])

    def test_valid_dependency(self):
        c = CronConfig(tasks=[
            CronTask(id='t1', group='g', name='n',
                     schedule='0 9 * * *', command='echo'),
            CronTask(id='t2', group='g', name='n',
                     schedule='0 10 * * *', command='echo',
                     depends_on=['t1']),
        ])
        assert len(c.tasks) == 2

    def test_get_enabled_tasks(self):
        c = CronConfig(tasks=[
            CronTask(id='t1', group='g', name='n',
                     schedule='0 9 * * *', command='echo', enabled=True),
            CronTask(id='t2', group='g', name='n',
                     schedule='0 10 * * *', command='echo', enabled=False),
        ])
        enabled = c.get_enabled_tasks()
        assert len(enabled) == 1
        assert enabled[0].id == 't1'

    def test_get_tasks_by_group(self):
        c = CronConfig(tasks=[
            CronTask(id='t1', group='download', name='n',
                     schedule='0 9 * * *', command='echo'),
            CronTask(id='t2', group='monitor', name='n',
                     schedule='0 10 * * *', command='echo'),
            CronTask(id='t3', group='download', name='n',
                     schedule='0 11 * * *', command='echo'),
        ])
        download_tasks = c.get_tasks_by_group('download')
        assert len(download_tasks) == 2

    def test_get_task(self):
        c = CronConfig(tasks=[
            CronTask(id='t1', group='g', name='n',
                     schedule='0 9 * * *', command='echo'),
        ])
        assert c.get_task('t1') is not None
        assert c.get_task('nonexistent') is None


class TestLoadAndValidate:
    def test_file_not_found(self):
        with pytest.raises(ConfigError):
            load_and_validate_cron_config('/nonexistent/path.yaml')

    def test_invalid_yaml(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  bad: yaml: [")
        with pytest.raises(ConfigError, match='YAML parse error'):
            load_and_validate_cron_config(str(bad))

    def test_valid_config(self, tmp_path):
        config_file = tmp_path / "valid.yaml"
        config_file.write_text("""
version: "1.0"
tasks:
  - id: test_task
    group: test
    name: Test
    schedule: "0 9 * * *"
    command: "echo hello"
    enabled: true
""")
        result = load_and_validate_cron_config(str(config_file))
        assert isinstance(result, CronConfig)
        assert len(result.tasks) == 1

    def test_config_with_duplicate_id(self, tmp_path):
        config_file = tmp_path / "dup.yaml"
        config_file.write_text("""
version: "1.0"
tasks:
  - id: dup
    group: g
    name: n
    schedule: "0 1 * * *"
    command: "x"
  - id: dup
    group: g
    name: n
    schedule: "0 2 * * *"
    command: "x"
""")
        with pytest.raises(ConfigError, match='重复'):
            load_and_validate_cron_config(str(config_file))


class TestRealCronConfig:
    """Test loading the actual project cron_config.yaml."""

    def test_load_project_config(self):
        """Validate the real cron_config.yaml passes schema."""
        config_path = 'config/cron_config.yaml'
        from pathlib import Path
        if not Path(config_path).exists():
            pytest.skip("cron_config.yaml not found")

        result = load_and_validate_cron_config(config_path)
        assert isinstance(result, CronConfig)
        assert len(result.tasks) > 0

        # Verify all task IDs are unique
        ids = [t.id for t in result.tasks]
        assert len(ids) == len(set(ids))

        # Verify groups exist
        groups = {t.group for t in result.tasks}
        assert 'data_download' in groups
        assert 'monitor' in groups
        assert 'trading' in groups
        assert 'report' in groups
