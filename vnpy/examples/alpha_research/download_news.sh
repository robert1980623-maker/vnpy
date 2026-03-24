#!/bin/bash
# 消息面数据下载脚本
# 每天 17:00 执行，与数据下载同步

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/news_$(date +%Y-%m-%d_%H-%M-%S).log"

echo "=========================================="
echo "消息面数据下载"
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 激活 venv
if [ -d "$SCRIPT_DIR/../../venv" ]; then
    source "$SCRIPT_DIR/../../venv/bin/activate"
    echo "✓ 已激活 venv"
else
    echo "⚠️ 未找到 venv，使用系统 Python"
fi

# 执行下载
python3 download_news_data.py 2>&1 | tee "$LOG_FILE"

echo ""
echo "=========================================="
echo "完成"
echo "日志：$LOG_FILE"
echo "=========================================="
