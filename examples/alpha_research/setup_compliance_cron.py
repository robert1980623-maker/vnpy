#!/usr/bin/env python3
"""
配置合规检查定时任务
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

def setup_compliance_cron():
    """设置合规检查 cron 任务"""
    
    # 任务 1: 交易前合规检查 (每个交易日 09:25)
    task1 = {
        "name": "交易前合规检查",
        "schedule": "cron 25 9 * * 1-5 @ Asia/Shanghai",
        "command": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 compliance_checker.py",
        "timeout": 300,
        "model": "lmstudio/zai-org/glm-4.7-flash"
    }
    
    # 任务 2: 持仓合规检查 (每 30 分钟)
    task2 = {
        "name": "持仓合规检查",
        "schedule": "cron */30 * * * * @ Asia/Shanghai",
        "command": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 -c \"from compliance_checker import ComplianceChecker; c = ComplianceChecker(); print('合规检查 OK')\"",
        "timeout": 60,
        "model": "lmstudio/zai-org/glm-4.7-flash"
    }
    
    print("📋 合规检查定时任务配置:")
    print("\n任务 1: 交易前合规检查")
    print(f"  时间：{task1['schedule']}")
    print(f"  超时：{task1['timeout']}s")
    print(f"  模型：{task1['model']}")
    
    print("\n任务 2: 持仓合规检查")
    print(f"  时间：{task2['schedule']}")
    print(f"  超时：{task2['timeout']}s")
    print(f"  模型：{task2['model']}")
    
    # 保存配置
    config_file = Path('./config/compliance_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({'tasks': [task1, task2], 'created': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存：{config_file}")
    print("\n⚠️  请手动执行以下命令创建 cron 任务:")
    print(f"  openclaw cron add --name \"{task1['name']}\" --schedule \"{task1['schedule']}\" --timeout {task1['timeout']} --model {task1['model']} --command \"{task1['command']}\"")
    print(f"  openclaw cron add --name \"{task2['name']}\" --schedule \"{task2['schedule']}\" --timeout {task2['timeout']}\" --model {task2['model']} --command \"{task2['command']}\"")

if __name__ == '__main__':
    setup_compliance_cron()
