# SQLite 任务派遣系统实现总结

**日期**: 2026-03-18  
**模式**: 派遣模式 (Dispatcher Pattern) + SQLite 状态管理

---

## 📋 实现内容

### 1. 核心模块

| 文件 | 说明 | 行数 |
|------|------|------|
| `sqlite_task_dispatcher.py` | 核心派遣系统 | ~650 行 |
| `run_download_dispatcher.py` | 数据下载集成示例 | ~250 行 |
| `DISPATCHER_USAGE.md` | 使用文档 | - |

### 2. 架构组件

```
TaskDispatcher (派遣器)
│
├── SQLiteStateManager (状态管理)
│   ├── tasks 表 - 任务队列
│   ├── workers 表 - Worker 状态
│   ├── task_history 表 - 执行历史
│   └── dispatcher_state 表 - 调度器状态
│
├── WorkerThread (工作线程)
│   ├── 并发执行任务
│   ├── 自动重试机制
│   └── 心跳保活
│
└── Task (任务定义)
    ├── task_id, task_type, payload
    ├── priority, status, retry_count
    └── 时间戳和结果
```

---

## 🎯 核心特性

### ✅ 派遣模式实现

| 特性 | 说明 |
|------|------|
| **中央调度** | TaskDispatcher 统一分发任务 |
| **Worker 池** | 可配置并发线程数 |
| **任务队列** | SQLite 持久化，支持优先级 |
| **状态跟踪** | 实时任务状态和 Worker 状态 |

### ✅ SQLite 状态管理

| 优势 | 说明 |
|------|------|
| **持久化** | 崩溃后恢复状态 |
| **并发安全** | 内置锁机制 |
| **查询灵活** | SQL 直接查询统计 |
| **轻量级** | 无需额外数据库服务 |

### ✅ 容错机制

| 机制 | 说明 |
|------|------|
| **自动重试** | 失败任务自动重试（可配置次数） |
| **崩溃恢复** | 重启后重置中断任务 |
| **超时控制** | 任务和执行超时保护 |
| **心跳检测** | Worker 心跳保活 |

---

## 🔧 集成到现有系统

### 1. 数据下载任务

**现有**: `batch_download_enhanced.py`  
**集成**: `run_download_dispatcher.py`

```bash
# 下载持仓股票
python3 run_download_dispatcher.py --holdings --workers 5

# 全量下载（沪深 300）
python3 run_download_dispatcher.py --full --workers 10

# 下载陈旧数据
python3 run_download_dispatcher.py --stale --days 7
```

### 2. Agent 调度任务

**现有**: `main_agent_dispatcher.py`  
**集成方式**:

```python
from sqlite_task_dispatcher import TaskDispatcher, Task

# 创建 Agent 派遣器
dispatcher = TaskDispatcher(
    db_path='agent_tasks.db',
    max_workers=3,
    task_handler=lambda task: dispatch_to_agent(task.payload)
)

# 提交 Agent 任务
task = Task(
    task_id='agent_delta_001',
    task_type='agent_dispatch',
    payload={'agent': 'delta', 'issues': [...]}
)
dispatcher.submit_task(task)
```

### 3. 定时任务集成

**OpenClaw Cron 配置** (`~/.openclaw/cron/jobs.json`):

```json
{
  "jobs": [
    {
      "id": "data-download-dispatcher",
      "name": "数据下载派遣任务",
      "schedule": "0 1 * * *",
      "command": "python3 /Users/rowang/projects/vnpy/examples/alpha_research/run_download_dispatcher.py --holdings",
      "timeout": 1800,
      "model": "glm-4.7-flash"
    },
    {
      "id": "full-download-dispatcher",
      "name": "全量数据下载",
      "schedule": "0 3 * * 0",
      "command": "python3 /Users/rowang/projects/vnpy/examples/alpha_research/run_download_dispatcher.py --full --workers 10",
      "timeout": 7200,
      "model": "glm-4.7-flash"
    }
  ]
}
```

---

## 📊 数据库 Schema

### tasks 表
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    payload TEXT NOT NULL,           -- JSON
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    worker_id TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result TEXT,                     -- JSON
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);
```

### workers 表
```sql
CREATE TABLE workers (
    worker_id TEXT PRIMARY KEY,
    thread_id INTEGER,
    status TEXT DEFAULT 'idle',
    current_task TEXT,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL
);
```

### 索引
```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_workers_status ON workers(status);
```

---

## 🚀 使用示例

### 基础用法
```python
from sqlite_task_dispatcher import TaskDispatcher, Task

# 创建派遣器
dispatcher = TaskDispatcher(
    db_path='tasks.db',
    max_workers=4,
    task_handler=my_handler
)

# 启动
dispatcher.start()

# 提交任务
task = Task(
    task_id='task_001',
    task_type='download',
    payload={'symbol': '600519.SH'},
    priority=5
)
dispatcher.submit_task(task)

# 等待完成
dispatcher.wait_completion(timeout=60)

# 停止
dispatcher.stop()
```

### 批量提交
```python
tasks = []
for symbol in stock_list:
    task = Task(
        task_id=f"dl_{symbol}_{timestamp}",
        task_type='download',
        payload={'symbol': symbol}
    )
    tasks.append(task)

dispatcher.submit_batch(tasks)
```

### 状态查询
```python
status = dispatcher.get_status()
print(f"活跃 Worker: {status['active_workers']}")
print(f"待处理任务：{status['pending_tasks']}")
```

---

## 📈 性能指标

### 并发能力
| Worker 数 | 适用场景 |
|-----------|----------|
| 2-4 | 轻量任务，低资源环境 |
| 5-8 | 数据下载（推荐） |
| 10-16 | 全量下载，大批量任务 |

### 下载性能估算
```
单线程：~2 秒/股票
5 Worker: ~10 股票/分钟
10 Worker: ~20 股票/分钟

持仓 14 只：~1.5 分钟 (5 workers)
沪深 300: ~15 分钟 (10 workers)
```

---

## ⚠️ 注意事项

### 1. 线程安全
- ✅ SQLiteStateManager 已内置锁
- ✅ 多 Worker 并发安全
- ⚠️ 避免任务处理器使用全局状态

### 2. 数据库路径
- `:memory:` - 内存库（测试用）
- `tasks.db` - 本地文件（生产用）

### 3. 错误处理
- 自动重试（默认 3 次）
- 失败任务记录错误信息
- 可查询 `task_history` 排查

### 4. 资源管理
- 合理设置 `max_workers`
- 定期清理历史数据
- 监控 SQLite 文件大小

---

## 🔍 监控与调试

### 实时状态
```python
status = dispatcher.get_status()
```

### SQLite 查询
```python
import sqlite3
conn = sqlite3.connect('tasks.db')

# 失败任务
cursor.execute('''
    SELECT task_id, error_message 
    FROM tasks 
    WHERE status = 'failed'
''')

# Worker 统计
cursor.execute('''
    SELECT worker_id, tasks_completed, tasks_failed 
    FROM workers
''')
```

### 日志级别
```python
import logging
logging.getLogger('TaskDispatcher').setLevel(logging.DEBUG)
```

---

## 📝 后续优化

### 短期
- [ ] 添加 Web 监控界面
- [ ] 集成 Slack/企业微信告警
- [ ] 任务依赖关系支持

### 中期
- [ ] 分布式 Worker 支持
- [ ] Redis 替代 SQLite（高性能场景）
- [ ] 任务优先级动态调整

### 长期
- [ ] 机器学习预测任务执行时间
- [ ] 自动 Worker 扩缩容
- [ ] 任务编排 DAG 支持

---

## 🎉 总结

**SQLite 任务派遣系统** 已成功实现，具备：

✅ 完整的派遣模式架构  
✅ SQLite 持久化状态管理  
✅ 并发 Worker 线程池  
✅ 自动重试和容错机制  
✅ 与现有系统无缝集成  

**下一步**: 开始在实际任务中使用，替换原有的顺序执行逻辑。

---

**版本**: 1.0  
**创建日期**: 2026-03-18  
**状态**: ✅ 完成
