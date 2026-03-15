#!/usr/bin/env python3
"""
修复问题报告输出

确保完整显示问题详情
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from issue_queue import IssueQueue

def check_and_report():
    """检查并报告问题"""
    queue = IssueQueue()
    pending = queue.get_pending_issues()
    
    print("\n" + "=" * 70)
    print("📋 问题队列检查报告")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print(f"待处理问题数：{len(pending)}")
    print()
    
    if pending:
        print("⚠️ 发现待处理问题:\n")
        for i, issue in enumerate(pending, 1):
            print(f"问题 {i}:")
            print(f"  🆔 ID: {issue.id}")
            print(f"  🔴 严重性：{issue.severity}")
            print(f"  📝 类型：{issue.error_type}")
            print(f"  💬 消息：{issue.error_message[:200]}")
            print(f"  🤖 Agent: {issue.agent}")
            print(f"  ⏰ 时间：{issue.timestamp}")
            print(f"  📊 状态：{issue.status}")
            if issue.assigned_to:
                print(f"  👤 已指派：{issue.assigned_to}")
            print()
    else:
        print("✅ 无待处理问题")
        print()
        print("系统运行正常！")
    
    print()
    print("=" * 70)

if __name__ == '__main__':
    check_and_report()
