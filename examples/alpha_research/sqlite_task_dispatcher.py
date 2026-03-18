#!/usr/bin/env python3
"""
基于 SQLite 的任务派遣系统

派遣模式 (Dispatcher Pattern) + SQLite 状态管理
- 中央调度器 (Dispatcher) 统一分发任务
- Worker 线程池并发执行
- SQLite 持久化所有状态（任务、线程、执行历史）
- 支持断点续跑、崩溃恢复

架构:
┌─────────────────────────────────────────────────────────┐
│                    TaskDispatcher                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  TaskQueue  │  │ WorkerPool  │  │ StateManager│     │
│  │  (SQLite)   │  │ (Threads)   │  │  (SQLite)   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
"""

import os
import sys
import json
import sqlite3
import threading
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger('TaskDispatcher')


# ============================================================================
# 数据模型
# ============================================================================

class TaskStatus(Enum):
    """任务状态"""
    PENDING = 'pending'       # 待执行
    QUEUED = 'queued'         # 已入队
    RUNNING = 'running'       # 执行中
    COMPLETED = 'completed'   # 已完成
    FAILED = 'failed'         # 失败
    CANCELLED = 'cancelled'   # 已取消
    RETRY = 'retry'           # 重试中


class WorkerStatus(Enum):
    """Worker 状态"""
    IDLE = 'idle'           # 空闲
    BUSY = 'busy'           # 忙碌
    STOPPED = 'stopped'     # 已停止
    ERROR = 'error'         # 错误


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str          # 任务类型：download/analyze/fix/report
    payload: Dict           # 任务参数
    priority: int = 0       # 优先级 (0-10, 越高越优先)
    status: str = TaskStatus.PENDING.value
    worker_id: Optional[str] = None
    created_at: str = ''
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Worker:
    """Worker 线程定义"""
    worker_id: str
    thread_id: Optional[int] = None
    status: str = WorkerStatus.IDLE.value
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    created_at: str = ''
    last_heartbeat: str = ''
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_heartbeat:
            self.last_heartbeat = datetime.now().isoformat()


# ============================================================================
# SQLite 状态管理器
# ============================================================================

class SQLiteStateManager:
    """SQLite 状态管理 - 持久化任务、Worker、执行历史"""
    
    def __init__(self, db_path: str = ':memory:'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._init_schema()
        logger.info(f"SQLite 数据库初始化：{db_path}")
    
    def _init_schema(self):
        """初始化数据库表结构"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    worker_id TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            ''')
            
            # Worker 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    thread_id INTEGER,
                    status TEXT DEFAULT 'idle',
                    current_task TEXT,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_heartbeat TEXT NOT NULL
                )
            ''')
            
            # 任务执行历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT
                )
            ''')
            
            # 调度器状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dispatcher_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id)')
            
            self.conn.commit()
            logger.info("数据库表结构初始化完成")
    
    # -------------------- 任务操作 --------------------
    
    def create_task(self, task: Task) -> bool:
        """创建任务"""
        with self.lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO tasks (
                        task_id, task_type, payload, priority, status,
                        created_at, max_retries
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id, task.task_type, json.dumps(task.payload),
                    task.priority, task.status, task.created_at, task.max_retries
                ))
                self.conn.commit()
                self._log_history(task.task_id, 'SYSTEM', 'TASK_CREATED', 
                                f'Priority: {task.priority}')
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"任务已存在：{task.task_id}")
                return False
    
    def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """获取待执行任务（按优先级排序）"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tasks 
                WHERE status IN ('pending', 'queued', 'retry')
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            ''', (limit,))
            
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取单个任务"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()
            return self._row_to_task(row) if row else None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          worker_id: Optional[str] = None,
                          result: Optional[Dict] = None,
                          error_message: Optional[str] = None):
        """更新任务状态"""
        with self.lock:
            cursor = self.conn.cursor()
            
            updates = ['status = ?']
            values = [status.value]
            
            if worker_id:
                updates.append('worker_id = ?')
                values.append(worker_id)
            
            if status == TaskStatus.RUNNING:
                updates.append('started_at = ?')
                values.append(datetime.now().isoformat())
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                updates.append('completed_at = ?')
                values.append(datetime.now().isoformat())
            
            if result:
                updates.append('result = ?')
                values.append(json.dumps(result))
            
            if error_message:
                updates.append('error_message = ?')
                values.append(error_message)
            
            if status == TaskStatus.RETRY:
                updates.append('retry_count = retry_count + 1')
            
            values.append(task_id)
            
            cursor.execute(f'''
                UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?
            ''', values)
            
            self.conn.commit()
            self._log_history(task_id, worker_id or 'SYSTEM', 
                            f'STATUS_{status.value.upper()}')
    
    def delete_task(self, task_id: str):
        """删除任务"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
            self.conn.commit()
    
    # -------------------- Worker 操作 --------------------
    
    def register_worker(self, worker: Worker) -> bool:
        """注册 Worker"""
        with self.lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO workers (
                        worker_id, thread_id, status, created_at, last_heartbeat
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    worker.worker_id, worker.thread_id, worker.status,
                    worker.created_at, worker.last_heartbeat
                ))
                self.conn.commit()
                logger.info(f"Worker 注册：{worker.worker_id}")
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_idle_worker(self) -> Optional[Worker]:
        """获取空闲 Worker"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM workers 
                WHERE status = 'idle'
                ORDER BY tasks_completed ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return self._row_to_worker(row) if row else None
    
    def update_worker_status(self, worker_id: str, status: WorkerStatus,
                            current_task: Optional[str] = None):
        """更新 Worker 状态"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE workers 
                SET status = ?, current_task = ?, last_heartbeat = ?
                WHERE worker_id = ?
            ''', (status.value, current_task, datetime.now().isoformat(), worker_id))
            self.conn.commit()
    
    def increment_worker_stats(self, worker_id: str, success: bool):
        """更新 Worker 统计"""
        with self.lock:
            cursor = self.conn.cursor()
            if success:
                cursor.execute('''
                    UPDATE workers 
                    SET tasks_completed = tasks_completed + 1,
                        last_heartbeat = ?
                    WHERE worker_id = ?
                ''', (datetime.now().isoformat(), worker_id))
            else:
                cursor.execute('''
                    UPDATE workers 
                    SET tasks_failed = tasks_failed + 1,
                        last_heartbeat = ?
                    WHERE worker_id = ?
                ''', (datetime.now().isoformat(), worker_id))
            self.conn.commit()
    
    def get_all_workers(self) -> List[Worker]:
        """获取所有 Worker"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM workers')
            return [self._row_to_worker(row) for row in cursor.fetchall()]
    
    # -------------------- 历史日志 --------------------
    
    def _log_history(self, task_id: str, worker_id: str, 
                    action: str, details: Optional[str] = None):
        """记录操作历史"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO task_history (task_id, worker_id, action, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (task_id, worker_id, action, datetime.now().isoformat(), details))
        self.conn.commit()
    
    def get_task_history(self, task_id: str, limit: int = 50) -> List[Dict]:
        """获取任务历史"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM task_history 
                WHERE task_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (task_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    # -------------------- 调度器状态 --------------------
    
    def save_state(self, key: str, value: Any):
        """保存调度器状态"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO dispatcher_state (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, json.dumps(value), datetime.now().isoformat()))
            self.conn.commit()
    
    def load_state(self, key: str, default: Any = None) -> Any:
        """加载调度器状态"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM dispatcher_state WHERE key = ?', (key,))
            row = cursor.fetchone()
            return json.loads(row['value']) if row else default
    
    # -------------------- 工具方法 --------------------
    
    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """将数据库行转换为 Task"""
        return Task(
            task_id=row['task_id'],
            task_type=row['task_type'],
            payload=json.loads(row['payload']),
            priority=row['priority'],
            status=row['status'],
            worker_id=row['worker_id'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            result=json.loads(row['result']) if row['result'] else None,
            error_message=row['error_message'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries']
        )
    
    def _row_to_worker(self, row: sqlite3.Row) -> Worker:
        """将数据库行转换为 Worker"""
        return Worker(
            worker_id=row['worker_id'],
            thread_id=row['thread_id'],
            status=row['status'],
            current_task=row['current_task'],
            tasks_completed=row['tasks_completed'],
            tasks_failed=row['tasks_failed'],
            created_at=row['created_at'],
            last_heartbeat=row['last_heartbeat']
        )
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# ============================================================================
# Worker 线程
# ============================================================================

class WorkerThread(threading.Thread):
    """Worker 线程 - 执行具体任务"""
    
    def __init__(self, worker_id: str, dispatcher: 'TaskDispatcher',
                 task_handler: Callable[[Task], Dict]):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.dispatcher = dispatcher
        self.task_handler = task_handler
        self.status = WorkerStatus.IDLE
        self.current_task: Optional[Task] = None
        self.stop_flag = threading.Event()
    
    def run(self):
        """Worker 主循环"""
        logger.info(f"Worker {self.worker_id} 启动")
        self.dispatcher.state_manager.update_worker_status(
            self.worker_id, WorkerStatus.IDLE)
        
        while not self.stop_flag.is_set():
            # 获取任务
            task = self.dispatcher._get_next_task_for_worker(self.worker_id)
            
            if task is None:
                time.sleep(0.5)  # 无任务，短暂等待
                continue
            
            # 执行任务
            self._execute_task(task)
        
        # 清理
        self.dispatcher.state_manager.update_worker_status(
            self.worker_id, WorkerStatus.STOPPED)
        logger.info(f"Worker {self.worker_id} 停止")
    
    def _execute_task(self, task: Task):
        """执行单个任务"""
        self.current_task = task
        self.status = WorkerStatus.BUSY
        
        # 更新状态
        self.dispatcher.state_manager.update_task_status(
            task.task_id, TaskStatus.RUNNING, worker_id=self.worker_id)
        self.dispatcher.state_manager.update_worker_status(
            self.worker_id, WorkerStatus.BUSY, current_task=task.task_id)
        
        logger.info(f"Worker {self.worker_id} 执行任务：{task.task_id}")
        
        try:
            # 执行任务处理函数
            result = self.task_handler(task)
            
            # 任务成功
            self.dispatcher.state_manager.update_task_status(
                task.task_id, TaskStatus.COMPLETED, 
                worker_id=self.worker_id, result=result)
            self.dispatcher.state_manager.increment_worker_stats(
                self.worker_id, success=True)
            
            logger.info(f"Worker {self.worker_id} 完成任务：{task.task_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Worker {self.worker_id} 任务失败：{task.task_id} - {e}")
            
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                self.dispatcher.state_manager.update_task_status(
                    task.task_id, TaskStatus.RETRY,
                    worker_id=self.worker_id, error_message=error_msg)
                logger.info(f"任务将重试：{task.task_id} (第 {task.retry_count + 1} 次)")
            else:
                self.dispatcher.state_manager.update_task_status(
                    task.task_id, TaskStatus.FAILED,
                    worker_id=self.worker_id, 
                    error_message=error_msg,
                    result={'error': error_msg})
                self.dispatcher.state_manager.increment_worker_stats(
                    self.worker_id, success=False)
        
        finally:
            self.current_task = None
            self.status = WorkerStatus.IDLE
            self.dispatcher.state_manager.update_worker_status(
                self.worker_id, WorkerStatus.IDLE)
    
    def stop(self):
        """停止 Worker"""
        self.stop_flag.set()


# ============================================================================
# 任务派遣器
# ============================================================================

class TaskDispatcher:
    """任务派遣器 - 核心调度中枢"""
    
    def __init__(self, db_path: str = ':memory:', 
                 max_workers: int = 4,
                 task_handler: Optional[Callable[[Task], Dict]] = None):
        self.state_manager = SQLiteStateManager(db_path)
        self.max_workers = max_workers
        self.task_handler = task_handler or self._default_task_handler
        
        self.workers: Dict[str, WorkerThread] = {}
        self.running = False
        self._lock = threading.Lock()
        
        # 恢复状态
        self._restore_state()
        
        logger.info(f"TaskDispatcher 初始化完成 (max_workers={max_workers})")
    
    def _restore_state(self):
        """恢复之前的状态（崩溃恢复）"""
        pending_count = len(self.state_manager.get_pending_tasks())
        workers = self.state_manager.get_all_workers()
        
        logger.info(f"恢复状态：{pending_count} 个待处理任务，{len(workers)} 个 Worker")
        
        # 重置运行中的任务为 pending
        for worker in workers:
            if worker.status == WorkerStatus.BUSY.value and worker.current_task:
                task = self.state_manager.get_task(worker.current_task)
                if task:
                    self.state_manager.update_task_status(
                        task.task_id, TaskStatus.PENDING)
                    logger.info(f"重置中断任务：{task.task_id}")
        
        # 停止所有旧 Worker
        for worker in workers:
            self.state_manager.update_worker_status(
                worker.worker_id, WorkerStatus.STOPPED)
    
    def start(self):
        """启动派遣器"""
        if self.running:
            logger.warning("派遣器已在运行中")
            return
        
        self.running = True
        self.state_manager.save_state('dispatcher_running', True)
        
        # 启动 Worker 线程池
        for i in range(self.max_workers):
            worker_id = f"worker_{i:03d}"
            worker = WorkerThread(worker_id, self, self.task_handler)
            worker.start()
            self.workers[worker_id] = worker
            
            # 注册到 SQLite
            self.state_manager.register_worker(Worker(
                worker_id=worker_id,
                thread_id=worker.ident,
                status=WorkerStatus.IDLE.value
            ))
        
        logger.info(f"派遣器启动，{self.max_workers} 个 Worker 就绪")
    
    def stop(self, wait: bool = True, timeout: float = 10.0):
        """停止派遣器"""
        logger.info("停止派遣器...")
        self.running = False
        self.state_manager.save_state('dispatcher_running', False)
        
        # 停止所有 Worker
        for worker in self.workers.values():
            worker.stop()
        
        if wait:
            # 等待 Worker 完成
            for worker in self.workers.values():
                worker.join(timeout=timeout / len(self.workers))
        
        self.workers.clear()
        logger.info("派遣器已停止")
    
    def submit_task(self, task: Task) -> str:
        """提交任务"""
        self.state_manager.create_task(task)
        logger.info(f"任务提交：{task.task_id} (类型：{task.task_type}, 优先级：{task.priority})")
        return task.task_id
    
    def submit_batch(self, tasks: List[Task]) -> List[str]:
        """批量提交任务"""
        task_ids = []
        for task in tasks:
            task_ids.append(self.submit_task(task))
        logger.info(f"批量提交 {len(tasks)} 个任务")
        return task_ids
    
    def _get_next_task_for_worker(self, worker_id: str) -> Optional[Task]:
        """为 Worker 获取下一个任务（原子操作）"""
        with self._lock:
            tasks = self.state_manager.get_pending_tasks(limit=1)
            if not tasks:
                return None
            
            task = tasks[0]
            # 原子性地标记为已分配
            self.state_manager.update_task_status(
                task.task_id, TaskStatus.RUNNING, worker_id=worker_id)
            return task
    
    def _default_task_handler(self, task: Task) -> Dict:
        """默认任务处理器"""
        logger.info(f"执行任务：{task.task_id}")
        time.sleep(0.1)  # 模拟执行
        return {'status': 'ok', 'task_id': task.task_id}
    
    def get_status(self) -> Dict:
        """获取派遣器状态"""
        workers = self.state_manager.get_all_workers()
        pending = len(self.state_manager.get_pending_tasks(limit=9999))
        
        return {
            'running': self.running,
            'max_workers': self.max_workers,
            'active_workers': len([w for w in workers if w.status == WorkerStatus.IDLE.value]),
            'busy_workers': len([w for w in workers if w.status == WorkerStatus.BUSY.value]),
            'pending_tasks': pending,
            'workers': [asdict(w) for w in workers]
        }
    
    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        start_time = time.time()
        
        while True:
            status = self.get_status()
            if status['pending_tasks'] == 0 and status['busy_workers'] == 0:
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(1)


# ============================================================================
# 示例用法
# ============================================================================

def example_download_handler(task: Task) -> Dict:
    """示例：数据下载任务处理器"""
    symbol = task.payload.get('symbol', 'UNKNOWN')
    logger.info(f"下载数据：{symbol}")
    
    # 模拟下载
    time.sleep(0.5)
    
    return {
        'symbol': symbol,
        'rows': 100,
        'status': 'success'
    }


def main():
    """示例：完整使用流程"""
    print("="*70)
    print("SQLite 任务派遣系统演示")
    print("="*70)
    
    # 创建派遣器
    dispatcher = TaskDispatcher(
        db_path='tasks.db',
        max_workers=3,
        task_handler=example_download_handler
    )
    
    # 启动
    dispatcher.start()
    
    # 提交任务
    tasks = []
    for i, symbol in enumerate(['000001.SZ', '600036.SH', '600519.SH', '000858.SZ', '300750.SZ']):
        task = Task(
            task_id=f"download_{symbol}_{datetime.now().strftime('%H%M%S')}",
            task_type='download',
            payload={'symbol': symbol, 'days': 30},
            priority=i % 3  # 不同优先级
        )
        tasks.append(task)
    
    dispatcher.submit_batch(tasks)
    
    # 等待完成
    print("\n等待任务完成...")
    dispatcher.wait_completion(timeout=30)
    
    # 打印状态
    status = dispatcher.get_status()
    print(f"\n最终状态:")
    print(f"  活跃 Worker: {status['active_workers']}")
    print(f"  忙碌 Worker: {status['busy_workers']}")
    print(f"  待处理任务：{status['pending_tasks']}")
    
    # 停止
    dispatcher.stop()
    
    print("\n✅ 演示完成")


if __name__ == '__main__':
    main()
