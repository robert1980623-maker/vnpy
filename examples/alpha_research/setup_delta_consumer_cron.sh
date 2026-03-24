#!/bin/bash
# Delta 消费者 Cron 配置脚本

echo "正在配置 Delta 消费者 cron 作业..."

# 获取当前用户的 crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 delta_consumer.py >> /Users/rowang/projects/vnpy/examples/alpha_research/logs/delta_consumer.log 2>&1") | crontab -

echo "Delta 消费者 cron 作业已配置完成"
echo "作业将在每 5 分钟执行一次"

