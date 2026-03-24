#!/usr/bin/env python3
"""
配置数据验证 Cron 任务
"""

import json
from pathlib import Path
from datetime import datetime

def create_validation_cron():
    """创建数据验证 Cron 任务"""
    
    jobs_file = Path.home() / '.openclaw/cron/jobs.json'
    with open(jobs_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 选股前验证任务
    pre_stock_job = {
        'id': f'pre-stock-validation-{datetime.now().strftime("%Y%m%d")}',
        'agentId': 'main',
        'name': '选股前数据验证',
        'description': '每天 08:30 验证数据质量，确保选股数据可靠',
        'enabled': True,
        'createdAtMs': int(datetime.now().timestamp() * 1000),
        'updatedAtMs': int(datetime.now().timestamp() * 1000),
        'schedule': {
            'kind': 'cron',
            'expr': '30 8 * * 1-5'  # 每个交易日 08:30
        },
        'sessionTarget': 'isolated',
        'wakeMode': 'now',
        'payload': {
            'kind': 'agentTurn',
            'message': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 data_validator.py --validate --pre-stock',
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        'delivery': {
            'mode': 'announce',
            'channel': 'd0ajbbddd9s',
            'to': 'D0AJBBDDD9S'
        },
        'state': {
            'nextRunAtMs': int(datetime.now().timestamp() * 1000),
            'consecutiveErrors': 0,
            'lastStatus': None,
            'lastRunStatus': None,
            'lastRunAtMs': None,
            'lastDurationMs': 0,
            'lastDeliveryStatus': None,
            'lastDelivered': False
        },
        'timeoutSeconds': 300
    }
    
    # 检查是否已存在
    exists = any(job.get('name') == '选股前数据验证' for job in data['jobs'])
    
    if not exists:
        data['jobs'].append(pre_stock_job)
        
        with open(jobs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✅ 选股前数据验证任务已创建")
        print(f"   时间：每个交易日 08:30")
        print(f"   命令：python3 data_validator.py --validate --pre-stock")
        print(f"   超时：300 秒")
    else:
        print("⚠️ 选股前数据验证任务已存在")
    
    # 打印所有验证相关任务
    print("\n📋 数据验证相关任务:")
    for job in data['jobs']:
        name = job.get('name', '')
        schedule = job.get('schedule', {}).get('expr', '')
        if '验证' in name or '验证' in name or 'validation' in name.lower():
            print(f"  - {name}: {schedule}")

if __name__ == '__main__':
    create_validation_cron()

def create_manager_check_cron():
    """创建 Manager 检查问题队列的 Cron 任务"""
    
    jobs_file = Path.home() / '.openclaw/cron/jobs.json'
    with open(jobs_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Manager 检查问题队列任务
    manager_check_job = {
        'id': f'manager-issue-check-{datetime.now().strftime("%Y%m%d")}',
        'agentId': 'main',
        'name': 'Manager 问题队列检查',
        'description': '每 30 分钟检查问题队列并自动调度 Agent 处理',
        'enabled': True,
        'createdAtMs': int(datetime.now().timestamp() * 1000),
        'updatedAtMs': int(datetime.now().timestamp() * 1000),
        'schedule': {
            'kind': 'cron',
            'expr': '*/30 * * * *'  # 每 30 分钟
        },
        'sessionTarget': 'isolated',
        'wakeMode': 'now',
        'payload': {
            'kind': 'agentTurn',
            'message': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 manager_interface.py --check-issues',
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        'delivery': {
            'mode': 'announce',
            'channel': 'd0ajbbddd9s',
            'to': 'D0AJBBDDD9S'
        },
        'state': {
            'nextRunAtMs': int(datetime.now().timestamp() * 1000),
            'consecutiveErrors': 0,
            'lastStatus': None,
            'lastRunStatus': None,
            'lastRunAtMs': None,
            'lastDurationMs': 0,
            'lastDeliveryStatus': None,
            'lastDelivered': False
        },
        'timeoutSeconds': 300
    }
    
    # 检查是否已存在
    exists = any(job.get('name') == 'Manager 问题队列检查' for job in data['jobs'])
    
    if not exists:
        data['jobs'].append(manager_check_job)
        
        with open(jobs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✅ Manager 问题队列检查任务已创建")
        print(f"   时间：每 30 分钟")
        print(f"   命令：python3 manager_interface.py --check-issues")
    else:
        print("⚠️ Manager 问题队列检查任务已存在")

if __name__ == '__main__':
    create_validation_cron()
    create_manager_check_cron()
