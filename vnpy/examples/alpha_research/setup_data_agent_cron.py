#!/usr/bin/env python3
"""
配置统一数据下载 Agent 的 Cron 任务
"""

import json
from pathlib import Path
from datetime import datetime

def create_cron_config():
    """创建 Cron 配置"""
    
    cron_jobs = [
        {
            'name': '统一数据下载 (凌晨)',
            'schedule': '0 1 * * *',
            'description': '每天凌晨 1 点下载所有数据',
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 data_agent.py --all',
            'timeout': 1800,  # 30 分钟
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '日线数据下载 (下午)',
            'schedule': '0 17 * * *',
            'description': '每天 17:00 下载当日日线数据',
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 data_agent.py --daily',
            'timeout': 600,  # 10 分钟
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '政策数据下载',
            'schedule': '0 3 * * *',
            'description': '每天凌晨 3 点下载政策数据',
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 data_agent.py --policy',
            'timeout': 300,  # 5 分钟
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '新闻数据下载',
            'schedule': '0 17 * * *',
            'description': '每天 17:00 下载新闻数据',
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 data_agent.py --news',
            'timeout': 300,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        }
    ]
    
    # 保存到配置文件
    config_file = Path('./config/data_agent_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({
            'created': datetime.now().isoformat(),
            'jobs': cron_jobs
        }, f, ensure_ascii=False, indent=2)
    
    print("✅ Cron 配置已保存")
    print(f"   文件：{config_file}")
    print(f"   任务数：{len(cron_jobs)}")
    print()
    
    # 打印配置摘要
    print("📋 Cron 任务配置:")
    for job in cron_jobs:
        print(f"\n  {job['name']}")
        print(f"    时间：{job['schedule']}")
        print(f"    超时：{job['timeout']}秒")
        print(f"    模型：{job['model']}")
    
    return cron_jobs

if __name__ == '__main__':
    create_cron_config()
