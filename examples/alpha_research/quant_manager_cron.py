#!/usr/bin/env python3
"""
量化 Manager Cron 任务配置

创建事件触发的 Manager 检查任务
"""

import json
from pathlib import Path
from datetime import datetime
from human_report import human_manager_report

def create_manager_cron():
    """创建量化 Manager cron 任务"""
    
    # 任务配置
    manager_task = {
        "id": "quant-manager-task",
        "agentId": "main",
        "name": "量化 Manager 任务处理",
        "description": "检查并处理量化任务队列",
        "enabled": True,
        "createdAtMs": int(datetime.now().timestamp() * 1000),
        "updatedAtMs": int(datetime.now().timestamp() * 1000),
        "schedule": {
            "kind": "cron",
            "expr": "*/5 * * * *"  # 每 5 分钟检查一次
        },
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 -c \"from manager_interface import QuantManager; m = QuantManager(); print('Manager 检查完成'); print(f'活跃任务：{len(m.active_tasks)}'); print(f'待处理：{len(m.issue_queue.get_pending_issues())}')\"",
            "model": "bailian/qwen3-max-2026-01-23"
        },
        "delivery": {
            "mode": "announce",
            "channel": "d0ajbbddd9s",
            "to": "D0AJBBDDD9S"
        },
        "state": {
            "nextRunAtMs": int(datetime.now().timestamp() * 1000),
            "consecutiveErrors": 0,
            "lastStatus": None,
            "lastRunStatus": None,
            "lastRunAtMs": None,
            "lastDurationMs": 0,
            "lastDeliveryStatus": None,
            "lastDelivered": False
        },
        "timeoutSeconds": 300
    }
    
    return manager_task

if __name__ == '__main__':
    task = create_manager_cron()
    print("量化 Manager 任务配置:")
    print(f"  名称：{task['name']}")
    print(f"  时间：每 5 分钟")
    print(f"  模型：qwen3-max")
    print(f"  超时：{task['timeoutSeconds']}秒")
    
    # 保存到配置文件
    config_file = Path('./config/quant_manager_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存：{config_file}")
