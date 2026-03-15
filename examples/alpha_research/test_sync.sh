#!/bin/bash

echo "=========================================="
echo "测试 Agent Neo4j 同步"
echo "=========================================="

# 使用 venv 的 Python
source /Users/rowang/projects/vnpy/venv/bin/activate

cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 sync_agents_to_neo4j.py --auto

echo ""
echo "=========================================="
echo "查看报告"
echo "=========================================="
ls -lt reports/agent_sync/*.md 2>/dev/null | head -3
