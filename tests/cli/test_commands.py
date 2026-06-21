"""Tests for CLI main entry point and commands."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestMainCLI:
    def test_help(self, runner):
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'VNPY' in result.output
        assert 'download' in result.output
        assert 'trade' in result.output
        assert 'report' in result.output
        assert 'health' in result.output
        assert 'cron' in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output

    def test_verbose_flag(self, runner):
        result = runner.invoke(cli, ['-v', '--help'])
        assert result.exit_code == 0

    def test_unknown_command(self, runner):
        result = runner.invoke(cli, ['nonexistent'])
        assert result.exit_code != 0


class TestDownloadCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ['download', '--help'])
        assert result.exit_code == 0
        assert 'akshare' in result.output
        assert 'tushare' in result.output
        assert 'policy' in result.output
        assert 'geopolitics' in result.output
        assert 'news' in result.output

    def test_akshare_dry_run(self, runner):
        result = runner.invoke(cli, ['download', 'akshare', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
        assert 'download_data_akshare.py' in result.output

    def test_akshare_with_options(self, runner):
        result = runner.invoke(cli, [
            'download', 'akshare',
            '--end', '2026-06-21',
            '--max', '10',
            '--force',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert '2026-06-21' in result.output
        assert '10' in result.output

    def test_policy_dry_run(self, runner):
        result = runner.invoke(cli, ['download', 'policy', '--days', '3', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output

    def test_geopolitics_dry_run(self, runner):
        result = runner.invoke(cli, ['download', 'geopolitics', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output

    def test_news_dry_run(self, runner):
        result = runner.invoke(cli, ['download', 'news', '--session', 'morning', '--dry-run'])
        assert result.exit_code == 0
        assert 'morning' in result.output

    def test_all_dry_run(self, runner):
        result = runner.invoke(cli, ['download', 'all', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output


class TestTradeCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ['trade', '--help'])
        assert result.exit_code == 0
        assert 'paper' in result.output
        assert 'rebalance' in result.output
        assert 'stop-loss' in result.output

    def test_paper_dry_run(self, runner):
        result = runner.invoke(cli, [
            'trade', 'paper',
            '--capital', '500000',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output

    def test_rebalance_dry_run(self, runner):
        result = runner.invoke(cli, [
            'trade', 'rebalance',
            '--target', '10',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert '10' in result.output

    def test_stop_loss_dry_run(self, runner):
        result = runner.invoke(cli, [
            'trade', 'stop-loss',
            '--threshold', '0.08',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert '0.08' in result.output

    def test_execute_dry_run(self, runner):
        result = runner.invoke(cli, [
            'trade', 'execute',
            '--action', 'close-all',
            '--reason', 'test',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert 'close-all' in result.output


class TestReportCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ['report', '--help'])
        assert result.exit_code == 0
        assert 'daily' in result.output
        assert 'hourly' in result.output
        assert 'weekly' in result.output
        assert 'review' in result.output

    def test_daily_dry_run(self, runner):
        result = runner.invoke(cli, ['report', 'daily', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output

    def test_hourly_dry_run(self, runner):
        result = runner.invoke(cli, [
            'report', 'hourly',
            '--hour', '14',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert '14' in result.output

    def test_weekly_dry_run(self, runner):
        result = runner.invoke(cli, [
            'report', 'weekly',
            '--week', '25',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert '25' in result.output

    def test_review_dry_run(self, runner):
        result = runner.invoke(cli, [
            'report', 'review',
            '--lang', 'en',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert 'en' in result.output


class TestHealthCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ['health', '--help'])
        assert result.exit_code == 0
        assert 'system' in result.output
        assert 'data' in result.output
        assert 'services' in result.output
        assert 'all' in result.output

    def test_system(self, runner):
        result = runner.invoke(cli, ['health', 'system'])
        assert result.exit_code == 0
        assert 'System' in result.output

    def test_data(self, runner):
        result = runner.invoke(cli, ['health', 'data'])
        assert result.exit_code == 0
        assert 'Data' in result.output

    def test_services(self, runner):
        result = runner.invoke(cli, ['health', 'services'])
        assert result.exit_code == 0
        assert 'Services' in result.output

    def test_all(self, runner):
        result = runner.invoke(cli, ['health', 'all'])
        assert result.exit_code == 0
        assert 'System' in result.output
        assert 'Data' in result.output
        assert 'Services' in result.output


class TestCronCommand:
    @pytest.fixture
    def valid_config(self, tmp_path):
        config = tmp_path / "cron_config.yaml"
        config.write_text("""
version: "1.0"
default_tz: Asia/Shanghai
default_timeout: 600
tasks:
  - id: test_task_one
    group: test
    name: 测试任务 1
    schedule: "0 9 * * *"
    command: "echo hello"
    timeout: 300
    enabled: true
    tags: [test]
  - id: test_task_two
    group: test
    name: 测试任务 2
    schedule: "0 17 * * 1-5"
    command: "echo world"
    timeout: 600
    enabled: false
    depends_on: [test_task_one]
""")
        return config

    def test_list(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'list',
        ])
        assert result.exit_code == 0
        assert 'test_task_one' in result.output
        assert 'test_task_two' in result.output
        assert '2' in result.output  # task count

    def test_list_group_filter(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'list',
            '--group', 'test',
        ])
        assert result.exit_code == 0
        assert 'test_task_one' in result.output

    def test_list_enabled_only(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'list',
            '--enabled-only',
        ])
        assert result.exit_code == 0
        assert 'test_task_one' in result.output

    def test_show(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'show', 'test_task_one',
        ])
        assert result.exit_code == 0
        assert 'test_task_one' in result.output
        assert '测试任务 1' in result.output
        assert '0 9 * * *' in result.output

    def test_show_not_found(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'show', 'nonexistent',
        ])
        assert result.exit_code != 0

    def test_validate(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'validate',
        ])
        assert result.exit_code == 0
        assert '✅' in result.output
        assert '2' in result.output

    def test_validate_duplicate_id(self, runner, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("""
version: "1.0"
tasks:
  - {id: dup, group: g, name: n, schedule: "0 1 * * *", command: "x"}
  - {id: dup, group: g, name: n, schedule: "0 2 * * *", command: "x"}
""")
        result = runner.invoke(cli, [
            'cron', '--config', str(bad), 'validate',
        ])
        assert result.exit_code != 0

    def test_validate_bad_cron_expr(self, runner, tmp_path):
        bad = tmp_path / "bad_cron.yaml"
        bad.write_text("""
version: "1.0"
tasks:
  - id: bad_cron
    group: g
    name: n
    schedule: "0 1 * *"
    command: "x"
""")
        result = runner.invoke(cli, [
            'cron', '--config', str(bad), 'validate',
        ])
        assert result.exit_code != 0

    def test_validate_bad_dependency(self, runner, tmp_path):
        bad = tmp_path / "bad_dep.yaml"
        bad.write_text("""
version: "1.0"
tasks:
  - id: task_a
    group: g
    name: n
    schedule: "0 1 * * *"
    command: "x"
    depends_on: [nonexistent_task]
""")
        result = runner.invoke(cli, [
            'cron', '--config', str(bad), 'validate',
        ])
        assert result.exit_code != 0

    def test_export(self, runner, valid_config, tmp_path):
        output_dir = tmp_path / "export_output"
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'export',
            '--output', str(output_dir),
        ])
        assert result.exit_code == 0
        assert '1' in result.output  # 1 enabled task

        # Verify exported file
        exported = output_dir / "test_task_one.json"
        assert exported.exists()
        with open(exported) as f:
            job = json.load(f)
        assert job['id'] == 'test_task_one'
        assert job['schedule']['kind'] == 'cron'

    def test_install_dry_run(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'install',
            '--dry-run',
        ])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
        assert 'test_task_one' in result.output

    def test_run_dry_run(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'run',
            'test_task_one', '--dry-run',
        ])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output

    def test_run_not_found(self, runner, valid_config):
        result = runner.invoke(cli, [
            'cron', '--config', str(valid_config), 'run',
            'nonexistent',
        ])
        assert result.exit_code != 0
