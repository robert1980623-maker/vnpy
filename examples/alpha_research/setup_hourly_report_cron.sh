#!/bin/bash

echo "=========================================="
echo "创建每小时增强报告 Cron 任务"
echo "=========================================="
echo ""

# 每小时 0 分执行
openclaw cron add --name "每小时增强报告" \
  --schedule "0 * * * *" \
  --model "lmstudio/zai-org/glm-4.7-flash" \
  --timeout 120 \
  --isolated \
  "/Users/rowang/projects/vnpy/venv/bin/python3 /Users/rowang/projects/vnpy/examples/alpha_research/hourly_enhanced_report.py"

echo ""
echo "✅ Cron 任务创建完成！"
echo ""
echo "配置:"
echo "  频率：每小时 0 分"
echo "  模型：glm-4.7-flash (本地)"
echo "  成本：¥0"
echo "  超时：120 秒"
echo ""
echo "查看任务：openclaw cron list | grep 增强报告"
echo "手动测试：/Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py"
