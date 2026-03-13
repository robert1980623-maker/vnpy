#!/usr/bin/env python3
"""添加陈旧数据自动更新 cron 任务"""

import json
import uuid
from pathlib import Path
from datetime import datetime

# 读取现有配置
jobs_file = Path.home() / '.openclaw/cron/jobs.json'
with open(jobs_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建新任务
now_ms = int(datetime.now().timestamp() * 1000)
new_job = {
    "id": str(uuid.uuid4()),
    "agentId": "main",
    "name": "陈旧数据自动更新",
    "description": "每天 16:30 自动更新陈旧持仓数据",
    "enabled": True,
    "createdAtMs": now_ms,
    "updatedAtMs": now_ms,
    "schedule": {
        "kind": "cron",
        "expr": "30 16 * * 1-5"  # 每个交易日 16:30
    },
    "sessionTarget": "isolated",
    "wakeMode": "now",
    "payload": {
        "kind": "agentTurn",
        "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && /Users/rowang/projects/vnpy/venv/bin/python3 stale_data_updater.py --auto",
        "model": "lmstudio/zai-org/glm-4.7-flash"
    },
    "delivery": {
        "mode": "announce",
        "channel": "d0ajbbddd9s",
        "to": "D0AJBBDDD9S"
    },
    "state": {
        "nextRunAtMs": now_ms,
        "consecutiveErrors": 0,
        "lastStatus": None,
        "lastRunStatus": None,
        "lastRunAtMs": None,
        "lastDurationMs": 0,
        "lastDeliveryStatus": None,
        "lastDelivered": False
    }
}

# 添加到 jobs
data['jobs'].append(new_job)

# 保存
with open(jobs_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 陈旧数据自动更新任务已创建")
print(f"   名称：{new_job['name']}")
print(f"   时间：每个交易日 16:30")
print(f"   模型：glm-4.7-flash (本地)")
print(f"   总任务数：{len(data['jobs'])}")
