#!/usr/bin/env python3
"""
自动重试工具模块

功能:
- 指数退避重试策略
- 可配置重试次数、延迟、超时
- 重试日志和监控
- 失败告警

用法:
    from retry_utils import retry_with_backoff, RetryMonitor
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0)
    def download_stock(stock_code):
        ...
"""

import time
import logging
import functools
from datetime import datetime
from typing import Callable, Any, Optional, Dict, List, Type
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


# 日志配置
logger = logging.getLogger(__name__)


class RetryStatus(Enum):
    """重试状态枚举"""
    SUCCESS = "success"
    RETRYING = "retrying"
    FAILED = "failed"


@dataclass
class RetryRecord:
    """单次重试记录"""
    attempt: int
    timestamp: str
    status: RetryStatus
    duration: float
    error: Optional[str] = None
    delay_before: float = 0.0


@dataclass
class RetrySession:
    """重试会话（完整重试过程）"""
    func_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    max_retries: int = 3
    records: List[RetryRecord] = field(default_factory=list)
    success: bool = False
    final_error: Optional[str] = None
    exception_type: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'func_name': self.func_name,
            'args': [str(a) for a in self.args],
            'kwargs': self.kwargs,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'max_retries': self.max_retries,
            'total_attempts': len(self.records),
            'success': self.success,
            'final_error': self.final_error,
            'exception_type': self.exception_type,
            'records': [
                {
                    'attempt': r.attempt,
                    'timestamp': r.timestamp,
                    'status': r.status.value,
                    'duration': r.duration,
                    'error': r.error,
                    'delay_before': r.delay_before
                }
                for r in self.records
            ]
        }


class RetryMonitor:
    """重试监控器"""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        初始化监控器
        
        Args:
            log_file: 日志文件路径，默认 None 不写入文件
        """
        self.sessions: List[RetrySession] = []
        self.log_file = Path(log_file) if log_file else None
        self.stats = {
            'total_calls': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_retries': 0
        }
    
    def start_session(self, func_name: str, args: tuple, kwargs: dict, max_retries: int) -> RetrySession:
        """开始新的重试会话"""
        session = RetrySession(
            func_name=func_name,
            args=args,
            kwargs=kwargs,
            start_time=datetime.now().isoformat(),
            max_retries=max_retries
        )
        self.sessions.append(session)
        self.stats['total_calls'] += 1
        return session
    
    def record_attempt(self, session: RetrySession, record: RetryRecord):
        """记录重试尝试"""
        session.records.append(record)
        if record.status == RetryStatus.RETRYING:
            self.stats['total_retries'] += 1
    
    def end_session(self, session: RetrySession, success: bool, error: Optional[str] = None, exception_type: str = ""):
        """结束重试会话"""
        session.end_time = datetime.now().isoformat()
        session.success = success
        session.final_error = error
        session.exception_type = exception_type
        
        if success:
            self.stats['total_success'] += 1
        else:
            self.stats['total_failed'] += 1
        
        # 写入日志文件
        if self.log_file:
            self._write_log(session)
        
        # 失败告警
        if not success:
            self._trigger_alert(session)
    
    def _write_log(self, session: RetrySession):
        """写入日志文件"""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'timestamp': session.end_time,
                'session': session.to_dict()
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"写入重试日志失败：{e}")
    
    def _trigger_alert(self, session: RetrySession):
        """触发失败告警"""
        alert_msg = (
            f"🚨 重试失败告警\n"
            f"函数：{session.func_name}\n"
            f"参数：{session.args}, {session.kwargs}\n"
            f"重试次数：{len(session.records)}/{session.max_retries}\n"
            f"错误：{session.final_error}\n"
            f"异常类型：{session.exception_type}\n"
            f"时间：{session.end_time}"
        )
        logger.error(alert_msg)
        
        # 可以扩展：发送邮件、短信、Webhook 等
        # send_alert(alert_msg)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def get_recent_failures(self, limit: int = 10) -> List[dict]:
        """获取最近的失败记录"""
        failures = [
            s.to_dict() for s in self.sessions
            if not s.success
        ]
        return failures[-limit:]
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("重试监控统计")
        logger.info("=" * 60)
        logger.info(f"总调用次数：{stats['total_calls']}")
        logger.info(f"成功次数：{stats['total_success']}")
        logger.info(f"失败次数：{stats['total_failed']}")
        logger.info(f"总重试次数：{stats['total_retries']}")
        
        if stats['total_calls'] > 0:
            success_rate = stats['total_success'] / stats['total_calls'] * 100
            logger.info(f"成功率：{success_rate:.1f}%")
        
        logger.info("=" * 60)


# 全局监控器实例
_global_monitor: Optional[RetryMonitor] = None


def get_retry_monitor(log_file: Optional[str] = None) -> RetryMonitor:
    """获取全局重试监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = RetryMonitor(log_file=log_file)
    return _global_monitor


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    jitter: bool = True
) -> float:
    """
    计算退避延迟
    
    Args:
        attempt: 当前尝试次数（从 1 开始）
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential: 是否使用指数退避
        jitter: 是否添加随机抖动
    
    Returns:
        float: 延迟时间（秒）
    """
    import random
    
    if exponential:
        # 指数退避：base_delay * 2^(attempt-1)
        delay = base_delay * (2 ** (attempt - 1))
    else:
        # 线性退避
        delay = base_delay * attempt
    
    # 限制最大延迟
    delay = min(delay, max_delay)
    
    # 添加随机抖动（避免多个请求同时重试）
    if jitter:
        jitter_factor = random.uniform(0.5, 1.0)
        delay *= jitter_factor
    
    return round(delay, 2)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    timeout: Optional[float] = None,
    exceptions: tuple = (Exception,),
    log_file: Optional[str] = None,
    alert_on_failure: bool = True
):
    """
    带指数退避的重试装饰器
    
    Args:
        max_retries: 最大重试次数（默认 3 次）
        base_delay: 基础延迟秒数（默认 1.0 秒）
        max_delay: 最大延迟秒数（默认 60 秒）
        timeout: 单次调用超时（秒），None 表示不限制
        exceptions: 需要捕获的异常类型元组
        log_file: 日志文件路径
        alert_on_failure: 失败时是否告警
    
    Returns:
        装饰器函数
    
    用法:
        @retry_with_backoff(max_retries=3, base_delay=2.0)
        def download_stock(stock_code):
            ...
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitor = get_retry_monitor(log_file)
            session = monitor.start_session(func.__name__, args, kwargs, max_retries)
            
            last_error: Optional[BaseException] = None
            last_error_str: str = ""
            start_time = time.time()
            
            for attempt in range(1, max_retries + 1):
                attempt_start = time.time()
                delay_before = 0.0
                
                # 计算重试前的延迟（从第 2 次尝试开始）
                if attempt > 1:
                    delay_before = calculate_backoff_delay(
                        attempt - 1, base_delay, max_delay
                    )
                    logger.info(f"⏳ 等待 {delay_before}秒后重试 (第 {attempt}/{max_retries} 次)")
                    time.sleep(delay_before)
                
                try:
                    # 执行函数（带超时）
                    if timeout:
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError(f"函数执行超时 ({timeout}秒)")
                        
                        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(int(timeout))
                        
                        try:
                            result = func(*args, **kwargs)
                        finally:
                            signal.alarm(0)
                            signal.signal(signal.SIGALRM, old_handler)
                    else:
                        result = func(*args, **kwargs)
                    
                    # 成功
                    duration = time.time() - attempt_start
                    record = RetryRecord(
                        attempt=attempt,
                        timestamp=datetime.now().isoformat(),
                        status=RetryStatus.SUCCESS,
                        duration=duration,
                        delay_before=delay_before
                    )
                    monitor.record_attempt(session, record)
                    
                    logger.info(f"✅ {func.__name__} 成功 (尝试 {attempt}/{max_retries}, 耗时 {duration:.2f}秒)")
                    
                    monitor.end_session(session, success=True)
                    return result
                
                except exceptions as e:
                    duration = time.time() - attempt_start
                    last_error = e
                    last_error_str = str(e)
                    
                    record = RetryRecord(
                        attempt=attempt,
                        timestamp=datetime.now().isoformat(),
                        status=RetryStatus.RETRYING if attempt < max_retries else RetryStatus.FAILED,
                        duration=duration,
                        error=last_error_str,
                        delay_before=delay_before
                    )
                    monitor.record_attempt(session, record)
                    
                    if attempt < max_retries:
                        logger.warning(f"⚠️ {func.__name__} 失败 (尝试 {attempt}/{max_retries}): {last_error_str}")
                    else:
                        logger.error(f"❌ {func.__name__} 最终失败 (共 {max_retries} 次尝试): {last_error_str}")
            
            # 所有重试都失败
            monitor.end_session(
                session, 
                success=False, 
                error=last_error_str,
                exception_type=type(last_error).__name__ if last_error else "Unknown"
            )
            
            # 抛出最后一次异常（保持原异常类型）
            if last_error:
                raise last_error
            else:
                raise Exception("重试失败")
        
        return wrapper
    return decorator


def retry_function(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    timeout: Optional[float] = None,
    exceptions: tuple = (Exception,),
    log_file: Optional[str] = None,
    **kwargs
) -> Any:
    """
    直接重试函数（不使用装饰器）
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        max_retries: 最大重试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        timeout: 超时时间
        exceptions: 捕获的异常类型
        log_file: 日志文件
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果
    """
    monitor = get_retry_monitor(log_file)
    session = monitor.start_session(func.__name__, args, kwargs, max_retries)
    
    last_error: Optional[BaseException] = None
    last_error_str: str = ""
    
    for attempt in range(1, max_retries + 1):
        attempt_start = time.time()
        delay_before = 0.0
        
        if attempt > 1:
            delay_before = calculate_backoff_delay(attempt - 1, base_delay, max_delay)
            logger.info(f"⏳ 等待 {delay_before}秒后重试 (第 {attempt}/{max_retries} 次)")
            time.sleep(delay_before)
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - attempt_start
            
            record = RetryRecord(
                attempt=attempt,
                timestamp=datetime.now().isoformat(),
                status=RetryStatus.SUCCESS,
                duration=duration,
                delay_before=delay_before
            )
            monitor.record_attempt(session, record)
            
            logger.info(f"✅ {func.__name__} 成功 (尝试 {attempt}/{max_retries}, 耗时 {duration:.2f}秒)")
            monitor.end_session(session, success=True)
            return result
        
        except exceptions as e:
            duration = time.time() - attempt_start
            last_error = e
            last_error_str = str(e)
            
            record = RetryRecord(
                attempt=attempt,
                timestamp=datetime.now().isoformat(),
                status=RetryStatus.RETRYING if attempt < max_retries else RetryStatus.FAILED,
                duration=duration,
                error=last_error_str,
                delay_before=delay_before
            )
            monitor.record_attempt(session, record)
            
            if attempt < max_retries:
                logger.warning(f"⚠️ {func.__name__} 失败 (尝试 {attempt}/{max_retries}): {last_error_str}")
            else:
                logger.error(f"❌ {func.__name__} 最终失败：{last_error_str}")
    
    monitor.end_session(
        session, 
        success=False, 
        error=last_error_str,
        exception_type=type(last_error).__name__ if last_error else "Unknown"
    )
    
    # 抛出最后一次异常
    if last_error:
        raise last_error
    else:
        raise Exception("重试失败")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("重试工具模块测试")
    print("=" * 60)
    
    # 测试 1: 装饰器方式
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def test_func_success(x):
        print(f"执行 test_func_success({x})")
        return x * 2
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def test_func_fail():
        print("执行 test_func_fail (总是失败)")
        raise ValueError("故意失败")
    
    print("\n--- 测试 1: 成功的情况 ---")
    result = test_func_success(5)
    print(f"结果：{result}")
    
    print("\n--- 测试 2: 失败的情况 ---")
    try:
        test_func_fail()
    except Exception as e:
        print(f"捕获异常：{type(e).__name__}: {e}")
    
    print("\n--- 测试 3: 监控统计 ---")
    monitor = get_retry_monitor()
    monitor.print_stats()
    
    print("\n✅ 所有测试完成")
