#!/usr/bin/env python3
"""
集成测试

测试完整的异常检测与上报流程
"""

from issue_queue import IssueQueue
from agent_error_handler import ErrorHandler, with_error_handling
from alert_notifier import AlertNotifier
from manager_interface import QuantManager


def test_full_workflow():
    """测试完整工作流程"""
    print("=" * 60)
    print("🧪 集成测试：完整工作流程")
    print("=" * 60)
    
    # 1. 创建问题
    print("\n1️⃣ 创建问题")
    queue = IssueQueue()
    issue = queue.create_issue(
        agent='test_agent',
        severity='P1',
        error_type='TypeError',
        error_message="Test error message"
    )
    issue_id = queue.write_issue(issue)
    print(f"   ✅ 问题已创建：{issue_id}")
    
    # 2. Manager 处理
    print("\n2️⃣ Manager 处理")
    manager = QuantManager()
    task = manager.handle_error_report(issue)
    print(f"   ✅ 已调度给：{task['agent']}")
    print(f"   ✅ 任务类型：{task['type']}")
    
    # 3. 模拟修复完成
    print("\n3️⃣ 模拟修复完成")
    report = manager.complete_task(issue_id, "已修复测试错误")
    if report:
        print(f"   ✅ 问题已解决")
        print(f"   📊 报告：{report['resolution']}")
    
    # 4. 检查状态
    print("\n4️⃣ 检查状态")
    status = manager.get_status()
    print(f"   📊 活跃任务：{status['active_tasks']}")
    print(f"   📊 待处理：{status['pending_issues']}")
    
    print("\n" + "=" * 60)
    print("✅ 集成测试通过")
    print("=" * 60)


def test_error_handler():
    """测试错误处理器"""
    print("\n🧪 单元测试：错误处理器")
    
    handler = ErrorHandler('test_agent')
    
    # 测试 P1 错误
    try:
        result = None > 5
    except Exception as e:
        result = handler.handle_error(e)
        assert result['severity'] == 'P1', "P1 分类错误"
        print("   ✅ P1 错误分类正确")
    
    # 测试 P2 错误
    try:
        raise TimeoutError("timeout")
    except Exception as e:
        result = handler.handle_error(e)
        assert result['severity'] == 'P2', "P2 分类错误"
        print("   ✅ P2 错误分类正确")
    
    print("   ✅ 错误处理器测试通过")


def test_notifier():
    """测试通知器"""
    print("\n🧪 单元测试：通知器")
    
    notifier = AlertNotifier()
    
    # 测试 P0 通知
    alert = notifier.create_alert(
        severity='P0',
        agent='test',
        error='test error'
    )
    assert notifier.should_notify('P0') == True
    print("   ✅ P0 通知配置正确")
    
    # 测试 P2 不通知
    assert notifier.should_notify('P2') == False
    print("   ✅ P2 不通知配置正确")
    
    print("   ✅ 通知器测试通过")


if __name__ == '__main__':
    print("\n🚀 开始集成测试\n")
    
    test_error_handler()
    test_notifier()
    test_full_workflow()
    
    print("\n✅ 所有测试通过！\n")
