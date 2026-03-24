#!/usr/bin/env python3
"""
配置每日自动更新 Cron 任务
"""

import subprocess
from pathlib import Path
from datetime import datetime

# 获取脚本路径
script_path = Path(__file__).parent / 'daily_portfolio_update.py'
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'portfolio_update.log'

# Cron 配置 - 每个交易日 17:30 执行
cron_job = f"30 17 * * 1-5 cd {script_path.parent} && /opt/homebrew/bin/python3 {script_path} >> {log_file} 2>&1"

print("=" * 80)
print(" " * 25 + "⚙️  配置 Cron 自动更新")
print("=" * 80)
print()
print("【Cron 任务配置】")
print(f"  脚本路径：{script_path}")
print(f"  日志文件：{log_file}")
print(f"  执行时间：每周一至周五 17:30")
print(f"  Cron 配置：{cron_job}")
print()

# 查看当前 Cron
print("【当前 Cron 任务】")
try:
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("  暂无 Cron 任务")
except Exception as e:
    print(f"  无法读取 Cron: {e}")

print()
print("【安装说明】")
print("  1. 运行以下命令编辑 Cron:")
print(f"     crontab -e")
print()
print("  2. 添加以下行:")
print(f"     {cron_job}")
print()
print("  3. 保存并退出")
print()
print("  或者手动运行测试:")
print(f"     python3 {script_path}")
print()

# 测试运行
print("【测试运行】")
print("-" * 80)
subprocess.run(['/opt/homebrew/bin/python3', str(script_path)])

print()
print("=" * 80)
print("✅ Cron 配置说明完成！")
print("=" * 80)
