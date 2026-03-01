#!/bin/bash
# 分批下载股票数据（增强版）
# 支持：更多批次、更长间隔、自动重试

# 配置
BATCH_SIZE=5          # 每批数量
BATCH_DELAY=60        # 批次间隔（秒）
MAX_RETRIES=2         # 最大重试次数
TOTAL_STOCKS=50       # 总下载数量（可增加）

cd /Users/rowang/projects/vnpy/examples/alpha_research

echo "======================================================================"
echo "                    分批下载股票数据（增强版）"
echo "======================================================================"
echo "每批：${BATCH_SIZE} 只股票"
echo "间隔：${BATCH_DELAY}秒"
echo "重试：最多 ${MAX_RETRIES} 次"
echo "总数：${TOTAL_STOCKS} 只股票"
echo "预计批次：$((TOTAL_STOCKS / BATCH_SIZE + (TOTAL_STOCKS % BATCH_SIZE > 0 ? 1 : 0)))"
echo "预计时间：$((TOTAL_STOCKS / BATCH_SIZE * BATCH_DELAY / 60)) 分钟"
echo "======================================================================"

# 统计
total_success=0
total_failed=0
total_retries=0
start_time=$(date +%s)

# 下载函数（支持重试）
download_with_retry() {
    local batch_num=$1
    local retry_count=0
    local success=false
    
    while [ $retry_count -le $MAX_RETRIES ] && [ "$success" = "false" ]; do
        if [ $retry_count -gt 0 ]; then
            echo "[重试 ${retry_count}/${MAX_RETRIES}] 批次 ${batch_num}..."
            total_retries=$((total_retries + 1))
        fi
        
        # 执行下载
        python3 download_data_akshare.py --max ${BATCH_SIZE} > /tmp/batch_${batch_num}_retry_${retry_count}.log 2>&1
        
        if [ $? -eq 0 ]; then
            success=true
            echo "✅ 批次 ${batch_num} 成功"
            total_success=$((total_success + BATCH_SIZE))
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -le $MAX_RETRIES ]; then
                echo "⚠️ 批次 ${batch_num} 失败，10 秒后重试..."
                sleep 10
            else
                echo "❌ 批次 ${batch_num} 失败（已重试 ${MAX_RETRIES} 次）"
                total_failed=$((total_failed + BATCH_SIZE))
            fi
        fi
    done
}

# 主循环
batch_num=1
total_batches=$((TOTAL_STOCKS / BATCH_SIZE + (TOTAL_STOCKS % BATCH_SIZE > 0 ? 1 : 0)))

while [ $batch_num -le $total_batches ]; do
    echo ""
    echo "---------------------------------------------------------------------"
    echo "[批次 ${batch_num}/${total_batches}] 下载第 $(( (batch_num-1)*BATCH_SIZE + 1 ))-$(( batch_num*BATCH_SIZE )) 只股票..."
    echo "---------------------------------------------------------------------"
    
    download_with_retry $batch_num
    
    # 批次间隔（最后一批不需要）
    if [ $batch_num -lt $total_batches ]; then
        echo ""
        echo "⏱️  等待 ${BATCH_DELAY}秒..."
        for i in $(seq $BATCH_DELAY -1 1); do
            printf "\r   剩余 ${i}秒  "
            sleep 1
        done
        echo ""
    fi
    
    batch_num=$((batch_num + 1))
done

# 计算总耗时
end_time=$(date +%s)
duration=$((end_time - start_time))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))

# 总结
echo ""
echo "======================================================================"
echo "                    下载完成！"
echo "======================================================================"
echo "总批次：${total_batches}"
echo "成功：${total_success} 只股票 ✅"
echo "失败：${total_failed} 只股票 ❌"
echo "重试：${total_retries} 次"
echo "总耗时：${hours}小时 ${minutes}分钟 (${duration}秒)"
echo "======================================================================"
echo ""
echo "验证数据："
file_count=$(ls -1 data/akshare/bars/*.csv 2>/dev/null | wc -l)
echo "数据文件：${file_count} 只股票"
echo "======================================================================"

# 如果有失败，提示
if [ $total_failed -gt 0 ]; then
    echo ""
    echo "⚠️  警告：有 ${total_failed} 只股票下载失败"
    echo "建议：手动重新下载或检查网络"
fi

exit 0
