#!/usr/bin/env python3
"""
配置每日 17:00 股票数据下载定时任务

功能:
- 配置 17:00 执行的数据下载任务
- 使用 openclaw cron add 命令
- 支持飞书通知

用法:
    python3 setup_daily_download_1700_cron.py
"""

import subprocess
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SHELL_SCRIPT = SCRIPT_DIR / "run_daily_download_1700.sh"

print("=" * 70)
print(" " * 20 + "配置每日 17:00 数据下载定时任务")
print("=" * 70)
print(f"脚本：{SHELL_SCRIPT}")
print(f"时间：每天 17:00")
print(f"任务：下载 A 股行情、消息面、宏观政策、国际形势数据")
print("=" * 70)
print()

# 检查脚本是否存在
if not SHELL_SCRIPT.exists():
    print(f"❌ 脚本不存在：{SHELL_SCRIPT}")
    exit(1)

# 使用 openclaw cron add 添加任务
cmd = [
    "openclaw", "cron", "add",
    "--name", "每日 17:00 数据下载",
    "--cron", "0 17 * * *",
    "--command", f"bash {SHELL_SCRIPT}",
    "--session", "isolated",
    "--agent", "data-agent",
    "--tz", "Asia/Shanghai"
]

print(f"执行命令：{' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("✅ 定时任务配置成功")
    print()
    print(result.stdout)
    
    # 显示任务信息
    print("\n" + "=" * 70)
    print("任务信息:")
    print(f"  名称：每日 17:00 数据下载")
    print(f"  时间：每天 17:00")
    print(f"  脚本：{SHELL_SCRIPT}")
    print(f"  日志：/Users/rowang/projects/vnpy/examples/alpha_research/logs/daily_download_1700/")
    print("=" * 70)
    
except subprocess.CalledProcessError as e:
    print(f"❌ 配置失败：{e}")
    print(f"stderr: {e.stderr}")
    exit(1)
except Exception as e:
    print(f"❌ 错误：{e}")
    exit(1)
