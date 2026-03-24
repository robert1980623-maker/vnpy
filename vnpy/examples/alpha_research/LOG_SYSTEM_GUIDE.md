# 日志系统与日志分析 Agent 使用指南

**版本**: v1.0  
**创建日期**: 2026-03-12  
**模型**: lmstudio/zai-org/glm-4.7-flash

---

## 📋 系统组成

### 1. 统一日志系统 (`logger.py`)

**功能**:
- ✅ 统一日志格式
- ✅ 任务执行失败自动记录
- ✅ 日志分级 (INFO/WARNING/ERROR/CRITICAL)
- ✅ 日志轮转 (按天)
- ✅ 异常堆栈追踪
- ✅ JSONL 格式错误日志（便于分析）

**日志文件位置**:
```
logs/
├── 2026-03-12.log          # 普通日志（按天轮转）
└── errors_2026-03-12.jsonl # 错误日志（JSONL 格式）
```

---

### 2. 日志分析 Agent (`log_analyzer_agent.py`)

**职责**:
1. ✅ 每 30 分钟检查日志
2. ✅ 分析错误模式和频率
3. ✅ 检测异常（错误率、重复失败、CRITICAL 错误）
4. ✅ 发现异常时通知主 Agent
5. ✅ 建议调用 Delta 修复

**定时任务**:
- **Job ID**: `13a12669-bc79-4e5d-9240-a427f8626738`
- **时间**: 每 30 分钟 (`*/30 * * * *`)
- **模型**: `lmstudio/zai-org/glm-4.7-flash`

---

## 🚀 使用方法

### 在任务中使用日志系统

```python
from logger import TaskLogger

# 创建日志记录器
logger = TaskLogger(task_name='my_task')

# 记录任务开始
logger.task_start()

try:
    # 执行任务
    result = do_something()
    logger.info('任务执行成功', result=result)
    logger.task_end(success=True)
    
except Exception as e:
    # 记录失败
    logger.task_failed(e)
    logger.task_end(success=False)
    raise
```

### 使用装饰器

```python
from logger import log_task_execution

@log_task_execution('data_download')
def download_data():
    # 自动记录开始/结束/异常
    pass
```

### 手动记录错误

```python
from logger import log_error

try:
    risky_operation()
except Exception as e:
    log_error('risky_task', '操作失败', exception=e, user_id=123)
```

---

## 🔍 日志分析 Agent 工作流程

```
每 30 分钟
    ↓
读取最近 2 小时错误日志
    ↓
分析错误模式
  - 按级别统计
  - 按任务统计
  - 按异常类型统计
  - 计算错误率
    ↓
检测异常
  - CRITICAL 错误 ≥1 → 立即告警
  - 错误率 > 5/小时 → 告警
  - 同一任务失败 ≥5 次 → 建议调用 Delta
  - 异常模式 → 代码审查
    ↓
生成告警
    ↓
通知主 Agent
  - 保存告警文件
  - 建议操作列表
```

---

## 📊 告警级别

| 级别 | Emoji | 触发条件 | 响应 |
|------|-------|----------|------|
| **CRITICAL** | 🚨 | CRITICAL 错误≥1 或 错误率>10/小时 | 立即通知主 Agent |
| **WARNING** | ⚠️ | 错误率>5/小时 或 任务重复失败 | 通知主 Agent |
| **INFO** | ℹ️ | 轻微异常 | 记录日志 |

---

## 📁 文件结构

```
logs/
├── 2026-03-12.log              # 普通日志
├── errors_2026-03-12.jsonl     # 错误日志

cache/log_analyzer/
├── analysis_20260312_2007.json # 分析报告
├── alert_20260312_2007.json    # 告警详情
└── main_agent_notification.json # 主 Agent 通知

reports/
└── DATA_ALERT_*.json           # 数据新鲜度告警
```

---

## 🎯 异常检测规则

### 1. CRITICAL 错误
```python
if CRITICAL_count >= 1:
    alert('critical_errors', severity='high')
```

### 2. 错误率过高
```python
if errors_per_hour > 10:
    alert('error_rate_high', severity='high')
elif errors_per_hour > 5:
    alert('error_rate_increasing', severity='medium')
```

### 3. 任务重复失败
```python
if task_failure_count >= 5:
    alert('task_repeated_failure', severity='medium')
    suggest('call_delta', task_name)
```

### 4. 异常模式
```python
if exception_count >= 3 and exception not in ['ValueError', 'KeyError']:
    alert('exception_pattern', severity='medium')
```

---

## 🔔 通知机制

### 告警文件

**位置**: `cache/log_analyzer/alert_YYYYMMDD_HHMM.json`

**内容**:
```json
{
  "timestamp": "2026-03-12T20:07:00",
  "level": "critical",
  "emoji": "🚨",
  "anomaly_count": 2,
  "anomalies": [...],
  "error_stats": {...},
  "suggested_actions": [
    {
      "priority": 1,
      "action": "notify_main_agent",
      "description": "立即通知主 Agent"
    },
    {
      "priority": 2,
      "action": "call_delta",
      "description": "调用 Delta 修复 data_download"
    }
  ]
}
```

### 主 Agent 通知

**位置**: `cache/log_analyzer/main_agent_notification.json`

主 Agent 可以定期检查此文件获取通知。

---

## 🛠️ 定时任务

| Job ID | 任务 | 时间 | 模型 |
|--------|------|------|------|
| 13a12669 | 日志分析 Agent | 每 30 分钟 | glm-4.7-flash |

**查看任务**:
```bash
openclaw cron list | grep "日志分析"
```

**手动触发**:
```bash
openclaw cron run 13a12669-bc79-4e5d-9240-a427f8626738
```

**查看日志**:
```bash
openclaw cron logs 13a12669-bc79-4e5d-9240-a427f8626738
```

---

## 📈 监控仪表板

### 健康状态

```bash
# 查看最新分析报告
cat cache/log_analyzer/analysis_*.json | python3 -m json.tool | tail -20

# 查看告警历史
ls -lt cache/log_analyzer/alert_*.json | head -10
```

### 错误统计

```bash
# 查看今日错误数量
wc -l logs/errors_$(date +%Y-%m-%d).jsonl

# 查看错误类型分布
cat logs/errors_*.jsonl | python3 -c "
import json,sys
from collections import Counter
errors = [json.loads(l) for l in sys.stdin]
tasks = Counter(e['task_name'] for e in errors)
for task, count in tasks.most_common(10):
    print(f'{task}: {count}')
"
```

---

## 🔧 配置选项

### 日志分析 Agent 配置

```python
# log_analyzer_agent.py
class LogAnalyzerAgent:
    def __init__(self):
        self.check_interval_minutes = 30  # 检查间隔
        self.error_threshold_per_hour = 5  # 每小时错误阈值
        self.critical_threshold = 1  # CRITICAL 级别立即告警
```

### 修改配置

编辑 `log_analyzer_agent.py` 调整阈值。

---

## 💡 最佳实践

### 1. 任务命名规范

```python
# ✅ 好的命名
logger = TaskLogger(task_name='data_download')
logger = TaskLogger(task_name='stock_selection')

# ❌ 避免
logger = TaskLogger(task_name='test')
logger = TaskLogger(task_name='task1')
```

### 2. 错误记录

```python
# ✅ 包含上下文信息
logger.error('数据下载失败', exception=e, url=url, retry_count=retry)

# ❌ 过于简单
logger.error('失败了')
```

### 3. 定期检查

```bash
# 添加到每日检查清单
- 查看 logs/ 目录大小
- 检查 errors_*.jsonl 行数
- 查看 cache/log_analyzer/main_agent_notification.json
```

---

## 🚨 故障排查

### 问题 1: 日志分析 Agent 未运行

```bash
# 检查定时任务状态
openclaw cron status

# 手动触发一次
openclaw cron run 13a12669-bc79-4e5d-9240-a427f8626738
```

### 问题 2: 告警未通知

检查 `cache/log_analyzer/main_agent_notification.json` 是否更新。

### 问题 3: 日志文件过大

```bash
# 清理 7 天前的日志
find logs/ -name "*.log" -mtime +7 -delete
find logs/ -name "*.jsonl" -mtime +7 -delete
```

---

## 📝 示例场景

### 场景 1: 数据下载任务频繁失败

**现象**: 日志分析 Agent 检测到 `data_download` 任务 2 小时内失败 8 次

**告警**:
```
⚠️ [MEDIUM] 任务 data_download 频繁失败 (8 次)
   操作：调用 Delta 修复 data_download
```

**响应**:
1. 主 Agent 收到通知
2. 调用 Delta 检查 `data_download` 代码
3. 修复 bug 或调整参数

### 场景 2: CRITICAL 错误

**现象**: 系统出现 CRITICAL 级别错误

**告警**:
```
🚨 [HIGH] 发现 1 个 CRITICAL 级别错误
   操作：立即通知主 Agent
```

**响应**:
1. 主 Agent 立即介入
2. 检查错误堆栈
3. 紧急修复或回滚

---

## 🔗 相关文档

- [数据新鲜度监控](../DATA_FRESHNESS_MONITOR.md)
- [精英组合系统](../ELITE_PORTFOLIO_GUIDE.md)
- [日志系统实现](logger.py)

---

**创建时间**: 2026-03-12 20:07  
**维护者**: OpenClaw  
**下次更新**: 根据实际使用情况优化
