# Manager 设计文档

**版本**: v1.0  
**日期**: 2026-03-14  
**作者**: 王雅轩 (Robert)

---

## 🎯 Manager 定位

**QuantManager** 是量化系统的**协调调度中心**，不是定时任务执行器。

---

## 🏗️ 架构设计

### 核心原则：事件驱动

```
Agent 报错 → Issue Queue → Manager 分析 → 调度对应 Agent → 跟踪修复
```

### 不是定时轮询

❌ **错误设计**：每 5 分钟检查一次（空转浪费）  
✅ **正确设计**：事件触发，有问题才处理

---

## 📋 Manager 职责

| 职责 | 说明 |
|------|------|
| 📥 错误上报接收 | 从 issue_queue 读取问题 |
| 🔍 错误分析 | 判断类型（工程/QA/交易/风控/数据） |
| 🤖 Agent 调度 | 分派给 Delta/QA/CRO/Data-Agent |
| 📊 进度跟踪 | 记录 active_tasks |
| 📝 报告生成 | 完成后生成 resolution report |

---

## 🗺️ Agent 调度映射

```python
self.agent_mapping = {
    'engineering': 'delta',        # 工程 bug → Delta
    'qa': 'qa',                    # 测试失败 → QA
    'trading': 'trading-agent',    # 交易问题 → Trading Agent
    'risk': 'cro',                 # 风控问题 → CRO
    'data': 'data-agent',          # 数据问题 → Data Agent
    'general': 'delta',            # 其他问题 → Delta
}
```

---

## ⚡ 问题分级处理

| 级别 | 响应 | 通知 | 预计修复 |
|------|------|------|---------|
| **P0** | 紧急调度 Delta | 立即告警 | 10-15 分钟 |
| **P1** | 调度 Delta | 发送告警 | 10 分钟 |
| **P2** | 加入队列/自动重试 | 不通知 | 待办处理 |

---

## 🤖 模型使用策略

| 组件 | 模型 | 位置 | 说明 |
|------|------|------|------|
| **定时检查任务** | glm-4.7-flash | 本地 ✅ | 每 30 分钟检查队列 |
| **调度逻辑本身** | 无 (Python 代码) | - | 基于规则的 if/else |
| **被调度 Agent** | 各自配置 | 混合 | Delta 用 qwen3-coder-plus |

### 为什么这样配置？

- ✅ **高频监控用本地**：节省成本，快速响应
- ✅ **调度逻辑是代码**：不需要 LLM，规则判断即可
- ✅ **复杂任务用云端**：Delta/QA 等需要强分析能力

---

## 📁 核心文件

| 文件 | 说明 |
|------|------|
| `manager_interface.py` | Manager 主逻辑 |
| `issue_queue.py` | 问题队列管理 |
| `alert_notifier.py` | 告警通知 |
| `issues/processing/` | 任务队列目录 |

---

## 🔄 工作流程

```
1. Agent 报错
   ↓
2. 写入 issue_queue (JSON 文件)
   ↓
3. Manager 检查队列（定时 or 事件触发）
   ↓
4. 分析错误类型（if/else 规则）
   ↓
5. 查表选择 Agent
   ↓
6. 写入对应 Agent 任务队列
   ↓
7. 目标 Agent 执行修复
   ↓
8. Manager 更新状态 → 完成
```

---

## 💡 设计优势

| 优势 | 说明 |
|------|------|
| **解耦** | Manager 不直接修复，只负责调度 |
| **专业化** | 不同类型问题由专业 Agent 处理 |
| **可扩展** | 新增 Agent 只需更新 agent_mapping |
| **可追踪** | 完整的问题生命周期记录 |
| **低成本** | 调度逻辑简单，用本地模型即可 |

---

## 📊 与其他系统的关系

```
┌─────────────────────────────────────────────────────┐
│                   OpenClaw Cron                      │
│                                                      │
│  ┌──────────────┐    ┌──────────────┐               │
│  │ 定时检查任务  │    │  其他 Agent   │               │
│  │ (本地模型)    │    │  (各种模型)   │               │
│  └──────┬───────┘    └──────┬───────┘               │
│         │                   │                        │
│         ▼                   ▼                        │
│  ┌──────────────────────────────────────┐           │
│  │         QuantManager                  │           │
│  │  (Python 代码，不是 LLM)               │           │
│  └──────────────────────────────────────┘           │
│                     │                                │
│                     ▼                                │
│  ┌──────────────────────────────────────┐           │
│  │         Issue Queue                   │           │
│  │  (JSON 文件，问题队列)                  │           │
│  └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 使用方式

### 手动触发 Manager

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source venv/bin/activate
python3 -c "from manager_interface import QuantManager; m = QuantManager(); print(m.get_status())"
```

### 查看问题队列

```bash
cat issues/pending/*.json
```

### 查看活跃任务

```bash
cat issues/processing/delta_tasks.json
```

---

## 📝 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-03-14 | 初始版本，明确 Manager 事件驱动设计 |

