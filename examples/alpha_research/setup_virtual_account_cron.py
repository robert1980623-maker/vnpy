#!/usr/bin/env python3
"""
配置虚拟账户 Cron 任务

功能:
- 每天 17:00 下载数据
- 每天 17:30 执行交易
- 每天 20:00 生成复盘
- 每周六 10:00 生成周总结
"""

import json
from datetime import datetime


def setup_cron_jobs():
    """配置 Cron 任务"""
    
    print("=" * 70)
    print(" " * 20 + "配置虚拟账户 Cron 任务")
    print("=" * 70)
    print()
    
    # Cron 任务配置
    jobs = [
        {
            "name": "虚拟账户 - 每日数据下载",
            "schedule": {
                "kind": "cron",
                "expr": "0 17 * * *",  # 每天 17:00
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "systemEvent",
                "text": "📊 虚拟账户：开始下载当日股票数据...\n\n任务：download_data_akshare.py\n时间：17:00\n状态：执行中"
            },
            "sessionTarget": "main",
            "enabled": True
        },
        {
            "name": "虚拟账户 - 每日自动交易",
            "schedule": {
                "kind": "cron",
                "expr": "30 17 * * *",  # 每天 17:30
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "systemEvent",
                "text": "💼 虚拟账户：开始执行每日交易...\n\n任务：daily_trading.py\n时间：17:30\n状态：执行中"
            },
            "sessionTarget": "main",
            "enabled": True
        },
        {
            "name": "虚拟账户 - 每日复盘",
            "schedule": {
                "kind": "cron",
                "expr": "0 20 * * 1-5",  # 工作日 20:00
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "systemEvent",
                "text": "📝 虚拟账户：生成每日复盘报告...\n\n任务：generate_reports.py (每日)\n时间：20:00\n状态：执行中"
            },
            "sessionTarget": "main",
            "enabled": True
        },
        {
            "name": "虚拟账户 - 每周总结",
            "schedule": {
                "kind": "cron",
                "expr": "0 10 * * 6",  # 周六 10:00
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "systemEvent",
                "text": "📈 虚拟账户：生成每周总结报告...\n\n任务：generate_reports.py (每周)\n时间：周六 10:00\n状态：执行中"
            },
            "sessionTarget": "main",
            "enabled": True
        }
    ]
    
    print("【Cron 任务配置】")
    print()
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['name']}")
        print(f"   时间：{job['schedule']['expr']}")
        print(f"   目标：{job['sessionTarget']}")
        print(f"   状态：{'✅ 启用' if job['enabled'] else '❌ 禁用'}")
        print()
    
    # 保存配置
    config_file = Path('./cron_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置已保存：{config_file}")
    print()
    
    print("=" * 70)
    print("【下一步操作】")
    print()
    print("请手动添加 Cron 任务 (或使用以下命令):")
    print()
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. 添加任务:")
        print(f"   cron add --job '{json.dumps(job, ensure_ascii=False)}'")
        print()
    
    print("=" * 70)
    
    return jobs


def main():
    from pathlib import Path
    
    print("=" * 70)
    print(" " * 15 + "虚拟账户定时任务配置")
    print("=" * 70)
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 配置 Cron 任务
    jobs = setup_cron_jobs()
    
    print()
    print("【任务说明】")
    print()
    print("1. 每日数据下载 (17:00)")
    print("   - 从 AKShare 下载当日股票数据")
    print("   - 更新本地数据缓存")
    print()
    print("2. 每日自动交易 (17:30)")
    print("   - 读取当日收盘价")
    print("   - 执行交易策略")
    print("   - 更新持仓和账户")
    print()
    print("3. 每日复盘 (工作日 20:00)")
    print("   - 统计当日收益")
    print("   - 分析交易执行")
    print("   - 生成复盘报告")
    print()
    print("4. 每周总结 (周六 10:00)")
    print("   - 统计周度收益")
    print("   - 分析交易表现")
    print("   - 生成周度报告")
    print()
    
    print("=" * 70)
    print()
    print("✅ 配置完成！")
    print()
    print("下一步:")
    print("  1. 检查 cron_config.json")
    print("  2. 使用 'cron add' 命令添加任务")
    print("  3. 使用 'cron list' 查看任务列表")
    print("  4. 等待明天 17:00 第一次自动执行")
    print()


if __name__ == '__main__':
    main()
