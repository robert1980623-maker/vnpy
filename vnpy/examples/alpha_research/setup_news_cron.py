#!/usr/bin/env python3
"""
配置消息面数据下载定时任务
每天 17:00 执行（与数据下载同步）
"""

import subprocess
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SHELL_SCRIPT = SCRIPT_DIR / "download_news.sh"

print(f"📋 配置消息面数据下载定时任务")
print(f"脚本：{SHELL_SCRIPT}")
print(f"时间：每天 17:00")
print()

# 使用 openclaw cron add 添加任务
cmd = [
    "openclaw", "cron", "add",
    "--name", "消息面数据下载",
    "--schedule", "cron 0 17 * * *",
    "--command", f"bash {SHELL_SCRIPT}",
    "--target", "isolated",
    "--agent-id", "data-agent"
]

print(f"执行命令：{' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("✅ 定时任务配置成功")
    print()
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"❌ 配置失败：{e}")
    print(f"stderr: {e.stderr}")
except Exception as e:
    print(f"❌ 错误：{e}")
