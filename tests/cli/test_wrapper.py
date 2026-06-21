"""Tests for cli/utils/wrapper.py — legacy script execution bridge."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.utils.errors import DependencyError
from cli.utils.wrapper import (
    LEGACY_SCRIPTS_DIR,
    legacy_command,
    run_legacy,
    run_legacy_import,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_scripts_dir(tmp_path):
    """Create a temporary directory with a fake legacy script."""
    script = tmp_path / "test_script.py"
    script.write_text("print('hello from legacy')\n")
    return tmp_path


# ── TestRunLegacy ────────────────────────────────────────────────────────


class TestRunLegacy:
    """Tests for run_legacy() function."""

    def test_run_legacy_success(self, fake_scripts_dir):
        """Successful subprocess execution returns CompletedProcess."""
        mock_result = subprocess.CompletedProcess(
            args=['python', 'test_script.py'], returncode=0,
        )
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result) as mock_run, \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='trace-123'):
            result = run_legacy('test_script.py', args=['--foo', 'bar'])

        assert result.returncode == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        cmd = call_kwargs[0][0]
        assert 'test_script.py' in cmd[-2] or 'test_script.py' in ' '.join(cmd)
        assert '--foo' in cmd
        assert 'bar' in cmd

    def test_run_legacy_failure(self, fake_scripts_dir):
        """Non-zero exit code raises DependencyError when check=True."""
        mock_result = subprocess.CompletedProcess(
            args=['python', 'test_script.py'], returncode=1,
        )
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='trace-123'):
            with pytest.raises(DependencyError, match='failed with exit code 1'):
                run_legacy('test_script.py')

    def test_run_legacy_check_false(self, fake_scripts_dir):
        """Non-zero exit code does NOT raise when check=False."""
        mock_result = subprocess.CompletedProcess(
            args=['python', 'test_script.py'], returncode=2,
        )
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='trace-123'):
            result = run_legacy('test_script.py', check=False)

        assert result.returncode == 2

    def test_run_legacy_not_found(self, tmp_path):
        """Missing script raises DependencyError before subprocess."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', tmp_path):
            with pytest.raises(DependencyError, match='Legacy script not found'):
                run_legacy('nonexistent.py')

    def test_run_legacy_with_args(self, fake_scripts_dir):
        """Args are appended to the command list."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result) as mock_run, \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='t'):
            run_legacy('test_script.py', args=['--end', '2026-06-21', '--max', '10'])

        cmd = mock_run.call_args[0][0]
        assert '--end' in cmd
        assert '2026-06-21' in cmd
        assert '--max' in cmd
        assert '10' in cmd

    def test_run_legacy_with_env(self, fake_scripts_dir):
        """Custom env vars are merged; TRACEPARENT is always set."""
        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result) as mock_run, \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='trace-abc'):
            run_legacy('test_script.py', env={'MY_VAR': 'hello'})

        run_env = mock_run.call_args[1]['env']
        assert run_env['MY_VAR'] == 'hello'
        assert run_env['TRACEPARENT'] == 'trace-abc'

    def test_run_legacy_file_not_found(self, fake_scripts_dir):
        """FileNotFoundError from subprocess → DependencyError."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', side_effect=FileNotFoundError('python not found')), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='t'):
            with pytest.raises(DependencyError, match='Failed to execute'):
                run_legacy('test_script.py')

    def test_run_legacy_unexpected_error(self, fake_scripts_dir):
        """Generic exception from subprocess → DependencyError."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', side_effect=OSError('disk full')), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='t'):
            with pytest.raises(DependencyError, match='Unexpected error'):
                run_legacy('test_script.py')


# ── TestRunLegacyImport ──────────────────────────────────────────────────


class TestRunLegacyImport:
    """Tests for run_legacy_import() function."""

    def test_run_legacy_import_success(self, fake_scripts_dir):
        """Successful import returns module globals dict."""
        fake_globals = {'__name__': '__main__', 'result': 42}
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.runpy.run_path', return_value=fake_globals):
            result = run_legacy_import('test_script.py')

        assert result == fake_globals

    def test_run_legacy_import_not_found(self, tmp_path):
        """Missing script raises DependencyError."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', tmp_path):
            with pytest.raises(DependencyError, match='Legacy script not found'):
                run_legacy_import('nonexistent.py')

    def test_run_legacy_import_system_exit_error(self, fake_scripts_dir):
        """SystemExit with non-zero code raises DependencyError."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.runpy.run_path', side_effect=SystemExit(1)):
            with pytest.raises(DependencyError, match='exited with code 1'):
                run_legacy_import('test_script.py')

    def test_run_legacy_import_system_exit_zero(self, fake_scripts_dir):
        """SystemExit(0) returns empty dict (clean exit)."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.runpy.run_path', side_effect=SystemExit(0)):
            result = run_legacy_import('test_script.py')

        assert result == {}

    def test_run_legacy_import_exception(self, fake_scripts_dir):
        """Generic exception from runpy → DependencyError."""
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.runpy.run_path', side_effect=RuntimeError('boom')):
            with pytest.raises(DependencyError, match='Failed to import'):
                run_legacy_import('test_script.py')


# ── TestLegacyCommand ────────────────────────────────────────────────────


class TestLegacyCommand:
    """Tests for @legacy_command decorator."""

    def test_legacy_command_creates_click_command(self):
        """Decorator produces a Click command with correct name and help."""
        @legacy_command('my_script.py', help_text='My help')
        def my_test_func(**kwargs):
            pass

        assert hasattr(my_test_func, 'callback')
        assert my_test_func.__name__ == 'my_test_func'
        # help_text goes to Click's help param, not __doc__
        assert my_test_func.help == 'My help'

    def test_legacy_command_invocation(self, fake_scripts_dir, runner):
        """Invoking the command calls run_legacy with correct args."""
        @legacy_command('test_script.py', help_text='test')
        def test_cmd(**kwargs):
            pass

        mock_result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', return_value=mock_result), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='t'):
            result = runner.invoke(test_cmd, [])

        assert result.exit_code == 0

    def test_legacy_command_failure(self, fake_scripts_dir, runner):
        """DependencyError → ctx.fail() → non-zero exit."""
        @legacy_command('test_script.py', help_text='test')
        def test_cmd(**kwargs):
            pass

        with patch('cli.utils.wrapper.LEGACY_SCRIPTS_DIR', fake_scripts_dir), \
             patch('cli.utils.wrapper.subprocess.run', side_effect=FileNotFoundError('no python')), \
             patch('cli.utils.wrapper.get_current_trace_id', return_value='t'):
            result = runner.invoke(test_cmd, [])

        assert result.exit_code != 0
