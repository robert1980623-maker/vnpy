#!/usr/bin/env python3
"""
设置涨停龙头策略的 cron 任务
"""

import json
import uuid
from pathlib import Path
from datetime import datetime

# OpenClaw cron 目录
CRON_DIR = Path('/Users/rowang/.openclaw/cron')
TASKS_DIR = CRON_DIR / 'tasks'
TASKS_DIR.mkdir(parents=True, exist_ok=True)

# 策略配置
task_config = {
    "id": str(uuid.uuid4()),
    "agentId": "main",
    "name": "涨停龙头策略 - 每日选股",
    "description": "每日收盘后筛选涨停龙头股票，生成交易信号",
    "enabled": True,
    "createdAtMs": int(datetime.now().timestamp() * 1000),
    "updatedAtMs": int(datetime.now().timestamp() * 1000),
    "schedule": {
        "kind": "cron",
        "expr": "0 17 * * 1-5"  # 交易日 17:00 运行
    },
    "sessionTarget": "isolated",
    "wakeMode": "now",
    "payload": {
        "kind": "agentTurn",
        "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && python3 limit_up_strategy_runner.py --auto --notify",
        "model": "bailian/qwen3.5-plus"
    },
    "state": {
        "nextRunAtMs": None,
        "consecutiveErrors": 0,
        "lastStatus": None,
        "lastRunStatus": None,
        "lastRunAtMs": None,
        "lastDurationMs": None,
        "lastDeliveryStatus": None,
        "lastError": None
    },
    "delivery": {
        "mode": "announce"
    },
    "metadata": {
        "risk_control": {
            "max_positions": 5,
            "stop_loss_pct": -8.0,
            "take_profit_pct": 20.0
        }
    }
}

# 保存任务配置到 tasks 目录
task_file = TASKS_DIR / 'limit_up_leader_strategy.json'
with open(task_file, 'w', encoding='utf-8') as f:
    json.dump(task_config, f, ensure_ascii=False, indent=2)

print(f"✅ 涨停龙头策略任务配置已保存：{task_file}")

# 添加到 jobs.json
jobs_file = CRON_DIR / 'jobs.json'
if jobs_file.exists():
    with open(jobs_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查是否是带版本的结构
    if isinstance(data, dict) and 'jobs' in data:
        jobs = data['jobs']
    else:
        jobs = data if isinstance(data, list) else []
    
    # 检查是否已存在
    existing = False
    for job in jobs:
        if isinstance(job, dict) and job.get('name') == task_config['name']:
            existing = True
            job.update(task_config)
            print(f"🔄 已更新现有任务配置")
            break
    
    if not existing:
        jobs.append(task_config)
        print(f"➕ 已添加新任务")
    
    # 保存更新
    if isinstance(data, dict) and 'jobs' in data:
        data['jobs'] = jobs
        with open(jobs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        with open(jobs_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ jobs.json 已更新")
else:
    # 创建新的 jobs.json
    with open(jobs_file, 'w', encoding='utf-8') as f:
        json.dump({
            "version": 1,
            "jobs": [task_config]
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ 已创建 jobs.json")

# 验证配置
print("\n📋 任务配置摘要:")
print(f"  名称：{task_config['name']}")
print(f"  调度：{task_config['schedule']['expr']}")
print(f"  模型：{task_config['payload']['model']}")
print(f"  最大持仓：{task_config['metadata']['risk_control']['max_positions']}")
print(f"  止损：{task_config['metadata']['risk_control']['stop_loss_pct']}%")
print(f"  止盈：{task_config['metadata']['risk_control']['take_profit_pct']}%")

print("\n🚀 使用方式:")
print(f"  # 手动运行策略")
print(f"  cd /Users/rowang/projects/vnpy/examples/alpha_research")
print(f"  python3 limit_up_strategy_runner.py --auto --notify")
print(f"\n  # 查看 cron 任务")
print(f"  openclaw cron list")
print(f"\n  # 立即运行任务")
print(f"  openclaw cron run limit_up_leader_strategy")
