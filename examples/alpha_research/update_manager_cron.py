#!/usr/bin/env python3
"""
更新 Manager cron 任务配置

让 Manager 任务真正处理问题队列，而不是只打印状态
"""

import json
from pathlib import Path
from datetime import datetime

def create_manager_monitor_task():
    """创建 Manager 问题队列监控任务"""
    
    task = {
        "id": "manager-queue-monitor",
        "agentId": "main",
        "name": "Manager 问题队列监控",
        "description": "每 40 分钟检查问题队列状态并生成报告",
        "enabled": True,
        "schedule": {
            "kind": "cron",
            "expr": "40 * * * *"  # 每小时 40 分
        },
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 manager_monitor.py --action check --non-interactive",
            "model": "lmstudio/zai-org/glm-4.7-flash"
        },
        "delivery": {
            "mode": "announce",
            "channel": "d0ajbbddd9s",
            "to": "D0AJBBDDD9S"
        },
        "timeoutSeconds": 300
    }
    
    return task


def create_manager_process_task():
    """创建 Manager 问题自动处理任务"""
    
    task = {
        "id": "manager-queue-process",
        "agentId": "main",
        "name": "Manager 问题自动处理",
        "description": "每 50 分钟自动处理待处理问题",
        "enabled": True,
        "schedule": {
            "kind": "cron",
            "expr": "50 * * * *"  # 每小时 50 分
        },
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 manager_monitor.py --action process --non-interactive",
            "model": "lmstudio/zai-org/glm-4.7-flash"
        },
        "delivery": {
            "mode": "announce",
            "channel": "d0ajbbddd9s",
            "to": "D0AJBBDDD9S"
        },
        "timeoutSeconds": 600
    }
    
    return task


if __name__ == '__main__':
    # 创建任务配置
    monitor_task = create_manager_monitor_task()
    process_task = create_manager_process_task()
    
    print("=" * 70)
    print("📋 Manager 任务配置更新")
    print("=" * 70)
    print()
    
    print("【任务 1: Manager 问题队列监控】")
    print(f"  时间：每小时 40 分")
    print(f"  命令：python3 manager_monitor.py --action check")
    print(f"  模型：glm-4.7-flash (本地)")
    print(f"  功能：检查队列状态，生成 Human 风格报告")
    print()
    
    print("【任务 2: Manager 问题自动处理】")
    print(f"  时间：每小时 50 分")
    print(f"  命令：python3 manager_monitor.py --action process")
    print(f"  模型：glm-4.7-flash (本地)")
    print(f"  功能：自动分配问题给对应 Agent")
    print()
    
    # 保存配置
    config_dir = Path('./config')
    config_dir.mkdir(parents=True, exist_ok=True)
    
    with open(config_dir / 'manager_monitor_cron.json', 'w', encoding='utf-8') as f:
        json.dump([monitor_task, process_task], f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置已保存：config/manager_monitor_cron.json")
    print()
    print("💡 下一步:")
    print("  1. 删除旧的 cron 任务")
    print("  2. 创建新的 cron 任务")
    print()
    print("  openclaw cron delete 08492e75-6fbe-4bcd-8cdf-d2b00facf22e  # 旧监控")
    print("  openclaw cron delete 5aeeec7e-03e7-452a-b824-51af93df4904  # 旧处理")
    print()
    print("  openclaw cron create --config config/manager_monitor_cron.json")
