#!/usr/bin/env python3
"""
配置综合消息面分析定时任务

任务:
- 每日凌晨 3 点下载政策数据
- 每日凌晨 4 点下载国际形势数据
- 每日凌晨 5 点运行综合分析
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime


def setup_cron_jobs():
    """配置定时任务"""
    print("=" * 70)
    print(" " * 18 + "配置综合消息面分析定时任务")
    print("=" * 70)
    
    cron_dir = Path('./cron_jobs')
    cron_dir.mkdir(parents=True, exist_ok=True)
    
    jobs = [
        {
            'name': '政策数据下载',
            'schedule': '0 3 * * *',  # 每天凌晨 3 点
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python download_policy_data.py',
            'enabled': True,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '国际形势数据下载',
            'schedule': '0 4 * * *',  # 每天凌晨 4 点
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python download_geopolitics_data.py',
            'enabled': True,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '综合消息面分析',
            'schedule': '0 5 * * *',  # 每天凌晨 5 点
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python comprehensive_analyzer.py',
            'enabled': True,
            'model': 'bailian/qwen3-max-2026-01-23'
        }
    ]
    
    for job in jobs:
        job_file = cron_dir / f"{job['name'].replace(' ', '_')}.json"
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=2)
        print(f"✅ 创建任务配置：{job['name']}")
        print(f"   时间：{job['schedule']}")
        print(f"   文件：{job_file}")
    
    print("\n" + "=" * 70)
    print("  提示：使用以下命令在 OpenClaw 中创建 cron 任务")
    print("=" * 70)
    for job in jobs:
        print(f"\nopenclaw cron create --name \"{job['name']}\" --schedule \"{job['schedule']}\" --command \"{job['command']}\"")
    
    print("\n")


if __name__ == '__main__':
    setup_cron_jobs()
