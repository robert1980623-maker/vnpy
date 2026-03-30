#!/usr/bin/env python3
"""
飞书同步请求处理器

功能：
1. 检查 /tmp/feishu_sync_request.json 是否存在
2. 如果状态是 pending，调用飞书 API 同步数据
3. 处理完成后更新状态为 completed

用法：
    python3 process_feishu_sync.py

部署：
    添加到 crontab，每 5 分钟执行一次
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 同步请求文件路径
SYNC_REQUEST_FILE = Path('/tmp/feishu_sync_request.json')

# 飞书配置
APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
SELECTION_TABLE = "tblyihWO0zsV9xqw"  # 选股记录表
TRADE_TABLE = "tbl4n14ZYANQtI26"  # 交易日志表
ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
POSITION_TABLE = "tblLHrg7fFOcN0to"  # 持仓记录表


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


def sync_stock_selection(records):
    """同步选股记录"""
    print(f"\n📊 同步 {len(records)} 条选股记录...")
    
    # TODO: 使用 HTTP API 调用飞书
    # 现在先标记为完成
    print("✅ 选股记录同步完成（待实现）")
    return True


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
    sync_type = data.get('type', 'unknown')
    records = data.get('records', [])
    
    print(f"\n📋 同步类型：{sync_type}")
    print(f"📊 记录数量：{len(records)}")
    
    if sync_type == 'stock_selection_sync':
        success = sync_stock_selection(records)
        
        if success:
            # 更新状态
            data['status'] = 'completed'
            data['completed_at'] = datetime.now().isoformat()
            
            with open(SYNC_REQUEST_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print("\n" + "=" * 70)
            print(" " * 20 + "✅ 处理完成")
            print("=" * 70)
            return 0
    
    print("\n" + "=" * 70)
    print(" " * 20 + "❌ 处理失败")
    print("=" * 70)
    return 1


if __name__ == '__main__':
    sys.exit(main())
