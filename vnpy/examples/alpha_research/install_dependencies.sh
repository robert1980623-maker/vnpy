#!/bin/bash
# vnpy 项目依赖快速安装脚本

echo "=================================================="
echo "vnpy 项目 - 依赖安装"
echo "=================================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✓ Python 版本：$(python3 --version)"
echo ""

# 1. 安装基础依赖
echo "📦 安装基础依赖..."
pip3 install pandas numpy --break-system-packages 2>/dev/null || \
pip3 install pandas numpy

echo ""

# 2. 安装 AKShare
echo "📦 安装 AKShare（主数据源）..."
pip3 install akshare --break-system-packages 2>/dev/null || \
pip3 install akshare

echo ""

# 3. 安装 Baostock（备选数据源）
echo "📦 安装 Baostock（备选数据源）..."
pip3 install baostock --break-system-packages 2>/dev/null || \
pip3 install baostock

echo ""

# 4. 安装 tqdm（进度条）
echo "📦 安装 tqdm（进度条）..."
pip3 install tqdm --break-system-packages 2>/dev/null || \
pip3 install tqdm

echo ""

# 5. 安装 akshare-proxy-patch（可选）
echo "📦 安装 akshare-proxy-patch（可选，提高稳定性）..."
pip3 install akshare-proxy-patch --break-system-packages 2>/dev/null || \
pip3 install akshare-proxy_patch 2>/dev/null || \
echo "⚠️ akshare-proxy-patch 安装失败，可手动安装"

echo ""

# 6. 安装 PyYAML（配置支持）
echo "📦 安装 PyYAML（配置支持）..."
pip3 install pyyaml --break-system-packages 2>/dev/null || \
pip3 install pyyaml

echo ""

# 验证安装
echo "=================================================="
echo "验证安装"
echo "=================================================="
echo ""

python3 << 'EOF'
import sys

print("检查依赖...")
print("")

# 基础依赖
try:
    import pandas as pd
    print("✓ pandas:", pd.__version__)
except ImportError as e:
    print("✗ pandas:", e)

try:
    import numpy as np
    print("✓ numpy:", np.__version__)
except ImportError as e:
    print("✗ numpy:", e)

# 数据源
try:
    import akshare as ak
    print("✓ akshare:", ak.__version__)
except ImportError as e:
    print("✗ akshare:", e)

try:
    import baostock as bs
    print("✓ baostock: 已安装")
except ImportError as e:
    print("✗ baostock:", e)

# 可选依赖
try:
    from tqdm import tqdm
    print("✓ tqdm: 已安装")
except ImportError as e:
    print("✗ tqdm:", e)

try:
    import akshare_proxy_patch
    print("✓ akshare-proxy-patch: 已安装")
except ImportError as e:
    print("⚠ akshare-proxy-patch: 未安装（可选）")

try:
    import yaml
    print("✓ PyYAML: 已安装")
except ImportError as e:
    print("✗ PyYAML:", e)

print("")
print("==================================================")
print("安装完成！")
print("==================================================")
print("")
print("测试下载（5 只股票）:")
print("  python3 download_optimized.py --max 5 --workers 5")
print("")
print("日常使用（20 只股票）:")
print("  python3 download_optimized.py --max 20 --cache")
print("")
EOF
