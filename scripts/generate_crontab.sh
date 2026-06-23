#!/bin/bash
# =============================================================================
# VNPY Crontab 安装脚本
# =============================================================================
# 用途: 根据 cron_config.yaml 生成并安装 crontab
#
# 用法:
#   # 查看 crontab 内容 (不安装)
#   ./generate_crontab.sh --show
#
#   # 预览安装
#   ./generate_crontab.sh --preview
#
#   # 安装 crontab (需要确认)
#   ./generate_crontab.sh --install
#
#   # 卸载 crontab
#   ./generate_crontab.sh --uninstall
# =============================================================================

set -euo pipefail

VNPY_DIR="/Users/rowang/projects/vnpy"
CONFIG_FILE="$VNPY_DIR/config/cron_config.yaml"
CRONTAB_FILE="/tmp/vnpy_crontab_$(date '+%Y%m%d_%H%M%S').txt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 解析 YAML 配置 (简化版，依赖 python3)
parse_cron_config() {
    python3 << 'PYTHON'
import sys
import yaml
from pathlib import Path

config_path = Path("/Users/rowang/projects/vnpy/config/cron_config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

vars = config.get('vars', {})
vnpy_dir = vars.get('VNPY_DIR', '/Users/rowang/projects/vnpy')
scripts_dir = vars.get('SCRIPTS_DIR', 'examples/alpha_research')

print("# VNPY Alpha Cron Jobs")
print("# Generated: " + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("# DO NOT EDIT MANUALLY - Edit config/cron_config.yaml and regenerate")
print("")
print("# 环境变量")
print(f'VNPY_DIR={vnpy_dir}')
print(f'SCRIPTS_DIR={scripts_dir}')
print("")
print("# Crontab Entries")

for task in config.get('tasks', []):
    if not task.get('enabled', True):
        continue
    
    task_id = task.get('id', 'unnamed')
    schedule = task.get('schedule', '')
    command = task.get('command', '')
    
    # 替换变量
    for var_name, var_value in vars.items():
        command = command.replace(f'${{{var_name}}}', var_value)
    
    print(f"# {task.get('name', task_id)} [{task_id}]")
    print(f"{schedule} {command}")
    print("")
PYTHON
}

case "${1:-}" in
    --show)
        log_info "显示当前 Crontab:"
        crontab -l 2>/dev/null || echo "(空)"
        ;;
    --preview)
        log_info "生成 Crontab 预览:"
        echo ""
        parse_cron_config | head -60
        echo ""
        log_info "完整 crontab 保存在临时文件"
        ;;
    --install)
        log_warn "即将安装新的 crontab，原有 crontab 将被替换"
        read -p "确认继续? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "取消安装"
            exit 0
        fi
        
        parse_cron_config > "$CRONTAB_FILE"
        log_info "Crontab 内容:"
        cat "$CRONTAB_FILE"
        echo ""
        read -p "确认安装? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "取消安装"
            exit 0
        fi
        
        crontab "$CRONTAB_FILE"
        log_info "✅ Crontab 安装成功!"
        log_info "安装文件: $CRONTAB_FILE"
        ;;
    --uninstall)
        log_warn "即将卸载 vnpy crontab"
        read -p "确认继续? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "取消"
            exit 0
        fi
        crontab -r 2>/dev/null || true
        log_info "✅ Crontab 已卸载"
        ;;
    *)
        echo "用法: $0 [--show|--preview|--install|--uninstall]"
        echo ""
        echo "  --show     显示当前 crontab"
        echo "  --preview  生成并预览 crontab (不安装)"
        echo "  --install  安装 crontab (需要确认)"
        echo "  --uninstall 卸载 crontab"
        exit 1
        ;;
esac
