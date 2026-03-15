#!/bin/bash

echo "=========================================="
echo "创建预测分析增强版 Cron 任务"
echo "=========================================="
echo ""

openclaw cron add \
  --name "预测分析增强版" \
  --cron "0 * * * *" \
  --description "每小时运行预测分析并发送到 Slack" \
  --agent "main" \
  --announce \
  --channel "D0AJBBDDD9S" \
  --exact \
  --timeout 300 \
  -- "/Users/rowang/projects/vnpy/venv/bin/python3" "/Users/rowang/projects/vnpy/examples/alpha_research/predictive_analytics_enhanced.py"

echo ""
echo "✅ Cron 任务创建完成！"
echo ""
echo "配置:"
echo "  频率：每小时 0 分"
echo "  模型：glm-4.7-flash (本地)"
echo "  成本：¥0"
echo "  超时：300 秒 (5 分钟)"
echo ""
echo "查看任务：openclaw cron list | grep 预测分析"
echo "手动测试：openclaw cron run <job_id>"
