#!/usr/bin/env python3
"""
飞书多维表格同步请求处理脚本

功能：
1. 检查 /tmp/feishu_sync_request.json 是否存在
2. 如果状态是 pending/processing，调用飞书 API 同步数据
3. 处理完成后更新状态为 completed

用法：
    python3 process_sync_requests.py
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 同步请求文件路径
SYNC_REQUEST_FILE = Path('/tmp/feishu_sync_request.json')
SYNC_COMMAND_FILE = Path('/tmp/feishu_sync_command.json')

# 飞书多维表格配置
APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"  # Multi-Agent CircleNet - Trade Data
TABLE_ID = "tblyihWO0zsV9xqw"  # 选股记录表


def load_sync_request():
    """加载同步请求"""
    if not SYNC_REQUEST_FILE.exists():
        return None
    
    try:
        with open(SYNC_REQUEST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ 加载失败：{e}")
        return None


def sync_to_feishu(records):
    """同步到飞书多维表格"""
    if not records:
        print("⚠️  没有记录需要同步")
        return False
    
    print(f"\n📊 准备同步 {len(records)} 条记录到飞书多维表格...")
    
    # 使用 feishu_bitable_app_table_record 工具
    # 由于这是独立脚本，我们通过 Python 直接调用飞书 API
    
    # 准备记录数据
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
    
    # 调用飞书 API（通过 OpenClaw 的 Python 工具）
    # 注意：这里需要导入飞书工具
    try:
        # 使用 subprocess 调用 Python 脚本执行飞书 API 调用
        sync_script = f'''
import sys
import json
sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')

# 导入飞书工具
from openclaw_lark import feishu_bitable_app_table_record

records = {json.dumps(feishu_records, ensure_ascii=False)}

result = feishu_bitable_app_table_record(
    action='batch_create',
    app_token='{APP_TOKEN}',
    table_id='{TABLE_ID}',
    records=records
)

print(json.dumps(result, ensure_ascii=False))
'''
        
        result = subprocess.run(
            ['python3', '-c', sync_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ 同步成功")
            print(result.stdout[:200])
            return True
        else:
            print(f"❌ 同步失败：{result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 同步异常：{e}")
        return False


def mark_completed(data):
    """标记同步完成"""
    data['status'] = 'completed'
    data['completed_at'] = datetime.now().isoformat()
    
    with open(SYNC_REQUEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 清理临时文件
    if SYNC_COMMAND_FILE.exists():
        SYNC_COMMAND_FILE.unlink()
    
    print(f"✅ 同步完成，状态已更新")


def main():
    print("=" * 70)
    print(" " * 20 + "飞书同步请求处理")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"文件：{SYNC_REQUEST_FILE}")
    print("=" * 70)
    
    # 加载同步请求
    data = load_sync_request()
    
    if data is None:
        print("\nℹ️  没有待处理的同步请求")
        return 0
    
    # 检查状态
    status = data.get('status', 'unknown')
    if status == 'completed':
        print(f"✅ 同步已完成，跳过")
        return 0
    
    if status == 'processing':
        print(f"⚠️  同步正在处理中，跳过")
        return 0
    
    # 处理同步
    records = data.get('records', [])
    success = sync_to_feishu(records)
    
    if success:
        mark_completed(data)
        print("\n" + "=" * 70)
        print(" " * 20 + "✅ 处理完成")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(" " * 20 + "❌ 处理失败")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
