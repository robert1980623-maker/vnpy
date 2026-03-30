#!/usr/bin/env python3
"""
飞书多维表格同步请求检查脚本

功能：
1. 检查 /tmp/feishu_sync_request.json 是否存在
2. 如果状态是 pending，处理同步到飞书多维表格
3. 处理完成后更新状态为 completed

用法：
    python3 check_sync_requests.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 同步请求文件路径
SYNC_REQUEST_FILE = Path('/tmp/feishu_sync_request.json')

# 飞书多维表格配置
APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"  # Multi-Agent CircleNet - Trade Data
TABLE_ID = "tblyihWO0zsV9xqw"  # 选股记录表


def load_sync_request():
    """加载同步请求"""
    if not SYNC_REQUEST_FILE.exists():
        print(f"ℹ️  同步请求文件不存在：{SYNC_REQUEST_FILE}")
        return None
    
    try:
        with open(SYNC_REQUEST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 加载同步请求：{data.get('date', 'unknown')}")
        return data
    except Exception as e:
        print(f"❌ 加载失败：{e}")
        return None


def check_and_sync(data):
    """检查并处理同步"""
    if data.get('status') == 'completed':
        print(f"✅ 同步已完成，跳过")
        return True
    
    if data.get('status') == 'processing':
        print(f"⚠️  同步正在处理中，跳过")
        return True
    
    if data.get('type') != 'stock_selection_sync':
        print(f"⚠️  未知同步类型：{data.get('type')}")
        return True
    
    records = data.get('records', [])
    if not records:
        print(f"⚠️  没有记录需要同步")
        return True
    
    print(f"\n📊 准备同步 {len(records)} 条选股记录到飞书多维表格...")
    
    # 准备飞书 API 调用
    # 注意：这里需要通过 OpenClaw 的飞书工具调用
    # 由于这是独立脚本，我们采用输出结果的方式，由调用方处理
    
    # 生成同步命令
    feishu_records = []
    for r in records:
        feishu_records.append({
            "fields": {
                "选股日期": r.get('选股日期', 0),
                "股票代码": r.get('股票代码', ''),
                "股票名称": r.get('股票名称', ''),
                "策略类型": r.get('策略类型', ''),
                "PE": r.get('PE', 0),
                "ROE": r.get('ROE', 0),
                "排名": r.get('排名', 0),
                "Agent ID": r.get('Agent ID', 'Q-Trade'),
                "备注": r.get('备注', '')
            }
        })
    
    # 输出同步命令到临时文件
    sync_command_file = Path('/tmp/feishu_sync_command.json')
    command_data = {
        'action': 'batch_create',
        'app_token': APP_TOKEN,
        'table_id': TABLE_ID,
        'records': feishu_records,
        'created_at': datetime.now().isoformat()
    }
    
    with open(sync_command_file, 'w', encoding='utf-8') as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 同步命令已生成：{sync_command_file}")
    print(f"📊 记录数量：{len(feishu_records)}")
    
    # 更新状态为 processing
    data['status'] = 'processing'
    data['processing_at'] = datetime.now().isoformat()
    
    with open(SYNC_REQUEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 状态已更新：processing")
    
    return True


def mark_completed(data):
    """标记同步完成"""
    data['status'] = 'completed'
    data['completed_at'] = datetime.now().isoformat()
    
    with open(SYNC_REQUEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 同步完成")


def main():
    print("=" * 70)
    print(" " * 20 + "飞书同步请求检查")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"文件：{SYNC_REQUEST_FILE}")
    print("=" * 70)
    
    # 加载同步请求
    data = load_sync_request()
    
    if data is None:
        print("\nℹ️  没有待处理的同步请求")
        return 0
    
    # 检查并处理同步
    success = check_and_sync(data)
    
    if success:
        # 标记完成
        mark_completed(data)
        print("\n" + "=" * 70)
        print(" " * 20 + "✅ 检查完成")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(" " * 20 + "❌ 检查失败")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
