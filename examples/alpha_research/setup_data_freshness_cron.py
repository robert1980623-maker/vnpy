#!/usr/bin/env python3
"""
配置数据新鲜度监控定时任务
"""

import json
from pathlib import Path
from datetime import datetime

def setup_cron():
    """设置数据新鲜度 cron 任务"""
    
    tasks = [
        {
            'name': '数据新鲜度检查',
            'schedule': 'cron 0 * * * * @ Asia/Shanghai',  # 每小时
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 stale_data_updater.py --check-only',
            'timeout': 120,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '陈旧数据自动更新',
            'schedule': 'cron 30 16 * * * @ Asia/Shanghai',  # 每天 16:30 (收盘后)
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 stale_data_updater.py --auto',
            'timeout': 600,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        }
    ]
    
    print("📋 数据新鲜度定时任务配置:")
    for task in tasks:
        print(f"\n{task['name']}:")
        print(f"  时间：{task['schedule']}")
        print(f"  超时：{task['timeout']}s")
        print(f"  模型：{task['model']}")
    
    # 保存配置
    config_file = Path('./config/data_freshness_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({'tasks': tasks, 'created': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存：{config_file}")
    
    return tasks

if __name__ == '__main__':
    setup_cron()
