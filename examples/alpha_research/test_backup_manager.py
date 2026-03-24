#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理器测试脚本

测试场景：
1. 创建完整备份
2. 创建增量备份
3. 验证备份完整性
4. 恢复备份
5. 清理过期备份
6. 列出备份统计
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backup_manager import BackupManager, BackupType, BackupStatus


def test_create_daily_backup(manager: BackupManager) -> bool:
    """测试创建每日备份"""
    print("\n" + "="*60)
    print("测试 1: 创建每日备份")
    print("="*60)
    
    metadata = manager.create_backup(
        BackupType.DAILY,
        is_incremental=False,
        description="测试每日备份"
    )
    
    if metadata:
        print(f"✅ 备份创建成功")
        print(f"   备份 ID: {metadata.backup_id}")
        print(f"   类型：{metadata.backup_type.value}")
        print(f"   大小：{metadata.size_bytes / 1024 / 1024:.2f} MB")
        print(f"   文件数：{metadata.file_count}")
        print(f"   状态：{metadata.status.value}")
        return True
    else:
        print("❌ 备份创建失败")
        return False


def test_create_incremental_backup(manager: BackupManager) -> bool:
    """测试创建增量备份"""
    print("\n" + "="*60)
    print("测试 2: 创建增量备份")
    print("="*60)
    
    metadata = manager.create_backup(
        BackupType.DAILY,
        is_incremental=True,
        description="测试增量备份"
    )
    
    if metadata:
        print(f"✅ 增量备份创建成功")
        print(f"   备份 ID: {metadata.backup_id}")
        print(f"   增量：{metadata.is_incremental}")
        print(f"   基础备份：{metadata.base_backup_id}")
        print(f"   大小：{metadata.size_bytes / 1024 / 1024:.2f} MB")
        return True
    else:
        print("❌ 增量备份创建失败")
        return False


def test_create_weekly_backup(manager: BackupManager) -> bool:
    """测试创建每周备份"""
    print("\n" + "="*60)
    print("测试 3: 创建每周备份")
    print("="*60)
    
    metadata = manager.create_backup(
        BackupType.WEEKLY,
        is_incremental=False,
        description="测试每周备份"
    )
    
    if metadata:
        print(f"✅ 每周备份创建成功")
        print(f"   备份 ID: {metadata.backup_id}")
        print(f"   类型：{metadata.backup_type.value}")
        return True
    else:
        print("❌ 每周备份创建失败")
        return False


def test_create_monthly_backup(manager: BackupManager) -> bool:
    """测试创建每月备份"""
    print("\n" + "="*60)
    print("测试 4: 创建每月备份")
    print("="*60)
    
    metadata = manager.create_backup(
        BackupType.MONTHLY,
        is_incremental=False,
        description="测试每月备份"
    )
    
    if metadata:
        print(f"✅ 每月备份创建成功")
        print(f"   备份 ID: {metadata.backup_id}")
        print(f"   类型：{metadata.backup_type.value}")
        return True
    else:
        print("❌ 每月备份创建失败")
        return False


def test_verify_backup(manager: BackupManager) -> bool:
    """测试验证备份"""
    print("\n" + "="*60)
    print("测试 5: 验证备份完整性")
    print("="*60)
    
    # 获取最新的备份
    backups = manager.list_backups(limit=1)
    if not backups:
        print("❌ 没有备份可验证")
        return False
    
    backup_id = backups[0]["backup_id"]
    success = manager.restore_backup(backup_id, verify_only=True)
    
    if success:
        print(f"✅ 备份验证通过：{backup_id}")
        return True
    else:
        print(f"❌ 备份验证失败：{backup_id}")
        return False


def test_restore_backup(manager: BackupManager) -> bool:
    """测试恢复备份"""
    print("\n" + "="*60)
    print("测试 6: 恢复备份")
    print("="*60)
    
    # 获取最新的备份
    backups = manager.list_backups(limit=1)
    if not backups:
        print("❌ 没有备份可恢复")
        return False
    
    backup_id = backups[0]["backup_id"]
    target_dir = manager.backup_root / "restore" / f"test_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    success = manager.restore_backup(backup_id, target_dir=target_dir)
    
    if success:
        print(f"✅ 备份恢复成功")
        print(f"   目标目录：{target_dir}")
        
        # 验证恢复的文件
        if target_dir.exists():
            file_count = sum(1 for f in target_dir.rglob("*") if f.is_file())
            print(f"   恢复文件数：{file_count}")
        
        return True
    else:
        print(f"❌ 备份恢复失败")
        return False


def test_list_backups(manager: BackupManager) -> bool:
    """测试列出备份"""
    print("\n" + "="*60)
    print("测试 7: 列出备份")
    print("="*60)
    
    backups = manager.list_backups(limit=10)
    
    if backups:
        print(f"找到 {len(backups)} 个备份:")
        print(f"{'ID':<30} {'类型':<10} {'时间':<20} {'大小':<10} {'状态':<10}")
        print("-" * 90)
        for backup in backups:
            print(f"{backup['backup_id']:<30} "
                  f"{backup['backup_type']:<10} "
                  f"{backup['timestamp'][:19]:<20} "
                  f"{backup['size_mb']:.1f}MB{'':<5} "
                  f"{backup['status']:<10}")
        return True
    else:
        print("❌ 没有备份")
        return False


def test_backup_stats(manager: BackupManager) -> bool:
    """测试备份统计"""
    print("\n" + "="*60)
    print("测试 8: 备份统计")
    print("="*60)
    
    stats = manager.get_backup_stats()
    
    print(f"总备份数：{stats['total_backups']}")
    print(f"成功：{stats['successful_backups']}")
    print(f"失败：{stats['failed_backups']}")
    print(f"总大小：{stats['total_size_gb']:.2f} GB")
    print(f"每日备份：{stats['daily_count']}")
    print(f"每周备份：{stats['weekly_count']}")
    print(f"每月备份：{stats['monthly_count']}")
    print(f"增量备份：{stats['incremental_count']}")
    print(f"最后备份：{stats['last_backup']}")
    
    return True


def test_cleanup_old_backups(manager: BackupManager) -> bool:
    """测试清理过期备份"""
    print("\n" + "="*60)
    print("测试 9: 清理过期备份 (Dry Run)")
    print("="*60)
    
    stats = manager.cleanup_old_backups(dry_run=True)
    
    print(f"总备份数：{stats['total_backups']}")
    print(f"过期备份：{stats['expired_backups']}")
    print(f"将删除：{stats['deleted_backups']}")
    print(f"将释放：{stats['freed_space_bytes'] / 1024 / 1024:.2f} MB")
    
    return True


def test_schedule_backup(manager: BackupManager) -> bool:
    """测试定时备份调度"""
    print("\n" + "="*60)
    print("测试 10: 定时备份调度")
    print("="*60)
    
    now = datetime.now()
    print(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"小时：{now.hour}, 日期：{now.day}, 星期：{now.weekday()}")
    
    # 注意：这个测试只在 20:00 左右才会实际执行备份
    result = manager.schedule_backup()
    
    if result:
        print(f"✅ 定时备份执行：{result.backup_id}")
        return True
    else:
        print("ℹ️  无需执行备份 (不在备份时间窗口或今天已备份)")
        return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("备份管理器测试套件")
    print("="*60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建备份管理器
    manager = BackupManager()
    
    results = []
    
    # 运行测试
    tests = [
        ("创建每日备份", lambda: test_create_daily_backup(manager)),
        ("创建增量备份", lambda: test_create_incremental_backup(manager)),
        ("创建每周备份", lambda: test_create_weekly_backup(manager)),
        ("创建每月备份", lambda: test_create_monthly_backup(manager)),
        ("验证备份", lambda: test_verify_backup(manager)),
        ("恢复备份", lambda: test_restore_backup(manager)),
        ("列出备份", lambda: test_list_backups(manager)),
        ("备份统计", lambda: test_backup_stats(manager)),
        ("清理过期备份", lambda: test_cleanup_old_backups(manager)),
        ("定时备份调度", lambda: test_schedule_backup(manager)),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试异常 [{test_name}]: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print("\n" + "-"*60)
    print(f"总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
