#!/bin/bash
# 下载持仓股票数据（用于晚间复盘）
# 特性：
# 1. 只下载当前持仓的股票（15-25 只）
# 2. 分段下载，每批 5 只
# 3. 失败自动重试（5 次，间隔 5 分钟）

# 配置
BATCH_SIZE=5               # 每批数量（持仓少，可以小批量）
BATCH_DELAY=10             # 批次间隔（秒）
MAX_RETRIES=5              # 最大重试次数
RETRY_INTERVAL=300         # 重试间隔（秒）= 5 分钟
ACCOUNT_FILE="./accounts/virtual_2026_account.json"
DATA_DIR="./data/akshare/bars"
LOG_FILE="./logs/holdings_download_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "./logs"

# 统计
declare -A failed_stocks
total_success=0
total_failed=0
total_retries=0
start_time=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 获取持仓股票列表
get_holdings() {
    if [ ! -f "$ACCOUNT_FILE" ]; then
        log "❌ 账户文件不存在：$ACCOUNT_FILE"
        return 1
    fi
    
    # 提取持仓股票代码
    python3 << PYEOF
import json
with open('$ACCOUNT_FILE', 'r') as f:
    account = json.load(f)

positions = account.get('positions', [])
if len(positions) == 0:
    print("")
else:
    symbols = [p['symbol'] for p in positions]
    print(" ".join(symbols))
PYEOF
}

# 下载单只股票
download_stock() {
    local symbol=$1
    local retry_count=0
    
    # 转换代码格式（去掉 .SZ/.SH 后缀）
    local code=${symbol%%.*}
    
    while [ $retry_count -le $MAX_RETRIES ]; do
        if [ $retry_count -gt 0 ]; then
            log "[重试 ${retry_count}/${MAX_RETRIES}] 下载 ${symbol}..."
            total_retries=$((total_retries + 1))
            log "等待 ${RETRY_INTERVAL} 秒（${RETRY_INTERVAL}/60 分钟）..."
            sleep $RETRY_INTERVAL
        else
            log "[尝试 1/${MAX_RETRIES}] 下载 ${symbol}..."
        fi
        
        # 执行下载（只下载最近 2 天）
        python3 download_data_akshare.py --symbols ${symbol} --start $(date -v-2d +%Y%m%d) --end $(date +%Y%m%d) >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            # 验证下载结果
            local file="${DATA_DIR}/${symbol//./_}.csv"
            if [ -f "$file" ]; then
                local lines=$(wc -l < "$file")
                if [ $lines -gt 1 ]; then
                    log "✅ ${symbol} 下载成功 (${lines} 行)"
                    return 0
                fi
            fi
        fi
        
        retry_count=$((retry_count + 1))
    done
    
    log "❌ ${symbol} 下载失败（已重试 ${MAX_RETRIES} 次）"
    failed_stocks[$symbol]=$retry_count
    return 1
}

# 主函数
main() {
    log "======================================================================"
    log "                    下载持仓股票数据"
    log "======================================================================"
    log "账户文件：$ACCOUNT_FILE"
    log "批次大小：${BATCH_SIZE}"
    log "重试配置：最多 ${MAX_RETRIES} 次，间隔 ${RETRY_INTERVAL}秒"
    log "======================================================================"
    
    # 获取持仓列表
    log "获取持仓股票..."
    local holdings=$(get_holdings)
    
    if [ -z "$holdings" ]; then
        log "⚠️  无持仓股票，跳过下载"
        exit 0
    fi
    
    # 转换为数组
    local symbols=($holdings)
    local count=${#symbols[@]}
    
    log "持仓数量：$count 只"
    log "持仓列表：${symbols[*]}"
    log ""
    
    # 分批下载
    local batch_num=1
    local total_batches=$(( (count + BATCH_SIZE - 1) / BATCH_SIZE ))
    
    for ((i=0; i<count; i+=BATCH_SIZE)); do
        local batch=("${symbols[@]:$i:$BATCH_SIZE}")
        
        log ""
        log "---------------------------------------------------------------------"
        log "[批次 ${batch_num}/${total_batches}]"
        log "---------------------------------------------------------------------"
        
        for symbol in "${batch[@]}"; do
            download_stock "$symbol"
            if [ $? -eq 0 ]; then
                total_success=$((total_success + 1))
            else
                total_failed=$((total_failed + 1))
            fi
            
            # 批次内间隔
            sleep 2
        done
        
        # 批次间隔（最后一批不需要）
        if [ $batch_num -lt $total_batches ]; then
            log ""
            log "⏱️  批次间隔 ${BATCH_DELAY}秒..."
            sleep $BATCH_DELAY
        fi
        
        batch_num=$((batch_num + 1))
    done
    
    # 总结
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    
    log ""
    log "======================================================================"
    log "                    下载完成！"
    log "======================================================================"
    log "成功：${total_success} 只股票 ✅"
    log "失败：${total_failed} 只股票 ❌"
    log "重试：${total_retries} 次"
    log "总耗时：${minutes}分钟"
    log "日志文件：$LOG_FILE"
    log "======================================================================"
    
    # 显示失败的股票
    if [ ${#failed_stocks[@]} -gt 0 ]; then
        log ""
        log "⚠️  失败的股票:"
        for symbol in "${!failed_stocks[@]}"; do
            log "  - ${symbol} (重试 ${failed_stocks[$symbol]} 次)"
        done
        log ""
        log "建议：手动重新下载或检查网络"
    fi
    
    # 验证数据
    log ""
    log "验证持仓数据:"
    for symbol in "${symbols[@]}"; do
        local file="${DATA_DIR}/${symbol//./_}.csv"
        if [ -f "$file" ]; then
            local last_date=$(tail -1 "$file" | cut -d',' -f2)
            local today=$(date +%Y-%m-%d)
            if [ "$last_date" = "$today" ] || [ "$last_date" = "$(date -v-1d +%Y-%m-%d)" ]; then
                log "  ✅ ${symbol}: $last_date"
            else
                log "  ⚠️  ${symbol}: $last_date (可能过期)"
            fi
        else
            log "  ❌ ${symbol}: 文件不存在"
        fi
    done
    
    log "======================================================================"
    
    # 如果有失败，返回错误码
    if [ $total_failed -gt 0 ]; then
        exit 1
    fi
    
    exit 0
}

# 执行
main
