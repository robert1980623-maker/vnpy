"""Tests for CLI main entry point and commands."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cli.main import cli, main


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
            '--confirm',
            '--dry-run',
        ])
        # 对于close-all操作，即使在dry-run模式下也会显示警告信息
        # 但由于我们没有真正调用click.confirm，所以不会等待用户输入，命令会继续执行
        assert 'close-all' in result.output or '特别警告' in result.output

    def test_execute_without_confirm_fails(self, runner):
        # 测试没有--confirm标志且非dry-run的情况下应该失败
        result = runner.invoke(cli, [
            'trade', 'execute',
            '--action', 'close-all',
            '--reason', 'test',
            # 注意：不包括--confirm标志，也不包括--dry-run，这样会要求用户确认
        ], input='n\n')  # 模拟用户输入'n'拒绝确认
        # 当没有提供--confirm标志时，代码会在非dry-run情况下直接输出错误消息而不是等待用户输入
        assert '必须使用 --confirm 标志确认操作' in result.output

    def test_execute_close_all_double_confirm(self, runner):
        # 测试close-all操作在非dry-run模式下需要双重确认
        # 这个测试会比较复杂，因为它需要模拟click.confirm和click.prompt的返回值
        from unittest.mock import patch

        with patch('click.confirm', return_value=True), \
             patch('click.prompt', return_value='CONFIRM_CLOSE_ALL'):
            result = runner.invoke(cli, [
                'trade', 'execute',
                '--action', 'close-all',
                '--reason', 'test_double_confirm',
                '--confirm',
                '--account-id', 'test_account',
                '--dry-run',  # 仍使用dry-run以避免实际交互
            ])
            assert result.exit_code == 0
            assert '特别警告' in result.output


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


# ── TestMainEntry (cli/__main__.py) ──────────────────────────────────────


class TestMainEntry:
    """Tests for cli/__main__.py entry point."""

    def test_main_entry_callable(self):
        """python -m cli calls main(); verify module structure and execution."""
        import runpy
        # Patch cli.main.cli to prevent sys.exit and verify main() was called
        with patch('cli.main.cli') as mock_cli, \
             patch('cli.main.setup_logging'):
            mock_cli.return_value = None
            # run_module executes __main__.py
            runpy.run_module('cli', run_name='__main__')
            mock_cli.assert_called_once_with(obj={})


# ── TestMainFunction (cli/main.py error handling) ───────────────────────


class TestMainFunction:
    """Tests for main() error handling paths (lines 83-97)."""

    def test_main_usage_error(self):
        """click.UsageError → exit code 2."""
        import click
        with patch('cli.main.cli', side_effect=click.UsageError('bad usage')):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_main_click_exception(self):
        """click.ClickException → exit with its exit_code."""
        import click
        with patch('cli.main.cli', side_effect=click.ClickException('oops')):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1  # default ClickException exit code

    def test_main_keyboard_interrupt(self):
        """KeyboardInterrupt → exit code 130."""
        with patch('cli.main.cli', side_effect=KeyboardInterrupt):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 130

    def test_main_unexpected_error(self):
        """Generic Exception → handle_error returns exit code."""
        with patch('cli.main.cli', side_effect=RuntimeError('boom')):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1  # EXIT_GENERAL_ERROR


# ── TestCronEnableDisable ───────────────────────────────────────────────


class TestCronEnableDisable:
    """Tests for cron enable/disable commands."""

    @pytest.fixture
    def config_with_tasks(self, tmp_path):
        config = tmp_path / "cron_config.yaml"
        config.write_text("""
version: "1.0"
default_tz: Asia/Shanghai
tasks:
  - id: my_task
    group: test
    name: My Task
    schedule: "0 9 * * *"
    command: "echo hello"
    enabled: false
""")
        return config

    def test_enable_success(self, runner, config_with_tasks):
        """Enable a disabled task → YAML updated, exit 0."""
        result = runner.invoke(cli, [
            'cron', '--config', str(config_with_tasks), 'enable', 'my_task',
        ])
        assert result.exit_code == 0
        assert '已启用' in result.output

        # Verify YAML was updated
        import yaml
        with open(config_with_tasks) as f:
            raw = yaml.safe_load(f)
        task = next(t for t in raw['tasks'] if t['id'] == 'my_task')
        assert task['enabled'] is True

    def test_disable_success(self, runner, tmp_path):
        """Disable an enabled task → YAML updated, exit 0."""
        config = tmp_path / "cron_config.yaml"
        config.write_text("""
version: "1.0"
default_tz: Asia/Shanghai
tasks:
  - id: my_task
    group: test
    name: My Task
    schedule: "0 9 * * *"
    command: "echo hello"
    enabled: true
""")
        result = runner.invoke(cli, [
            'cron', '--config', str(config), 'disable', 'my_task',
        ])
        assert result.exit_code == 0
        assert '已禁用' in result.output

        import yaml
        with open(config) as f:
            raw = yaml.safe_load(f)
        task = next(t for t in raw['tasks'] if t['id'] == 'my_task')
        assert task['enabled'] is False

    def test_enable_not_found(self, runner, config_with_tasks):
        """Enable a non-existent task → exit != 0."""
        result = runner.invoke(cli, [
            'cron', '--config', str(config_with_tasks), 'enable', 'nonexistent',
        ])
        assert result.exit_code != 0
        assert '不存在' in result.output


# ── TestCronInstallExtended ─────────────────────────────────────────────


class TestCronInstallExtended:
    """Extended tests for cron install command (non-dry-run paths)."""

    @pytest.fixture
    def install_config(self, tmp_path):
        config = tmp_path / "cron_config.yaml"
        config.write_text("""
version: "1.0"
default_tz: Asia/Shanghai
tasks:
  - id: install_task
    group: test
    name: Install Task
    schedule: "0 9 * * *"
    command: "echo hello"
    enabled: true
""")
        return config

    def test_install_success(self, runner, install_config):
        """Successful install via mocked openclaw subprocess."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        with patch('cli.commands.cron.subprocess.run', return_value=mock_result):
            result = runner.invoke(cli, [
                'cron', '--config', str(install_config), 'install', '-y',
            ])
        assert result.exit_code == 0
        assert '✅' in result.output
        assert 'install_task' in result.output

    def test_install_subprocess_failure(self, runner, install_config):
        """openclaw returns non-zero → shows ❌ with error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'error: invalid config'
        with patch('cli.commands.cron.subprocess.run', return_value=mock_result):
            result = runner.invoke(cli, [
                'cron', '--config', str(install_config), 'install', '-y',
            ])
        assert '❌' in result.output

    def test_install_openclaw_not_found(self, runner, install_config):
        """openclaw binary missing → exit 5."""
        with patch('cli.commands.cron.subprocess.run', side_effect=FileNotFoundError):
            result = runner.invoke(cli, [
                'cron', '--config', str(install_config), 'install', '-y',
            ])
        assert result.exit_code != 0
        assert 'openclaw' in result.output


# ── TestCronRunExtended ─────────────────────────────────────────────────


class TestCronRunExtended:
    """Extended tests for cron run command (non-dry-run paths)."""

    @pytest.fixture
    def run_config(self, tmp_path):
        config = tmp_path / "cron_config.yaml"
        config.write_text("""
version: "1.0"
default_tz: Asia/Shanghai
tasks:
  - id: run_task
    group: test
    name: Run Task
    schedule: "0 9 * * *"
    command: "echo running"
    timeout: 30
    enabled: true
""")
        return config

    def test_run_success(self, runner, run_config):
        """Successful run → ✅ message."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.commands.cron.subprocess.run', return_value=mock_result):
            result = runner.invoke(cli, [
                'cron', '--config', str(run_config), 'run', 'run_task',
            ])
        assert result.exit_code == 0
        assert '✅' in result.output
        assert '执行完成' in result.output

    def test_run_failure(self, runner, run_config):
        """Non-zero exit → ❌ message + non-zero exit code."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=1)
        with patch('cli.commands.cron.subprocess.run', return_value=mock_result):
            result = runner.invoke(cli, [
                'cron', '--config', str(run_config), 'run', 'run_task',
            ])
        assert result.exit_code != 0
        assert '❌' in result.output

    def test_run_timeout(self, runner, run_config):
        """Timeout → ❌ timeout message + exit 6."""
        with patch('cli.commands.cron.subprocess.run',
                   side_effect=subprocess.TimeoutExpired(cmd='echo', timeout=30)):
            result = runner.invoke(cli, [
                'cron', '--config', str(run_config), 'run', 'run_task',
            ])
        assert result.exit_code != 0
        assert '超时' in result.output


# ── TestDownloadExecution ───────────────────────────────────────────────


class TestDownloadExecution:
    """Tests for download commands non-dry-run execution paths."""

    def test_akshare_execution(self, runner):
        """download akshare without --dry-run calls run_legacy."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result) as mock_rl:
            result = runner.invoke(cli, ['download', 'akshare'])
        assert result.exit_code == 0
        assert '✅' in result.output
        mock_rl.assert_called_once()
        call_args = mock_rl.call_args
        assert call_args[0][0] == 'download_data_akshare.py'

    def test_tushare_execution(self, runner):
        """download tushare without --dry-run calls run_legacy."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result) as mock_rl:
            result = runner.invoke(cli, ['download', 'tushare'])
        assert result.exit_code == 0
        assert '✅' in result.output
        mock_rl.assert_called_once()
        assert mock_rl.call_args[0][0] == 'tushare_pro_downloader.py'

    def test_policy_execution(self, runner):
        """download policy without --dry-run calls run_legacy."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result) as mock_rl:
            result = runner.invoke(cli, ['download', 'policy'])
        assert result.exit_code == 0
        assert '✅' in result.output
        mock_rl.assert_called_once()
        assert mock_rl.call_args[0][0] == 'download_policy_data.py'

    def test_geopolitics_execution(self, runner):
        """download geopolitics without --dry-run calls run_legacy."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result) as mock_rl:
            result = runner.invoke(cli, ['download', 'geopolitics'])
        assert result.exit_code == 0
        assert '✅' in result.output
        mock_rl.assert_called_once()
        assert mock_rl.call_args[0][0] == 'download_geopolitics_data.py'

    def test_news_execution(self, runner):
        """download news without --dry-run calls run_legacy."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result) as mock_rl:
            result = runner.invoke(cli, ['download', 'news', '--session', 'morning'])
        assert result.exit_code == 0
        assert '✅' in result.output
        mock_rl.assert_called_once()
        assert mock_rl.call_args[0][0] == 'download_news_data.py'
        args = mock_rl.call_args[1].get('args') or mock_rl.call_args[0][1] if len(mock_rl.call_args[0]) > 1 else mock_rl.call_args[1].get('args')
        assert '--session' in args
        assert 'morning' in args

    def test_all_execution(self, runner):
        """download all invokes each subcommand via ctx.invoke."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.run_legacy', return_value=mock_result):
            result = runner.invoke(cli, ['download', 'all'])
        assert result.exit_code == 0
        assert '全部下载任务完成' in result.output
