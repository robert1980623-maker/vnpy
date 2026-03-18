#!/usr/bin/env python3
"""
重试机制测试脚本

测试内容:
1. 装饰器方式重试（成功场景）
2. 装饰器方式重试（失败场景）
3. 函数方式重试
4. 指数退避延迟验证
5. 监控统计
6. 日志记录验证

用法:
    python3 test_retry.py
"""

import logging
import time
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from retry_utils import (
    retry_with_backoff,
    retry_function,
    get_retry_monitor,
    calculate_backoff_delay,
    RetryMonitor
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_backoff_delay():
    """测试 1: 指数退避延迟计算"""
    print("\n" + "=" * 60)
    print("测试 1: 指数退避延迟计算")
    print("=" * 60)
    
    base_delay = 2.0
    max_delay = 60.0
    
    print(f"配置：base_delay={base_delay}s, max_delay={max_delay}s\n")
    
    for attempt in range(1, 8):
        delay = calculate_backoff_delay(
            attempt, base_delay, max_delay, exponential=True, jitter=False
        )
        print(f"  第{attempt}次重试延迟：{delay}秒")
    
    print("\n✅ 测试 1 通过")


def test_decorator_success():
    """测试 2: 装饰器方式 - 成功场景"""
    print("\n" + "=" * 60)
    print("测试 2: 装饰器方式 - 成功场景")
    print("=" * 60)
    
    call_count = 0
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        log_file='logs/test_retry_success.json'
    )
    def always_succeeds(x, y):
        nonlocal call_count
        call_count += 1
        logger.info(f"执行 always_succeeds({x}, {y}) - 第{call_count}次调用")
        return x + y
    
    result = always_succeeds(10, 20)
    print(f"结果：{result}")
    print(f"调用次数：{call_count}")
    
    assert result == 30, "结果应该是 30"
    assert call_count == 1, "应该只调用 1 次"
    
    print("\n✅ 测试 2 通过")


def test_decorator_fail_then_success():
    """测试 3: 装饰器方式 - 失败后成功"""
    print("\n" + "=" * 60)
    print("测试 3: 装饰器方式 - 失败后成功")
    print("=" * 60)
    
    call_count = 0
    fail_until = 2  # 前 2 次失败，第 3 次成功
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=0.5,  # 缩短延迟加快测试
        max_delay=5.0,
        log_file='logs/test_retry_fail_then_success.json'
    )
    def fail_then_succeed():
        nonlocal call_count
        call_count += 1
        logger.info(f"执行 fail_then_succeed() - 第{call_count}次调用")
        
        if call_count < fail_until:
            raise ValueError(f"故意失败 (第{call_count}次)")
        
        return "成功!"
    
    result = fail_then_succeed()
    print(f"结果：{result}")
    print(f"调用次数：{call_count}")
    
    assert result == "成功!", "应该最终成功"
    assert call_count == fail_until, f"应该调用{fail_until}次"
    
    print("\n✅ 测试 3 通过")


def test_decorator_always_fail():
    """测试 4: 装饰器方式 - 总是失败"""
    print("\n" + "=" * 60)
    print("测试 4: 装饰器方式 - 总是失败")
    print("=" * 60)
    
    call_count = 0
    max_retries = 3
    
    @retry_with_backoff(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=5.0,
        log_file='logs/test_retry_always_fail.json'
    )
    def always_fails():
        nonlocal call_count
        call_count += 1
        logger.info(f"执行 always_fails() - 第{call_count}次调用")
        raise ValueError("总是失败")
    
    try:
        always_fails()
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"捕获异常：{e}")
    
    print(f"调用次数：{call_count}")
    assert call_count == max_retries, f"应该调用{max_retries}次"
    
    print("\n✅ 测试 4 通过")


def test_function_retry():
    """测试 5: 函数方式重试"""
    print("\n" + "=" * 60)
    print("测试 5: 函数方式重试")
    print("=" * 60)
    
    call_count = 0
    
    def fail_twice():
        nonlocal call_count
        call_count += 1
        logger.info(f"执行 fail_twice() - 第{call_count}次调用")
        
        if call_count < 3:
            raise RuntimeError(f"失败 (第{call_count}次)")
        
        return "函数重试成功!"
    
    result = retry_function(
        fail_twice,
        max_retries=3,
        base_delay=0.5,
        max_delay=5.0,
        log_file='logs/test_retry_function.json'
    )
    
    print(f"结果：{result}")
    print(f"调用次数：{call_count}")
    
    assert result == "函数重试成功!"
    assert call_count == 3
    
    print("\n✅ 测试 5 通过")


def test_monitor_stats():
    """测试 6: 监控统计"""
    print("\n" + "=" * 60)
    print("测试 6: 监控统计")
    print("=" * 60)
    
    monitor = get_retry_monitor()
    stats = monitor.get_stats()
    
    print("\n统计信息:")
    print(f"  总调用次数：{stats['total_calls']}")
    print(f"  成功次数：{stats['total_success']}")
    print(f"  失败次数：{stats['total_failed']}")
    print(f"  总重试次数：{stats['total_retries']}")
    
    if stats['total_calls'] > 0:
        success_rate = stats['total_success'] / stats['total_calls'] * 100
        print(f"  成功率：{success_rate:.1f}%")
    
    # 打印详细统计
    monitor.print_stats()
    
    # 检查失败记录
    failures = monitor.get_recent_failures(limit=5)
    if failures:
        print(f"\n最近失败记录：{len(failures)}条")
        for f in failures:
            print(f"  - {f['func_name']}: {f['final_error']}")
    
    print("\n✅ 测试 6 通过")


def test_timeout():
    """测试 7: 超时处理"""
    print("\n" + "=" * 60)
    print("测试 7: 超时处理")
    print("=" * 60)
    
    @retry_with_backoff(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        timeout=2.0,  # 2 秒超时
        log_file='logs/test_retry_timeout.json'
    )
    def slow_function():
        logger.info("执行 slow_function() - 将超时")
        time.sleep(5)  # 超过超时时间
        return "不应该到达这里"
    
    try:
        slow_function()
        assert False, "应该超时"
    except (TimeoutError, Exception) as e:
        print(f"捕获超时异常：{type(e).__name__}: {e}")
    
    print("\n✅ 测试 7 通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("重试机制测试套件")
    print("=" * 60)
    print(f"开始时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("指数退避延迟", test_backoff_delay),
        ("装饰器 - 成功", test_decorator_success),
        ("装饰器 - 失败后成功", test_decorator_fail_then_success),
        ("装饰器 - 总是失败", test_decorator_always_fail),
        ("函数方式重试", test_function_retry),
        ("监控统计", test_monitor_stats),
        ("超时处理", test_timeout),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ 测试失败 [{name}]: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # 最终统计
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过：{passed}/{len(tests)}")
    print(f"失败：{failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ {failed}个测试失败")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
