#!/usr/bin/env python3
"""
配置任务监控的定时任务
每天运行两次：09:00 和 17:00
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

def setup_monitor_cron():
    cron_file = Path('/Users/rowang/.openclaw/cron/jobs.json')
    
    with open(cron_file, 'r') as f:
        data = json.load(f)
    
    # 检查是否已存在
    existing = None
    for job in data.get('jobs', []):
        if '任务监控检查' in job.get('name', ''):
            existing = job
            break
    
    monitor_job = {
        'id': 'task-monitor-daily-check',
        'agentId': 'main',
        'name': '任务监控检查',
        'description': '每天检查两次所有自动任务的运行情况（09:00 和 17:00）',
        'enabled': True,
        'createdAtMs': int(datetime.now().timestamp() * 1000),
        'updatedAtMs': int(datetime.now().timestamp() * 1000),
        'schedule': {
            'kind': 'cron',
            'expr': '0 9,17 * * *',
            'tz': 'Asia/Shanghai'
        },
        'sessionTarget': 'isolated',
        'wakeMode': 'now',
        'payload': {
            'kind': 'agentTurn',
            'message': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 task_monitor.py',
            'model': 'lmstudio/zai-org/glm-4.7-flash',
            'timeoutSeconds': 300
        },
        'delivery': {
            'mode': 'announce',
            'channel': 'D0AJBBDDD9S'
        },
        'state': {
            'nextRunAtMs': 0,
            'consecutiveErrors': 0,
            'lastStatus': 'idle',
            'lastRunStatus': None
        }
    }
    
    if existing:
        print(f"ℹ️  已存在任务监控任务，正在更新...")
        idx = data['jobs'].index(existing)
        data['jobs'][idx] = monitor_job
    else:
        print("➕ 添加新任务：任务监控检查")
        data['jobs'].append(monitor_job)
    
    with open(cron_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 任务监控已配置")
    print(f"   时间：每天 09:00 和 17:00")
    print(f"   频道：D0AJBBDDD9S")
    print(f"   超时：300 秒")

if __name__ == '__main__':
    setup_monitor_cron()
