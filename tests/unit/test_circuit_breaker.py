#!/usr/bin/env python3
"""
core/circuit_breaker.py 单元测试

覆盖:
- CircuitState 枚举值正确性
- CircuitBreaker 初始化参数（默认值 & 自定义值）
- CLOSED 状态：成功调用重置 failure_count
- 连续失败触发熔断：failure_count >= threshold → OPEN
- OPEN 状态拒绝调用：抛出 CircuitBreakerError
- recovery_timeout 后进入 HALF_OPEN
- HALF_OPEN 成功调用达到 half_open_max_calls 后恢复 CLOSED
- HALF_OPEN 失败后回到 OPEN
- reset() 方法重置所有状态
- get_state() 返回正确字典
- 装饰器模式 @circuit_breaker() 正常工作
"""

import time
import pytest
from unittest.mock import patch

from core.circuit_breaker import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerError,
    circuit_breaker,
)


# ---------------------------------------------------------------------------
# CircuitState 枚举
# ---------------------------------------------------------------------------
class TestCircuitState:
    """CircuitState 枚举测试"""

    def test_enum_values(self):
        """枚举值应为预期的字符串"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_enum_members_count(self):
        """枚举应恰好包含 3 个成员"""
        assert len(CircuitState) == 3


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------
class TestCircuitBreakerInit:
    """CircuitBreaker 初始化测试"""

    def test_default_parameters(self):
        """默认参数应正确设置"""
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.half_open_max_calls == 3

    def test_custom_parameters(self):
        """自定义参数应正确设置"""
        cb = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=30,
            half_open_max_calls=5,
        )
        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 30
        assert cb.half_open_max_calls == 5

    def test_initial_state_is_closed(self):
        """初始状态应为 CLOSED"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.half_open_successes == 0


# ---------------------------------------------------------------------------
# CLOSED 状态行为
# ---------------------------------------------------------------------------
class TestClosedState:
    """CLOSED 状态（正常）测试"""

    def test_successful_call_returns_result(self):
        """成功调用应返回函数结果"""
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42

    def test_successful_call_resets_failure_count(self):
        """成功调用应重置 failure_count 为 0"""
        cb = CircuitBreaker(failure_threshold=5)

        # 先模拟 3 次失败
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.failure_count == 3

        # 一次成功调用
        cb.call(lambda: "ok")
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_call_with_args_and_kwargs(self):
        """call() 应正确传递位置参数和关键字参数"""
        cb = CircuitBreaker()

        def add(a, b, c=0):
            return a + b + c

        assert cb.call(add, 1, 2, c=3) == 6


# ---------------------------------------------------------------------------
# 连续失败触发熔断
# ---------------------------------------------------------------------------
class TestOpenTransition:
    """失败触发 OPEN 状态测试"""

    def _failing_func(self):
        """始终抛出异常的函数"""
        raise RuntimeError("boom")

    def test_failure_count_increments(self):
        """每次失败 failure_count 应递增"""
        cb = CircuitBreaker(failure_threshold=5)
        for i in range(3):
            with pytest.raises(RuntimeError):
                cb.call(self._failing_func)
            assert cb.failure_count == i + 1

    def test_opens_at_threshold(self):
        """failure_count 达到 threshold 时应切换到 OPEN"""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(self._failing_func)
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_does_not_open_below_threshold(self):
        """failure_count 未达 threshold 时不应切换到 OPEN"""
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            with pytest.raises(RuntimeError):
                cb.call(self._failing_func)
        assert cb.state == CircuitState.CLOSED

    def test_last_failure_time_is_set(self):
        """失败后 last_failure_time 应被设置"""
        cb = CircuitBreaker()
        before = time.time()
        with pytest.raises(RuntimeError):
            cb.call(self._failing_func)
        after = time.time()
        assert before <= cb.last_failure_time <= after


# ---------------------------------------------------------------------------
# OPEN 状态行为
# ---------------------------------------------------------------------------
class TestOpenState:
    """OPEN 状态（熔断）测试"""

    def _make_open_breaker(self, threshold=3):
        """辅助：构造一个已处于 OPEN 状态的熔断器"""
        cb = CircuitBreaker(failure_threshold=threshold, recovery_timeout=60)
        for _ in range(threshold):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN
        return cb

    def test_open_rejects_calls(self):
        """OPEN 状态下调用应抛出 CircuitBreakerError"""
        cb = self._make_open_breaker()
        with pytest.raises(CircuitBreakerError, match="OPEN"):
            cb.call(lambda: "should not run")

    def test_open_rejects_without_executing_func(self):
        """OPEN 状态拒绝调用时，目标函数不应被执行"""
        cb = self._make_open_breaker()
        called = False

        def track_call():
            nonlocal called
            called = True

        with pytest.raises(CircuitBreakerError):
            cb.call(track_call)
        assert called is False


# ---------------------------------------------------------------------------
# OPEN → HALF_OPEN 转换
# ---------------------------------------------------------------------------
class TestHalfOpenTransition:
    """OPEN → HALF_OPEN 状态转换测试"""

    def test_transitions_to_half_open_after_timeout(self):
        """recovery_timeout 后应进入 HALF_OPEN 状态"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # 触发 OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        # 模拟时间流逝，跳过 recovery_timeout
        with patch("core.circuit_breaker.time") as mock_time:
            # last_failure_time + recovery_timeout + 1 秒
            mock_time.time.return_value = cb.last_failure_time + 2
            # 此时调用应进入 HALF_OPEN 并执行函数
            result = cb.call(lambda: "recovered")
            assert result == "recovered"
            assert cb.state == CircuitState.HALF_OPEN

    def test_stays_open_before_timeout(self):
        """recovery_timeout 未到期前应保持 OPEN"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        # 只过了 10 秒，还没到 60 秒
        with patch("core.circuit_breaker.time") as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 10
            with pytest.raises(CircuitBreakerError):
                cb.call(lambda: "too early")
            assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# HALF_OPEN 状态行为
# ---------------------------------------------------------------------------
class TestHalfOpenState:
    """HALF_OPEN 状态（试探恢复）测试"""

    def _make_half_open_breaker(self):
        """辅助：构造一个已处于 HALF_OPEN 状态的熔断器"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max_calls=3)
        # 触发 OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        # 模拟时间流逝，进入 HALF_OPEN
        with patch("core.circuit_breaker.time") as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 2
            cb.call(lambda: "first_success")
        assert cb.state == CircuitState.HALF_OPEN
        return cb

    def test_half_open_success_increments_counter(self):
        """HALF_OPEN 状态下成功调用应递增 half_open_successes"""
        cb = self._make_half_open_breaker()
        assert cb.half_open_successes == 1

        cb.call(lambda: "second")
        assert cb.half_open_successes == 2

    def test_half_open_recovers_to_closed(self):
        """HALF_OPEN 成功次数达到 half_open_max_calls 后应恢复 CLOSED"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max_calls=3)
        # 触发 OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        # 模拟时间流逝，进入 HALF_OPEN 并完成 3 次成功
        with patch("core.circuit_breaker.time") as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 2
            for _ in range(3):
                cb.call(lambda: "ok")

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_returns_to_open(self):
        """HALF_OPEN 状态下失败应回到 OPEN"""
        cb = self._make_half_open_breaker()
        assert cb.state == CircuitState.HALF_OPEN

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail again")))

        assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# reset() 方法
# ---------------------------------------------------------------------------
class TestReset:
    """reset() 方法测试"""

    def test_reset_restores_initial_state(self):
        """reset() 应恢复到初始状态"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        # 触发 OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.half_open_successes == 0

    def test_reset_allows_new_calls(self):
        """reset() 后应能正常调用"""
        cb = CircuitBreaker(failure_threshold=1)

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        cb.reset()
        result = cb.call(lambda: "after_reset")
        assert result == "after_reset"
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# get_state() 方法
# ---------------------------------------------------------------------------
class TestGetState:
    """get_state() 方法测试"""

    def test_get_state_returns_dict(self):
        """get_state() 应返回字典"""
        cb = CircuitBreaker()
        state = cb.get_state()
        assert isinstance(state, dict)

    def test_get_state_keys(self):
        """get_state() 应包含预期的键"""
        cb = CircuitBreaker()
        state = cb.get_state()
        expected_keys = {"state", "failure_count", "last_failure_time", "half_open_successes"}
        assert set(state.keys()) == expected_keys

    def test_get_state_values_initial(self):
        """初始状态下 get_state() 应返回正确的值"""
        cb = CircuitBreaker()
        state = cb.get_state()
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["last_failure_time"] is None
        assert state["half_open_successes"] == 0

    def test_get_state_reflects_changes(self):
        """get_state() 应反映当前状态"""
        cb = CircuitBreaker(failure_threshold=5)

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        state = cb.get_state()
        assert state["state"] == "closed"
        assert state["failure_count"] == 1
        assert state["last_failure_time"] is not None


# ---------------------------------------------------------------------------
# 装饰器模式
# ---------------------------------------------------------------------------
class TestDecorator:
    """装饰器模式测试"""

    def test_circuit_breaker_decorator_basic(self):
        """@circuit_breaker() 装饰器应正常工作"""

        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def healthy_func():
            return "healthy"

        result = healthy_func()
        assert result == "healthy"

    def test_circuit_breaker_decorator_opens_after_threshold(self):
        """@circuit_breaker() 装饰器连续失败后应熔断"""

        @circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def failing_func():
            raise ValueError("broken")

        # 连续失败 2 次
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_func()

        # 第 3 次应被熔断器拦截
        with pytest.raises(CircuitBreakerError):
            failing_func()

    def test_decorator_preserves_function_name(self):
        """装饰器应保留原函数名（functools.wraps）"""

        @circuit_breaker(failure_threshold=5, recovery_timeout=30)
        def my_special_func():
            """docstring"""
            return 1

        assert my_special_func.__name__ == "my_special_func"
        assert my_special_func.__doc__ == "docstring"

    def test_instance_as_decorator(self):
        """CircuitBreaker 实例可直接作为装饰器使用"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @cb
        def add(a, b):
            return a + b

        assert add(1, 2) == 3
