#!/bin/bash
# 股票数据下载脚本
# 用于定时任务调用

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "股票数据定时下载任务"
echo "执行时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# 切换目录
cd ~/projects/vnpy/examples/alpha_research

# 激活虚拟环境
if [ -f ../../venv/bin/activate ]; then
    source ../../venv/bin/activate
    echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
else
    echo -e "${RED}✗ 虚拟环境不存在${NC}"
    exit 1
fi

# 设置 PYTHONPATH
export PYTHONPATH=../..

# 执行下载
echo ""
echo "开始下载股票数据..."
echo -e "${YELLOW}模式：夜间下载${NC}"
echo -e "${YELLOW}数量：最多 20 只股票${NC}"
echo -e "${YELLOW}缓存：自动启用${NC}"
echo ""

python download_data_akshare.py --night-mode --max 20

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo -e "${GREEN}✓ 下载任务完成！${NC}"
    echo "完成时间：$(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"
    
    # 显示下载统计
    if [ -d "./data/akshare/bars" ]; then
        count=$(ls -1 ./data/akshare/bars/*.csv 2>/dev/null | wc -l)
        echo -e "${GREEN}  累计下载：$count 只股票${NC}"
    fi
else
    echo ""
    echo "============================================================"
    echo -e "${RED}✗ 下载任务失败${NC}"
    echo "失败时间：$(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"
    exit 1
fi
