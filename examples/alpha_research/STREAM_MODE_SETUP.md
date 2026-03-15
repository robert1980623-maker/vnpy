# Stream 模式 Slack 监控 - 快速配置指南

## 1 分钟快速配置

```bash
# 1. 设置环境变量
export SLACK_STREAM_MODE=1
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
export SLACK_AGGREGATION_WINDOW=300
export SLACK_MAX_ALERTS_PER_WINDOW=5

# 2. 添加到 ~/.zshrc
echo "" >> ~/.zshrc
echo "# Slack Stream 模式配置" >> ~/.zshrc
echo "export SLACK_STREAM_MODE=1" >> ~/.zshrc
echo "export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'" >> ~/.zshrc
echo "export SLACK_AGGREGATION_WINDOW=300" >> ~/.zshrc

# 3. 使配置生效
source ~/.zshrc
```

## 定时摘要任务

| 报告 | 时间 | 命令 |
|------|------|------|
| 晨间简报 | 交易日 09:00 | `python3 slack_digest.py --type morning` |
| 午间更新 | 交易日 12:00 | `python3 slack_digest.py --type noon` |
| 收盘报告 | 交易日 17:30 | `python3 slack_digest.py --type market_close` |
| 晚间复盘 | 交易日 20:00 | `python3 slack_digest.py --type evening` |

## 告警策略

| 级别 | 处理方式 | 频率限制 |
|------|---------|---------|
| CRITICAL 🚨 | 立即发送 | 无限制 |
| HIGH ⚠️ | 立即发送 | 5 分钟 1 条/类型 |
| MEDIUM ⚡ | 聚合发送 | 15 分钟汇总 |
| LOW ℹ️ | 不发送 | 仅日志 |

## 测试

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 测试 HIGH 告警
python3 -c "from world_model.smart_alert import SmartAlertSystem, AlertLevel; alert = SmartAlertSystem(); alert.create_alert(AlertLevel.HIGH, '测试', '消息')"

# 测试摘要报告
python3 slack_digest.py --type morning
```

## 效果对比

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 日均消息 | 200+ | 20-30 |
| 响应时间 | 30 分钟 | 5 分钟 |
