#!/bin/bash
# Slack 监控设置脚本

echo "============================================================"
echo " " * 15 + "Slack 监控设置向导")
echo "============================================================"

# 1. 检查环境变量
echo ""
echo "【步骤 1/3】检查 Slack Webhook 配置"
echo "------------------------------------------------------------"

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "⚠️  SLACK_WEBHOOK_URL 未设置"
    echo ""
    echo "请按照以下步骤获取 Webhook URL:"
    echo "1. 在 Slack 中创建一个新的频道（如 #vnpy-alerts）"
    echo "2. 添加 'Incoming Webhooks' 应用"
    echo "3. 复制 Webhook URL"
    echo ""
    echo "然后将以下行添加到 ~/.zshrc:"
    echo ""
    echo "  export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'"
    echo ""
    read -p "按回车继续..."
else
    echo "✅ SLACK_WEBHOOK_URL 已配置"
    echo "   Webhook: ${SLACK_WEBHOOK_URL:0:30}..."
fi

# 2. 测试 Slack 通知
echo ""
echo "【步骤 2/3】测试 Slack 通知"
echo "------------------------------------------------------------"

cd /Users/rowang/projects/vnpy/examples/alpha_research

python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, 'world_model')

try:
    from smart_alert import SmartAlertSystem, AlertLevel, AlertType
    
    alert = SmartAlertSystem()
    
    print("发送测试告警到 Slack...")
    alert.create_alert(
        level=AlertLevel.MEDIUM,
        alert_type=AlertType.SYSTEM_ERROR,
        title="🧪 测试告警",
        message="这是一条测试告警消息，用于验证 Slack 集成是否正常工作",
        metadata={
            "环境": "development",
            "测试时间": "now"
        }
    )
    
    print("✅ 测试告警已发送，请检查 Slack 频道")
    
except Exception as e:
    print(f"❌ 发送测试告警失败：{e}")
    print("   请检查 SLACK_WEBHOOK_URL 是否正确配置")
PYEOF

# 3. 创建监控频道建议
echo ""
echo "【步骤 3/3】Slack 频道组织建议"
echo "------------------------------------------------------------"
echo ""
echo "建议在 Slack 中创建以下频道:"
echo ""
echo "  #vnpy-alerts        - 所有告警通知（P0/P1）"
echo "  #vnpy-trades        - 交易执行通知"
echo "  #vnpy-daily         - 每日/每周报告"
echo "  #vnpy-health        - Agent 健康状态"
echo ""
echo "可以为不同频道配置不同的 Webhook URL，实现告警分流"
echo ""

# 4. 完成
echo ""
echo "============================================================"
echo " " * 20 + "设置完成")
echo "============================================================"
echo ""
echo "下一步:"
echo "1. 在 ~/.zshrc 中配置 SLACK_WEBHOOK_URL"
echo "2. 运行 source ~/.zshrc 使配置生效"
echo "3. 再次运行此脚本测试 Slack 通知"
echo ""
echo "查看监控指南:"
echo "  cat SLACK_MONITORING_GUIDE.md"
echo ""
