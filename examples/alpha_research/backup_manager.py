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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """备份信息"""
    backup_type: str  # daily/weekly/monthly
    timestamp: str
    path: str
    size_mb: float
    file_count: int
    verified: bool = False


class BackupManager:
    """备份管理器"""
    
    def __init__(self, data_dir: str = "./data", 
                 backup_dir: str = "./data/backups"):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
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
    
    def create_backup(self, backup_type: str = 'daily') -> BackupInfo:
        """
        创建备份
        
        Args:
            backup_type: daily/weekly/monthly
            
        Returns:
            BackupInfo: 备份信息
        """
        logger.info(f"开始创建 {backup_type} 备份")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = self.config[backup_type]['subdir']
        backup_path = self.backup_dir / backup_subdir / timestamp
        
        # 创建备份目录
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 复制数据
        file_count = 0
        total_size = 0
        
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
                file_count += sum(1 for _ in item.rglob('*'))
                total_size += sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
        
        # 保存元数据
        metadata = {
            'backup_type': backup_type,
            'timestamp': timestamp,
            'file_count': file_count,
            'total_size_bytes': total_size,
            'source_dir': str(self.data_dir)
        }
        
        with open(backup_path / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 创建备份信息
        backup_info = BackupInfo(
            backup_type=backup_type,
            timestamp=timestamp,
            path=str(backup_path),
            size_mb=total_size / 1024 / 1024,
            file_count=file_count
        )
        
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
    
    def cleanup_old_backups(self, backup_type: str = 'daily') -> int:
        """
        清理过期备份
        
        Args:
            backup_type: daily/weekly/monthly
            
        Returns:
            int: 清理的备份数量
        """
        retention_days = self.config[backup_type]['retention_days']
        backup_subdir = self.config[backup_type]['subdir']
        backup_path = self.backup_dir / backup_subdir
        
        if not backup_path.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        for backup_dir in backup_path.iterdir():
            if not backup_dir.is_dir():
                continue
            
            # 解析备份时间
            try:
                backup_time = datetime.strptime(backup_dir.name, '%Y%m%d_%H%M%S')
                if backup_time < cutoff_date:
                    shutil.rmtree(backup_dir)
                    cleaned_count += 1
                    logger.info(f"清理过期备份：{backup_dir.name}")
            except ValueError:
                continue
        
        logger.info(f"清理完成：删除 {cleaned_count} 个过期备份")
        return cleaned_count
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for btype in [backup_type] if backup_type else ['daily', 'weekly', 'monthly']:
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
                        'type': btype,
                        'timestamp': metadata.get('timestamp', backup_dir.name),
                        'path': str(backup_dir),
                        'size_mb': metadata.get('total_size_bytes', 0) / 1024 / 1024,
                        'file_count': metadata.get('file_count', 0)
                    })
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)


# 便捷函数

def create_daily_backup() -> BackupInfo:
    """创建每日备份"""
    manager = BackupManager()
    return manager.create_backup('daily')


def create_weekly_backup() -> BackupInfo:
    """创建每周备份"""
    manager = BackupManager()
    return manager.create_backup('weekly')


def create_monthly_backup() -> BackupInfo:
    """创建每月备份"""
    manager = BackupManager()
    return manager.create_backup('monthly')


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
        print(f"· {backup['type']}: {backup['timestamp']} ({backup['size_mb']:.2f} MB)")
    
    print("\n✅ 备份管理器已就绪")
