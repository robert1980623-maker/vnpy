# 通知系统集成文档

## 📊 集成概览

### 完成状态

| 组件 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 通知工具模块 | ✅ | `notification_utils.py` | 通用通知工具类 |
| 数据下载任务 | ✅ | `batch_download_enhanced.py` | 下载完成通知 |
| 每日选股任务 | ✅ | `daily_stock_selection.py` | 选股结果通知 |
| 自动交易任务 | ✅ | `daily_trading.py` | 交易执行通知 |
| 每日复盘任务 | ✅ | `daily_review.py` | 复盘总结通知 |
| 集成测试脚本 | ✅ | `test_notification_integration.py` | 验证通知功能 |

### 通知客户端依赖

- **OpenClaw 通知客户端**: `/Users/rowang/.openclaw/cron/lib/notification_client.py`
- **企业微信群**: `wecom:wrQuLeEAAAOjgxc51Z3_P5DtrQ1LBtcQ` (当前群)
- **配置**: `/Users/rowang/.openclaw/cron/config/wecom_notification_config.json`

---

## 🔧 使用方法

### 1. 导入通知工具

```python
from notification_utils import (
    TaskNotifier,
    notify_task_start,
    notify_task_complete,
    notify_task_error,
    send_to_group
)
```

### 2. 发送任务通知

#### 任务开始通知

```python
notify_task_start("任务名称", {
    "参数 1": "值 1",
    "参数 2": "值 2"
})
```

#### 任务完成通知

```python
notify_task_complete("任务名称", {
    "处理数量": "100",
    "耗时": "5.2s",
    "结果": "成功"
})
```

#### 任务错误通知

```python
notify_task_error("任务名称", "错误信息", {
    "错误类型": "Exception",
    "堆栈": "..."
})
```

### 3. 自定义通知

```python
notifier = TaskNotifier("自定义任务")
notifier.send_success(
    title="自定义标题",
    content="自定义内容",
    details={"关键指标": "数值"}
)
```

### 4. 直接发送消息

```python
send_to_group("""
📢 **通知标题**

这是通知内容...

📊 详细信息:
· 项目 1: 值 1
· 项目 2: 值 2
""")
```

---

## 📋 已集成任务详情

### 1. 数据下载 (batch_download_enhanced.py)

**触发时机**: 批量数据下载开始/完成

**通知内容**:
- 开始：下载模式、时间
- 完成：下载股票数、失败数量

**示例消息**:
```
✅ 数据下载 - 执行成功
⏰ 时间：2026-03-18 06:25:00

📊 详细信息:
· 下载股票数：300
· 失败数量：0
```

---

### 2. 每日选股 (daily_stock_selection.py)

**触发时机**: 选股任务开始/完成

**通知内容**:
- 开始：日期、目标数量
- 完成：选股数量、报告文件

**示例消息**:
```
✅ 每日选股 - 执行成功
⏰ 时间：2026-03-18 09:00:00

📊 详细信息:
· 选股数量：14
· 报告文件：reports/stock_selection_2026-03-18.json
```

---

### 3. 自动交易 (daily_trading.py)

**触发时机**: 交易任务开始/完成

**通知内容**:
- 开始：日期、交易模式
- 完成：日期、执行状态

**示例消息**:
```
✅ 自动交易 - 执行成功
⏰ 时间：2026-03-18 09:35:00

📊 详细信息:
· 日期：2026-03-18
· 状态：交易执行完成
```

---

### 4. 每日复盘 (daily_review.py)

**触发时机**: 复盘任务开始/完成

**通知内容**:
- 开始：日期、复盘类型
- 完成：日期、完成状态

**示例消息**:
```
✅ 每日复盘 - 执行成功
⏰ 时间：2026-03-18 20:00:00

📊 详细信息:
· 日期：2026-03-18
· 状态：已完成
```

---

## 🧪 测试验证

### 运行集成测试

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 test_notification_integration.py
```

### 测试内容

1. ✅ 通知工具模块导入
2. ✅ 发送测试消息到企业微信群
3. ✅ 验证各任务脚本通知集成
4. ✅ 模拟任务通知（开始/成功）

### 测试输出

```
======================================================================
                    通知系统集成测试
======================================================================

📦 测试 1: 通知工具模块导入
✅ 通知工具模块导入成功

📤 测试 2: 发送测试消息到企业微信群
✅ 测试消息发送成功

📋 测试 3: 验证任务脚本通知集成
✅ 数据下载 (batch_download_enhanced.py)
✅ 每日选股 (daily_stock_selection.py)
✅ 自动交易 (daily_trading.py)
✅ 每日复盘 (daily_review.py)

🎭 测试 4: 模拟任务通知
✅ 模拟通知发送成功

✅ 所有测试完成！
```

---

## 📝 消息格式规范

### 支持 Markdown

- **粗体**: `**文本**`
- _斜体_: `_文本_`
- 列表：`· 项目`
- 代码：`` `代码` ``
- 分割线：`---`

### 表情符号

| 状态 | 表情 | 用途 |
|------|------|------|
| success | ✅ | 任务成功 |
| error | ❌ | 任务失败 |
| warning | ⚠️ | 警告信息 |
| info | 📋 | 普通通知 |
| start | 🚀 | 任务启动 |

---

## 🔍 故障排查

### 问题 1: 通知客户端未加载

**症状**: `⚠️ 通知客户端未初始化，仅打印消息`

**原因**: OpenClaw 路径配置错误

**解决**:
```python
# 检查路径
from pathlib import Path
print(Path.home() / ".openclaw")
```

---

### 问题 2: 消息发送失败

**症状**: `❌ 通知发送失败：...`

**原因**: 企业微信配置错误或网络问题

**解决**:
1. 检查配置文件：`/Users/rowang/.openclaw/cron/config/wecom_notification_config.json`
2. 验证 Chat ID 是否正确
3. 检查网络连接

---

### 问题 3: 任务脚本未集成通知

**症状**: 任务执行后没有收到通知

**解决**:
1. 检查脚本是否导入 `notification_utils`
2. 检查是否调用 `notify_task_*` 函数
3. 运行 `test_notification_integration.py` 验证

---

## 📈 后续优化

### 待办事项

- [ ] 添加通知频率限制（避免重复通知）
- [ ] 添加通知模板系统
- [ ] 支持多渠道通知（钉钉、Telegram 等）
- [ ] 添加通知历史记录
- [ ] 支持通知订阅/取消订阅
- [ ] 添加通知统计分析

### 可扩展任务

以下任务也可以添加通知集成：

- `check_data_quality.py` - 数据质量检查
- `architect_test_reviewer.py` - 代码审查
- `chief_risk_officer.py` - 风险评估
- `compliance_checker.py` - 合规检查
- `agent_health_check.py` - Agent 健康检查

---

## 📞 联系方式

如有问题或建议，请在企业微信群中 @机器人。

---

_文档更新时间：2026-03-18_
_版本：v1.0_
