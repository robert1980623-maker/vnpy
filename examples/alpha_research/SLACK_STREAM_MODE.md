# Stream 模式 Slack 监控策略

## Stream 模式特点

- ✅ **连续流动**: 消息按时间顺序排列，新消息不断推送到顶部
- ⚠️ **易被淹没**: 重要告警可能被后续消息推到视线外
- ⚠️ **告警疲劳**: 频繁通知会导致用户忽略重要信息
- ✅ **实时性强**: 适合接收即时状态更新

## 优化策略

### 1. 告警聚合 (Alert Aggregation)

**问题**: 每条告警都发送会刷屏

**解决**: 相同类型的告警合并发送

```python
# 告警聚合配置
ALERT_AGGREGATION = {
    'window_seconds': 300,      # 5 分钟窗口
    'max_alerts': 3,            # 最多聚合 3 条
    'group_by': ['type', 'level']  # 按类型和级别分组
}
```

**示例**:
```
❌ 不聚合（刷屏）:
[10:01] ⚠️ 数据下载失败：股票 A
[10:02] ⚠️ 数据下载失败：股票 B
[10:03] ⚠️ 数据下载失败：股票 C
[10:04] ⚠️ 数据下载失败：股票 D

✅ 聚合后:
[10:05] ⚠️ 数据下载失败 (4 只股票)
   • 股票 A, 股票 B, 股票 C, 股票 D
   详情：查看 reports/data_errors_20260315.log
```

### 2. 分级通知策略

| 级别 | Stream 策略 | 频率限制 | 示例 |
|------|------------|---------|------|
| **CRITICAL** | 立即发送 | 无限制 | Agent 崩溃、数据丢失 |
| **HIGH** | 立即发送 | 同类型 5 分钟 1 条 | 交易失败、风控触发 |
| **MEDIUM** | 聚合发送 | 15 分钟汇总 1 条 | 数据延迟、性能下降 |
| **LOW** | 不发送 | 仅日志 | 常规状态更新 |

### 3. 摘要报告 (Digest)

**定时发送汇总报告**，而非单条通知：

| 报告类型 | 时间 | 内容 |
|---------|------|------|
| 晨间简报 | 09:00 | 昨日总结、今日计划 |
| 午间更新 | 12:00 | 上午执行情况 |
| 收盘报告 | 17:30 | 当日交易、盈亏 |
| 晚间复盘 | 20:00 | 完整复盘报告 |

### 4. 关键事件优先

**只推送真正重要的事件**:

```python
# 推荐推送的事件类型
PRIORITY_EVENTS = [
    'TradeExecutedEvent',      # 交易执行 ✅
    'RiskLimitBreached',       # 风控触发 ✅
    'AgentCrashed',            # Agent 崩溃 ✅
    'DataQualityCritical',     # 数据严重问题 ✅
    'DailyReportReady',        # 日报完成 ✅
]

# 不推荐推送的事件
SKIP_EVENTS = [
    'DataDownloaded',          # 数据下载完成（太频繁）
    'HealthCheckOK',           # 健康检查正常
    'TaskScheduled',           # 任务调度
]
```

### 5. 交互式通知

**使用 Slack Block Kit** 创建可交互消息：

```json
{
  "text": "⚠️ 止盈止损检查完成",
  "blocks": [
    {
      "type": "section",
      "text": {"text": "⚠️ 发现 2 只股票触发止盈止损", "type": "mrkdwn"},
      "accessory": {
        "type": "button",
        "text": {"text": "查看详情", "type": "plain_text"},
        "action_id": "view_details",
        "url": "https://your-dashboard.com/alerts/123"
      }
    }
  ]
}
```

## Stream 模式最佳实践

### ✅ 推荐

1. **精简通知**: 只推送关键信息
2. **聚合告警**: 避免同类问题刷屏
3. **定时摘要**: 用报告替代零散通知
4. **清晰标题**: 一眼看出重要性
5. **行动导向**: 每条通知都有明确的行动建议

### ❌ 避免

1. ~~每条日志都发送~~
2. ~~正常状态频繁报告~~
3. ~~无聚合的连续告警~~
4. ~~缺少上下文的错误信息~~
5. ~~无法追溯的历史通知~~

## 配置示例

### 环境变量

```bash
# Stream 模式配置
export SLACK_STREAM_MODE=1
export SLACK_AGGREGATION_WINDOW=300      # 5 分钟
export SLACK_MAX_ALERTS_PER_WINDOW=5    # 最多 5 条/窗口
export SLACK_DIGEST_SCHEDULE="0 9,12,17,20 * * *"  # 定时摘要
```

### 告警聚合配置

```yaml
# config/slack_stream_config.yaml
stream_mode:
  enabled: true
  
  aggregation:
    window_seconds: 300
    max_alerts: 5
    group_by:
      - type
      - level
  
  digest:
    enabled: true
    schedules:
      - "0 9 * * *"    # 晨间简报
      - "0 12 * * *"   # 午间更新
      - "30 17 * * 1-5" # 收盘报告
      - "0 20 * * 1-5" # 晚间复盘
  
  priority:
    immediate:
      - critical
      - high
    aggregated:
      - medium
    skipped:
      - low
```

## 实施计划

### 阶段 1: 基础集成 (本周)
- [ ] 配置 Slack Webhook
- [ ] 启用告警聚合
- [ ] 设置定时摘要

### 阶段 2: 优化体验 (下周)
- [ ] 添加交互式按钮
- [ ] 实现告警去重
- [ ] 优化消息格式

### 阶段 3: 高级功能 (下月)
- [ ] 集成 Slack Threads
- [ ] 添加告警确认功能
- [ ] 实现告警升级机制

## 消息格式建议

### CRITICAL 告警
```
🚨 [CRITICAL] Agent 崩溃
━━━━━━━━━━━━━━━━━━━━
Agent: 每日选股 Agent
错误：Timeout after 300s
影响：今日选股任务未执行
建议：立即检查 Agent 状态
时间：2026-03-15 22:35
━━━━━━━━━━━━━━━━━━━━
[查看日志] [重启 Agent] [忽略]
```

### HIGH 告警
```
⚠️ [HIGH] 止盈止损触发
━━━━━━━━━━━━━━━━━━━━
股票：宁德时代 (300750.SZ)
动作：止盈卖出
价格：¥256.50
盈亏：+32.5%
━━━━━━━━━━━━━━━━━━━━
[查看详情] [取消交易]
```

### 定时摘要
```
📊 午间监控摘要 (12:00)
━━━━━━━━━━━━━━━━━━━━
✅ 正常运行：32 个 Agent
⚠️ 警告：2 个 Agent
❌ 失败：0 个 Agent

今日交易：
• 买入：3 只
• 卖出：1 只
• 盈亏：+¥12,345 (+1.2%)

详情：/vnpy status
━━━━━━━━━━━━━━━━━━━━
```

## 监控效果对比

| 指标 | 传统模式 | Stream 优化 |
|------|---------|------------|
| 日均消息数 | 200+ | 20-30 |
| 告警响应时间 | 30 分钟 | 5 分钟 |
| 告警疲劳度 | 高 | 低 |
| 重要信息遗漏 | 经常 | 极少 |

## 下一步

1. 更新 `smart_alert.py` 添加告警聚合
2. 配置定时摘要任务
3. 优化消息格式
4. 测试 stream 模式效果
