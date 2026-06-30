#!/usr/bin/env python3
"""
Manager Watchdog - 自动重启机制

功能:
- 定期检测 Manager 心跳状态
- 心跳超时后自动重启 Manager
- 保存/恢复 active_tasks 状态
- 支持 dry-run 模式
- 记录重启日志

心跳文件: state/manager.heartbeat
超时阈值: 90 秒 (与 Manager.HEARTBEAT_TIMEOUT 保持一致)
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# ========== 配置常量 ==========
HEARTBEAT_TIMEOUT = 90  # 秒，与 QuantManager.HEARTBEAT_TIMEOUT 保持一致
CHECK_INTERVAL = 10     # 秒，检测间隔
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 30   # 秒，重启冷却时间
LOG_FILE = "logs/watchdog.log"


@dataclass
class WatchdogConfig:
    """Watchdog 配置"""
    base_dir: Path = Path("./issues")
    heartbeat_file: Path = field(init=False)
    state_file: Path = field(init=False)
    check_interval: int = CHECK_INTERVAL
    timeout: int = HEARTBEAT_TIMEOUT
    max_restart_attempts: int = MAX_RESTART_ATTEMPTS
    restart_cooldown: int = RESTART_COOLDOWN
    dry_run: bool = False
    log_file: Path = field(init=False)

    def __post_init__(self):
        state_dir = self.base_dir / 'state'
        state_dir.mkdir(parents=True, exist_ok=True)
        self.heartbeat_file = state_dir / 'manager.heartbeat'
        self.state_file = state_dir / 'manager_state.json'
        logs_dir = self.base_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = logs_dir / 'watchdog.log'


@dataclass
class RestartContext:
    """重启上下文"""
    reason: str
    last_heartbeat: Optional[Union[float, str]] = None
    heartbeat_age: float = 0.0
    active_tasks_snapshot: Dict = field(default_factory=dict)
    restart_count: int = 0
    last_restart_time: Optional[float] = None


class ManagerWatchdog:
    """
    Manager Watchdog - 独立于 Manager 运行的监控进程

    职责:
    1. 定期检测心跳文件状态
    2. 心跳超时后执行优雅重启
    3. 保存/恢复 active_tasks 状态
    4. 验证 Manager 重启成功
    """

    def __init__(self, config: Optional[WatchdogConfig] = None):
        self.config = config or WatchdogConfig()
        self.logger = self._setup_logger()
        self.running = False
        self.restart_count = 0
        self._current_context: Optional[RestartContext] = None

    def _setup_logger(self) -> logging.Logger:
        """配置日志"""
        logger = logging.getLogger('ManagerWatchdog')
        logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if logger.handlers:
            return logger

        # 文件 handler
        file_handler = logging.FileHandler(
            self.config.log_file,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)

        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_fmt = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_fmt)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _load_heartbeat(self) -> Optional[Dict]:
        """加载心跳文件"""
        if not self.config.heartbeat_file.exists():
            return None
        try:
            with open(self.config.heartbeat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"心跳文件读取失败: {e}")
            return None

    def _parse_timestamp(self, timestamp: Union[float, str]) -> float:
        """解析时间戳，支持 Unix 时间戳或 ISO 格式字符串"""
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        # ISO 格式字符串
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return 0.0

    def _get_heartbeat_age(self, heartbeat: Dict) -> float:
        """计算心跳年龄（秒）"""
        timestamp = heartbeat.get('timestamp')
        if timestamp is None:
            return float('inf')
        
        ts = self._parse_timestamp(timestamp)
        if ts <= 0:
            return float('inf')
        
        return time.time() - ts

    def _is_heartbeat_stale(self, heartbeat: Optional[Dict]) -> bool:
        """检查心跳是否过期"""
        if heartbeat is None:
            return True
        return self._get_heartbeat_age(heartbeat) > self.config.timeout

    def _is_manager_running(self) -> bool:
        """检查 Manager 进程是否运行"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'manager_interface.py'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _save_active_tasks_snapshot(self) -> Dict:
        """保存 active_tasks 快照"""
        snapshot = {}
        if self.config.state_file.exists():
            try:
                with open(self.config.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    snapshot = state.get('active_tasks', {})
                    self.logger.info(f"已保存 active_tasks 快照: {len(snapshot)} 个任务")
            except (json.JSONDecodeError, OSError) as e:
                self.logger.warning(f"状态文件读取失败，跳过快照: {e}")
        return snapshot

    def _wait_for_manager_ready(self, timeout: int = 30) -> bool:
        """等待 Manager 启动并恢复正常"""
        self.logger.info("等待 Manager 恢复正常...")
        start = time.time()
        
        while time.time() - start < timeout:
            # 检查进程是否运行
            if not self._is_manager_running():
                time.sleep(1)
                continue
            
            # 检查心跳是否正常
            heartbeat = self._load_heartbeat()
            if heartbeat and not self._is_heartbeat_stale(heartbeat):
                self.logger.info("✅ Manager 已恢复正常运行")
                return True
            
            time.sleep(2)
        
        self.logger.warning("⚠️ Manager 恢复验证超时")
        return False

    def _stop_manager(self) -> bool:
        """停止 Manager 进程"""
        self.logger.info("正在停止 Manager 进程...")
        
        try:
            # 查找 Manager 进程
            result = subprocess.run(
                ['pgrep', '-f', 'manager_interface.py'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.info("Manager 进程未运行")
                return True
            
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        self.logger.info(f"已发送 SIGTERM 到进程 {pid}")
                    except (ProcessLookupError, ValueError) as e:
                        self.logger.warning(f"进程 {pid} 不存在或已停止: {e}")
            
            # 等待进程退出
            time.sleep(2)
            
            # 如果还在运行，强制杀死
            if self._is_manager_running():
                self.logger.warning("进程未响应 SIGTERM，发送 SIGKILL")
                subprocess.run(
                    ['pkill', '-9', '-f', 'manager_interface.py'],
                    capture_output=True
                )
                time.sleep(1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"停止 Manager 失败: {e}")
            return False

    def _start_manager(self) -> bool:
        """启动 Manager 进程"""
        self.logger.info("正在启动 Manager...")
        
        try:
            # 查找 manager_interface.py 的绝对路径
            script_path = Path(__file__).parent / 'manager_interface.py'
            if not script_path.exists():
                script_path = Path(self.config.base_dir).parent / 'manager_interface.py'
            
            if not script_path.exists():
                self.logger.error(f"找不到 manager_interface.py: {script_path}")
                return False
            
            # 启动 Manager（后台运行）
            subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            self.logger.info(f"Manager 启动命令已执行: {script_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动 Manager 失败: {e}")
            return False

    def _restart_manager(self) -> bool:
        """执行 Manager 重启"""
        context = self._current_context
        
        self.logger.info("=" * 50)
        self.logger.info("开始执行 Manager 重启")
        self.logger.info(f"重启原因: {context.reason if context else '未知'}")
        self.logger.info(f"心跳年龄: {context.heartbeat_age:.1f}s" if context else "N/A")
        self.logger.info(f"活跃任务数: {len(context.active_tasks_snapshot) if context else 0}")
        self.logger.info("=" * 50)

        if self.config.dry_run:
            self.logger.info("[DRY-RUN] 跳过实际重启")
            return True

        # 检查重启冷却
        if context and context.last_restart_time:
            elapsed = time.time() - context.last_restart_time
            if elapsed < self.config.restart_cooldown:
                self.logger.warning(
                    f"重启冷却中 (剩余 {self.config.restart_cooldown - elapsed:.1f}s)，跳过本次重启"
                )
                return False

        # 保存状态快照
        context.active_tasks_snapshot = self._save_active_tasks_snapshot()

        # 停止 Manager
        if not self._stop_manager():
            self.logger.error("停止 Manager 失败，放弃重启")
            return False

        # 启动 Manager
        if not self._start_manager():
            self.logger.error("启动 Manager 失败")
            return False

        # 更新重启计数
        self.restart_count += 1
        if context:
            context.restart_count = self.restart_count
            context.last_restart_time = time.time()

        # 验证恢复
        if not self._wait_for_manager_ready():
            self.logger.warning("Manager 恢复验证失败，但重启流程已完成")
        
        self.logger.info(f"✅ Manager 重启完成 (第 {self.restart_count} 次)")
        return True

    def _check_and_restart(self) -> None:
        """检查心跳并执行重启"""
        heartbeat = self._load_heartbeat()
        heartbeat_age = self._get_heartbeat_age(heartbeat) if heartbeat else float('inf')
        is_running = self._is_manager_running()
        
        # 构建上下文
        self._current_context = RestartContext(
            reason="",
            last_heartbeat=heartbeat.get('timestamp') if heartbeat else None,
            heartbeat_age=heartbeat_age,
        )

        # 判断状态
        if not is_running:
            self._current_context.reason = "Manager 进程未运行"
            self.logger.warning("⚠️ Manager 进程未运行")
            
            if heartbeat and not self._is_heartbeat_stale(heartbeat):
                # 进程不存在但心跳正常，可能是进程名检测问题
                self.logger.info("心跳正常但进程检测失败，跳过重启")
                return
            
            # 无心跳或心跳过期，需要重启
            if self.restart_count < self.config.max_restart_attempts:
                self._restart_manager()
            else:
                self.logger.error(
                    f"已达到最大重启次数 ({self.config.max_restart_attempts})，停止重启"
                )
            return

        # 进程运行中，检查心跳
        if self._is_heartbeat_stale(heartbeat):
            self._current_context.reason = f"心跳超时 (年龄: {heartbeat_age:.1f}s > {self.config.timeout}s)"
            self.logger.warning(
                f"⚠️ Manager 心跳超时: {heartbeat_age:.1f}s > {self.config.timeout}s"
            )
            
            if self.restart_count < self.config.max_restart_attempts:
                self._restart_manager()
            else:
                self.logger.error(
                    f"已达到最大重启次数 ({self.config.max_restart_attempts})，停止重启"
                )
        else:
            self.logger.debug(f"❤️ Manager 心跳正常: {heartbeat_age:.1f}s")

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        self.logger.info(f"收到信号 {signum}，准备退出...")
        self.running = False

    def run(self) -> None:
        """运行 Watchdog 主循环"""
        self.running = True
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("=" * 60)
        self.logger.info("Manager Watchdog 启动")
        self.logger.info(f"心跳文件: {self.config.heartbeat_file}")
        self.logger.info(f"超时阈值: {self.config.timeout}s")
        self.logger.info(f"检测间隔: {self.config.check_interval}s")
        self.logger.info(f"Dry-run 模式: {self.config.dry_run}")
        self.logger.info("=" * 60)

        try:
            while self.running:
                self._check_and_restart()
                time.sleep(self.config.check_interval)
        except Exception as e:
            self.logger.error(f"Watchdog 异常退出: {e}")
            raise
        finally:
            self.logger.info("Watchdog 已停止")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Manager Watchdog - 自动重启监控',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                     # 启动 watchdog
  %(prog)s --dry-run           # 干跑模式（只检测不重启）
  %(prog)s --timeout 60        # 设置超时为 60 秒
  %(prog)s --interval 5       # 设置检测间隔为 5 秒
  %(prog)s --base-dir ./issues # 指定 issues 目录
        """
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='干跑模式：只检测不重启'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=HEARTBEAT_TIMEOUT,
        help=f'心跳超时阈值（秒），默认 {HEARTBEAT_TIMEOUT}'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=CHECK_INTERVAL,
        help=f'检测间隔（秒），默认 {CHECK_INTERVAL}'
    )
    parser.add_argument(
        '--base-dir', '-d',
        type=str,
        default='./issues',
        help='issues 目录路径，默认 ./issues'
    )
    parser.add_argument(
        '--max-restarts', '-m',
        type=int,
        default=MAX_RESTART_ATTEMPTS,
        help=f'最大重启次数，默认 {MAX_RESTART_ATTEMPTS}'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='单次检测后退出（用于 cron 调度）'
    )
    
    return parser.parse_args()


def main():
    """主入口"""
    args = parse_args()
    
    config = WatchdogConfig(
        base_dir=Path(args.base_dir),
        check_interval=args.interval,
        timeout=args.timeout,
        max_restart_attempts=args.max_restarts,
        dry_run=args.dry_run,
    )
    
    watchdog = ManagerWatchdog(config)
    
    if args.once:
        # 单次检测模式（用于 cron 调度）
        heartbeat = watchdog._load_heartbeat()
        is_running = watchdog._is_manager_running()
        heartbeat_age = watchdog._get_heartbeat_age(heartbeat) if heartbeat else float('inf')
        is_stale = watchdog._is_heartbeat_stale(heartbeat)
        
        print(f"Manager 运行状态: {'是' if is_running else '否'}")
        print(f"心跳年龄: {heartbeat_age:.1f}s")
        print(f"心跳状态: {'正常' if not is_stale else '超时'}")
        
        if (is_stale or not is_running) and not args.dry_run:
            print("触发重启...")
            context = RestartContext(
                reason="单次检测触发重启",
                last_heartbeat=heartbeat.get('timestamp') if heartbeat else None,
                heartbeat_age=heartbeat_age,
            )
            watchdog._current_context = context
            watchdog._restart_manager()
            print(f"重启完成: {'成功' if context.last_restart_time else '失败'}")
        elif args.dry_run:
            print("[DRY-RUN] 跳过实际重启")
    else:
        # 持续运行模式
        watchdog.run()


if __name__ == '__main__':
    main()
