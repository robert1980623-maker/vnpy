#!/bin/bash
# 选股结果同步到飞书多维表格
# 用法：./sync_stock_to_feishu.sh 2026-03-27

set -e

DATE=${1:-$(date +%Y-%m-%d)}
REPORTS_DIR="/Users/rowang/projects/vnpy/examples/alpha_research/reports"
REPORT_FILE="$REPORTS_DIR/stock_selection_$DATE.json"

echo "======================================================================"
echo "                    选股结果同步到飞书多维表格"
echo "======================================================================"
echo "日期：$DATE"
echo "报告：$REPORT_FILE"
echo "======================================================================"

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ 报告文件不存在：$REPORT_FILE"
    exit 1
fi

# 使用 Python 读取报告并生成同步命令
python3 << PYEOF
import json
from datetime import datetime

# 加载报告
with open('$REPORT_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data.get('stocks', [])
date_str = data.get('date', '$DATE')
date_obj = datetime.strptime(date_str, '%Y-%m-%d')
date_timestamp = int(date_obj.timestamp() * 1000)

print(f"\n📊 准备同步 {len(stocks)} 条记录...")

# 生成 records JSON
records = []
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

# 写入临时文件
with open('/tmp/feishu_sync_records.json', 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"📝 记录已写入：/tmp/feishu_sync_records.json")
PYEOF

# 使用 OpenClaw 调用飞书工具
echo ""
echo "📱 调用 OpenClaw 飞书工具..."

openclaw feishu_bitable_app_table_record batch_create \
    --app_token "YpWLbsLAfaXw3HsprKfcj0AFnrh" \
    --table_id "tblyihWO0zsV9xqw" \
    --records "$(cat /tmp/feishu_sync_records.json)" \
    2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 同步成功！"
    
    # 更新状态文件
    python3 << PYEOF
import json
from datetime import datetime

with open('/tmp/feishu_sync_records.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

sync_data = {
    'type': 'stock_selection_sync',
    'date': '$DATE',
    'records': [r['fields'] for r in records],
    'status': 'completed',
    'created_at': datetime.now().isoformat(),
    'completed_at': datetime.now().isoformat()
}

with open('/tmp/feishu_sync_request.json', 'w', encoding='utf-8') as f:
    json.dump(sync_data, f, ensure_ascii=False, indent=2)

print("📝 状态文件已更新：/tmp/feishu_sync_request.json")
PYEOF
else
    echo "❌ 同步失败"
    exit 1
fi

echo ""
echo "======================================================================"
echo "                    ✅ 同步完成"
echo "======================================================================"
