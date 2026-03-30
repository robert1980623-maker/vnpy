#!/usr/bin/env python3
"""
飞书同步请求处理器 - Q-Trade 专用版本

功能：
1. 检查 /tmp/feishu_sync_request.json 是否存在
2. 根据同步类型调用飞书 API
3. 处理完成后更新状态

用法：
    在 Q-Trade 会话中调用：
    python3 process_feishu_sync_qtrade.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加 OpenClaw 飞书工具路径
sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')

try:
    from openclaw_lark import (
        feishu_bitable_app_table_record,
        feishu_bitable_app_table
    )
    FEISHU_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 飞书工具不可用：{e}")
    FEISHU_AVAILABLE = False

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
    """
    同步选股记录到飞书多维表格
    
    Args:
        records: 记录列表，每个元素是 fields 字典
    """
    if not records:
        print("⚠️ 没有选股记录需要同步")
        return False
    
    print(f"\n📊 同步 {len(records)} 条选股记录...")
    
    try:
        # 批量创建
        result = feishu_bitable_app_table_record(
            action='batch_create',
            app_token=APP_TOKEN,
            table_id=SELECTION_TABLE,
            records=[{"fields": r} for r in records]
        )
        
        if result.get('records'):
            print(f"✅ 选股记录同步成功！写入 {len(result['records'])} 条")
            return True
        else:
            print(f"❌ 选股记录同步失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 选股记录同步异常：{e}")
        return False


def sync_trade_records(records):
    """
    同步交易记录到飞书多维表格
    
    Args:
        records: 交易记录列表
    """
    if not records:
        print("⚠️ 没有交易记录需要同步")
        return False
    
    print(f"\n📊 同步 {len(records)} 条交易记录...")
    
    try:
        # 批量创建
        result = feishu_bitable_app_table_record(
            action='batch_create',
            app_token=APP_TOKEN,
            table_id=TRADE_TABLE,
            records=[{"fields": r} for r in records]
        )
        
        if result.get('records'):
            print(f"✅ 交易记录同步成功！写入 {len(result['records'])} 条")
            return True
        else:
            print(f"❌ 交易记录同步失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 交易记录同步异常：{e}")
        return False


def sync_account(cash, update_time=None):
    """
    同步账户资金到飞书多维表格
    
    Args:
        cash: 当前资金
        update_time: 更新时间戳（毫秒）
    """
    print(f"\n💰 同步账户资金：{cash:,.2f} 元...")
    
    try:
        result = feishu_bitable_app_table_record(
            action='update',
            app_token=APP_TOKEN,
            table_id=ACCOUNT_TABLE,
            record_id='recveSFVVfD6EJ',  # 主账户记录 ID
            fields={
                "当前资金": cash,
                "更新时间": update_time or int(datetime.now().timestamp() * 1000)
            }
        )
        
        print(f"✅ 账户资金同步成功！")
        return True
        
    except Exception as e:
        print(f"❌ 账户资金同步异常：{e}")
        return False


def sync_positions(records):
    """
    同步持仓记录到飞书多维表格
    
    Args:
        records: 持仓记录列表
    """
    if not records:
        print("⚠️ 没有持仓记录需要同步")
        return False
    
    print(f"\n📊 同步 {len(records)} 条持仓记录...")
    
    try:
        # 批量创建
        result = feishu_bitable_app_table_record(
            action='batch_create',
            app_token=APP_TOKEN,
            table_id=POSITION_TABLE,
            records=[{"fields": r} for r in records]
        )
        
        if result.get('records'):
            print(f"✅ 持仓记录同步成功！写入 {len(result['records'])} 条")
            return True
        else:
            print(f"❌ 持仓记录同步失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 持仓记录同步异常：{e}")
        return False


def mark_completed(data):
    """标记同步完成"""
    data['status'] = 'completed'
    data['completed_at'] = datetime.now().isoformat()
    
    with open(SYNC_REQUEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 同步状态已更新为 completed")


def process_sync_request():
    """
    处理同步请求
    
    Returns:
        bool: 是否成功处理
    """
    # 加载同步请求
    data = load_sync_request()
    
    if data is None:
        print("\nℹ️  没有待处理的同步请求")
        return False
    
    # 检查状态
    status = data.get('status', 'unknown')
    if status == 'completed':
        print(f"✅ 同步已完成，跳过")
        return False
    
    if status == 'processing':
        print(f"⚠️  同步正在处理中，跳过")
        return False
    
    # 检查飞书工具是否可用
    if not FEISHU_AVAILABLE:
        print(f"❌ 飞书工具不可用，无法同步")
        return False
    
    # 处理同步
    sync_type = data.get('type', 'unknown')
    records = data.get('records', [])
    
    print(f"\n📋 同步类型：{sync_type}")
    print(f"📊 记录数量：{len(records)}")
    
    success = False
    
    if sync_type == 'stock_selection_sync':
        success = sync_stock_selection(records)
    elif sync_type == 'trade_sync':
        success = sync_trade_records(records)
    elif sync_type == 'account_sync':
        success = sync_account(
            data.get('cash', 0),
            data.get('update_time')
        )
    elif sync_type == 'position_sync':
        success = sync_positions(records)
    else:
        print(f"⚠️  未知同步类型：{sync_type}")
    
    # 更新状态
    if success:
        mark_completed(data)
        return True
    else:
        print(f"\n❌ 同步失败")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "飞书同步请求处理 (Q-Trade)")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"文件：{SYNC_REQUEST_FILE}")
    print(f"飞书工具：{'✅ 可用' if FEISHU_AVAILABLE else '❌ 不可用'}")
    print("=" * 70)
    
    success = process_sync_request()
    
    print("\n" + "=" * 70)
    if success:
        print(" " * 20 + "✅ 处理完成")
    else:
        print(" " * 20 + "ℹ️  无需处理或处理失败")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
