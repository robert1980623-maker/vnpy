#!/usr/bin/env python3
"""
配置精英组合定时任务

任务:
1. 每小时实时监控
2. 每日 09:00 精选选股
3. 每日 17:30 执行调仓
4. 每日 20:00 复盘
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime


def setup_cron_jobs():
    """配置定时任务"""
    print("=" * 70)
    print(" " * 20 + "配置精英组合定时任务")
    print("=" * 70)
    
    jobs = [
        {
            'name': '每小时实时监控',
            'schedule': '0 * * * *',  # 每小时整点
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 realtime_monitor.py --once',
            'model': 'lmstudio/zai-org/glm-4.7-flash',
            'timeout': 300,
            'description': '每小时检查持仓、止盈止损、数据新鲜度'
        },
        {
            'name': '每日精选选股',
            'schedule': '0 9 * * 1-5',  # 周一至周五 09:00
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 elite_stock_selector.py',
            'model': 'bailian/qwen3-max-2026-01-23',
            'timeout': 600,
            'description': '精选 5 只股票，整合基本面 + 消息面'
        },
        {
            'name': '数据更新 (凌晨)',
            'schedule': '0 1 * * *',  # 每天凌晨 01:00
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 download_data_akshare.py --end $(date +%Y-%m-%d)',
            'model': 'lmstudio/zai-org/glm-4.7-flash',
            'timeout': 600,
            'description': '下载最新股票数据'
        },
        {
            'name': '数据更新 (下午)',
            'schedule': '0 17 * * *',  # 每天 17:00
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 download_data_akshare.py --end $(date +%Y-%m-%d)',
            'model': 'lmstudio/zai-org/glm-4.7-flash',
            'timeout': 600,
            'description': '下载当日收盘数据'
        },
        {
            'name': '每日调仓',
            'schedule': '30 17 * * 1-5',  # 周一至周五 17:30
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 rebalance_portfolio.py',
            'model': 'bailian/qwen3-max-2026-01-23',
            'timeout': 600,
            'description': '根据选股结果调仓至 5 只精英组合'
        },
        {
            'name': '严格止盈止损检查',
            'schedule': '0 15 * * 1-5',  # 周一至周五 15:00 (收盘后)
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 strict_stop_loss.py',
            'model': 'lmstudio/zai-org/glm-4.7-flash',
            'timeout': 300,
            'description': '检查并执行止盈止损'
        },
        {
            'name': '每日复盘',
            'schedule': '0 20 * * 1-5',  # 周一至周五 20:00
            'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 daily_review.py',
            'model': 'bailian/qwen3-max-2026-01-23',
            'timeout': 600,
            'description': '生成每日复盘报告'
        }
    ]
    
    print(f"\n📋 配置 {len(jobs)} 个定时任务:\n")
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['name']}")
        print(f"   时间：{job['schedule']}")
        print(f"   模型：{job['model']}")
        print(f"   说明：{job['description']}")
        print()
    
    # 使用 openclaw cron add 添加任务
    print("=" * 70)
    print(" " * 20 + "添加定时任务")
    print("=" * 70)
    
    added_jobs = []
    for job in jobs:
        try:
            # 构建命令
            cmd = [
                'openclaw', 'cron', 'add',
                '--name', job['name'],
                '--schedule', job['schedule'],
                '--model', job['model'],
                '--timeout', str(job['timeout']),
                '--isolated',
                job['command']
            ]
            
            print(f"\n添加：{job['name']}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"  ✅ 成功")
                # 从输出中提取 Job ID
                if 'Job ID:' in result.stdout:
                    job_id = result.stdout.split('Job ID:')[1].strip().split()[0]
                    job['job_id'] = job_id
                    added_jobs.append(job)
            else:
                print(f"  ⚠️ 失败：{result.stderr}")
        except Exception as e:
            print(f"  ✗ 错误：{e}")
    
    # 保存配置
    config = {
        'created_at': datetime.now().isoformat(),
        'target_stocks': 5,
        'stop_loss': -0.15,
        'take_profit': 0.30,
        'monitor_interval': 3600,
        'jobs': added_jobs
    }
    
    config_file = Path('./config/elite_portfolio_cron.json')
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存：{config_file}")
    print(f"\n📊 成功添加 {len(added_jobs)}/{len(jobs)} 个任务")
    
    # 显示已添加的任务
    if added_jobs:
        print("\n" + "=" * 70)
        print(" " * 20 + "已配置任务列表")
        print("=" * 70)
        for job in added_jobs:
            print(f"  {job.get('job_id', 'N/A')[:8]} - {job['name']}")
            print(f"              {job['schedule']}")
    
    print("\n" + "=" * 70)
    print(" " * 20 + "完成")
    print("=" * 70)
    print("\n💡 提示:")
    print("  - 查看任务：openclaw cron list")
    print("  - 删除任务：openclaw cron delete <job_id>")
    print("  - 手动触发：openclaw cron run <job_id>")
    print("  - 查看日志：openclaw cron logs <job_id>")


if __name__ == '__main__':
    setup_cron_jobs()
