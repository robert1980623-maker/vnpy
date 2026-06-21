"""Tests for CLI utilities: logging, config, errors."""
import json
import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.utils.errors import (
    CLIError, ConfigError, ValidationError, DependencyError,
    TimeoutError, CircuitBreakerError, handle_error,
    EXIT_GENERAL_ERROR, EXIT_CONFIG_ERROR, EXIT_VALIDATION_ERROR,
    EXIT_DEPENDENCY_ERROR, EXIT_TIMEOUT, EXIT_CIRCUIT_BREAKER,
)
from cli.utils.logging import (
    new_trace_id, get_current_trace_id, set_trace_id,
    JSONFormatter, TextFormatter, setup_logging,
)
from cli.utils.config import (
    load_cli_config, load_cron_config, DEFAULT_CONFIG, _deep_merge,
    _resolve_env_vars,
)


# ==================== errors ====================

class TestErrors:
    def test_cli_error_defaults(self):
        e = CLIError("test error")
        assert str(e) == "test error"
        assert e.exit_code == EXIT_GENERAL_ERROR
        assert e.details == {}

    def test_cli_error_with_details(self):
        e = CLIError("msg", details={"key": "value"})
        assert e.details == {"key": "value"}

    def test_config_error_exit_code(self):
        assert ConfigError.exit_code == EXIT_CONFIG_ERROR

    def test_validation_error_exit_code(self):
        assert ValidationError.exit_code == EXIT_VALIDATION_ERROR

    def test_dependency_error_exit_code(self):
        assert DependencyError.exit_code == EXIT_DEPENDENCY_ERROR

    def test_timeout_error_exit_code(self):
        assert TimeoutError.exit_code == EXIT_TIMEOUT

    def test_circuit_breaker_error_exit_code(self):
        assert CircuitBreakerError.exit_code == EXIT_CIRCUIT_BREAKER

    def test_handle_error_cli_error(self):
        e = ConfigError("bad config")
        assert handle_error(e) == EXIT_CONFIG_ERROR

    def test_handle_error_generic(self):
        e = RuntimeError("unexpected")
        assert handle_error(e) == EXIT_GENERAL_ERROR

    def test_handle_error_keyboard_interrupt(self):
        e = KeyboardInterrupt()
        assert handle_error(e) == 130


# ==================== logging ====================

class TestLogging:
    def test_new_trace_id_format(self):
        tid = new_trace_id()
        assert len(tid) == 16
        assert all(c in '0123456789abcdef' for c in tid)

    def test_set_and_get_trace_id(self):
        tid = "abcd1234ef567890"
        set_trace_id(tid)
        assert get_current_trace_id() == tid
        assert os.environ.get('TRACEPARENT') == tid

    def test_trace_id_from_env(self):
        os.environ['TRACEPARENT'] = 'env_trace_1234567'
        try:
            # Clear context var
            from cli.utils.logging import _trace_id_var
            token = _trace_id_var.set(None)
            try:
                tid = get_current_trace_id()
                assert tid == 'env_trace_1234567'
            finally:
                _trace_id_var.reset(token)
        finally:
            del os.environ['TRACEPARENT']

    def test_json_formatter(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='hello world', args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data['message'] == 'hello world'
        assert data['level'] == 'INFO'
        assert data['logger'] == 'test'
        assert 'trace_id' in data

    def test_text_formatter(self):
        formatter = TextFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='hello', args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert 'INFO' in output
        assert 'hello' in output

    def test_setup_logging_text(self):
        setup_logging(level='DEBUG', fmt='text')
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) >= 1

    def test_setup_logging_json(self):
        setup_logging(level='INFO', fmt='json')
        root = logging.getLogger()
        assert isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_setup_logging_with_trace_id(self):
        setup_logging(level='INFO', fmt='text', trace_id='custom_trace')
        assert get_current_trace_id() == 'custom_trace'


# ==================== config ====================

class TestConfig:
    def test_deep_merge_simple(self):
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = _deep_merge(base, override)
        assert result == {'a': 1, 'b': 3, 'c': 4}

    def test_deep_merge_nested(self):
        base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        override = {'a': {'y': 99, 'z': 100}}
        result = _deep_merge(base, override)
        assert result == {'a': {'x': 1, 'y': 99, 'z': 100}, 'b': 3}

    def test_resolve_env_vars_string(self):
        os.environ['TEST_VAR_XYZ'] = 'hello'
        try:
            assert _resolve_env_vars('${TEST_VAR_XYZ}') == 'hello'
        finally:
            del os.environ['TEST_VAR_XYZ']

    def test_resolve_env_vars_missing(self):
        result = _resolve_env_vars('${NONEXISTENT_VAR_12345}')
        assert result == '${NONEXISTENT_VAR_12345}'

    def test_resolve_env_vars_dict(self):
        os.environ['TEST_A'] = 'val_a'
        try:
            result = _resolve_env_vars({'key': '${TEST_A}'})
            assert result == {'key': 'val_a'}
        finally:
            del os.environ['TEST_A']

    def test_resolve_env_vars_list(self):
        os.environ['TEST_B'] = 'val_b'
        try:
            result = _resolve_env_vars(['${TEST_B}', 'literal'])
            assert result == ['val_b', 'literal']
        finally:
            del os.environ['TEST_B']

    def test_load_cli_config_defaults(self):
        """Test loading defaults when no config file exists."""
        with patch('cli.utils.config.DEFAULT_CONFIG_PATHS', []):
            config = load_cli_config()
        assert 'log' in config
        assert 'runtime' in config
        assert config['log']['level'] == 'INFO'

    def test_load_cli_config_from_file(self, tmp_path):
        """Test loading config from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
log:
  level: DEBUG
  format: json
runtime:
  default_timeout: 300
""")
        config = load_cli_config(str(config_file))
        assert config['log']['level'] == 'DEBUG'
        assert config['log']['format'] == 'json'
        assert config['runtime']['default_timeout'] == 300

    def test_load_cli_config_bad_yaml(self, tmp_path):
        """Test error on invalid YAML."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(":\n  invalid: yaml: [")
        with pytest.raises(ConfigError):
            load_cli_config(str(config_file))

    def test_load_cron_config_not_found(self):
        """Test error when cron config is missing."""
        with patch('cli.utils.config.Path.exists', return_value=False):
            with pytest.raises(ConfigError):
                load_cron_config('/nonexistent/path.yaml')

    def test_load_cron_config_success(self, tmp_path):
        """Test loading valid cron config."""
        config_file = tmp_path / "cron.yaml"
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
        config = load_cron_config(str(config_file))
        assert config['version'] == '1.0'
        assert len(config['tasks']) == 1
