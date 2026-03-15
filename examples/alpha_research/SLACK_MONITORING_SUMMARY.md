# Slack 监控集成总结

## 完成时间
2026-03-15 22:32

## 架构概览

```
┌─────────────────────────────────────────────┐
│           Slack (用户界面)                   │
│  #vnpy-alerts  #vnpy-trades  #vnpy-daily   │
└─────────────────────────────────────────────┘
                    ↑↓ Slack Webhook
┌─────────────────────────────────────────────┐
│      world_model/smart_alert.py             │
│  - 告警创建与分级                            │
│  - Slack 通知发送                            │
│  - 多渠道通知（Slack/邮件/日志）             │
└─────────────────────────────────────────────┘
                    ↑↓ Redis/Neo4j
┌─────────────────────────────────────────────┐
│         世界模型核心                         │
│  - Event Bus (事件总线)                     │
│  - Agent Registry (Agent 注册)              │
│  - Knowledge Graph (知识图谱)               │
└─────────────────────────────────────────────┘
```

## 已完成的工作

### 1. 文档创建 ✅

- **SLACK_MONITORING_GUIDE.md** - 完整的监控指南
  - 架构图
  - 监控场景
  - 告警级别策略
  - 集成步骤
  - 故障排查

- **setup_slack_monitoring.sh** - 自动化设置脚本
  - 环境检查
  - Webhook 配置
  - 测试通知
  - 频道建议

### 2. 代码更新 ✅

**world_model/smart_alert.py** 更新：
- ✅ 添加 `requests` 库支持
- ✅ 实现 `_send_slack()` 方法
- ✅ 支持环境变量 `SLACK_WEBHOOK_URL`
- ✅ 告警级别颜色映射
- ✅ 告警级别 Emoji 映射
- ✅ 元数据支持

### 3. 监控场景

| 场景 | 频率 | 内容 | 实现方式 |
|------|------|------|---------|
| Agent 健康 | 30 分钟 | 运行状态、错误统计 | `openclaw cron run 59f72f69` |
| 数据新鲜度 | 每小时 | 数据更新状态、陈旧数据 | `openclaw cron run 1f751de7` |
| 交易执行 | 实时 | 买入/卖出、止盈止损 | Agent 内集成告警 |
| 每日复盘 | 每日 20:00 | 盈亏、持仓、总结 | `openclaw cron run a64be49d` |

### 4. 告警级别与通知策略

| 级别 | Slack | 日志 | 颜色 | Emoji |
|------|-------|------|------|-------|
| CRITICAL | ✅ | ✅ | 🔴 danger | 🚨 |
| HIGH | ✅ | ✅ | 🟠 warning | ⚠️ |
| MEDIUM | ⏸️ | ✅ | 🟡 #FFA500 | ⚡ |
| LOW | ⏸️ | ✅ | 🟢 good | ℹ️ |

## 使用指南

### 快速开始

```bash
# 1. 配置 Slack Webhook
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# 2. 添加到 ~/.zshrc 使其永久生效
echo "export SLACK_WEBHOOK_URL='...'" >> ~/.zshrc
source ~/.zshrc

# 3. 运行设置脚本
cd /Users/rowang/projects/vnpy/examples/alpha_research
./setup_slack_monitoring.sh

# 4. 测试通知
python3 -c "
from world_model.smart_alert import SmartAlertSystem, AlertLevel, AlertType
alert = SmartAlertSystem()
alert.create_alert(
    level=AlertLevel.MEDIUM,
    alert_type=AlertType.SYSTEM_ERROR,
    title='测试告警',
    message='Slack 集成测试'
)
"
```

### 在 Agent 中使用

```python
from world_model.smart_alert import SmartAlertSystem, AlertLevel, AlertType

class YourAgent:
    def __init__(self):
        self.alert_system = SmartAlertSystem()
    
    def do_something(self):
        try:
            # 你的逻辑
            pass
        except Exception as e:
            # 发送告警到 Slack
            self.alert_system.create_alert(
                level=AlertLevel.HIGH,
                alert_type=AlertType.AGENT_FAILURE,
                title="Agent 执行失败",
                message=f"{self.name} 执行出错：{str(e)}",
                metadata={"error": str(e), "agent": self.name}
            )
```

### 查看现有监控任务

```bash
# 查看所有 cron 任务
openclaw cron list

# 手动触发健康检查
openclaw cron run 59f72f69-ca44-4400-823d-90f85de0d6fb

# 手动触发数据新鲜度检查
openclaw cron run 1f751de7-ce60-430b-8640-fc934dccee3c
```

## 推荐配置

### Slack 频道组织

```
#vnpy-alerts        - P0/P1 告警（配置主 Webhook）
#vnpy-trades        - 交易通知（配置交易 Webhook）
#vnpy-daily         - 日报周报（配置报告 Webhook）
#vnpy-health        - 健康状态（配置监控 Webhook）
```

### 环境变量配置

在 `~/.zshrc` 中添加：

```bash
# Slack Webhook (主频道 - 所有告警)
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX'

# 可选：分频道 Webhook
export SLACK_TRADES_WEBHOOK='https://hooks.slack.com/services/...'
export SLACK_ALERTS_WEBHOOK='https://hooks.slack.com/services/...'
```

## 监控覆盖率

### 已覆盖 (34 个 cron 任务)

- ✅ 所有任务执行结果自动发送到 Slack（通过 OpenClaw）
- ✅ 2 个 error 任务已修复并监控
- ✅ 3 个 idle 任务已触发并监控

### 待集成

- [ ] 交易执行实时通知（需在交易 Agent 中添加）
- [ ] 止盈止损触发通知（需在风控 Agent 中添加）
- [ ] 数据下载失败告警（需在数据 Agent 中添加）
- [ ] 性能指标监控（CPU/内存/磁盘）

## 故障排查

### 问题 1: Slack 未收到通知

```bash
# 检查 Webhook 配置
echo $SLACK_WEBHOOK_URL

# 测试连接
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"测试"}' \
  $SLACK_WEBHOOK_URL

# 检查日志
cd /Users/rowang/projects/vnpy/examples/alpha_research
tail -f logs/*.log | grep -i slack
```

### 问题 2: 告警过多

调整告警阈值或启用告警聚合：

```python
# 在 smart_alert.py 中添加告警聚合
ALERT_COOLDOWN = 300  # 5 分钟冷却时间
```

### 问题 3: 告警过少

检查：
1. 告警规则是否过于宽松
2. Agent 是否正确调用 `create_alert()`
3. 环境变量是否正确配置

## 下一步行动

1. **立即**: 配置 `SLACK_WEBHOOK_URL` 并测试
2. **本周**: 在交易 Agent 中集成实时通知
3. **下周**: 创建 Slack 监控仪表板频道
4. **长期**: 添加性能指标监控和趋势分析

## 相关文档

- `SLACK_MONITORING_GUIDE.md` - 详细使用指南
- `setup_slack_monitoring.sh` - 自动化设置脚本
- `world_model/smart_alert.py` - 智能告警系统源码
- `config/monitoring_alerting.yaml` - 监控告警配置
