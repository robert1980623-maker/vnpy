# 每小时增强报告 Cron 任务配置指南

## 问题

`openclaw cron add` CLI 命令语法有变化，当前无法直接通过命令行创建。

## 解决方案

### 方案 1: 使用 OpenClaw Web 界面 (推荐)

1. 打开 OpenClaw Dashboard
2. 导航到 Cron 任务管理
3. 点击"创建任务"
4. 填写以下配置:

```json
{
  "name": "每小时增强报告",
  "description": "每小时生成增强报告并发送到 Slack",
  "agentId": "main",
  "schedule": {
    "kind": "cron",
    "expr": "0 * * * *",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "cd /Users/rowang/projects/vnpy/examples/alpha_research && /Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py"
  },
  "delivery": {
    "mode": "announce",
    "channel": "D0AJBBDDD9S",
    "to": "D0AJBBDDD9S"
  },
  "timeoutSeconds": 120
}
```

### 方案 2: 使用 OpenClaw API

```bash
curl -X POST http://localhost:8080/api/cron \
  -H "Content-Type: application/json" \
  -d @hourly_report_cron_config.json
```

### 方案 3: 手动测试 (当前可用)

在 Slack 中直接运行:

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
/Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py
```

---

## 配置说明

| 字段 | 值 | 说明 |
|------|-----|------|
| **name** | 每小时增强报告 | 任务名称 |
| **schedule** | `0 * * * *` | 每小时 0 分执行 |
| **agentId** | main | 使用主 Agent |
| **sessionTarget** | isolated | 独立会话 |
| **payload.message** | python3 脚本路径 | 执行的命令 |
| **delivery.mode** | announce | 发送到 Slack |
| **delivery.channel** | D0AJBBDDD9S | 你的 Slack channel |
| **timeoutSeconds** | 120 | 超时 2 分钟 |

---

## 测试步骤

### 1. 手动测试 (立即)

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
/Users/rowang/projects/vnpy/venv/bin/python3 hourly_enhanced_report.py
```

### 2. 创建 cron 任务

使用上述任一方案创建任务。

### 3. 验证

```bash
# 查看任务列表
openclaw cron list | grep 增强报告

# 手动触发测试
openclaw cron run <job_id>

# 查看执行历史
openclaw cron runs <job_id>
```

---

## 预期效果

**每小时整点**，你会在 Slack 收到:

```
📊 每小时增强报告 (00:00)

📊 系统整体状态：健康运行...
✅ 正常运行的组件：...
⚠️ 需要关注的项：...
📈 趋势分析：...
💡 建议：...

---
由 每小时增强报告 Agent 自动生成
模型：glm-4.7-flash (本地) | 成本：¥0
```

---

## 成本

| 项目 | 成本 |
|------|------|
| 模型 | ¥0 (本地) |
| 每小时 | ~¥0.01 |
| 每天 (24 次) | ~¥0.24 |
| 每月 (720 次) | ~¥7.20 |

---

## 故障排查

### 问题 1: Slack 没收到

**检查**:
1. delivery.channel 是否正确
2. delivery.mode 是否为 announce
3. cron 任务状态是否正常

### 问题 2: 报告生成失败

**检查**:
1. nemotron 服务是否运行
2. Python 脚本路径是否正确
3. venv 是否激活

### 问题 3: 任务未执行

**检查**:
```bash
openclaw cron list
openclaw cron runs <job_id>
```

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `hourly_enhanced_report.py` | 报告生成脚本 |
| `world_model/nemotron_enhancer.py` | nemotron 增强模块 |
| `hourly_report_cron_config.json` | cron 配置 |
| `CRON_SETUP_GUIDE.md` | 本指南 |

---

**状态**: ⏸️ 等待 cron 任务创建
