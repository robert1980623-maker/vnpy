#!/bin/bash

# 每小时增强报告快速启动脚本
# 用法：./run_hourly_report.sh

echo "=========================================="
echo "🤖 每小时增强报告"
echo "=========================================="
echo ""

cd /Users/rowang/projects/vnpy/examples/alpha_research

# 运行报告
/Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py

echo ""
echo "=========================================="
echo "✅ 报告已生成！"
echo ""
echo "📄 最新报告:"
ls -lt reports/hourly_enhanced/*.md 2>/dev/null | head -1 | awk '{print "  " $NF}'
echo ""
echo "⏰ 下次运行：下个小时整点"
echo "=========================================="
