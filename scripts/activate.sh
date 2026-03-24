#!/bin/bash
# VNPY 环境快速激活脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_ROOT/examples/alpha_research/venv-py313"

echo "🚀 VNPY 环境激活"
echo "=" * 40

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 虚拟环境不存在：$VENV_PATH"
    return 1
fi

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 加载环境变量
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    echo "✅ .env 已加载"
fi

# 运行环境检查
echo ""
python "$SCRIPT_DIR/check_environment.py"

echo ""
echo "💡 提示：运行 'deactivate' 退出环境"
