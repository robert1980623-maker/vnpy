#!/bin/bash
# 完整交易流程一键启动脚本
# 用于测试和演示

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 主流程
main() {
    echo "======================================================================"
    echo "                    完整交易流程演示"
    echo "======================================================================"
    echo "日期：$(date '+%Y-%m-%d %H:%M:%S')"
    echo "模式：模拟交易"
    echo ""
    
    # 1. 多策略选股
    print_info "【09:00】开始多策略选股..."
    python3 daily_stock_selection.py
    print_success "选股完成"
    echo ""
    
    # 2. 消息面分析
    print_info "【09:30】开始消息面分析..."
    python3 news_analyzer.py
    print_success "消息面分析完成"
    echo ""
    
    # 3. 执行交易
    print_info "【14:50】开始执行交易..."
    python3 start_trading.py --mode paper
    print_success "交易执行完成"
    echo ""
    
    # 4. 每日复盘
    print_info "【20:00】开始每日复盘..."
    python3 daily_review.py
    print_success "复盘完成"
    echo ""
    
    echo "======================================================================"
    echo "                    所有任务完成!"
    echo "======================================================================"
    echo ""
    print_info "查看报告:"
    echo "  - 选股报告：cat reports/stock_selection_*.json"
    echo "  - 交易计划：cat reports/trading_plan_*.json"
    echo "  - 每日复盘：cat reports/daily/daily_review_*.json"
    echo "  - 消息分析：cat reports/news/news_analysis_*.json"
    echo ""
    print_info "查看日志:"
    echo "  - tail -f logs/*.log"
    echo ""
}

# 运行主流程
main "$@"
