#!/usr/bin/env python3
"""
熔断器实现

功能:
- 自动熔断故障服务
- 半开状态试探恢复
- 失败计数和恢复超时
"""

import time
import logging
from typing import Callable, Any, Optional
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态 (试探恢复)


class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值，达到后打开熔断
            recovery_timeout: 恢复超时 (秒)
            half_open_max_calls: 半开状态最大尝试次数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_successes = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """带熔断的调用"""
        if self.state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                logger.info("熔断器进入半开状态")
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            
            # 成功调用
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_max_calls:
                    logger.info("熔断器关闭，服务恢复")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            else:
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # 检查是否需要打开熔断
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"熔断器打开：{self.failure_count} 次失败 >= {self.failure_threshold}"
                )
                self.state = CircuitState.OPEN
            
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """装饰器模式"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_successes = 0
    
    def get_state(self) -> dict:
        """获取状态"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time,
            'half_open_successes': self.half_open_successes,
        }


# 装饰器快捷方式
def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> Callable:
    """熔断器装饰器"""
    breaker = CircuitBreaker(failure_threshold, recovery_timeout)
    return lambda func: breaker(func)
