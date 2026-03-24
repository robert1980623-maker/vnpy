#!/usr/bin/env python3
"""
清理误报任务

将 status=0 或 status=* 的 agent_health 任务标记为 completed（因为是误报）
"""

import json
from pathlib import Path
from datetime import datetime

tasks_file = Path('./issues/processing/delta_tasks.json')

with open(tasks_file, 'r', encoding='utf-8') as f:
    tasks = json.load(f)

print(f"总任务数：{len(tasks)}")

# 筛选误报任务
false_positive_keywords = ['status=0', 'status=*', 'status=the', 'status=Status']
false_positives = []

for task in tasks:
    if task.get('status') != 'pending':
        continue
    
    error_msg = task.get('error_message', '')
    error_type = task.get('error_type', '')
    
    # 只清理 agent_health 类型的误报
    if error_type != 'agent_health':
        continue
    
    # 检查是否是误报
    if any(kw in error_msg for kw in false_positive_keywords):
        false_positives.append(task)

print(f"误报任务数：{len(false_positives)}")

# 标记为 completed
cleaned = 0
for task in false_positives:
    task['status'] = 'completed'
    task['completed_at'] = datetime.now().isoformat()
    task['resolution'] = '健康检查误报 - cron 配置正常，只是未到运行时间'
    cleaned += 1

# 保存
with open(tasks_file, 'w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f"✅ 已清理 {cleaned} 个误报任务")

# 统计
pending = [t for t in tasks if t.get('status') == 'pending']
completed = [t for t in tasks if t.get('status') == 'completed']
print(f"\n剩余待处理：{len(pending)}")
print(f"已完成：{len(completed)}")
