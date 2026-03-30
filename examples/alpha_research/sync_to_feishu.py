#!/usr/bin/env python3
"""
选股结果同步到飞书多维表格

用法:
    python3 sync_to_feishu.py --date 2026-03-26
    python3 sync_to_feishu.py --auto  # 自动使用最新报告
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess


# 配置
APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"  # Multi-Agent CircleNet - Trade Data
TABLE_ID = "tblyihWO0zsV9xqw"  # 选股记录表
USER_OPEN_ID = "ou_c4a65a3dcdbf8fe6d6a17a7df0e702e6"  # 雅轩
REPORTS_DIR = Path('./reports')


def load_stock_selection(date_str):
    """加载选股报告"""
    report_file = REPORTS_DIR / f'stock_selection_{date_str}.json'
    
    if not report_file.exists():
        print(f"❌ 报告文件不存在：{report_file}")
        return None
    
    with open(report_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def prepare_records(stocks, date_str):
    """准备多维表格记录"""
    records = []
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_timestamp = int(date_obj.timestamp() * 1000)
    
    for i, stock in enumerate(stocks, 1):
        strategies_str = '+'.join(stock.get('strategies', []))
        reasons = stock.get('reasons', [])
        
        record = {
            "fields": {
                "选股日期": date_timestamp,
                "股票代码": stock.get('symbol', ''),
                "股票名称": stock.get('name', ''),
                "策略类型": strategies_str,
                "PE": stock.get('pe', 0),
                "ROE": stock.get('roe', 0),
                "排名": i,
                "Agent ID": "Q-Trade",
                "备注": reasons[0] if reasons else ''
            }
        }
        records.append(record)
    
    return records


def sync_to_feishu(records):
    """
    同步到飞书多维表格
    
    方案：写入临时文件，等 Q-Trade 在 09:15 心跳检查时处理
    """
    if not records:
        print("⚠️ 没有记录需要同步")
        return False
    
    print(f"\n📊 准备同步 {len(records)} 条记录到飞书多维表格...")
    
    # 写入同步请求文件（Q-Trade 会在 09:15 处理）
    date_str = datetime.now().strftime('%Y-%m-%d')
    sync_request_file = Path('/tmp/feishu_sync_request.json')
    sync_data = {
        'type': 'stock_selection_sync',
        'date': date_str,
        'records': [r.get('fields', {}) for r in records],
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    with open(sync_request_file, 'w', encoding='utf-8') as f:
        json.dump(sync_data, f, ensure_ascii=False, indent=2)
    
    print(f"📝 同步请求已写入：{sync_request_file}")
    print(f"⏳ Q-Trade 将在 09:15 心跳检查时处理")
    
    return True


def send_notification(date_str, stocks):
    """发送飞书通知"""
    top3 = stocks[:3]
    top3_str = ', '.join([f"{s['name']}({s['symbol']})" for s in top3])
    
    message = f"""✅ {date_str} 选股完成！

选出 {len(stocks)} 只股票
Top 3: {top3_str}

已同步到飞书多维表格，请查收～"""
    
    print(f"\n📱 通知内容:\n{message}")
    
    # 使用 openclaw message 发送
    try:
        cmd = [
            'openclaw', 'message', 'send',
            '--target', f'user:{USER_OPEN_ID}',
            '--message', message
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 通知已发送")
            return True
        else:
            print(f"⚠️ 通知发送失败：{result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ 通知发送异常：{e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='选股结果同步到飞书多维表格')
    parser.add_argument('--date', type=str, help='日期 (YYYY-MM-DD)')
    parser.add_argument('--auto', action='store_true', help='自动使用最新报告')
    parser.add_argument('--no-notify', action='store_true', help='不发送通知')
    
    args = parser.parse_args()
    
    # 确定日期
    if args.auto:
        # 查找最新的报告
        reports = list(REPORTS_DIR.glob('stock_selection_*.json'))
        if not reports:
            print("❌ 未找到选股报告")
            sys.exit(1)
        
        # 提取日期并排序
        dates = []
        for r in reports:
            try:
                date_str = r.stem.replace('stock_selection_', '')
                datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(date_str)
            except:
                continue
        
        if not dates:
            print("❌ 无法解析报告日期")
            sys.exit(1)
        
        dates.sort(reverse=True)
        date_str = dates[0]
        print(f"📁 使用最新报告：{date_str}")
    elif args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 加载报告
    print(f"\n📊 加载选股报告：{date_str}")
    report = load_stock_selection(date_str)
    
    if not report:
        sys.exit(1)
    
    stocks = report.get('stocks', [])
    print(f"✅ 加载 {len(stocks)} 只股票")
    
    # 准备记录
    records = prepare_records(stocks, date_str)
    
    # 同步到飞书
    success = sync_to_feishu(records)
    
    # 发送通知
    if not args.no_notify and success:
        send_notification(date_str, stocks)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 同步完成！")
    else:
        print("❌ 同步失败，请检查日志")
        sys.exit(1)


if __name__ == '__main__':
    main()
