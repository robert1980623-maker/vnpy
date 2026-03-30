#!/usr/bin/env python3
"""
初级助理 - 飞书同步提醒

功能：在选股完成后 15 分钟，发送消息提醒 Q-Trade 处理飞书同步

用法：
    python3 assistant_remind_feishu_sync.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 同步请求文件路径
SYNC_REQUEST_FILE = Path('/tmp/feishu_sync_request.json')

# 提醒消息
REMIND_MESSAGE = """🔔 Q-Trade，选股同步提醒！

📊 检测到选股结果待同步到飞书多维表格
⏰ 请立即处理同步请求

文件：/tmp/feishu_sync_request.json
状态：pending

处理命令：
```bash
python3 /Users/rowang/projects/vnpy/examples/alpha_research/process_sync_requests.py
```

处理完成后记得向雅轩汇报结果哦～ 💪"""


def check_and_remind():
    """检查并发送提醒"""
    print("=" * 70)
    print(" " * 20 + "初级助理：飞书同步提醒")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查文件是否存在
    if not SYNC_REQUEST_FILE.exists():
        print("ℹ️  无同步请求文件，跳过提醒")
        return True
    
    # 加载请求
    try:
        with open(SYNC_REQUEST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 加载失败：{e}")
        return False
    
    # 检查状态
    status = data.get('status', 'unknown')
    date = data.get('date', 'unknown')
    records = data.get('records', [])
    
    print(f"📊 同步请求：{date}")
    print(f"📊 记录数量：{len(records)}")
    print(f"📊 当前状态：{status}")
    
    if status == 'completed':
        print("✅ 已完成，不需要提醒")
        return True
    
    if status == 'processing':
        print("⚠️  处理中，不需要提醒")
        return True
    
    # 需要提醒
    print("\n🔔 发送提醒消息...")
    print(REMIND_MESSAGE)
    
    # 输出提醒消息到临时文件，供调用方发送
    remind_file = Path('/tmp/feishu_remind_message.txt')
    with open(remind_file, 'w', encoding='utf-8') as f:
        f.write(REMIND_MESSAGE)
    
    print(f"\n✅ 提醒消息已写入：{remind_file}")
    print("📝 请调用方发送消息给 Q-Trade")
    
    return True


if __name__ == '__main__':
    success = check_and_remind()
    sys.exit(0 if success else 1)
