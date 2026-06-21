#!/bin/bash
# 每日选股任务包装脚本
# 功能：执行选股脚本，然后同步到飞书多维表格

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/rowang/projects/vnpy/examples/alpha_research"
REPORTS_DIR="$PROJECT_DIR/reports"
TODAY=$(date +%Y-%m-%d)

# Fix PATH for cron
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Load environment variables (needed for cron)
# Use absolute path for cron compatibility
ZSHRC_PATH="/Users/rowang/.zshrc"

# Method 1: Direct grep from .zshrc (most reliable for cron)
if [ -f "$ZSHRC_PATH" ]; then
    echo "📌 从 ~/.zshrc 加载环境变量..."
    TUSHARE_TOKEN=$(grep -E "^export TUSHARE_TOKEN=" "$ZSHRC_PATH" | cut -d'=' -f2 | tr -d '"')
    echo "✅ TUSHARE_TOKEN 已加载 (长度：${#TUSHARE_TOKEN})"
fi

# Method 2: Try sourcing .zshrc
if [ -z "$TUSHARE_TOKEN" ] && [ -f "$ZSHRC_PATH" ]; then
    export TUSHARE_TOKEN=$(/bin/zsh -c "source $ZSHRC_PATH && echo \$TUSHARE_TOKEN" 2>/dev/null)
    echo "✅ TUSHARE_TOKEN 通过 zsh 加载 (长度：${#TUSHARE_TOKEN})"
fi

# Method 3: Load from .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env" 2>/dev/null || true
fi

# Verify token is loaded
if [ -z "$TUSHARE_TOKEN" ]; then
    echo "❌ 错误：TUSHARE_TOKEN 未设置"
    echo "请检查 ~/.zshrc 中是否配置了 TUSHARE_TOKEN"
    exit 1
fi

echo "✅ TUSHARE_TOKEN 已加载 (长度：${#TUSHARE_TOKEN})"

echo "======================================================================"
echo "                    每日选股任务 (含飞书同步)"
echo "======================================================================"
echo "日期：$TODAY"
echo "时间：$(date +%H:%M:%S)"
echo "======================================================================"

cd "$PROJECT_DIR"

# 检查数据是否存在
CSV_COUNT=$(ls -1 data/akshare/bars/*.csv 2>/dev/null | wc -l)
if [ "$CSV_COUNT" -eq 0 ]; then
    echo "❌ 错误：未找到股票数据文件"
    echo "请先运行数据下载："
    echo "  cd $PROJECT_DIR && ./batch_download_enhanced.sh"
    exit 1
fi

echo "✅ 股票数据：$CSV_COUNT 只股票"
echo ""

# 执行选股
echo "【执行选股】..."
export TUSHARE_TOKEN="$TUSHARE_TOKEN"
python3 daily_stock_selection.py 2>&1

# 检查报告是否生成
if [ -f "$REPORTS_DIR/stock_selection_$TODAY.json" ]; then
    echo ""
    echo "======================================================================"
    echo "                    ✅ 选股完成"
    echo "======================================================================"
    echo ""
    echo "📁 报告位置:"
    echo "   选股报告：$REPORTS_DIR/stock_selection_$TODAY.json"
    echo "   交易计划：$REPORTS_DIR/trading_plan_$TODAY.json"
    echo ""
    
    # 显示总结
    echo "📊 快速总结:"
    python3 -c "
import json
with open('$REPORTS_DIR/stock_selection_$TODAY.json') as f:
    data = json.load(f)
    print(f\"  总匹配：{data['total_count']} 只股票\")
    print(f\"  Top 3 股票:\")
    for i, stock in enumerate(data['stocks'][:3], 1):
        strategies = '+'.join(stock['strategies'])
        print(f\"    {i}. {stock['symbol']} {stock['name']} (得分：{stock['score']}, 策略：{strategies})\")
"
    echo ""
    
    # 同步到飞书多维表格
    echo "======================================================================"
    echo "                    同步到飞书多维表格"
    echo "======================================================================"
    python3 sync_to_feishu.py --date "$TODAY" 2>&1
    
    echo ""
    echo "======================================================================"
    echo "                    ✅ 任务全部完成"
    echo "======================================================================"
else
    echo "❌ 错误：选股报告未生成"
    exit 1
fi
