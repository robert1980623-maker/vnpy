#!/usr/bin/env python3
"""
问题队列管理系统 (P0-2 增强版 - 添加状态追踪字段)
"""

import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Issue:
    """问题定义 (P0-2 增强版)"""
    id: str
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
        if not self.error_type and self.type:
            self.error_type = self.type
        if not self.error_message and self.description:
            self.error_message = self.description[:200]


class IssueQueue:
    """问题队列管理器"""
    
    def __init__(self, base_dir: str = "./issues"):
        self.base_dir = Path(base_dir)
        self.pending_dir = self.base_dir / "pending"
        self.processing_dir = self.base_dir / "processing"
        self.resolved_dir = self.base_dir / "resolved"
        self.archive_dir = self.base_dir / "archive"
        
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_issue(self, agent: str, severity: str, error_type: str, 
                    error_message: str) -> Issue:
        """创建新问题"""
        return Issue(id="", agent=agent, severity=severity, error_type=error_type,
                    error_message=error_message, timestamp="", status="pending")
    
    def write_issue(self, issue: Issue) -> str:
        """写入问题"""
        file_path = self.pending_dir / f"{issue.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(issue), f, ensure_ascii=False, indent=2)
        return issue.id
    
    def read_issue(self, issue_id: str) -> Optional[Issue]:
        """读取问题"""
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            file_path = dir_path / f"{issue_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return Issue(**json.load(f))
        return None
    
    def get_pending_issues(self) -> List[Issue]:
        """获取待处理问题"""
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
        issues = []
        for file_path in self.processing_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    issues.append(Issue(**json.load(f)))
            except Exception as e:
                print(f"读取失败：{e}")
        return issues
    
    def update_status(self, issue_id: str, new_status: str, 
                     assigned_to: Optional[str] = None,
                     resolution: Optional[str] = None,
                     resolved_at: Optional[str] = None,
                     assigned_agent: Optional[str] = None,
                     assigned_at: Optional[str] = None,
                     completed_at: Optional[str] = None,
                     retry_count: Optional[int] = None,
                     escalation_level: Optional[int] = None) -> bool:
        """更新问题状态 (P0-2 增强版)"""
        issue = self.read_issue(issue_id)
        if not issue:
            return False
        
        status_to_dir = {
            'pending': self.pending_dir,
            'processing': self.processing_dir,
            'resolved': self.resolved_dir,
            'archived': self.archive_dir,
            'timeout': self.pending_dir,  # timeout 的问题回到 pending 等待重试
            'escalated': self.processing_dir,  # escalated 的问题保留在 processing
        }
        
        issue.status = new_status
        if assigned_to:
            issue.assigned_to = assigned_to
        if resolution:
            issue.resolution = resolution
        if resolved_at:
            issue.resolved_at = resolved_at
        elif new_status == 'resolved':
            issue.resolved_at = datetime.now().isoformat()
        
        # P0-2 新增字段更新
        if assigned_agent is not None:
            issue.assigned_agent = assigned_agent
        if assigned_at is not None:
            issue.assigned_at = assigned_at
        if completed_at is not None:
            issue.completed_at = completed_at
        if retry_count is not None:
            issue.retry_count = retry_count
        if escalation_level is not None:
            issue.escalation_level = escalation_level
        
        old_file = self.pending_dir / f"{issue_id}.json"
        if not old_file.exists():
            old_file = self.processing_dir / f"{issue_id}.json"
        
        new_file = status_to_dir.get(new_status, self.pending_dir) / f"{issue_id}.json"
        
        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(issue), f, ensure_ascii=False, indent=2)
        
        if old_file.exists() and old_file != new_file:
            old_file.unlink()
        
        return True
    
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
                return True
        return False
