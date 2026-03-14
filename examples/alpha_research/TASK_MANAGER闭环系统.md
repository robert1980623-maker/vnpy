# 任务管理闭环系统

## 📋 核心流程

```
Manager 派发 → Agent 执行 → Manager 检查 → 成功闭环
                                    ↓
                                失败？
                                    ↓
                            触发 QA 闭环
                                    ↓
                            QA 验证通过？
                                    ↓
                               重新派发 Agent
```

---

## 🎯 系统组件

### 1. TaskManager (任务管理器)

**职责**:
- 创建任务
- 派发任务给 Agent
- 检查任务结果
- 触发 QA 闭环
- 生成任务报告

**文件**: `task_manager.py`

### 2. QuantManager (调度中心)

**职责**:
- 接收错误上报
- 分析错误类型
- 选择合适 Agent
- 跟踪修复进度

**文件**: `manager_interface.py`

### 3. IssueQueue (问题队列)

**职责**:
- 管理问题状态
- 问题持久化
- 状态流转

**文件**: `issue_queue.py`

### 4. QA-Architect Loop (QA 闭环)

**职责**:
- QA 生成测试用例
- 架构师审核
- 迭代修复
- 验证通过

**文件**: `qa_architect_loop.py`

---

## 📊 任务状态

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `pending` | 待派发 | 任务创建 |
| `assigned` | 已派发 | Manager 分配给 Agent |
| `running` | 执行中 | Agent 开始执行 |
| `completed` | 已完成 | 执行成功 |
| `failed` | 失败 | 执行失败 |
| `qa_review` | QA 审核中 | 触发 QA 闭环 |

---

## 🔄 完整流程示例

### 场景 1: 成功闭环

```python
from task_manager import TaskManager

tm = TaskManager()

# 1. 创建 Issue
issue = tm.issue_queue.create_issue(
    agent='data-agent',
    severity='P1',
    error_type='DataError',
    error_message='数据下载失败'
)
issue_id = tm.issue_queue.write_issue(issue)

# 2. Manager 派发任务
task_id = tm.create_task(issue_id, 'data-agent', 'data_download')
tm.assign_task(task_id)

# 3. Agent 执行任务
success, output = tm.execute_task(
    task_id,
    'python3 download_data_akshare.py'
)

# 4. Manager 检查结果
if success:
    tm.check_task_result(task_id)
    print("✅ 任务成功闭环")
```

### 场景 2: 失败触发 QA 闭环

```python
# 1-3. 同上...

# 4. 执行失败
success, output = tm.execute_task(
    task_id,
    'python3 broken_script.py'  # 会失败
)

if not success:
    # 5. 触发 QA 闭环
    tm.trigger_qa_loop(task_id)
    
    # 6. QA 验证通过后重新派发
    if tm.tasks[task_id]['status'] == TaskStatus.PENDING:
        tm.assign_task(task_id)
        tm.execute_task(task_id, 'python3 fixed_script.py')
```

---

## 📁 使用方式

### 命令行执行

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate

# 运行演示
python3 task_manager.py

# 运行测试
python3 -m pytest tests/unit/test_task_manager.py -v
```

### API 调用

```python
from task_manager import TaskManager

tm = TaskManager()

# 创建任务
task_id = tm.create_task(issue_id, 'delta', 'code_fix')

# 派发任务
tm.assign_task(task_id)

# 执行任务
success, output = tm.execute_task(task_id, 'python3 script.py')

# 检查结果
if success:
    tm.check_task_result(task_id)
else:
    tm.trigger_qa_loop(task_id)

# 生成报告
report = tm.generate_report()
print(f"完成任务：{report['completed_tasks']}")
```

---

## 📊 任务报告

```json
{
  "total_tasks": 10,
  "active_tasks": 2,
  "completed_tasks": 7,
  "failed_tasks": 1,
  "qa_triggered": 2,
  "tasks": [...],
  "history": [...]
}
```

---

## 🎯 QA 闭环触发条件

| 条件 | 说明 | 操作 |
|------|------|------|
| **执行失败** | Agent 执行返回非 0 | 触发 QA |
| **超时** | 超过设定时间 | 触发 QA |
| **异常** | 抛出未处理异常 | 触发 QA |
| **验证失败** | Manager 检查不通过 | 触发 QA |

---

## 🔧 配置选项

### 超时设置

```python
# 默认 600 秒
success, output = tm.execute_task(
    task_id,
    'python3 script.py',
    timeout=600
)
```

### 优先级设置

```python
# priority: low / normal / high / critical
task_id = tm.create_task(
    issue_id,
    'delta',
    'code_fix',
    priority='high'
)
```

---

## 📈 监控指标

| 指标 | 说明 | 目标 |
|------|------|------|
| **任务成功率** | 完成任务/总任务 | ≥90% |
| **QA 触发率** | QA 触发/失败任务 | 100% |
| **平均执行时间** | 总时间/任务数 | <5 分钟 |
| **闭环率** | 已闭环/总任务 | ≥95% |

---

## 🚀 最佳实践

### 1. 任务粒度

- ✅ 小任务 - 单一职责
- ❌ 大任务 - 多职责混合

### 2. 超时设置

- ✅ 合理超时 - 避免无限等待
- ❌ 无超时 - 可能卡死

### 3. QA 触发

- ✅ 及时触发 - 失败立即 QA
- ❌ 延迟触发 - 问题累积

### 4. 任务追踪

- ✅ 完整记录 - 便于回溯
- ❌ 无记录 - 难以追踪

---

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `task_manager.py` | 任务管理器主程序 |
| `manager_interface.py` | Manager 调度接口 |
| `issue_queue.py` | 问题队列管理 |
| `qa_architect_loop.py` | QA 闭环系统 |
| `tests/unit/test_task_manager.py` | 任务管理器测试 |

---

## 🎓 示例场景

### 场景 1: 数据下载失败

```
1. Agent 报告：数据下载超时
2. Manager 分析：数据类错误
3. 派发：data-agent
4. 执行：重新下载
5. 失败：网络问题
6. QA 闭环：检查网络配置
7. 修复：更新代理设置
8. 重新派发：data-agent
9. 成功：下载完成
10. 闭环：任务完成
```

### 场景 2: 代码 Bug 修复

```
1. Agent 报告：TypeError
2. Manager 分析：工程类错误
3. 派发：delta-engineer
4. 执行：修复代码
5. 失败：测试不通过
6. QA 闭环：生成测试用例
7. 迭代：修复→测试→通过
8. 重新派发：delta-engineer
9. 成功：代码修复
10. 闭环：任务完成
```

---

**最后更新**: 2026-03-15  
**维护者**: QA Team  
**状态**: ✅ 已启用
