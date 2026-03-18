# SQLite 任务派遣系统使用指南

## 📋 概述

基于 **派遣模式 (Dispatcher Pattern)** + **SQLite** 的任务管理系统，用于：
- ✅ 统一调度并发任务（数据下载、质量检查、Agent 执行等）
- ✅ 持久化所有状态（任务、Worker、执行历史）
- ✅ 支持崩溃恢复、断点续跑
- ✅ 实时监控任务进度和 Worker 状态

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    TaskDispatcher                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              SQLiteStateManager                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│  │  │  tasks   │ │ workers  │ │ task_history     │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│         ┌───────────────┼───────────────┐              │
│         ▼               ▼               ▼              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│  │ Worker 0 │   │ Worker 1 │   │ Worker 2 │  ...     │
│  │ (Thread) │   │ (Thread) │   │ (Thread) │          │
│  └──────────┘   └──────────┘   └──────────┘          │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 基础用法

```python
from sqlite_task_dispatcher import TaskDispatcher, Task

# 创建派遣器
dispatcher = TaskDispatcher(
    db_path='tasks.db',      # SQLite 数据库路径
    max_workers=4,           # 最大并发 Worker 数
    task_handler=my_handler  # 任务处理函数
)

# 启动
dispatcher.start()

# 提交任务
task = Task(
    task_id='task_001',
    task_type='download',
    payload={'symbol': '600519.SH', 'days': 30},
    priority=5  # 0-10, 越高越优先
)
dispatcher.submit_task(task)

# 等待完成
dispatcher.wait_completion(timeout=60)

# 停止
dispatcher.stop()
```

### 2. 自定义任务处理器

```python
def download_handler(task: Task) -> Dict:
    """数据下载任务处理器"""
    symbol = task.payload['symbol']
    days = task.payload.get('days', 30)
    
    # 执行下载逻辑
    result = download_stock_data(symbol, days)
    
    return {
        'symbol': symbol,
        'rows': len(result),
        'status': 'success'
    }

def quality_check_handler(task: Task) -> Dict:
    """质量检查任务处理器"""
    symbol = task.payload['symbol']
    
    # 执行检查逻辑
    issues = check_data_quality(symbol)
    
    return {
        'symbol': symbol,
        'issues': issues,
        'passed': len(issues) == 0
    }
```

### 3. 批量提交任务

```python
# 批量提交下载任务
tasks = []
for symbol in stock_list:
    task = Task(
        task_id=f"download_{symbol}_{timestamp}",
        task_type='download',
        payload={'symbol': symbol, 'days': 30},
        priority=calculate_priority(symbol)  # 根据持仓等计算优先级
    )
    tasks.append(task)

dispatcher.submit_batch(tasks)
```

## 📊 数据库表结构

### tasks - 任务表
| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | TEXT | 任务 ID（主键） |
| task_type | TEXT | 任务类型 |
| payload | TEXT | 任务参数（JSON） |
| priority | INTEGER | 优先级 (0-10) |
| status | TEXT | 状态 |
| worker_id | TEXT | 执行 Worker |
| created_at | TEXT | 创建时间 |
| started_at | TEXT | 开始时间 |
| completed_at | TEXT | 完成时间 |
| result | TEXT | 执行结果（JSON） |
| error_message | TEXT | 错误信息 |
| retry_count | INTEGER | 重试次数 |
| max_retries | INTEGER | 最大重试 |

### workers - Worker 表
| 字段 | 类型 | 说明 |
|------|------|------|
| worker_id | TEXT | Worker ID |
| thread_id | INTEGER | 线程 ID |
| status | TEXT | 状态 (idle/busy/stopped) |
| current_task | TEXT | 当前任务 |
| tasks_completed | INTEGER | 完成任务数 |
| tasks_failed | INTEGER | 失败任务数 |
| created_at | TEXT | 创建时间 |
| last_heartbeat | TEXT | 最后心跳 |

### task_history - 执行历史表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增 ID |
| task_id | TEXT | 任务 ID |
| worker_id | TEXT | Worker ID |
| action | TEXT | 操作类型 |
| timestamp | TEXT | 时间戳 |
| details | TEXT | 详情 |

## 🔧 集成到现有系统

### 1. 数据下载任务

```python
# batch_download_enhanced.py 集成示例
from sqlite_task_dispatcher import TaskDispatcher, Task

class BatchDownloadEnhanced:
    def __init__(self):
        self.dispatcher = TaskDispatcher(
            db_path='download_tasks.db',
            max_workers=5,
            task_handler=self._download_handler
        )
    
    def _download_handler(self, task: Task) -> Dict:
        symbol = task.payload['symbol']
        # 调用现有下载逻辑
        return download_stock_data(symbol)
    
    def run_batch_download(self, symbols: List[str]):
        self.dispatcher.start()
        
        tasks = []
        for symbol in symbols:
            task = Task(
                task_id=f"dl_{symbol}_{int(time.time())}",
                task_type='download',
                payload={'symbol': symbol}
            )
            tasks.append(task)
        
        self.dispatcher.submit_batch(tasks)
        self.dispatcher.wait_completion(timeout=300)
        self.dispatcher.stop()
```

### 2. Agent 调度任务

```python
# main_agent_dispatcher.py 集成示例
from sqlite_task_dispatcher import TaskDispatcher, Task

class MainAgentDispatcher:
    def __init__(self):
        self.dispatcher = TaskDispatcher(
            db_path='agent_tasks.db',
            max_workers=3,
            task_handler=self._agent_handler
        )
    
    def _agent_handler(self, task: Task) -> Dict:
        agent_name = task.payload['agent']
        issues = task.payload['issues']
        
        # 调用现有 Agent 逻辑
        result = self.dispatch_to_agent(agent_name, issues)
        return result
    
    def dispatch_issues(self, issues: List[Dict]):
        self.dispatcher.start()
        
        # 按 Agent 分组提交
        categorized = self.categorize_issues(issues)
        for agent_name, agent_issues in categorized.items():
            task = Task(
                task_id=f"agent_{agent_name}_{int(time.time())}",
                task_type='agent_dispatch',
                payload={'agent': agent_name, 'issues': agent_issues},
                priority=8
            )
            self.dispatcher.submit_task(task)
        
        self.dispatcher.wait_completion()
        self.dispatcher.stop()
```

### 3. 定时任务集成

```python
# 与 OpenClaw cron 集成
# ~/.openclaw/cron/jobs.json
{
  "jobs": [
    {
      "id": "data-download-dispatcher",
      "name": "数据下载派遣任务",
      "schedule": "0 1 * * *",
      "command": "python3 /Users/rowang/projects/vnpy/examples/alpha_research/run_download_dispatcher.py",
      "timeout": 1800,
      "model": "glm-4.7-flash"
    }
  ]
}
```

## 📈 监控与查询

### 1. 实时状态查询

```python
status = dispatcher.get_status()
print(f"活跃 Worker: {status['active_workers']}")
print(f"忙碌 Worker: {status['busy_workers']}")
print(f"待处理任务：{status['pending_tasks']}")
```

### 2. SQLite 直接查询

```python
import sqlite3

conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 查询所有失败任务
cursor.execute('''
    SELECT task_id, task_type, error_message 
    FROM tasks 
    WHERE status = 'failed'
''')
failed_tasks = cursor.fetchall()

# 查询 Worker 统计
cursor.execute('''
    SELECT worker_id, tasks_completed, tasks_failed 
    FROM workers
''')
worker_stats = cursor.fetchall()

conn.close()
```

### 3. 生成报告

```python
def generate_daily_report(db_path: str) -> Dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 今日任务统计
    cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM tasks
        WHERE DATE(created_at) = DATE('now')
        GROUP BY status
    ''')
    today_stats = dict(cursor.fetchall())
    
    # Worker 效率
    cursor.execute('''
        SELECT AVG(tasks_completed) as avg_completed,
               AVG(tasks_failed) as avg_failed
        FROM workers
    ''')
    worker_efficiency = dict(cursor.fetchone())
    
    conn.close()
    
    return {
        'date': datetime.now().isoformat(),
        'today_stats': today_stats,
        'worker_efficiency': worker_efficiency
    }
```

## ⚠️ 注意事项

### 1. 线程安全
- ✅ SQLiteStateManager 已内置锁机制
- ✅ 多 Worker 并发安全
- ⚠️ 避免在任务处理器中使用全局共享状态

### 2. 数据库路径
- `:memory:` - 内存数据库（重启丢失）
- `tasks.db` - 本地文件（持久化）
- `/path/to/tasks.db` - 指定路径

### 3. 错误处理
- 任务失败自动重试（可配置次数）
- Worker 崩溃自动恢复
- 派遣器崩溃后重启会重置中断任务

### 4. 性能优化
- 合理设置 `max_workers`（建议 CPU 核心数 * 2）
- 大批量任务分批提交
- 定期清理历史数据

## 🔍 故障排查

### 问题：任务一直处于 pending 状态
```python
# 检查 Worker 是否运行
status = dispatcher.get_status()
print(status['active_workers'])  # 应该 > 0

# 检查数据库锁
import sqlite3
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
# 如果能执行说明数据库正常
```

### 问题：Worker 数量不足
```python
# 增加 Worker 数量
dispatcher = TaskDispatcher(max_workers=8)  # 增加并发
```

### 问题：任务重试过多
```python
# 调整最大重试次数
task = Task(
    task_id='...',
    task_type='...',
    payload={...},
    max_retries=1  # 减少重试
)
```

## 📝 最佳实践

1. **任务 ID 唯一性**: 使用时间戳 + 业务标识
2. **优先级设计**: 核心任务高优先级，批量任务低优先级
3. **监控告警**: 定期检查失败任务，设置告警阈值
4. **数据备份**: 定期备份 SQLite 数据库
5. **日志记录**: 启用详细日志便于排查

---

**版本**: 1.0  
**创建日期**: 2026-03-18
