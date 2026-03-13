#!/usr/bin/env python3
"""
创建 cron 任务 - 直接修改 jobs.json
"""

import json
import uuid
from pathlib import Path
from datetime import datetime

def create_job(name, description, cron_expr, agent_id, message, model, session_target="isolated"):
    """创建 cron 任务配置"""
    now_ms = int(datetime.now().timestamp() * 1000)
    
    return {
        "id": str(uuid.uuid4()),
        "agentId": agent_id,
        "name": name,
        "description": description,
        "enabled": True,
        "createdAtMs": now_ms,
        "updatedAtMs": now_ms,
        "schedule": {
            "kind": "cron",
            "expr": cron_expr
        },
        "sessionTarget": session_target,
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": message,
            "model": model
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

def main():
    base_dir = "/Users/rowang/projects/vnpy/examples/alpha_research"
    venv_python = "/Users/rowang/projects/vnpy/venv/bin/python3"
    
    # 定义任务
    jobs = [
        create_job(
            name="交易前合规检查",
            description="每个交易日 09:25 执行交易前合规检查",
            cron_expr="25 9 * * 1-5",
            agent_id="main",
            message=f"cd {base_dir} && {venv_python} compliance_checker.py",
            model="lmstudio/zai-org/glm-4.7-flash"
        ),
        create_job(
            name="绩效归因报告",
            description="每个交易日 21:00 生成绩效归因报告",
            cron_expr="0 21 * * 1-5",
            agent_id="main",
            message=f"cd {base_dir} && {venv_python} performance_attribution.py",
            model="lmstudio/zai-org/glm-4.7-flash"
        ),
        create_job(
            name="Agent 健康检查",
            description="每 30 分钟检查 Agent 健康状态",
            cron_expr="*/30 * * * *",
            agent_id="main",
            message=f"cd {base_dir} && {venv_python} agent_health_check.py",
            model="lmstudio/zai-org/glm-4.7-flash"
        )
    ]
    
    # 输出 JSON
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    
    # 保存配置
    config_file = Path('./config/cron_jobs_to_add.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存：{config_file}")
    print(f"\n📝 共 {len(jobs)} 个任务，请手动添加到 ~/.openclaw/cron/jobs.json")

if __name__ == '__main__':
    main()
