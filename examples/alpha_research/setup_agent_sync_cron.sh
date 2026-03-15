#!/bin/bash

echo "=========================================="
echo "创建 Agent Neo4j 同步 Cron 任务"
echo "=========================================="

# 每天凌晨 2 点同步一次
openclaw cron add --name "Agent Neo4j 同步" \
  --schedule "0 2 * * *" \
  --model "lmstudio/nvidia/nemotron-3-nano" \
  --timeout 300 \
  --isolated \
  "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 sync_agents_to_neo4j.py --auto"

echo ""
echo "✅ Cron 任务创建完成！"
echo ""
echo "查看任务：openclaw cron list | grep Neo4j"
echo "手动运行：openclaw cron run <job_id>"
