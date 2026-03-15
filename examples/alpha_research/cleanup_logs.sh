#!/bin/bash
# 日志清理脚本 - 每天早 5:30 执行
# 保留最近 7 天的日志，删除旧日志

LOG_DIR="/Users/rowang/projects/vnpy/examples/alpha_research/logs"
RETENTION_DAYS=7

echo "============================================================"
echo "                    日志清理任务"
echo "============================================================"
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "日志目录：$LOG_DIR"
echo "保留天数：$RETENTION_DAYS 天"
echo "============================================================"

# 统计清理前的日志数量和大小
before_count=$(find "$LOG_DIR" -name "*.log" -type f 2>/dev/null | wc -l)
before_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
echo "清理前：$before_count 个文件，$before_size"

# 删除超过保留期的日志文件
deleted_count=0
while IFS= read -r file; do
    if [ -n "$file" ]; then
        rm -f "$file"
        ((deleted_count++))
        echo "  🗑️  删除：$(basename "$file")"
    fi
done < <(find "$LOG_DIR" -name "*.log" -type f -mtime +$RETENTION_DAYS 2>/dev/null)

# 压缩 3-7 天的日志（节省空间）
compressed_count=0
while IFS= read -r file; do
    if [ -n "$file" ] && [ ! -f "${file}.gz" ]; then
        gzip -f "$file"
        ((compressed_count++))
        echo "  📦 压缩：$(basename "$file")"
    fi
done < <(find "$LOG_DIR" -name "*.log" -type f -mtime +3 -mtime -$RETENTION_DAYS 2>/dev/null)

# 统计清理后的日志数量和大小
after_count=$(find "$LOG_DIR" -name "*.log" -o -name "*.log.gz" -type f 2>/dev/null | wc -l)
after_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

echo "============================================================"
echo "清理完成！"
echo "  删除：$deleted_count 个文件"
echo "  压缩：$compressed_count 个文件"
echo "  清理后：$after_count 个文件，$after_size"
echo "============================================================"
