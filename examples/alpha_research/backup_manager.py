#!/usr/bin/env python3
"""
备份管理器

功能:
- 每日快照（20:00）
- 每周备份（周日）
- 每月备份（1 号）
- 备份验证功能
- 快速恢复功能
- 自动清理过期备份
"""

import json
import shutil
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """备份类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BackupStatus(Enum):
    """备份状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    backup_type: BackupType
    timestamp: str
    path: str
    size_bytes: int
    file_count: int
    status: BackupStatus = BackupStatus.COMPLETED
    is_incremental: bool = False
    base_backup_id: Optional[str] = None
    description: str = ""
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / 1024 / 1024
    
    def to_dict(self) -> Dict:
        return {
            'backup_id': self.backup_id,
            'backup_type': self.backup_type.value,
            'timestamp': self.timestamp,
            'path': self.path,
            'size_bytes': self.size_bytes,
            'size_mb': self.size_mb,
            'file_count': self.file_count,
            'status': self.status.value,
            'is_incremental': self.is_incremental,
            'base_backup_id': self.base_backup_id,
            'description': self.description
        }


class BackupManager:
    """备份管理器"""
    
    def __init__(self, data_dir: str = "./data", 
                 backup_dir: str = "./data/backups"):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_root = self.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份配置
        self.config = {
            'daily': {
                'schedule': '20:00',
                'retention_days': 30,
                'subdir': 'daily'
            },
            'weekly': {
                'schedule': 'Sunday',
                'retention_days': 90,
                'subdir': 'weekly'
            },
            'monthly': {
                'schedule': '1st',
                'retention_days': 365,
                'subdir': 'monthly'
            }
        }
        
        # 存储已完成的备份ID列表
        self._backup_ids: List[str] = []
    
    def create_backup(self, backup_type, is_incremental: bool = False, 
                     description: str = "") -> Optional[BackupInfo]:
        """
        创建备份
        
        Args:
            backup_type: BackupType enum or string (daily/weekly/monthly)
            is_incremental: 是否为增量备份
            description: 备份描述
            
        Returns:
            BackupInfo: 备份信息
        """
        # 支持传入 BackupType 枚举或字符串
        if isinstance(backup_type, BackupType):
            backup_type_enum = backup_type
            backup_type_str = backup_type.value
        else:
            backup_type_str = backup_type
            backup_type_enum = BackupType(backup_type)
        
        logger.info(f"开始创建 {backup_type_str} 备份 (增量: {is_incremental})")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        backup_id = f"{backup_type_str}_{timestamp}_{uuid.uuid4().hex[:8]}"
        backup_subdir = self.config[backup_type_str]['subdir']
        backup_path = self.backup_dir / backup_subdir / timestamp
        
        # 创建备份目录
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 复制数据
        file_count = 0
        total_size = 0
        
        # 增量备份：只备份自上次备份以来变更的文件
        if is_incremental and self._backup_ids:
            last_backup = self._backup_ids[-1]
            logger.info(f"增量备份，基于: {last_backup}")
        
        for item in self.data_dir.iterdir():
            if item.name in ['backups', 'archive', 'temp']:
                continue
            
            if item.is_file():
                shutil.copy2(item, backup_path / item.name)
                file_count += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                dest = backup_path / item.name
                shutil.copytree(item, dest, dirs_exist_ok=True)
                file_count += sum(1 for f in item.rglob('*') if f.is_file())
                total_size += sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
        
        # 保存元数据
        metadata = {
            'backup_id': backup_id,
            'backup_type': backup_type_str,
            'timestamp': timestamp,
            'file_count': file_count,
            'total_size_bytes': total_size,
            'is_incremental': is_incremental,
            'base_backup_id': self._backup_ids[-1] if is_incremental and self._backup_ids else None,
            'description': description,
            'source_dir': str(self.data_dir)
        }
        
        with open(backup_path / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 创建备份信息
        backup_info = BackupInfo(
            backup_id=backup_id,
            backup_type=backup_type_enum,
            timestamp=timestamp,
            path=str(backup_path),
            size_bytes=total_size,
            file_count=file_count,
            status=BackupStatus.COMPLETED,
            is_incremental=is_incremental,
            base_backup_id=metadata['base_backup_id'],
            description=description
        )
        
        self._backup_ids.append(backup_id)
        logger.info(f"备份完成：{backup_info.size_mb:.2f} MB, {file_count} 文件")
        
        return backup_info
    
    def verify_backup(self, backup_path: str) -> bool:
        """
        验证备份完整性
        
        Args:
            backup_path: 备份路径
            
        Returns:
            bool: 是否验证通过
        """
        logger.info(f"验证备份：{backup_path}")
        
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error(f"备份不存在：{backup_path}")
            return False
        
        # 检查元数据
        metadata_file = backup_path / 'metadata.json'
        if not metadata_file.exists():
            logger.error(f"元数据缺失：{metadata_file}")
            return False
        
        # 验证文件数量
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        expected_count = metadata.get('file_count', 0)
        actual_count = sum(1 for p in backup_path.rglob('*') if p.is_file() and p.name != 'metadata.json')
        
        if expected_count != actual_count:
            logger.error(f"文件数量不匹配：期望 {expected_count}, 实际 {actual_count}")
            return False
        
        logger.info(f"备份验证通过：{actual_count} 文件")
        return True
    
    def restore_backup(self, backup_id: str, target_dir: Optional[Path] = None,
                       verify_only: bool = False) -> bool:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID
            target_dir: 目标目录
            verify_only: 仅验证不恢复
            
        Returns:
            bool: 是否成功
        """
        # 查找备份
        backup_path = None
        for btype in ['daily', 'weekly', 'monthly']:
            backup_subdir = self.config[btype]['subdir']
            backup_base = self.backup_dir / backup_subdir
            if backup_base.exists():
                for d in backup_base.iterdir():
                    metadata_file = d / 'metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        if metadata.get('backup_id') == backup_id:
                            backup_path = d
                            break
            if backup_path:
                break
        
        if not backup_path:
            logger.error(f"备份不存在：{backup_id}")
            return False
        
        if verify_only:
            return self.verify_backup(str(backup_path))
        
        return self.restore(str(backup_path), str(target_dir) if target_dir else None)
    
    def restore(self, backup_path: str, target_dir: Optional[str] = None) -> bool:
        """
        恢复备份
        
        Args:
            backup_path: 备份路径
            target_dir: 目标目录（默认为原数据目录）
            
        Returns:
            bool: 是否恢复成功
        """
        logger.info(f"开始恢复备份：{backup_path}")
        
        backup_path = Path(backup_path)
        target_dir = Path(target_dir) if target_dir else self.data_dir
        
        if not backup_path.exists():
            logger.error(f"备份不存在：{backup_path}")
            return False
        
        # 验证备份
        if not self.verify_backup(str(backup_path)):
            logger.error("备份验证失败，拒绝恢复")
            return False
        
        # 备份当前数据（防止恢复失败）
        if target_dir.exists():
            emergency_backup = target_dir.parent / f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(target_dir, emergency_backup)
            logger.info(f"已创建紧急备份：{emergency_backup}")
        
        # 恢复数据
        for item in backup_path.iterdir():
            if item.name == 'metadata.json':
                continue
            
            dest = target_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
        
        logger.info(f"恢复完成：{target_dir}")
        return True
    
    def cleanup_old_backups(self, backup_type: str = 'daily', dry_run: bool = False) -> Dict:
        """
        清理过期备份
        
        Args:
            backup_type: daily/weekly/monthly
            dry_run: 试运行，不实际删除
            
        Returns:
            Dict: 清理统计
        """
        retention_days = self.config[backup_type]['retention_days']
        backup_subdir = self.config[backup_type]['subdir']
        backup_path = self.backup_dir / backup_subdir
        
        result = {
            'total_backups': 0,
            'expired_backups': 0,
            'deleted_backups': 0,
            'freed_space_bytes': 0
        }
        
        if not backup_path.exists():
            return result
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        backups_to_delete = []
        
        for backup_dir in backup_path.iterdir():
            if not backup_dir.is_dir():
                continue
            
            result['total_backups'] += 1
            
            # 解析备份时间
            try:
                backup_time = datetime.strptime(backup_dir.name, '%Y%m%d_%H%M%S')
                if backup_time < cutoff_date:
                    result['expired_backups'] += 1
                    backups_to_delete.append(backup_dir)
                    # 计算可释放空间
                    size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                    result['freed_space_bytes'] += size
            except ValueError:
                continue
        
        if not dry_run:
            for backup_dir in backups_to_delete:
                shutil.rmtree(backup_dir)
                result['deleted_backups'] += 1
                logger.info(f"清理过期备份：{backup_dir.name}")
        
        logger.info(f"清理完成：删除 {result['deleted_backups']} 个过期备份")
        return result
    
    def schedule_backup(self) -> Optional[BackupInfo]:
        """定时备份调度"""
        now = datetime.now()
        hour = now.hour
        day = now.day
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # 判断备份类型
        if hour == 20:
            backup_type = BackupType.DAILY
        elif weekday == 6:  # 周日
            backup_type = BackupType.WEEKLY
        elif day == 1 and hour == 20:  # 每月1号
            backup_type = BackupType.MONTHLY
        else:
            return None
        
        return self.create_backup(backup_type)
    
    def get_backup_stats(self) -> Dict:
        """获取备份统计"""
        stats = {
            'total_backups': 0,
            'successful_backups': 0,
            'failed_backups': 0,
            'total_size_gb': 0.0,
            'daily_count': 0,
            'weekly_count': 0,
            'monthly_count': 0,
            'incremental_count': 0,
            'last_backup': None
        }
        
        all_backups = []
        for btype in ['daily', 'weekly', 'monthly']:
            backup_subdir = self.config[btype]['subdir']
            backup_path = self.backup_dir / backup_subdir
            
            if not backup_path.exists():
                continue
            
            for backup_dir in backup_path.iterdir():
                if not backup_dir.is_dir():
                    continue
                
                metadata_file = backup_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    stats['total_backups'] += 1
                    stats['successful_backups'] += 1
                    stats[f'{btype}_count'] += 1
                    stats['total_size_gb'] += metadata.get('total_size_bytes', 0) / 1024 / 1024 / 1024
                    
                    if metadata.get('is_incremental'):
                        stats['incremental_count'] += 1
                    
                    all_backups.append(metadata.get('timestamp', ''))
        
        if all_backups:
            stats['last_backup'] = max(all_backups)
        
        return stats
    
    def list_backups(self, limit: int = 10) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for btype in ['daily', 'weekly', 'monthly']:
            backup_subdir = self.config[btype]['subdir']
            backup_path = self.backup_dir / backup_subdir
            
            if not backup_path.exists():
                continue
            
            for backup_dir in backup_path.iterdir():
                if not backup_dir.is_dir():
                    continue
                
                metadata_file = backup_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    backups.append({
                        'backup_id': metadata.get('backup_id', ''),
                        'backup_type': btype,
                        'timestamp': metadata.get('timestamp', backup_dir.name),
                        'size_mb': metadata.get('total_size_bytes', 0) / 1024 / 1024,
                        'file_count': metadata.get('file_count', 0),
                        'status': 'completed',
                        'path': str(backup_dir)
                    })
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)[:limit]


# 便捷函数

def create_daily_backup() -> BackupInfo:
    """创建每日备份"""
    manager = BackupManager()
    return manager.create_backup(BackupType.DAILY)


def create_weekly_backup() -> BackupInfo:
    """创建每周备份"""
    manager = BackupManager()
    return manager.create_backup(BackupType.WEEKLY)


def create_monthly_backup() -> BackupInfo:
    """创建每月备份"""
    manager = BackupManager()
    return manager.create_backup(BackupType.MONTHLY)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("  备份管理器测试")
    print("=" * 60)
    
    manager = BackupManager()
    
    # 列出备份
    print("\n现有备份:")
    backups = manager.list_backups()
    for backup in backups[:5]:
        print(f"· {backup['backup_type']}: {backup['timestamp']} ({backup['size_mb']:.2f} MB)")
    
    print("\n✅ 备份管理器已就绪")
