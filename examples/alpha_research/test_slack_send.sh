#!/bin/bash

echo "=========================================="
echo "测试 Slack 发送"
echo "=========================================="
echo ""

# 运行报告并捕获输出
REPORT=$(/Users/rowang/projects/vnpy/venv/bin/python3 /Users/rowang/projects/vnpy/examples/alpha_research/hourly_enhanced_report.py 2>&1)

echo "报告内容:"
echo "$REPORT"
echo ""
echo "=========================================="
echo "✅ 测试完成！"
echo ""
echo "⚠️  注意：要让报告自动发送到 Slack，需要:"
echo "  1. 通过 OpenClaw cron 任务运行"
echo "  2. 或者使用 sessions_send 工具"
echo ""
echo "当前报告已保存到:"
ls -lt /Users/rowang/projects/vnpy/examples/alpha_research/reports/hourly_enhanced/*.md | head -3
