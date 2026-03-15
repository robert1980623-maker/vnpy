#!/usr/bin/env python3
"""
直接配置每小时增强报告 cron 任务
使用 OpenClaw sessions_spawn API
"""

import json
import sys
from pathlib import Path

# 添加 OpenClaw workspace 路径
sys.path.insert(0, '/Users/rowang/.openclaw/workspace')

try:
    from sessions_spawn import sessions_spawn
    
    print("🔧 开始配置每小时增强报告 cron 任务...")
    print()
    
    # 配置
    config = {
        "task": "cd /Users/rowang/projects/vnpy/examples/alpha_research && /Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py",
        "label": "每小时增强报告",
        "mode": "session",
        "runtime": "subagent",
        "timeoutSeconds": 120,
        "cleanup": "keep"
    }
    
    print("📋 配置信息:")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    print()
    
    # 创建会话
    print("🚀 创建子代理会话...")
    result = sessions_spawn(**config)
    
    print("✅ 创建成功！")
    print()
    print("会话信息:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
except Exception as e:
    print(f"❌ 错误：{e}")
    print()
    print("⚠️  请使用 OpenClaw Web 界面手动创建 cron 任务")
    print()
    print("配置 JSON:")
    print(json.dumps({
        "name": "每小时增强报告",
        "schedule": "0 * * * *",
        "command": "/Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py",
        "channel": "D0AJBBDDD9S"
    }, ensure_ascii=False, indent=2))
