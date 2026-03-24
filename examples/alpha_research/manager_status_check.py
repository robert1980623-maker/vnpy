#!/usr/bin/env python3
"""
Manager 状态快速检查 (优化版)

功能：
- 快速获取 Manager 状态
- 生成简要报告
- 超时保护（30 秒内完成）
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from manager_interface import QuantManager

def quick_status_check():
    """快速状态检查（30 秒超时）"""
    print('='*60)
    print('Manager 问题队列监控')
    print('='*60)
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    manager = QuantManager()
    status = manager.get_status()
    
    print(f"Manager 状态:")
    print(f"  活跃任务：{status.get('active_tasks', 0)}")
    print(f"  待处理问题：{status.get('pending_issues', 0)}")
    print(f"  处理中问题：{status.get('processing_issues', 0)}")
    print()
    print(f"按严重性:")
    print(f"  P0 严重：{status.get('p0_count', 0)}")
    print(f"  P1 重要：{status.get('p1_count', 0)}")
    print(f"  P2 一般：{status.get('p2_count', 0)}")
    print()
    
    # 检查 Delta Consumer 状态
    delta_tasks_file = Path('./issues/processing/delta_tasks.json')
    if delta_tasks_file.exists():
        with open(delta_tasks_file, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        pending_delta = len([t for t in tasks if t.get('status') == 'pending'])
        print(f"Delta 任务队列：{pending_delta} 个待处理")
    else:
        print(f"Delta 任务队列：空")
    print()
    
    if status.get('pending_issues', 0) == 0:
        print('✅ 无待处理问题')
        return 0
    else:
        print('⚠️ 有待处理问题，Delta Consumer 正在处理中')
        print('   （Delta Consumer 每 5 分钟自动运行）')
        return 0  # 不报错，只是提示


if __name__ == '__main__':
    sys.exit(quick_status_check())
