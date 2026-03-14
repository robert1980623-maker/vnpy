#!/usr/bin/env python3
"""
配置缺失的关键 Agent Cron 任务

功能:
- 首席风险官 (CRO) - 每日风险检查
- 止盈止损执行 - 每日止盈止损执行
"""

import json
from pathlib import Path


def setup_cron_jobs():
    """配置 Cron 任务"""
    
    print("=" * 70)
    print(" " * 20 + "配置缺失的关键 Agent Cron 任务")
    print("=" * 70)
    print()
    
    # Cron 任务配置
    jobs = [
        {
            "name": "首席风险官 - 每日风险检查",
            "schedule": {
                "kind": "cron",
                "expr": "0 10 * * 1-5",  # 工作日 10:00
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "agentTurn",
                "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 chief_risk_officer.py"
            },
            "sessionTarget": "isolated",
            "enabled": True,
            "is_critical": True
        },
        {
            "name": "止盈止损执行 - 每日止盈止损",
            "schedule": {
                "kind": "cron",
                "expr": "0 16 * * 1-5",  # 工作日 16:00
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "agentTurn",
                "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 stop_loss_executor.py"
            },
            "sessionTarget": "isolated",
            "enabled": True,
            "is_critical": True
        }
    ]
    
    print("【Cron 任务配置】")
    print()
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['name']}")
        print(f"   时间：{job['schedule']['expr']}")
        print(f"   目标：{job['sessionTarget']}")
        print(f"   状态：{'✅ 启用' if job['enabled'] else '❌ 禁用'}")
        print(f"   关键：{'⚠️ 是' if job.get('is_critical', False) else '否'}")
        print()
    
    # 保存配置
    config_file = Path('./config/missing_agents_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置已保存：{config_file}")
    print()
    print("【安装 Cron 任务】")
    print()
    print("运行以下命令安装 Cron 任务：")
    print(f"  openclaw cron add < {config_file}")
    print()


if __name__ == '__main__':
    setup_cron_jobs()
