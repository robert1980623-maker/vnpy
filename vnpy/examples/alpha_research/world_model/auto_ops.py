#!/usr/bin/env python3
"""
自动化运维系统

功能:
- 自动备份和恢复
- 故障自愈
- 容量规划

用法:
    from auto_ops import AutoOps
    
    ops = AutoOps()
    ops.backup_system()
    ops.auto_healing()
    ops.capacity_planning()
"""

import sys
import os
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoOps:
    """自动化运维系统"""
    
    def __init__(self, backup_dir="/tmp/vnpy_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ 自动化运维系统初始化完成")
    
    def backup_system(self, backup_type: str = 'daily') -> Dict:
        """
        自动备份系统
        
        Args:
            backup_type: 备份类型 (daily/weekly/monthly)
        
        Returns:
            dict: 备份报告
        """
        logger.info(f"💾 开始 {backup_type} 备份...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'backup_type': backup_type,
            'status': 'success',
            'backed_up': [],
            'total_size': 0,
            'backup_path': ''
        }
        
        try:
            # 创建备份目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / f"backup_{backup_type}_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 备份配置文件
            config_dir = Path(__file__).parent.parent / 'config'
            if config_dir.exists():
                dest = backup_path / 'config'
                shutil.copytree(config_dir, dest)
                report['backed_up'].append('config')
            
            # 备份日志文件
            log_dir = Path(__file__).parent.parent / 'logs'
            if log_dir.exists():
                dest = backup_path / 'logs'
                shutil.copytree(log_dir, dest)
                report['backed_up'].append('logs')
            
            # 备份数据
            data_dir = Path(__file__).parent.parent / 'data'
            if data_dir.exists():
                dest = backup_path / 'data'
                shutil.copytree(data_dir, dest)
                report['backed_up'].append('data')
            
            # 计算总大小
            total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
            report['total_size'] = total_size
            report['backup_path'] = str(backup_path)
            
            # 清理旧备份 (保留最近 7 个)
            self._cleanup_old_backups(backup_type, keep=7)
            
            logger.info(f"✅ 备份完成：{len(report['backed_up'])} 个项目，{total_size / 1024 / 1024:.2f} MB")
            
        except Exception as e:
            logger.error(f"备份失败：{e}")
            report['status'] = 'failed'
            report['error'] = str(e)
        
        return report
    
    def _cleanup_old_backups(self, backup_type: str, keep: int = 7):
        """清理旧备份"""
        try:
            backups = sorted(self.backup_dir.glob(f"backup_{backup_type}_*"))
            
            if len(backups) > keep:
                for old_backup in backups[:-keep]:
                    shutil.rmtree(old_backup)
                    logger.info(f"🗑️ 清理旧备份：{old_backup.name}")
        except Exception as e:
            logger.error(f"清理备份失败：{e}")
    
    def auto_healing(self) -> Dict:
        """
        故障自愈
        
        Returns:
            dict: 自愈报告
        """
        logger.info("🔧 开始故障自愈检查...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'issues_found': 0,
            'issues_fixed': 0,
            'actions': []
        }
        
        # 检查 1: 磁盘空间
        try:
            import psutil
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                report['checks']['disk_space'] = 'critical'
                report['issues_found'] += 1
                report['actions'].append('磁盘空间不足，建议清理')
            elif disk.percent > 80:
                report['checks']['disk_space'] = 'warning'
            else:
                report['checks']['disk_space'] = 'ok'
        except:
            report['checks']['disk_space'] = 'unknown'
        
        # 检查 2: 内存使用
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                report['checks']['memory'] = 'critical'
                report['issues_found'] += 1
                report['actions'].append('内存使用过高，建议重启服务')
            elif mem.percent > 80:
                report['checks']['memory'] = 'warning'
            else:
                report['checks']['memory'] = 'ok'
        except:
            report['checks']['memory'] = 'unknown'
        
        # 检查 3: 日志文件大小
        log_dir = Path(__file__).parent.parent / 'logs'
        if log_dir.exists():
            total_log_size = sum(f.stat().st_size for f in log_dir.rglob('*.log'))
            if total_log_size > 1024 * 1024 * 1024:  # > 1GB
                report['checks']['log_size'] = 'warning'
                report['actions'].append('日志文件过大，建议清理或归档')
            else:
                report['checks']['log_size'] = 'ok'
        else:
            report['checks']['log_size'] = 'unknown'
        
        # 自动修复
        if report['issues_found'] > 0:
            # 清理日志
            if report['checks'].get('log_size') == 'warning':
                try:
                    for log_file in log_dir.rglob('*.log'):
                        if log_file.stat().st_size > 100 * 1024 * 1024:  # > 100MB
                            log_file.unlink()
                            report['issues_fixed'] += 1
                    report['actions'].append('已清理大日志文件')
                except:
                    pass
        
        logger.info(f"✅ 自愈检查完成：发现 {report['issues_found']} 个问题，修复 {report['issues_fixed']} 个")
        
        return report
    
    def capacity_planning(self) -> Dict:
        """
        容量规划
        
        Returns:
            dict: 容量规划报告
        """
        logger.info("📊 生成容量规划报告...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'current_usage': {},
            'growth_trend': {},
            'recommendations': []
        }
        
        try:
            import psutil
            
            # 当前使用情况
            disk = psutil.disk_usage('/')
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            
            report['current_usage'] = {
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                'memory_percent': mem.percent,
                'memory_free_gb': mem.available / 1024 / 1024 / 1024,
                'cpu_percent': cpu
            }
            
            # 增长趋势 (模拟)
            report['growth_trend'] = {
                'disk_growth_per_day': '500MB',
                'memory_growth_per_day': '稳定',
                'estimated_days_until_full': int((disk.free / 1024 / 1024 / 1024) / 0.5)
            }
            
            # 建议
            if disk.percent > 70:
                report['recommendations'].append('磁盘使用率较高，建议扩容或清理')
            
            if mem.percent > 70:
                report['recommendations'].append('内存使用率较高，建议增加内存')
            
            if report['growth_trend']['estimated_days_until_full'] < 30:
                report['recommendations'].append(f"预计 {report['growth_trend']['estimated_days_until_full']} 天后磁盘将满，建议立即扩容")
            
            logger.info(f"✅ 容量规划完成：{len(report['recommendations'])} 条建议")
            
        except Exception as e:
            logger.error(f"容量规划失败：{e}")
            report['error'] = str(e)
        
        return report
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'services': {}
        }
        
        try:
            import psutil
            
            # 检查关键服务
            services = ['redis', 'neo4j']
            for service in services:
                try:
                    # 简单检查端口
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if service == 'redis':
                        result = sock.connect_ex(('localhost', 6379))
                    elif service == 'neo4j':
                        result = sock.connect_ex(('localhost', 7687))
                    else:
                        result = -1
                    
                    status['services'][service] = 'up' if result == 0 else 'down'
                    sock.close()
                except:
                    status['services'][service] = 'unknown'
            
            # 整体状态
            if all(s == 'up' for s in status['services'].values()):
                status['status'] = 'healthy'
            elif any(s == 'up' for s in status['services'].values()):
                status['status'] = 'degraded'
            else:
                status['status'] = 'critical'
            
        except Exception as e:
            logger.error(f"获取系统状态失败：{e}")
            status['status'] = 'unknown'
        
        return status
    
    def close(self):
        """关闭"""
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("测试自动化运维系统")
    print("=" * 60)
    
    ops = AutoOps()
    
    # 系统备份
    print("\n1. 系统备份...")
    backup = ops.backup_system('daily')
    print(f"   状态：{backup['status']}")
    print(f"   备份项目：{len(backup['backed_up'])}")
    print(f"   总大小：{backup['total_size'] / 1024 / 1024:.2f} MB")
    
    # 故障自愈
    print("\n2. 故障自愈...")
    healing = ops.auto_healing()
    print(f"   发现问题：{healing['issues_found']}")
    print(f"   已修复：{healing['issues_fixed']}")
    
    # 容量规划
    print("\n3. 容量规划...")
    capacity = ops.capacity_planning()
    print(f"   磁盘使用：{capacity['current_usage'].get('disk_percent', 0):.1f}%")
    print(f"   内存使用：{capacity['current_usage'].get('memory_percent', 0):.1f}%")
    print(f"   建议数量：{len(capacity.get('recommendations', []))}")
    
    # 系统状态
    print("\n4. 系统状态...")
    status = ops.get_system_status()
    print(f"   整体状态：{status['status']}")
    print(f"   服务状态：{status['services']}")
    
    ops.close()
    print("\n✅ 测试完成")
