#!/usr/bin/env python3
"""创建每小时增强报告 cron 任务"""

import json
import subprocess
from pathlib import Path

# 读取配置
config_file = Path(__file__).parent / 'hourly_report_cron_config.json'
with open(config_file, 'r') as f:
    config = json.load(f)

# 构建完整的 cron 任务配置
cron_config = {
    "name": config['name'],
    "description": config['description'],
    "agentId": config['agentId'],
    "schedule": config['schedule'],
    "sessionTarget": config['sessionTarget'],
    "wakeMode": config['wakeMode'],
    "payload": config['payload'],
    "delivery": config['delivery'],
    "timeoutSeconds": config['timeoutSeconds']
}

# 保存到临时文件
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(cron_config, f, ensure_ascii=False, indent=2)
    temp_file = f.name

print(f"✅ 配置已保存到：{temp_file}")
print()
print("配置内容:")
print(json.dumps(cron_config, ensure_ascii=False, indent=2))
print()
print("⚠️  由于 openclaw cron add 命令语法限制，建议手动创建:")
print()
print("1. 复制以上配置")
print("2. 使用 openclaw web 界面创建")
print("3. 或者联系 OpenClaw 支持获取正确的 CLI 语法")
