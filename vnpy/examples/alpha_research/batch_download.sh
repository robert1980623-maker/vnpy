#!/bin/bash
# 分批下载股票数据
# 每批 5 只，批次间隔 30 秒

# 加载 TUSHARE_TOKEN 环境变量（如果存在）
if [ -n "$TUSHARE_TOKEN" ]; then
    echo "✓ TUSHARE_TOKEN 已设置"
else
    # 尝试从 .zshrc 中提取 TUSHARE_TOKEN
    if [ -f ~/.zshrc ]; then
        TUSHARE_TOKEN=$(grep -E "^export TUSHARE_TOKEN=" ~/.zshrc 2>/dev/null | cut -d'=' -f2 | tr -d "'" | tr -d '"')
        if [ -n "$TUSHARE_TOKEN" ]; then
            export TUSHARE_TOKEN
            echo "✓ 从 ~/.zshrc 加载 TUSHARE_TOKEN"
        fi
    fi
fi

cd /Users/rowang/projects/vnpy/examples/alpha_research

echo "======================================================================"
echo "                    分批下载股票数据"
echo "======================================================================"
echo "每批：5 只股票"
echo "间隔：30 秒"
echo "总数：20 只"
echo "======================================================================"

# 第 1 批
echo ""
echo "[批次 1/4] 下载第 1-5 只股票..."
python3 download_data_akshare.py --max 5
echo "[批次 1 完成] 等待 30 秒..."
sleep 30

# 第 2 批
echo ""
echo "[批次 2/4] 下载第 6-10 只股票..."
python3 download_data_akshare.py --max 5
echo "[批次 2 完成] 等待 30 秒..."
sleep 30

# 第 3 批
echo ""
echo "[批次 3/4] 下载第 11-15 只股票..."
python3 download_data_akshare.py --max 5
echo "[批次 3 完成] 等待 30 秒..."
sleep 30

# 第 4 批
echo ""
echo "[批次 4/4] 下载第 16-20 只股票..."
python3 download_data_akshare.py --max 5
echo "[批次 4 完成]"

echo ""
echo "======================================================================"
echo "                    下载完成！"
echo "======================================================================"
echo "验证数据："
ls -lh data/akshare/bars/*.csv | wc -l
echo "======================================================================"
