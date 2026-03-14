#!/usr/bin/env python3
"""
问题队列管理系统

功能:
- 写入问题到队列
- 读取待处理问题
- 更新问题状态
- 查询问题历史
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Issue:
    """问题定义"""
    id: str
    agent: str = ""
    severity: str = "P2"  # P0/P1/P2/P3
    error_type: str = ""
    error_message: str = ""
    timestamp: str = ""
    status: str = "pending"  # pending/processing/resolved/archived
    assigned_to: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    # 兼容 QA report 格式
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict] = field(default_factory=dict)
    report_file: Optional[str] = None
    requires_action: Optional[bool] = None
    action_items: Optional[List[str]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        # 如果没有 error_type，从 type 字段复制
        if not self.error_type and self.type:
            self.error_type = self.type
        # 如果没有 error_message，从 description 复制
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
        
        # 确保目录存在
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_issue(self, agent: str, severity: str, error_type: str, 
                    error_message: str) -> Issue:
        """创建新问题"""
        issue = Issue(
            id="",
            agent=agent,
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            timestamp="",
            status="pending"
        )
        return issue
    
    def write_issue(self, issue: Issue) -> str:
        """写入问题到队列"""
        file_path = self.pending_dir / f"{issue.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(issue), f, ensure_ascii=False, indent=2)
        return issue.id
    
    def read_issue(self, issue_id: str) -> Optional[Issue]:
        """读取问题"""
        # 在所有目录中查找
        for dir_path in [self.pending_dir, self.processing_dir, 
                        self.resolved_dir, self.archive_dir]:
            file_path = dir_path / f"{issue_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return Issue(**data)
        return None
    
    def get_pending_issues(self) -> List[Issue]:
        """获取所有待处理问题"""
        issues = []
        for file_path in self.pending_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    issues.append(Issue(**data))
            except Exception as e:
                print(f"读取问题 {file_path.name} 失败：{e}")
        return issues
    
    def update_status(self, issue_id: str, new_status: str, 
                     assigned_to: Optional[str] = None,
                     resolution: Optional[str] = None) -> bool:
        """更新问题状态"""
        issue = self.read_issue(issue_id)
        if not issue:
            return False
        
        # 确定目标目录
        status_to_dir = {
            'pending': self.pending_dir,
            'processing': self.processing_dir,
            'resolved': self.resolved_dir,
            'archived': self.archive_dir,
        }
        
        # 更新问题
        issue.status = new_status
        if assigned_to:
            issue.assigned_to = assigned_to
        if resolution:
            issue.resolution = resolution
        if new_status == 'resolved':
            issue.resolved_at = datetime.now().isoformat()
        
        # 移动文件到新目录
        old_file = self.pending_dir / f"{issue_id}.json"
        if not old_file.exists():
            old_file = self.processing_dir / f"{issue_id}.json"
        
        new_file = status_to_dir.get(new_status, self.pending_dir) / f"{issue_id}.json"
        
        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(issue), f, ensure_ascii=False, indent=2)
        
        if old_file.exists() and old_file != new_file:
            old_file.unlink()
        
        return True
    
    def get_issues_by_severity(self, severity: str) -> List[Issue]:
        """按严重性获取问题"""
        issues = self.get_pending_issues()
        return [i for i in issues if i.severity == severity]
    
    def get_p0_issues(self) -> List[Issue]:
        """获取所有 P0 问题"""
        return self.get_issues_by_severity('P0')
    
    def clear_old_issues(self, days: int = 30):
        """清理旧问题（移动到归档）"""
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        for dir_path in [self.resolved_dir]:
            for file_path in dir_path.glob("*.json"):
                mtime = file_path.stat().st_mtime
                if mtime < cutoff:
                    # 移动到归档
                    archive_file = self.archive_dir / file_path.name
                    file_path.rename(archive_file)


# 快捷函数
def report_issue(agent: str, severity: str, error_type: str, 
                error_message: str) -> str:
    """快速上报问题"""
    queue = IssueQueue()
    issue = queue.create_issue(agent, severity, error_type, error_message)
    issue_id = queue.write_issue(issue)
    return issue_id


if __name__ == '__main__':
    # 测试
    queue = IssueQueue()
    
    # 获取待处理问题
    pending = queue.get_pending_issues()
    print(f"待处理问题数：{len(pending)}")
    
    for issue in pending[:3]:
        print(f"\n问题：{issue.id}")
        print(f"  严重性：{issue.severity}")
        print(f"  类型：{issue.error_type or issue.type}")
        print(f"  状态：{issue.status}")
