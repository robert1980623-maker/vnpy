#!/bin/bash

echo "=========================================="
echo "创建 Agent Neo4j 同步 Cron 任务"
echo "=========================================="
echo ""
echo "⚠️  重要：使用 venv 中的 Python 执行"
echo ""

# 每天凌晨 2 点同步一次
openclaw cron add --name "Agent Neo4j 同步" \
  --schedule "0 2 * * *" \
  --model "lmstudio/zai-org/glm-4.7-flash" \
  --timeout 300 \
  --isolated \
  "/Users/rowang/projects/vnpy/venv/bin/python3 /Users/rowang/projects/vnpy/examples/alpha_research/sync_agents_to_neo4j.py --auto"

echo ""
echo "✅ Cron 任务创建完成！"
echo ""
echo "查看任务：openclaw cron list | grep Neo4j"
echo "手动运行：openclaw cron run <job_id>"
echo ""
echo "📝 注意：脚本会在 venv 环境中执行，确保 neo4j 模块可用"
