#!/usr/bin/env bash
# ============================================================
# VNPY 修复计划调度系统 - Cron 安装脚本
# cron_setup.sh
#
# 功能：
#   - 安装 / 卸载 / 查看 cron 调度任务
#   - 每周检查调度（P0 任务每周检查进度）
#
# 使用方式：
#   ./cron_setup.sh install   # 安装 cron
#   ./cron_setup.sh uninstall # 卸载 cron
#   ./cron_setup.sh status    # 查看 cron 状态
#   ./cron_setup.sh run       # 手动运行一次
# ============================================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"
DISPATCHER_MODULE="fix_scheduler.task_dispatcher"
PYTHONPATH="${SCRIPT_DIR}/..:${PYTHONPATH}"

# Cron 配置
CRON_USER="${USER}"
CRON_JOB_PREFIX="# VNPY Fix Scheduler"

# 每 30 分钟检查一次（P0 阶段高频）
CRON_SCHEDULE="*/30 * * * *"

# Cron 表达式
# 每周一 09:00 执行调度检查
CRON_WEEKLY="0 9 * * 1"

# 每天 09:05 检查 P0 任务进度（如有重试）
CRON_DAILY_CHECK="5 9 * * *"

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    cat << EOF
VNPY 修复计划调度系统 - Cron 安装脚本

用法: $(basename "$0") <command>

命令:
    install     安装 cron 调度任务
    uninstall   卸载 cron 调度任务
    status      查看 cron 状态
    run         手动运行一次调度
    test        测试调度器是否能正常运行

示例:
    $(basename "$0") install   # 安装每周调度
    $(basename "$0") status    # 查看状态
    $(basename "$0") run        # 手动运行
EOF
}

# ============================================================
# 日志函数
# ============================================================

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_success() {
    echo "[SUCCESS] $1"
}

# ============================================================
# 检查依赖
# ============================================================

check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        log_error "python3 未找到，请先安装"
        exit 1
    fi

    # 检查调度器是否可导入
    if ! PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" python3 -c "import fix_scheduler" 2>/dev/null; then
        log_error "无法导入 fix_scheduler，请检查 PYTHONPATH 或安装"
        exit 1
    fi

    log_info "依赖检查通过"
}

# ============================================================
# 生成 cron 任务内容
# ============================================================

generate_cron_content() {
    local py_path="$1"
    cat << EOF
${CRON_JOB_PREFIX} - 每周检查调度
${CRON_WEEKLY} cd ${SCRIPT_DIR} && PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" ${py_path} -m ${DISPATCHER_MODULE} >> ${SCRIPT_DIR}/logs/scheduler.log 2>&1

${CRON_JOB_PREFIX} - 每天检查重试
${CRON_DAILY_CHECK} cd ${SCRIPT_DIR} && PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" ${py_path} -m ${DISPATCHER_MODULE} >> ${SCRIPT_DIR}/logs/scheduler.log 2>&1
EOF
}

# ============================================================
# 安装 cron
# ============================================================

install_cron() {
    check_dependencies

    local python_bin="${PYTHON_BIN}"
    local cron_content
    cron_content=$(generate_cron_content "${python_bin}")

    # 创建日志目录
    mkdir -p "${SCRIPT_DIR}/logs"

    # 生成临时文件
    local cron_file
    cron_file=$(mktemp)

    # 获取现有 crontab（排除本系统的 cron）
    crontab -l 2>/dev/null | grep -v "VNPY Fix Scheduler" > "${cron_file}" || true

    # 添加新 cron
    echo "" >> "${cron_file}"
    echo "${cron_content}" >> "${cron_file}"

    # 安装 crontab
    crontab "${cron_file}"
    rm -f "${cron_file}"

    log_success "Cron 任务已安装"
    echo ""
    echo "调度时间:"
    echo "  每周一 09:00  - 完整调度检查"
    echo "  每天 09:05   - 检查重试任务"
    echo ""
    echo "日志位置: ${SCRIPT_DIR}/logs/scheduler.log"
}

# ============================================================
# 卸载 cron
# ============================================================

uninstall_cron() {
    local cron_file
    cron_file=$(mktemp)

    # 过滤掉 VNPY Fix Scheduler 相关条目
    crontab -l 2>/dev/null | grep -v "VNPY Fix Scheduler" > "${cron_file}" || true

    crontab "${cron_file}"
    rm -f "${cron_file}"

    log_success "Cron 任务已卸载"
}

# ============================================================
# 查看 cron 状态
# ============================================================

show_cron_status() {
    echo "=== VNPY Fix Scheduler Cron 状态 ==="
    echo ""

    # 检查是否存在
    local existing
    existing=$(crontab -l 2>/dev/null | grep "VNPY Fix Scheduler" || true)

    if [ -n "${existing}" ]; then
        echo "✅ Cron 任务已安装"
        echo ""
        echo "当前 cron 条目:"
        crontab -l 2>/dev/null | grep -A1 "VNPY Fix Scheduler" | head -10
    else
        echo "❌ Cron 任务未安装"
    fi

    echo ""
    echo "=== 最近日志 ==="
    local log_file="${SCRIPT_DIR}/logs/scheduler.log"
    if [ -f "${log_file}" ]; then
        echo "最后 20 行:"
        tail -20 "${log_file}"
    else
        echo "日志文件不存在: ${log_file}"
    fi
}

# ============================================================
# 手动运行
# ============================================================

run_scheduler() {
    check_dependencies

    mkdir -p "${SCRIPT_DIR}/logs"
    local log_file="${SCRIPT_DIR}/logs/scheduler.log"

    log_info "运行调度器..."
    cd "${SCRIPT_DIR}"
    PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" "${PYTHON_BIN}" -m "${DISPATCHER_MODULE}" 2>&1 | tee -a "${log_file}"
}

# ============================================================
# 测试调度器
# ============================================================

test_scheduler() {
    check_dependencies

    log_info "测试调度器导入..."
    if PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" python3 -c "from fix_scheduler import FixScheduler; print('OK')"; then
        log_success "调度器导入成功"
    else
        log_error "调度器导入失败"
        exit 1
    fi

    log_info "测试 fix_plan.md 解析..."
    PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH" python3 -c "
from fix_scheduler.task_dispatcher import FixScheduler, FixPlanParser
from pathlib import Path
tasks = FixPlanParser.parse(Path('${SCRIPT_DIR}/../fix_plan.md'))
print(f'解析到 {len(tasks)} 个任务')
for t in tasks:
    print(f'  {t.id}: {t.title[:40]} [{t.team}]')
" || {
        log_error "fix_plan.md 解析失败"
        exit 1
    }

    log_success "测试通过"
}

# ============================================================
# 主入口
# ============================================================

main() {
    case "${1:-}" in
        install)
            install_cron
            ;;
        uninstall)
            uninstall_cron
            ;;
        status)
            show_cron_status
            ;;
        run)
            run_scheduler
            ;;
        test)
            test_scheduler
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

main "$@"
