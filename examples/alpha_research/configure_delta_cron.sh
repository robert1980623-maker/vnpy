#!/bin/bash
# 配置 Delta 消费者 cron 作业

echo "正在配置 Delta 消费者 cron 作业..."
# 创建日志目录
mkdir -p logs

# 配置每5分钟运行一次的 cron 作业
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && /opt/homebrew/opt/python@3.14/bin/python3 delta_consumer.py >> logs/delta_consumer.log 2>&1") | crontab -

echo "Delta 消费者 cron 作业配置完成"
echo "将在每5分钟运行一次 /Users/rowang/projects/vnpy/examples/alpha_research/delta_consumer.py"

