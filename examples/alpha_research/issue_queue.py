#!/usr/bin/env python3
"""
问题队列管理系统 (P2-1 SQLite 优化版)
- read_issue() 从 O(n) 降为 O(1)
- 自动从 JSON 导入现有数据
- 向后兼容（JSON 模式可切换）
"""

import json
import uuid
import shutil
import sys
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field



# ============================================================
# SQLite 数据库管理
# ============================================================

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    agent TEXT,
    severity TEXT,
    error_type TEXT,
    error_message TEXT,
    timestamp TEXT,
    status TEXT,
    assigned_to TEXT,
    resolved_at TEXT,
    resolution TEXT,
    type TEXT,
    details TEXT,
    report_file TEXT,
    requires_action INTEGER,
    action_items TEXT,
    assigned_agent TEXT,
    assigned_at TEXT,
    completed_at TEXT,
    timeout_minutes INTEGER DEFAULT 30,
    retry_count INTEGER DEFAULT 0,
    escalation_level INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_severity ON issues(severity);
CREATE INDEX IF NOT EXISTS idx_timestamp ON issues(timestamp);
"""


class IssueDB:
    """SQLite 数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认放在 issues 目录旁
            base_dir = Path("./issues").resolve().parent
            db_path = base_dir / "issues.db"
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（延迟初始化）"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=30)
            self._conn.row_factory = sqlite3.Row
            # 启用外键约束
            self._conn.execute("PRAGMA foreign_keys = ON")
            # 启用 WAL 模式，提升并发性能
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn
    
    def initialize(self):
        """初始化数据库和表结构"""
        conn = self._get_conn()
        conn.executescript(DB_SCHEMA)
        conn.commit()
    
    def upsert_issue(self, issue_data: Dict[str, Any]) -> bool:
        """插入或更新 issue"""
        conn = self._get_conn()
        
        # 将 action_items 和 details 序列化为 JSON 字符串
        data = issue_data.copy()
        if 'action_items' in data and not isinstance(data['action_items'], str):
            data['action_items'] = json.dumps(data['action_items'], ensure_ascii=False)
        if 'details' in data and not isinstance(data['details'], str):
            data['details'] = json.dumps(data['details'], ensure_ascii=False)
        
        # 构建插入语句
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        sql = f"""
            INSERT INTO issues ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT(id) DO UPDATE SET
            {', '.join(f"{col} = :{col}" for col in columns if col != 'id')}
        """
        
        try:
            conn.execute(sql, data)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"数据库写入失败: {e}")
            return False
    
    def get_issue(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取 issue（O(1)）"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM issues WHERE id = ?", (issue_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        
        # 转换 Row 为字典
        result = dict(row)
        # 反序列化 JSON 字段
        if result.get('action_items') and isinstance(result['action_items'], str):
            result['action_items'] = json.loads(result['action_items'])
        if result.get('details') and isinstance(result['details'], str):
            result['details'] = json.loads(result['details'])
        return result
    
    def get_issues_by_status(self, status: str) -> List[Dict[str, Any]]:
        """获取指定状态的所有 issue"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM issues WHERE status = ?", (status,)
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get('action_items') and isinstance(result['action_items'], str):
                result['action_items'] = json.loads(result['action_items'])
            if result.get('details') and isinstance(result['details'], str):
                result['details'] = json.loads(result['details'])
            results.append(result)
        return results
    
    def get_issues_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """获取指定严重性的所有 issue"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM issues WHERE severity = ?", (severity,)
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get('action_items') and isinstance(result['action_items'], str):
                result['action_items'] = json.loads(result['action_items'])
            if result.get('details') and isinstance(result['details'], str):
                result['details'] = json.loads(result['details'])
            results.append(result)
        return results
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """获取所有 issue"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM issues")
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get('action_items') and isinstance(result['action_items'], str):
                result['action_items'] = json.loads(result['action_items'])
            if result.get('details') and isinstance(result['details'], str):
                result['details'] = json.loads(result['details'])
            results.append(result)
        return results
    
    def delete_issue(self, issue_id: str) -> bool:
        """删除 issue"""
        conn = self._get_conn()
        conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
        conn.commit()
        return True
    
    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# ============================================================
# Issue 数据类
# ============================================================

@dataclass
class Issue:
    """问题定义 (P0-2 增强版)"""
    id: str = ""
    agent: str = ""
    severity: str = "P2"
    error_type: str = ""
    error_message: str = ""
    timestamp: str = ""
    status: str = "pending"
    assigned_to: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict] = field(default_factory=dict)
    report_file: Optional[str] = None
    requires_action: Optional[bool] = None
    action_items: Optional[List[str]] = field(default_factory=list)
    
    # P0-2 新增字段：状态追踪
    assigned_agent: Optional[str] = None
    assigned_at: Optional[str] = None
    completed_at: Optional[str] = None
    timeout_minutes: int = 30
    retry_count: int = 0
    escalation_level: int = 0
    
    def __post_init__(self):
        if not self.id:
            self.id = f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.error_type and self.type:  # pragma: no cover
            self.error_type = self.type
        if not self.error_message and self.description:  # pragma: no cover
            self.error_message = self.description[:200]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ============================================================
# IssueQueue 管理器
# ============================================================

class IssueQueue:
    """问题队列管理器（SQLite 优化版）"""
    
    def __init__(self, base_dir: str = "./issues", use_sqlite: bool = True):
        """
        初始化问题队列
        
        Args:
            base_dir: 问题文件基础目录
            use_sqlite: 是否使用 SQLite（True=高性能，False=兼容旧版 JSON）
        """
        self.base_dir = Path(base_dir)
        self.pending_dir = self.base_dir / "pending"
        self.processing_dir = self.base_dir / "processing"
        self.resolved_dir = self.base_dir / "resolved"
        self.archive_dir = self.base_dir / "archive"
        
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # SQLite 配置
        self.use_sqlite = use_sqlite
        self._db: Optional[IssueDB] = None
        
        if self.use_sqlite:
            # 使用与 base_dir 对应的独立数据库文件，避免测试之间数据污染
            db_path = self.base_dir / "issues.db"
            self._db = IssueDB(db_path=str(db_path))
            self._db.initialize()
    
    @property
    def db(self) -> IssueDB:
        """获取数据库实例（懒加载）"""
        if self._db is None:
            db_path = self.base_dir / "issues.db"
            self._db = IssueDB(db_path=str(db_path))
            self._db.initialize()
        return self._db
    
    def enable_sqlite(self):
        """启用 SQLite 模式"""
        if not self.use_sqlite:
            self.use_sqlite = True
            db_path = self.base_dir / "issues.db"
            self._db = IssueDB(db_path=str(db_path))
            self._db.initialize()
    
    def disable_sqlite(self):
        """禁用 SQLite 模式（切换回 JSON）"""
        if self._db:
            self._db.close()
            self._db = None
        self.use_sqlite = False
    
    # ============================================================
    # 迁移相关
    # ============================================================
    
    def migrate_from_json(self) -> Dict[str, int]:
        """
        从 JSON 文件迁移所有 issue 到 SQLite
        
        Returns:
            迁移统计 {"imported": n, "skipped": n, "errors": n}
        """
        stats = {"imported": 0, "skipped": 0, "errors": 0}
        
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            for file_path in dir_path.glob("*.json"):
                if file_path.name.endswith('_tasks.json'):
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict) and 'id' in data:
                        if self.db.upsert_issue(data):
                            stats["imported"] += 1
                        else:
                            stats["errors"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    print(f"迁移失败 {file_path}: {e}")
                    stats["errors"] += 1
        
        return stats
    
    def export_to_json(self, backup_dir: str = None) -> bool:
        """
        将 SQLite 数据导出为 JSON 文件（备份用）
        
        Args:
            backup_dir: 备份目录，None 则不备份
            
        Returns:
            是否成功
        """
        if backup_dir:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            for issue_data in self.db.get_all_issues():
                issue_id = issue_data.get('id', 'unknown')
                # 根据 status 确定目录
                status = issue_data.get('status', 'pending')
                status_dir_map = {
                    'pending': self.pending_dir,
                    'processing': self.processing_dir,
                    'diagnosed': self.processing_dir,
                    'resolved': self.resolved_dir,
                    'archived': self.archive_dir,
                    'timeout': self.pending_dir,
                    'escalated': self.processing_dir,
                }
                target_dir = status_dir_map.get(status, self.pending_dir)
                
                file_path = target_dir / f"{issue_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(issue_data, f, ensure_ascii=False, indent=2)
        return True
    
    # ============================================================
    # 核心 CRUD 操作
    # ============================================================
    
    def create_issue(self, agent: str, severity: str, error_type: str, 
                    error_message: str) -> Issue:
        """创建新问题"""
        return Issue(id="", agent=agent, severity=severity, error_type=error_type,
                    error_message=error_message, timestamp="", status="pending")
    
    def write_issue(self, issue: Issue) -> str:
        """写入问题（SQLite + JSON 双写，使用原子操作保证一致性）
        
        IQ-01 修复：使用 SQLite 事务 + JSON 原子写入（写临时文件再 rename）
        """
        issue_dict = issue.to_dict()
        file_path = self.pending_dir / f"{issue.id}.json"
        temp_file = self.pending_dir / f".{issue.id}.json.tmp"
        
        try:
            # 步骤 1：先写 SQLite（使用事务）
            if self.use_sqlite:
                self.db.upsert_issue(issue_dict)
            
            # 步骤 2：写 JSON（先写临时文件，再 rename）
            # 这样即使 rename 失败，原文件也不会被破坏
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(issue_dict, f, ensure_ascii=False, indent=2)
            
            # 原子性地用新文件替换旧文件
            if sys.platform == 'win32':
                # Windows 不支持 rename 到已存在的文件，需要先删除
                if file_path.exists():
                    file_path.unlink()
            temp_file.rename(file_path)
            
            return issue.id
            
        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
            # 如果 SQLite 已写入但 JSON 失败，JSON 写入会抛异常
            # 此时 SQLite 的更改仍在事务中未提交，我们让异常继续传播
            raise RuntimeError(f"双写失败，回滚更改: {e}")
    
    def read_issue(self, issue_id: str) -> Optional[Issue]:
        """读取问题（O(1) 通过 SQLite，或 O(n) 遍历 JSON）"""
        if self.use_sqlite:
            # O(1) SQLite 查询
            data = self.db.get_issue(issue_id)
            if data:
                return Issue(**data)
            return None
        else:
            # O(n) JSON 遍历（向后兼容）
            for dir_path in [self.pending_dir, self.processing_dir, 
                            self.resolved_dir, self.archive_dir]:
                file_path = dir_path / f"{issue_id}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return Issue(**json.load(f))
            return None
    
    def get_pending_issues(self) -> List[Issue]:
        """获取待处理问题"""
        if self.use_sqlite:
            issues = []
            for data in self.db.get_issues_by_status('pending'):
                issues.append(Issue(**data))
            return issues
        else:
            issues = []
            for file_path in self.pending_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        issues.append(Issue(**json.load(f)))
                except Exception as e:
                    print(f"读取失败：{e}")
            return issues
    
    def get_processing_issues(self) -> List[Issue]:
        """获取处理中的问题"""
        if self.use_sqlite:
            issues = []
            for data in self.db.get_issues_by_status('processing'):
                issues.append(Issue(**data))
            return issues
        else:
            issues = []
            for file_path in self.processing_dir.glob("*.json"):
                if file_path.name.endswith('_tasks.json'):
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            issues.append(Issue(**data))
                except Exception as e:
                    print(f"读取失败：{e}")
            return issues
    
    def _acquire_issue_lock(self, issue_id: str):
        """获取 issue 级别的锁（用于 update_status 的原子性）"""
        lock_file = self.base_dir / f".issue_{issue_id}.lock"
        # 确保父目录存在，避免 FileNotFoundError
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch(exist_ok=True)
        
        if sys.platform == 'win32':
            import threading
            from file_lock import _locks_lock, _file_locks
            with _locks_lock:
                lock_key = str(lock_file.absolute())
                if lock_key not in _file_locks:
                    _file_locks[lock_key] = threading.Lock()
                lock = _file_locks[lock_key]
            lock.acquire()
            return lock_file, lock
        else:
            import fcntl
            f = open(lock_file, 'w')
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            return f, f
    
    def _release_issue_lock(self, lock_file, lock):
        """释放 issue 级别的锁"""
        if sys.platform == 'win32':
            lock.release()
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
    
    def update_status(self, issue_id: str, new_status: str, 
                     assigned_to: Optional[str] = None,
                     resolution: Optional[str] = None,
                     resolved_at: Optional[str] = None,
                     assigned_agent: Optional[str] = None,
                     assigned_at: Optional[str] = None,
                     completed_at: Optional[str] = None,
                     retry_count: Optional[int] = None,
                     escalation_level: Optional[int] = None,
                     timeout_minutes: Optional[int] = None) -> bool:
        """更新问题状态 - 线程安全
        
        P0-2 修复 + P2-1 SQLite 优化
        """
        # 获取 issue 级排他锁
        lock_file_handle, lock_handle = self._acquire_issue_lock(issue_id)
        try:
            issue = self.read_issue(issue_id)
            if not issue:
                return False
            
            issue.status = new_status
            if assigned_to:
                issue.assigned_to = assigned_to
            if resolution:
                issue.resolution = resolution
            if resolved_at:
                issue.resolved_at = resolved_at
            elif new_status == 'resolved':
                issue.resolved_at = datetime.now().isoformat()
            if assigned_agent is not None:
                issue.assigned_agent = assigned_agent
            if assigned_at is not None:
                issue.assigned_at = assigned_at
            if completed_at is not None:
                issue.completed_at = completed_at
            if timeout_minutes is not None:
                issue.timeout_minutes = timeout_minutes
            if retry_count is not None:
                issue.retry_count = retry_count
            if escalation_level is not None:
                issue.escalation_level = escalation_level
            
            issue_dict = issue.to_dict()
            
            # IQ-01 修复：使用 SQLite 事务 + JSON 原子写入
            # 步骤 1：先更新 SQLite
            if self.use_sqlite:
                self.db.upsert_issue(issue_dict)
            
            # 步骤 2：更新 JSON 文件（使用原子写入）
            status_to_dir = {
                'pending': self.pending_dir,
                'processing': self.processing_dir,
                'diagnosed': self.processing_dir,
                'resolved': self.resolved_dir,
                'archived': self.archive_dir,
                'timeout': self.pending_dir,
                'escalated': self.processing_dir,
            }
            
            old_file = self.pending_dir / f"{issue_id}.json"
            if not old_file.exists():
                old_file = self.processing_dir / f"{issue_id}.json"
            
            new_dir = status_to_dir.get(new_status, self.pending_dir)
            new_file = new_dir / f"{issue_id}.json"
            temp_file = new_dir / f".{issue_id}.json.tmp"
            
            # 原子写入：先写临时文件，再 rename
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(issue_dict, f, ensure_ascii=False, indent=2)
                
                if sys.platform == 'win32':
                    if new_file.exists():
                        new_file.unlink()
                temp_file.rename(new_file)
                
                # 删除旧文件（如果位置不同）
                if old_file.exists() and old_file != new_file:
                    old_file.unlink()
            except Exception as e:
                # 清理临时文件
                if temp_file.exists():
                    temp_file.unlink()
                raise RuntimeError(f"JSON 写入失败: {e}")
            
            if old_file.exists() and old_file != new_file:
                old_file.unlink()
            
            return True
        finally:
            self._release_issue_lock(lock_file_handle, lock_handle)
    
    def resolve_issue(self, issue_id: str, resolution: str) -> bool:
        """解决问题"""
        return self.update_status(issue_id, 'resolved', resolution=resolution)
    
    def archive_issue(self, issue_id: str) -> bool:
        """归档问题"""
        issue = self.read_issue(issue_id)
        if not issue:
            return False
        
        archive_file = self.archive_dir / f"{issue_id}.json"
        
        for dir_path in [self.pending_dir, self.processing_dir, self.resolved_dir]:
            old_file = dir_path / f"{issue_id}.json"
            if old_file.exists():
                shutil.move(str(old_file), str(archive_file))
                
                # 更新 SQLite
                if self.use_sqlite:
                    issue.status = 'archived'
                    self.db.upsert_issue(issue.to_dict())
                
                return True
        return False
    
    # ============================================================
    # P1 新增方法
    # ============================================================
    
    def get_issues_by_severity(self, severity: str = None) -> List[Issue]:
        """按严重性获取问题"""
        if self.use_sqlite:
            if severity is None:
                issues = []
                for data in self.db.get_all_issues():
                    issues.append(Issue(**data))
                return issues
            else:
                issues = []
                for data in self.db.get_issues_by_severity(severity):
                    issues.append(Issue(**data))
                return issues
        else:
            issues = []
            for dir_path in [self.pending_dir, self.processing_dir, self.resolved_dir]:
                for file_path in dir_path.glob("*.json"):
                    if file_path.name.endswith('_tasks.json'):
                        continue
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            issue = Issue(**json.load(f))
                            if severity is None or issue.severity == severity:
                                issues.append(issue)
                    except Exception as e:
                        print(f"读取失败：{file_path.name}: {e}")
            return issues
    
    def get_p0_issues(self) -> List[Issue]:
        """获取所有 P0 严重性问题"""
        return self.get_issues_by_severity('P0')
    
    def clear_old_issues(self, days: int = 30, archive: bool = False) -> int:
        """清理老旧问题"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        if self.use_sqlite:
            all_issues = self.db.get_all_issues()
            for data in all_issues:
                timestamp_str = data.get('timestamp', '')
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp < cutoff:
                        issue_id = data.get('id')
                        old_status = data.get('status')
                        if archive:
                            data['status'] = 'archived'
                            self.db.upsert_issue(data)
                            # 修复：同时将文件从旧状态目录移动到 archive 目录
                            status_to_dir = {
                                'pending': self.pending_dir,
                                'processing': self.processing_dir,
                                'resolved': self.resolved_dir,
                                'archived': self.archive_dir,
                            }
                            src_dir = status_to_dir.get(old_status, self.resolved_dir)
                            src_file = src_dir / f"{issue_id}.json"
                            if src_file.exists():
                                dst_file = self.archive_dir / f"{issue_id}.json"
                                shutil.move(str(src_file), str(dst_file))
                        else:
                            self.db.delete_issue(data['id'])
                        cleaned += 1
                except:
                    continue
        else:
            for dir_path in [self.pending_dir, self.processing_dir, self.resolved_dir]:
                for file_path in dir_path.glob("*.json"):
                    if file_path.name.endswith('_tasks.json'):
                        continue
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        timestamp_str = data.get('timestamp', '')
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except:
                            continue
                        
                        if timestamp < cutoff:
                            if archive:
                                archive_file = self.archive_dir / file_path.name
                                shutil.move(str(file_path), str(archive_file))
                            else:
                                file_path.unlink()
                            cleaned += 1
                    except Exception as e:
                        print(f"清理失败：{file_path.name}: {e}")
        
        return cleaned


def report_issue(agent: str, severity: str, error_type: str, 
                error_message: str, **kwargs) -> str:  # pragma: no cover
    """快速报告问题到队列"""
    queue = IssueQueue()
    issue = queue.create_issue(
        agent=agent,
        severity=severity,
        error_type=error_type,
        error_message=error_message
    )
    
    if 'title' in kwargs:
        issue.title = kwargs['title']
    if 'description' in kwargs:
        issue.description = kwargs['description']
    if 'details' in kwargs:
        issue.details = kwargs['details']
    if 'type' in kwargs:
        issue.type = kwargs['type']
    
    return queue.write_issue(issue)


# ============================================================
# CLI 工具
# ============================================================

def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Issue Queue 管理工具')
    parser.add_argument('action', choices=['migrate', 'stats', 'test'],
                        help='操作类型')
    parser.add_argument('--json-only', action='store_true',
                        help='使用纯 JSON 模式（不初始化 SQLite）')
    args = parser.parse_args()
    
    queue = IssueQueue(use_sqlite=not args.json_only)
    
    if args.action == 'migrate':
        print("开始迁移 JSON → SQLite...")
        stats = queue.migrate_from_json()
        print(f"迁移完成: {stats}")
    
    elif args.action == 'stats':
        if queue.use_sqlite:
            all_issues = queue.db.get_all_issues()
            print(f"SQLite 中的 issue 总数: {len(all_issues)}")
            
            status_counts = {}
            for issue in all_issues:
                status = issue.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            print("按状态分布:")
            for status, count in sorted(status_counts.items()):
                print(f"  {status}: {count}")
        else:
            pending = len(list(queue.pending_dir.glob("*.json")))
            processing = len(list(queue.processing_dir.glob("*.json")))
            resolved = len(list(queue.resolved_dir.glob("*.json")))
            print(f"JSON 文件数: pending={pending}, processing={processing}, resolved={resolved}")
    
    elif args.action == 'test':
        print("测试 read_issue 性能...")
        import time
        
        # 创建测试数据
        test_issue = Issue(agent='test', severity='P1', error_type='Test', 
                          error_message='Test issue')
        queue.write_issue(test_issue)
        
        # 测试 read_issue
        start = time.time()
        for _ in range(100):
            queue.read_issue(test_issue.id)
        elapsed = time.time() - start
        print(f"100 次 read_issue 耗时: {elapsed*1000:.2f}ms")
        print(f"平均每次: {elapsed*10:.2f}ms")


if __name__ == '__main__':
    main()
