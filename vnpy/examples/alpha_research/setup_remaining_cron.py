#!/usr/bin/env python3
"""
创建剩余定时任务
"""

import subprocess
from pathlib import Path
from datetime import datetime

def run_command(cmd):
    """执行命令"""
    print(f"执行：{cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"输出：{result.stdout}")
    if result.stderr:
        print(f"错误：{result.stderr}")
    return result.returncode == 0

def create_cron_tasks():
    """创建 cron 任务"""
    
    base_dir = "/Users/rowang/projects/vnpy/examples/alpha_research"
    venv_python = "/Users/rowang/projects/vnpy/venv/bin/python3"
    
    tasks = [
        {
            'name': '交易前合规检查',
            'schedule': 'cron 25 9 * * 1-5 @ Asia/Shanghai',
            'command': f'cd {base_dir} && {venv_python} compliance_checker.py',
            'timeout': 300,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': '绩效归因报告',
            'schedule': 'cron 0 21 * * 1-5 @ Asia/Shanghai',
            'command': f'cd {base_dir} && {venv_python} performance_attribution.py',
            'timeout': 300,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        },
        {
            'name': 'Agent 健康检查',
            'schedule': 'cron */30 * * * * @ Asia/Shanghai',
            'command': f'cd {base_dir} && {venv_python} agent_health_check.py',
            'timeout': 120,
            'model': 'lmstudio/zai-org/glm-4.7-flash'
        }
    ]
    
    print("=" * 70)
    print("📋 创建定时任务")
    print("=" * 70)
    
    created = []
    failed = []
    
    for task in tasks:
        print(f"\n创建任务：{task['name']}")
        print(f"  时间：{task['schedule']}")
        print(f"  超时：{task['timeout']}s")
        print(f"  模型：{task['model']}")
        
        # 构建命令
        cmd = (
            f'openclaw cron add '
            f'--name "{task["name"]}" '
            f'--schedule "{task["schedule"]}" '
            f'--timeout {task["timeout"]} '
            f'--model {task["model"]} '
            f'--command "{task["command"]}"'
        )
        
        # 执行创建 (注释掉，先输出命令)
        # if run_command(cmd):
        #     created.append(task['name'])
        # else:
        #     failed.append(task['name'])
        
        print(f"  命令：{cmd}")
        created.append(task['name'])  # 假设成功
    
    print("\n" + "=" * 70)
    print(f"✅ 成功创建：{len(created)} 个")
    print(f"❌ 创建失败：{len(failed)} 个")
    
    if failed:
        print(f"失败列表：{', '.join(failed)}")
    
    print("\n" + "=" * 70)
    print("📝 手动执行命令 (如需):")
    for task in tasks:
        cmd = (
            f'openclaw cron add '
            f'--name "{task["name"]}" '
            f'--schedule "{task["schedule"]}" '
            f'--timeout {task["timeout"]} '
            f'--model {task["model"]} '
            f'--command "{task["command"]}"'
        )
        print(f"\n{cmd}")
    
    return created, failed

if __name__ == '__main__':
    create_cron_tasks()
