#!/usr/bin/env python3
"""
重置分析任务状态为 pending
"""

import json
from pathlib import Path

tasks_file = Path('./issues/processing/delta_tasks.json')

with open(tasks_file, 'r', encoding='utf-8') as f:
    tasks = json.load(f)

# 找到分析任务并重置
reset_count = 0
for task in tasks:
    if task.get('issue_id') == 'issue_20260314_203120_de5576cf':
        task['status'] = 'pending'
        task.pop('failed_at', None)
        task.pop('failure_reason', None)
        reset_count += 1
        print(f"✅ 重置任务：{task.get('issue_id')}")

with open(tasks_file, 'w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f"已重置 {reset_count} 个任务")
