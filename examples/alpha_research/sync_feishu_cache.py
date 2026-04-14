#!/usr/bin/env python3
"""
从飞书多维表格同步数据到本地缓存
在 Cron 任务开始时执行，确保检查脚本读到最新数据
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加 OpenClaw 飞书工具路径
sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')

try:
    from openclaw_lark import feishu_bitable_app_table_record
    FEISHU_AVAILABLE = True
except ImportError:
    print("⚠️ 飞书工具不可用")
    FEISHU_AVAILABLE = False
    sys.exit(1)

# 配置
APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
ACCOUNT_TABLE = "tblMqYRdqBjhMnik"  # 虚拟账户表
POSITION_TABLE = "tblLHrg7fFOcN0to"  # 持仓记录表
CACHE_DIR = Path(__file__).parent / "data" / "feishu_cache"
CACHE_DIR.mkdir(exist_ok=True)

def sync_account():
    """同步账户数据"""
    try:
        result = feishu_bitable_app_table_record(
            action="list",
            app_token=APP_TOKEN,
            table_id=ACCOUNT_TABLE,
            page_size=10
        )
        if result and result.get("items"):
            item = result["items"][0]
            fields = item.get("fields", {})
            cache_data = {
                "account_id": fields.get("账户 ID", "ACC001"),
                "account_name": fields.get("账户名称", "王雅轩主账户"),
                "initial_capital": float(fields.get("初始资金", 1000000)),
                "current_cash": float(fields.get("现金余额", fields.get("当前资金", 1000000))),
                "currency": "CNY",
                "status": fields.get("状态", "active"),
                "updated_at": datetime.now().isoformat()
            }
            with open(CACHE_DIR / "account.json", "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 账户数据已同步：现金余额 ¥{cache_data['current_cash']:,.2f}")
            return cache_data
    except Exception as e:
        print(f"❌ 同步账户数据失败：{e}")
    return None

def sync_positions():
    """同步持仓数据"""
    try:
        result = feishu_bitable_app_table_record(
            action="list",
            app_token=APP_TOKEN,
            table_id=POSITION_TABLE,
            page_size=100
        )
        if result and result.get("items"):
            positions = []
            for item in result["items"]:
                fields = item.get("fields", {})
                symbol = fields.get("股票代码", "")
                if symbol:
                    positions.append({
                        "symbol": symbol,
                        "name": fields.get("股票名称", ""),
                        "quantity": int(fields.get("持仓数量", 0)),
                        "avg_price": float(fields.get("平均成本", 0)),
                        "cost": float(fields.get("持仓数量", 0)) * float(fields.get("平均成本", 0))
                    })
            with open(CACHE_DIR / "positions.json", "w", encoding="utf-8") as f:
                json.dump(positions, f, ensure_ascii=False, indent=2)
            print(f"✅ 持仓数据已同步：{len(positions)} 只股票")
            return positions
    except Exception as e:
        print(f"❌ 同步持仓数据失败：{e}")
    return None

if __name__ == "__main__":
    print("🔄 开始同步飞书数据到本地缓存...")
    sync_account()
    sync_positions()
    print("✅ 同步完成")
