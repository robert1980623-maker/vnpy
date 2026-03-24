# 异常检测与上报系统

**创建时间**: 2026-03-13  
**版本**: 1.0  
**状态**: ✅ 已完成

---

## 🎯 系统概述

全自动异常检测与上报系统，实现：
- ✅ Agent 执行失败自动检测
- ✅ 问题自动分类 (P0/P1/P2/P3)
- ✅ 自动上报给 Manager
- ✅ 自动调度修复
- ✅ 你只需要看最终报告

---

## 📋 核心组件

### 1. 问题队列系统 (`issue_queue.py`)

**功能**:
- 创建和管理问题
- 问题状态跟踪 (pending/processing/resolved/archived)
- 按严重性查询

**使用示例**:
```python
from issue_queue import IssueQueue

queue = IssueQueue()

# 创建问题
issue = queue.create_issue(
    agent='daily_stock_selection',
    severity='P1',
    error_type='TypeError',
    error_message=" '>' not supported"
)

# 写入队列
issue_id = queue.write_issue(issue)

# 获取待处理问题
pending = queue.get_pending_issues()
```

---

### 2. Agent 错误处理 (`agent_error_handler.py`)

**功能**:
- 统一错误处理装饰器
- 自动错误分类 (P0/P1/P2/P3)
- 自动写入日志和队列
- P0 立即触发 Manager

**错误分类标准**:
```python
P0: SystemExit, 数据丢失，连续失败 3 次+
P1: TypeError, KeyError, ImportError
P2: Timeout, 网络错误
P3: Warning, 配置建议
```

**使用示例**:
```python
from agent_error_handler import with_error_handling

@with_error_handling('daily_stock_selection')
def execute_stock_selection():
    # 业务逻辑
    pass

# 执行结果
# {'status': 'success', 'result': ...}
# 或 {'status': 'error', 'severity': 'P1', 'issue_id': '...'}
```

---

### 3. 通知机制 (`alert_notifier.py`)

**功能**:
- P0/P1 立即通知
- P2/P3 汇总报告
- 正常工作不打扰

**通知策略**:
| 级别 | 通知方式 | 示例 |
|------|---------|------|
| P0 | 🚨 立即通知 | 系统崩溃 |
| P1 | ⚠️ 立即通知 | TypeError |
| P2 | 📊 汇总报告 | Timeout |
| P3 | 📝 日报汇总 | 警告 |

**使用示例**:
```python
from alert_notifier import notify_exception

# P1 错误，立即通知
notify_exception(
    severity='P1',
    agent='daily_stock_selection',
    error='TypeError',
    action='已调度 Delta 修复',
    estimate='10 分钟'
)
```

---

### 4. Manager 接口 (`manager_interface.py`)

**功能**:
- 接收错误上报
- 分析错误类型
- 调度对应 Agent
- 跟踪修复进度
- 生成完成报告

**Agent 映射**:
```python
engineering → delta (Delta 工程师)
qa → qa (QA 质量保障)
trading → trading-agent
risk → cro (首席风险官)
data → data-agent
```

**使用示例**:
```python
from manager_interface import QuantManager

manager = QuantManager()

# 处理错误上报
task = manager.handle_error_report(issue)

# 完成任务
report = manager.complete_task(issue_id, "已修复")
```

---

## 📊 工作流程

```
Agent 执行失败
    ↓
ErrorHandler 捕获并分类
    ↓
写入问题队列
    ↓
Manager 接收并分析
    ↓
调度对应 Agent 修复
    ↓
QA 验证
    ↓
生成完成报告
    ↓
通知用户 (如果需要)
```

---

## 🔧 集成测试

**运行测试**:
```bash
python3 test_integration.py
```

**测试内容**:
- ✅ 错误处理器单元测试
- ✅ 通知器单元测试
- ✅ 完整工作流程集成测试

---

## 📁 目录结构

```
issues/
├── pending/          # 待处理问题
├── processing/       # 处理中
├── resolved/         # 已解决
└── archive/          # 归档

logs/
├── errors/           # 错误日志
└── alerts/           # 告警日志
```

---

## 📝 使用指南

### 场景 1: Agent 自动错误处理

```python
from agent_error_handler import with_error_handling

@with_error_handling('my_agent')
def my_function():
    # 可能出错的代码
    pass

# 自动处理所有异常
```

### 场景 2: 手动上报问题

```python
from issue_queue import report_issue

issue_id = report_issue(
    agent='my_agent',
    severity='P1',
    error_type='TypeError',
    error_message='Something went wrong'
)
```

### 场景 3: Manager 调度修复

```python
from manager_interface import QuantManager

manager = QuantManager()

# 读取待处理问题
pending = manager.issue_queue.get_pending_issues()

# 处理每个问题
for issue in pending:
    manager.handle_error_report(issue)
```

---

## 📊 监控和统计

**查看系统状态**:
```python
manager = QuantManager()
status = manager.get_status()

print(f"活跃任务：{status['active_tasks']}")
print(f"待处理：{status['pending_issues']}")
print(f"P0: {status['p0_count']}")
print(f"P1: {status['p1_count']}")
print(f"P2: {status['p2_count']}")
```

---

## 🎯 最佳实践

### ✅ 推荐做法

1. **所有 Agent 都使用错误处理装饰器**
   ```python
   @with_error_handling('agent_name')
   def execute():
       pass
   ```

2. **P0/P1 错误立即处理**
   - Manager 自动调度
   - Delta 优先修复

3. **定期清理归档问题**
   ```python
   queue.clear_old_issues(days=30)
   ```

### ❌ 避免做法

1. **不要忽略错误**
   ```python
   # ❌ 错误做法
   try:
       execute()
   except:
       pass
   
   # ✅ 正确做法
   @with_error_handling('agent')
   def execute():
       pass
   ```

2. **不要重复创建问题**
   - 系统自动去重
   - 相同错误只创建一次

---

## 📈 性能指标

**预期性能**:
- P0 响应时间：< 1 分钟
- P1 响应时间：< 10 分钟
- P2 处理时间：< 2 小时
- 系统开销：< 5%

---

## 🚀 版本历史

- **v1.0** (2026-03-13): 初始版本
  - ✅ 问题队列系统
  - ✅ 错误处理
  - ✅ 通知机制
  - ✅ Manager 接口
  - ✅ 集成测试

---

**文档完成时间**: 2026-03-13 19:05  
**系统状态**: ✅ 已完成并测试通过
