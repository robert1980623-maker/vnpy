# Slack 监控 Agent 工作指南

## 世界模型架构下的监控体系

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack 监控面板                            │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              | Slack API
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   智能告警系统 (smart_alert.py)              │
│  - 异常交易检测                                              │
│  - 数据质量告警                                              │
│  - Agent 故障告警                                            │
│  - 风险警告                                                  │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              | Redis Streams / Neo4j
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  世界模型核心组件                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Event Bus   │  │Agent Registry│  │ Knowledge  │         │
│  │ (Redis)     │  │ (Neo4j)     │  │ Graph      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              |
┌─────────────────────────────────────────────────────────────┐
│                    Agent 执行层                              │
│  [数据 Agent] [交易 Agent] [风控 Agent] [报告 Agent] ...     │
└─────────────────────────────────────────────────────────────┘
```

## 监控渠道

### 1. OpenClaw Cron 任务状态通知

所有 cron 任务执行结果自动发送到 Slack：

```json
{
  "delivery": {
    "mode": "announce",
    "channel": "d0ajbbddd9s",
    "to": "D0AJBBDDD9S"
  }
}
```

**查看方式**: 直接在 Slack 中查看 cron 任务执行日志

### 2. 智能告警系统

启用 `smart_alert.py` 的 Slack 通知功能：

```python
from world_model.smart_alert import SmartAlertSystem, AlertLevel, AlertType

alert = SmartAlertSystem()

# 创建告警
alert.create_alert(
    level=AlertLevel.HIGH,
    alert_type=AlertType.AGENT_FAILURE,
    title="Agent 故障",
    message="每日选股 Agent 连续失败 3 次",
    metadata={"agent": "elite_stock_selector", "error": "Timeout"}
)
```

### 3. 事件监听与推送

通过 `event_listener.py` 监听关键事件并推送到 Slack：

```python
from world_model.event_listener import EventListener

listener = EventListener()

# 监听交易事件
@listener.on_event("TradeExecutedEvent")
def on_trade(event):
    send_slack(f"📈 交易执行：{event['symbol']} @ {event['price']}")

# 监听告警事件
@listener.on_event("AlertEvent")
def on_alert(event):
    send_slack(f"🚨 告警：{event['title']}")
```

## 监控场景

### 场景 1: Agent 健康状态监控

**频率**: 每 30 分钟

**内容**:
- ✅ 正常运行的 Agent
- ❌ 失败的 Agent
- ⚠️ 警告状态的 Agent

**实现**:
```bash
# 手动触发检查
openclaw cron run 59f72f69-ca44-4400-823d-90f85de0d6fb  # Agent 健康检查
```

### 场景 2: 数据新鲜度监控

**频率**: 每小时

**内容**:
- 📊 持仓数据新鲜度统计
- ⚠️ 陈旧数据列表
- ✅ 自动更新结果

**实现**:
```bash
# 数据新鲜度检查
openclaw cron run 1f751de7-ce60-430b-8640-fc934dccee3c
```

### 场景 3: 交易执行监控

**频率**: 实时

**内容**:
- 📈 买入交易通知
- 📉 卖出交易通知
- 💰 止盈止损触发
- ⚠️ 异常交易告警

**实现**:
```python
# 在交易 Agent 中添加
from world_model.smart_alert import SmartAlertSystem

def execute_trade(symbol, price, quantity):
    # ... 执行交易 ...
    
    # 发送 Slack 通知
    alert = SmartAlertSystem()
    alert.send_alert(
        level="medium",
        title=f"交易执行：{symbol}",
        message=f"买入 {quantity} 股 @ ¥{price}"
    )
```

### 场景 4: 每日复盘报告

**频率**: 每日 20:00

**内容**:
- 📊 当日盈亏
- 📈 持仓变化
- 🎯 选股成功率
- ⚠️ 问题总结

**实现**:
```bash
# 每日复盘任务
openclaw cron run a64be49d-e7d0-4665-a400-370cbd96b2a1
```

## 告警级别与通知策略

| 级别 | Slack 通知 | 日志 | 邮件 | 示例 |
|------|-----------|------|------|------|
| **CRITICAL** | ✅ 高亮 | ✅ | ✅ | Agent 崩溃、数据丢失 |
| **HIGH** | ✅ | ✅ | ⏸️ | 交易失败、风控触发 |
| **MEDIUM** | ⏸️ | ✅ | ⏸️ | 数据延迟、性能下降 |
| **LOW** | ⏸️ | ✅ | ⏸️ | 常规状态更新 |

## 启用 Slack 通知

### 步骤 1: 配置 Slack Webhook

编辑 `world_model/smart_alert.py`:

```python
def _send_slack(self, alert: Dict):
    """发送 Slack 通知"""
    import requests
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    payload = {
        "text": f"{'🚨' if alert['level'] == 'critical' else '⚠️'} {alert['title']}",
        "attachments": [{
            "color": "danger" if alert['level'] == 'critical' else "warning",
            "fields": [
                {"title": "级别", "value": alert['level'], "short": True},
                {"title": "类型", "value": alert['alert_type'], "short": True},
                {"title": "详情", "value": alert['message'], "short": False}
            ],
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    requests.post(webhook_url, json=payload)
```

### 步骤 2: 集成到 Agent

在关键 Agent 中添加告警调用：

```python
# data_agent.py
from world_model.smart_alert import SmartAlertSystem, AlertLevel, AlertType

class UnifiedDataAgent:
    def __init__(self):
        self.alert_system = SmartAlertSystem()
    
    def download_daily_bars(self, symbols):
        try:
            # ... 下载逻辑 ...
        except Exception as e:
            self.alert_system.create_alert(
                level=AlertLevel.HIGH,
                alert_type=AlertType.DATA_QUALITY,
                title="数据下载失败",
                message=f"无法下载 {len(symbols)} 只股票数据：{str(e)}"
            )
```

### 步骤 3: 测试通知

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 -c "
from world_model.smart_alert import SmartAlertSystem, AlertLevel, AlertType
alert = SmartAlertSystem()
alert.create_alert(
    level=AlertLevel.MEDIUM,
    alert_type=AlertType.SYSTEM_ERROR,
    title='测试告警',
    message='这是一条测试告警消息'
)
"
```

## 监控仪表板

### 实时查看

在 Slack 中创建以下频道分类：

```
#vnpy-alerts        - 所有告警通知
#vnpy-trades        - 交易执行通知
#vnpy-daily        - 每日报告
#vnpy-health        - Agent 健康状态
```

### 定期报告

| 报告类型 | 时间 | 频道 | 负责人 |
|---------|------|------|--------|
| 健康检查 | 每 30 分钟 | #vnpy-health | Agent 健康检查 |
| 数据新鲜度 | 每小时 | #vnpy-alerts | 数据新鲜度监控 |
| 交易汇总 | 每日收盘 | #vnpy-trades | 每日复盘 |
| 周度总结 | 每周五 20:00 | #vnpy-daily | 绩效归因报告 |

## 故障排查

### 问题 1: Slack 通知未发送

检查：
1. Webhook URL 是否正确
2. 网络连接是否正常
3. 告警级别是否达到阈值

### 问题 2: 告警过多

解决：
1. 调整告警阈值
2. 启用告警聚合（相同告警 5 分钟内只发一次）
3. 降低低优先级告警的通知级别

### 问题 3: 告警过少

解决：
1. 检查监控规则是否过于宽松
2. 添加更多监控点
3. 降低告警阈值

## 最佳实践

1. **分级告警**: 只在必要时发送 Slack 通知，避免告警疲劳
2. **聚合告警**: 相同问题的告警合并发送
3. **可操作告警**: 每条告警都应包含明确的行动建议
4. **告警恢复**: 问题解决后发送恢复通知
5. **定期回顾**: 每周回顾告警有效性，优化规则

## 下一步

- [ ] 集成 Slack Webhook
- [ ] 在关键 Agent 中添加告警调用
- [ ] 配置告警聚合规则
- [ ] 创建 Slack 监控频道
- [ ] 设置告警升级策略
