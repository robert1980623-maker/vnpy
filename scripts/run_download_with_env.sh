#!/bin/bash
# =============================================================================
# VNPY 数据下载 Wrapper 脚本
# =============================================================================
# 用途: 在 cron 环境中正确加载环境变量和虚拟环境后执行下载命令
#
# 问题背景:
#   Cron 任务运行在最小化 shell 环境中，不会加载 .zshrc / .bash_profile，
#   导致 TUSHARE_TOKEN 等关键环境变量缺失，数据下载失败。
#
# 用法:
#   scripts/run_download_with_env.sh <python_script> [args...]
#
# 示例 (在 cron_config.yaml 中):
#   command: "${VNPY_DIR}/scripts/run_download_with_env.sh download_data_akshare.py --end 2026-06-24"
#
# 工作流程:
#   1. 加载项目根目录 .env (TUSHARE_TOKEN, AKSHARE_PROXY 等)
#   2. 加载 alpha_research/.env (兼容已有脚本的 _load_env)
#   3. 激活 Python 虚拟环境
#   4. cd 到工作目录并执行命令
# =============================================================================

set -euo pipefail

# ==================== 路径配置 ====================
VNPY_DIR="/Users/rowang/projects/vnpy"
PROJECT_ROOT="$VNPY_DIR"
WORK_DIR="$VNPY_DIR/examples/alpha_research"
VENV_PATH="$WORK_DIR/venv"

# ==================== 日志配置 ====================
LOG_DIR="$WORK_DIR/logs/wrapper"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_$(date '+%Y%m%d_%H%M%S').log"

# ==================== 辅助函数 ====================

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

load_env_file() {
    local env_file="$1"
    if [ ! -f "$env_file" ]; then
        log "⚠️  .env 文件不存在: $env_file"
        return 1
    fi
    local count=0
    while IFS= read -r line || [ -n "$line" ]; do
        # 跳过空行和注释
        line="$(echo "$line" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
        [ -z "$line" ] && continue
        [[ "$line" == \#* ]] && continue
        [[ "$line" != *=* ]] && continue
        local key="${line%%=*}"
        local value="${line#*=}"
        # 去除引号
        value="$(echo "$value" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//')"
        # 只设置未存在的环境变量 (不覆盖已有值)
        if [ -z "${!key+x}" ]; then
            export "$key=$value"
            count=$((count + 1))
        fi
    done < "$env_file"
    log "✅ 已加载 $env_file ($count 个变量)"
    return 0
}

# ==================== 主流程 ====================

log "=========================================="
log "🚀 VNPY 下载 Wrapper 启动"
log "=========================================="

# 1. 加载环境变量
log "📋 加载环境变量..."
load_env_file "$PROJECT_ROOT/.env" || true
load_env_file "$WORK_DIR/.env" || true

# 验证关键变量
if [ -z "${TUSHARE_TOKEN:-}" ]; then
    log "❌ 警告: TUSHARE_TOKEN 未设置，数据下载可能失败"
else
    log "✅ TUSHARE_TOKEN 已设置 (${#TUSHARE_TOKEN} 字符)"
fi

# 2. 激活虚拟环境
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    log "✅ 虚拟环境已激活: $VENV_PATH"
    log "   Python: $(which python3)"
    log "   Version: $(python3 --version 2>&1)"
else
    log "⚠️  虚拟环境不存在: $VENV_PATH，使用系统 Python"
    log "   Python: $(which python3)"
fi

# 3. 切换到工作目录
cd "$WORK_DIR"
log "📂 工作目录: $(pwd)"

# 4. 执行命令
if [ $# -eq 0 ]; then
    log "❌ 错误: 未指定要执行的命令"
    log "用法: $0 <python_script> [args...]"
    log "示例: $0 download_data_akshare.py --end 2026-06-24"
    exit 1
fi

SCRIPT="$1"
shift

log "▶️  执行: python3 $SCRIPT $*"
log "------------------------------------------"

# 执行并捕获退出码
set +e
python3 "$SCRIPT" "$@" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

# 5. 记录结果
log "------------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    log "✅ 任务执行成功 (退出码: $EXIT_CODE)"
else
    log "❌ 任务执行失败 (退出码: $EXIT_CODE)"
fi
log "📝 日志文件: $LOG_FILE"
log "=========================================="

exit $EXIT_CODE
