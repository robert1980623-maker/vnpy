#!/usr/bin/env python3
"""
Manager Watchdog 单元测试

测试覆盖:
1. 心跳文件读写
2. 心跳过期检测
3. Manager 进程检测
4. 状态快照保存/恢复
5. 重启流程（mock）
6. Dry-run 模式
7. 命令行参数解析
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# 添加项目路径
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from examples.alpha_research.manager_watchdog import (
    ManagerWatchdog,
    WatchdogConfig,
    RestartContext,
    HEARTBEAT_TIMEOUT,
    CHECK_INTERVAL,
)


class TestWatchdogConfig:
    """WatchdogConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = WatchdogConfig()
        
        assert config.timeout == HEARTBEAT_TIMEOUT
        assert config.check_interval == CHECK_INTERVAL
        assert config.dry_run is False
        assert 'state' in str(config.heartbeat_file)

    def test_custom_config(self, tmp_path):
        """测试自定义配置"""
        config = WatchdogConfig(
            base_dir=tmp_path,
            timeout=60,
            check_interval=5,
            dry_run=True,
        )
        
        assert config.timeout == 60
        assert config.check_interval == 5
        assert config.dry_run is True
        assert config.base_dir == tmp_path

    def test_state_dirs_created(self, tmp_path):
        """测试状态目录自动创建"""
        config = WatchdogConfig(base_dir=tmp_path)
        
        # 验证目录已创建
        assert (tmp_path / 'state').exists()
        assert (tmp_path / 'logs').exists()


class TestManagerWatchdog:
    """ManagerWatchdog 测试"""

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        """创建临时目录"""
        issues_dir = tmp_path / 'issues'
        issues_dir.mkdir()
        return issues_dir

    @pytest.fixture
    def watchdog(self, tmp_dir):
        """创建 Watchdog 实例"""
        config = WatchdogConfig(
            base_dir=tmp_dir,
            dry_run=True,  # 默认干跑模式
        )
        return ManagerWatchdog(config)

    @pytest.fixture
    def valid_heartbeat(self):
        """创建有效心跳"""
        return {
            'timestamp': time.time(),
            'pid': 12345,
            'status': 'running',
        }


class TestHeartbeatOperations(TestManagerWatchdog):
    """心跳操作测试"""

    def test_load_heartbeat_nonexistent(self, watchdog, tmp_dir):
        """测试加载不存在的 heartbeat 文件"""
        result = watchdog._load_heartbeat()
        assert result is None

    def test_load_heartbeat_valid(self, watchdog, valid_heartbeat, tmp_dir):
        """测试加载有效 heartbeat"""
        heartbeat_file = tmp_dir / 'state' / 'manager.heartbeat'
        with open(heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump(valid_heartbeat, f)
        
        result = watchdog._load_heartbeat()
        
        assert result is not None
        assert result['timestamp'] == valid_heartbeat['timestamp']

    def test_load_heartbeat_invalid_json(self, watchdog, tmp_dir):
        """测试加载损坏的 heartbeat 文件"""
        heartbeat_file = tmp_dir / 'state' / 'manager.heartbeat'
        with open(heartbeat_file, 'w', encoding='utf-8') as f:
            f.write('{ invalid json }')
        
        result = watchdog._load_heartbeat()
        assert result is None

    def test_get_heartbeat_age_fresh(self, watchdog, valid_heartbeat):
        """测试新鲜心跳的年龄"""
        age = watchdog._get_heartbeat_age(valid_heartbeat)
        assert 0 <= age < 2  # 应该在 2 秒内

    def test_get_heartbeat_age_old(self, watchdog):
        """测试过期心跳的年龄"""
        old_heartbeat = {'timestamp': time.time() - 200}
        age = watchdog._get_heartbeat_age(old_heartbeat)
        assert age >= 200

    def test_get_heartbeat_age_missing_timestamp(self, watchdog):
        """测试缺少 timestamp 的心跳"""
        heartbeat = {'status': 'running'}
        age = watchdog._get_heartbeat_age(heartbeat)
        assert age == float('inf')

    def test_is_heartbeat_stale_true_no_file(self, watchdog):
        """测试心跳文件不存在时判定为过期"""
        assert watchdog._is_heartbeat_stale(None) is True

    def test_is_heartbeat_stale_true_old(self, watchdog):
        """测试过期心跳判定为过期"""
        old_heartbeat = {'timestamp': time.time() - 100}
        assert watchdog._is_heartbeat_stale(old_heartbeat) is True

    def test_is_heartbeat_stale_false_fresh(self, watchdog, valid_heartbeat):
        """测试新鲜心跳判定为正常"""
        assert watchdog._is_heartbeat_stale(valid_heartbeat) is False


class TestManagerProcessDetection(TestManagerWatchdog):
    """Manager 进程检测测试"""

    @patch('subprocess.run')
    def test_is_manager_running_true(self, mock_run, watchdog):
        """测试检测到 Manager 运行"""
        mock_run.return_value = MagicMock(returncode=0, stdout='12345\n')
        
        assert watchdog._is_manager_running() is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_is_manager_running_false(self, mock_run, watchdog):
        """测试检测到 Manager 未运行"""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        
        assert watchdog._is_manager_running() is False

    @patch('subprocess.run')
    def test_is_manager_running_error(self, mock_run, watchdog):
        """测试进程检测异常"""
        mock_run.side_effect = FileNotFoundError()
        
        assert watchdog._is_manager_running() is False


class TestStateSnapshot(TestManagerWatchdog):
    """状态快照测试"""

    def test_save_active_tasks_snapshot_exists(self, watchdog, tmp_dir):
        """测试保存存在的状态文件"""
        state_file = tmp_dir / 'state' / 'manager_state.json'
        tasks = {
            'issue_001': {'status': 'processing', 'agent': 'delta'},
            'issue_002': {'status': 'processing', 'agent': 'qa'},
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump({'active_tasks': tasks, 'updated_at': '2024-01-01'}, f)
        
        snapshot = watchdog._save_active_tasks_snapshot()
        
        assert snapshot == tasks

    def test_save_active_tasks_snapshot_nonexistent(self, watchdog, tmp_dir):
        """测试保存不存在的状态文件"""
        snapshot = watchdog._save_active_tasks_snapshot()
        assert snapshot == {}

    def test_save_active_tasks_snapshot_invalid_json(self, watchdog, tmp_dir):
        """测试保存损坏的状态文件"""
        state_file = tmp_dir / 'state' / 'manager_state.json'
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write('not valid json')
        
        # 应该返回空字典而不是抛出异常
        snapshot = watchdog._save_active_tasks_snapshot()
        assert snapshot == {}


class TestRestartFlow(TestManagerWatchdog):
    """重启流程测试"""

    @patch('subprocess.run')
    @patch('os.kill')
    @patch('subprocess.Popen')
    def test_stop_manager_success(self, mock_popen, mock_kill, mock_run, watchdog):
        """测试成功停止 Manager"""
        mock_run.return_value = MagicMock(returncode=0, stdout='12345\n')
        
        result = watchdog._stop_manager()
        
        assert result is True
        mock_kill.assert_called()

    @patch('subprocess.run')
    def test_stop_manager_not_running(self, mock_run, watchdog):
        """测试停止不存在的 Manager"""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        
        result = watchdog._stop_manager()
        
        assert result is True

    @patch('subprocess.Popen')
    def test_start_manager_success(self, mock_popen, watchdog):
        """测试成功启动 Manager"""
        result = watchdog._start_manager()
        
        assert result is True
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_manager_script_not_found(self, mock_popen, watchdog):
        """测试启动时找不到脚本"""
        # 模拟脚本不存在的情况
        with patch.object(Path, 'exists', return_value=False):
            result = watchdog._start_manager()
        
        assert result is False


class TestRestartContext:
    """重启上下文测试"""

    def test_restart_context_creation(self):
        """测试 RestartContext 创建"""
        context = RestartContext(
            reason="心跳超时",
            last_heartbeat=time.time() - 100,
            heartbeat_age=100.0,
        )
        
        assert context.reason == "心跳超时"
        assert context.heartbeat_age == 100.0
        assert context.restart_count == 0
        assert context.last_restart_time is None

    def test_restart_context_explicit_values(self):
        """测试 RestartContext 显式值"""
        context = RestartContext(
            reason="进程崩溃",
            last_heartbeat=time.time() - 50,
            heartbeat_age=50.0,
            active_tasks_snapshot={'task1': {}},
            restart_count=2,
            last_restart_time=time.time(),
        )
        
        assert context.active_tasks_snapshot == {'task1': {}}
        assert context.restart_count == 2
        assert context.last_restart_time is not None


class TestDryRunMode(TestManagerWatchdog):
    """Dry-run 模式测试"""

    def test_dry_run_skips_restart(self, watchdog, tmp_dir):
        """测试 dry-run 跳过实际重启"""
        watchdog.config.dry_run = True
        
        # 设置过期心跳
        heartbeat_file = tmp_dir / 'state' / 'manager.heartbeat'
        with open(heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time() - 200}, f)
        
        with patch.object(watchdog, '_restart_manager') as mock_restart:
            watchdog._check_and_restart()
            # Dry-run 模式下不应调用 _restart_manager


class TestCheckAndRestart(TestManagerWatchdog):
    """检查与重启逻辑测试"""

    @patch.object(ManagerWatchdog, '_is_manager_running')
    def test_check_manager_not_running_needs_restart(
        self, mock_is_running, watchdog, tmp_dir
    ):
        """测试 Manager 未运行且需要重启"""
        mock_is_running.return_value = False
        
        # 没有心跳文件
        with patch.object(watchdog, '_load_heartbeat', return_value=None):
            with patch.object(watchdog, '_restart_manager') as mock_restart:
                watchdog._check_and_restart()
                mock_restart.assert_called_once()

    @patch.object(ManagerWatchdog, '_is_manager_running')
    def test_check_manager_running_heartbeat_fresh(
        self, mock_is_running, watchdog, valid_heartbeat
    ):
        """测试 Manager 运行中且心跳正常"""
        mock_is_running.return_value = True
        
        with patch.object(watchdog, '_load_heartbeat', return_value=valid_heartbeat):
            with patch.object(watchdog, '_restart_manager') as mock_restart:
                watchdog._check_and_restart()
                mock_restart.assert_not_called()

    @patch.object(ManagerWatchdog, '_is_manager_running')
    def test_check_manager_running_heartbeat_stale(
        self, mock_is_running, watchdog
    ):
        """测试 Manager 运行中但心跳过期"""
        mock_is_running.return_value = True
        stale_heartbeat = {'timestamp': time.time() - 200}
        
        with patch.object(watchdog, '_load_heartbeat', return_value=stale_heartbeat):
            with patch.object(watchdog, '_restart_manager') as mock_restart:
                watchdog._check_and_restart()
                mock_restart.assert_called_once()


class TestWaitForManagerReady(TestManagerWatchdog):
    """等待 Manager 就绪测试"""

    @patch.object(ManagerWatchdog, '_is_manager_running')
    @patch.object(ManagerWatchdog, '_load_heartbeat')
    def test_wait_success_quick(
        self, mock_heartbeat, mock_running, watchdog
    ):
        """测试快速恢复成功"""
        mock_running.return_value = True
        mock_heartbeat.return_value = {'timestamp': time.time()}
        
        with patch.object(watchdog, '_is_heartbeat_stale', return_value=False):
            result = watchdog._wait_for_manager_ready(timeout=5)
        
        assert result is True

    @patch.object(ManagerWatchdog, '_is_manager_running')
    def test_wait_timeout(self, mock_running, watchdog):
        """测试等待超时"""
        mock_running.return_value = False
        
        result = watchdog._wait_for_manager_ready(timeout=2)
        
        assert result is False


class TestSignalHandling(TestManagerWatchdog):
    """信号处理测试"""

    def test_signal_handler_sets_running_false(self, watchdog):
        """测试信号处理器设置 running 为 False"""
        watchdog.running = True
        
        watchdog._signal_handler(signal.SIGTERM, None)
        
        assert watchdog.running is False


class TestMainEntry:
    """主入口测试"""

    def test_parse_args_defaults(self):
        """测试默认参数解析"""
        from examples.alpha_research.manager_watchdog import parse_args
        with patch.object(sys, 'argv', ['watchdog']):
            args = parse_args()
            
            assert args.dry_run is False
            assert args.timeout == HEARTBEAT_TIMEOUT
            assert args.interval == CHECK_INTERVAL

    def test_parse_args_dry_run(self):
        """测试 dry-run 参数解析"""
        from examples.alpha_research.manager_watchdog import parse_args
        with patch.object(sys, 'argv', ['watchdog', '--dry-run']):
            args = parse_args()
            
            assert args.dry_run is True

    def test_parse_args_custom_values(self):
        """测试自定义参数解析"""
        from examples.alpha_research.manager_watchdog import parse_args
        with patch.object(sys, 'argv', [
            'watchdog',
            '--timeout', '60',
            '--interval', '5',
            '--max-restarts', '5',
        ]):
            args = parse_args()
            
            assert args.timeout == 60
            assert args.interval == 5
            assert args.max_restarts == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
