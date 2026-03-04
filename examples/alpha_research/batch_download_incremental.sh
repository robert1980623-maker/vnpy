#!/bin/bash
# 增量下载股票数据（优化版）
# 特性：
# 1. 增量下载：只下载没有的股票或更新已有股票
# 2. 自动重试：失败后每 20 分钟重试，最多 5 次
# 3. 智能检测：检查数据完整性

# 配置
BATCH_SIZE=10              # 每批数量
BATCH_DELAY=30             # 批次间隔（秒）
MAX_RETRIES=5              # 最大重试次数
RETRY_INTERVAL=1200        # 重试间隔（秒）= 20 分钟
TOTAL_STOCKS=50            # 总下载数量
DATA_DIR="./data/akshare/bars"

# 计算日期范围（下载最近 1 天）
TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -v-1d +%Y%m%d)

# 日志文件
LOG_FILE="./logs/download_$(date +%Y%m%d_%H%M%S).log"
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

# 检查股票是否需要更新
needs_update() {
    local symbol=$1
    local file="${DATA_DIR}/${symbol//./_}.csv"
    
    # 文件不存在，需要下载
    if [ ! -f "$file" ]; then
        return 0
    fi
    
    # 检查最后更新日期
    local last_date=$(tail -1 "$file" 2>/dev/null | cut -d',' -f2)
    if [ "$last_date" != "$YESTERDAY" ] && [ "$last_date" != "$TODAY" ]; then
        return 0  # 需要更新
    fi
    
    return 1  # 不需要更新
}

# 下载单只股票
download_stock() {
    local symbol=$1
    local retry_count=0
    
    while [ $retry_count -le $MAX_RETRIES ]; do
        if [ $retry_count -gt 0 ]; then
            log "[重试 ${retry_count}/${MAX_RETRIES}] 下载 ${symbol}..."
            total_retries=$((total_retries + 1))
            log "等待 ${RETRY_INTERVAL} 秒（${RETRY_INTERVAL}/60 分钟）..."
            sleep $RETRY_INTERVAL
        else
            log "[尝试 1/${MAX_RETRIES}] 下载 ${symbol}..."
        fi
        
        # 执行下载
        python3 download_data_akshare.py --symbols ${symbol} --start ${YESTERDAY} --end ${TODAY} >> "$LOG_FILE" 2>&1
        
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
    log "                    增量下载股票数据"
    log "======================================================================"
    log "日期范围：$YESTERDAY - $TODAY"
    log "批次大小：${BATCH_SIZE}"
    log "重试配置：最多 ${MAX_RETRIES} 次，间隔 ${RETRY_INTERVAL}秒"
    log "======================================================================"
    
    # 获取股票列表（从 000300 成分股）
    log "获取 000300 成分股..."
    local symbols=$(python3 -c "
import akshare as ak
try:
    df = ak.index_stock_cons(symbol='000300')
    # 取前 TOTAL_STOCKS 只
    for symbol in df['品种代码'].head(${TOTAL_STOCKS}).tolist():
        print(symbol)
except Exception as e:
    # 备用列表
    backup = ['000001', '000002', '600000', '600036', '601318']
    for s in backup:
        print(s)
" 2>/dev/null)
    
    if [ -z "$symbols" ]; then
        log "❌ 无法获取股票列表，使用备用列表"
        symbols="000001 000002 600000 600036 601318"
    fi
    
    # 筛选需要更新的股票
    local to_download=()
    local skip_count=0
    
    for symbol in $symbols; do
        if needs_update "$symbol"; then
            to_download+=("$symbol")
        else
            skip_count=$((skip_count + 1))
        fi
    done
    
    log "总股票数：${#symbols[@]}"
    log "需要更新：${#to_download[@]}"
    log "跳过（已最新）：$skip_count"
    log ""
    
    if [ ${#to_download[@]} -eq 0 ]; then
        log "✅ 所有股票数据已是最新，无需下载"
        exit 0
    fi
    
    # 分批下载
    local batch_num=1
    local total_batches=$(( (${#to_download[@]} + BATCH_SIZE - 1) / BATCH_SIZE ))
    
    for ((i=0; i<${#to_download[@]}; i+=BATCH_SIZE)); do
        local batch=("${to_download[@]:$i:$BATCH_SIZE}")
        
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
    local hours=$((duration / 3600))
    local minutes=$(( (duration % 3600) / 60 ))
    
    log ""
    log "======================================================================"
    log "                    下载完成！"
    log "======================================================================"
    log "成功：${total_success} 只股票 ✅"
    log "失败：${total_failed} 只股票 ❌"
    log "重试：${total_retries} 次"
    log "总耗时：${hours}小时 ${minutes}分钟"
    log "日志文件：$LOG_FILE"
    log "======================================================================"
    
    # 显示失败的股票
    if [ ${#failed_stocks[@]} -gt 0 ]; then
        log ""
        log "⚠️  失败的股票:"
        for symbol in "${!failed_stocks[@]}"; do
            log "  - ${symbol} (重试 ${failed_stocks[$symbol]} 次)"
        done
    fi
    
    # 验证数据
    local file_count=$(ls -1 ${DATA_DIR}/*.csv 2>/dev/null | wc -l)
    log ""
    log "数据文件总数：${file_count} 只股票"
    
    # 显示最新日期
    if [ $file_count -gt 0 ]; then
        local latest_dates=$(tail -1 ${DATA_DIR}/*.csv 2>/dev/null | grep -v "^==" | cut -d',' -f2 | sort -u | tail -5)
        log "最新数据日期:"
        echo "$latest_dates" | while read date; do
            log "  - $date"
        done
    fi
    
    log "======================================================================"
    
    # 如果有失败，返回错误码
    if [ $total_failed -gt 0 ]; then
        exit 1
    fi
    
    exit 0
}

# 执行
main
