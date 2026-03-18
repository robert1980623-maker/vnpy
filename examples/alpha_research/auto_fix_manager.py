#!/usr/bin/env python3
"""
自动修复管理器

功能:
- 自动修复数据问题
- 支持多种问题类型
- 自动选择修复策略
- 修复失败后人工介入
- 记录修复历史
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 导入重试工具
from retry_utils import retry_with_backoff

# 导入通知工具
from notification_utils import notify_task_start, notify_task_complete, notify_task_error

# 日志配置
logger = logging.getLogger(__name__)


class ProblemType(Enum):
    """问题类型"""
    DOWNLOAD_FAILED = "download_failed"
    DATA_STALE = "data_stale"
    DATA_CORRUPTED = "data_corrupted"
    FILE_MISSING = "file_missing"


class FixStrategy(Enum):
    """修复策略"""
    RETRY = "retry"
    REDOWNLOAD = "redownload"
    UPDATE = "update"
    MANUAL = "manual"


@dataclass
class FixRecord:
    """修复记录"""
    timestamp: str
    problem_type: str
    stock_list: List[str]
    strategy: str
    status: str
    attempts: int = 0
    error: Optional[str] = None


class AutoFixManager:
    """自动修复管理器"""
    
    def __init__(self, data_dir: str = "./data/akshare/bars"):
        self.data_dir = Path(data_dir)
        self.fix_history: List[FixRecord] = []
        self.stats = {
            'total_fixes': 0,
            'successful_fixes': 0,
            'failed_fixes': 0,
            'manual_interventions': 0
        }
    
    def fix_problem(self, problem_type: ProblemType, stock_list: List[str], 
                    context: Optional[Dict] = None) -> bool:
        """
        修复数据问题
        
        Args:
            problem_type: 问题类型
            stock_list: 受影响的股票列表
            context: 上下文信息
            
        Returns:
            bool: 是否修复成功
        """
        logger.info(f"开始修复问题：{problem_type.value}, 股票数：{len(stock_list)}")
        
        # 发送开始通知
        notify_task_start("自动修复", {
            "问题类型": problem_type.value,
            "股票数量": str(len(stock_list))
        })
        
        # 选择修复策略
        strategy = self._select_strategy(problem_type)
        
        # 执行修复
        success = False
        attempts = 0
        
        try:
            if strategy == FixStrategy.RETRY:
                success = self._fix_by_retry(stock_list, context)
                attempts = 3
            elif strategy == FixStrategy.REDOWNLOAD:
                success = self._fix_by_redownload(stock_list)
                attempts = 2
            elif strategy == FixStrategy.UPDATE:
                success = self._fix_by_update(stock_list)
                attempts = 1
            elif strategy == FixStrategy.MANUAL:
                success = False
                attempts = 0
            
            # 记录修复历史
            record = FixRecord(
                timestamp=datetime.now().isoformat(),
                problem_type=problem_type.value,
                stock_list=stock_list,
                strategy=strategy.value,
                status='success' if success else 'failed',
                attempts=attempts
            )
            self.fix_history.append(record)
            
            # 更新统计
            self.stats['total_fixes'] += 1
            if success:
                self.stats['successful_fixes'] += 1
            else:
                self.stats['failed_fixes'] += 1
                if strategy == FixStrategy.MANUAL:
                    self.stats['manual_interventions'] += 1
            
            # 发送完成通知
            if success:
                notify_task_complete("自动修复", {
                    "问题类型": problem_type.value,
                    "修复策略": strategy.value,
                    "尝试次数": str(attempts)
                })
            else:
                notify_task_error("自动修复", f"修复失败，需要人工介入", {
                    "问题类型": problem_type.value,
                    "股票列表": ", ".join(stock_list[:5])
                })
            
            return success
            
        except Exception as e:
            logger.error(f"修复过程异常：{e}")
            notify_task_error("自动修复", str(e))
            return False
    
    def _select_strategy(self, problem_type: ProblemType) -> FixStrategy:
        """选择修复策略"""
        strategy_map = {
            ProblemType.DOWNLOAD_FAILED: FixStrategy.RETRY,
            ProblemType.DATA_STALE: FixStrategy.UPDATE,
            ProblemType.DATA_CORRUPTED: FixStrategy.REDOWNLOAD,
            ProblemType.FILE_MISSING: FixStrategy.REDOWNLOAD,
        }
        return strategy_map.get(problem_type, FixStrategy.MANUAL)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _fix_by_retry(self, stock_list: List[str], context: Optional[Dict] = None) -> bool:
        """通过重试修复"""
        logger.info(f"重试下载 {len(stock_list)} 只股票")
        # 调用下载逻辑
        from batch_download_enhanced import download_single_stock
        for stock in stock_list:
            download_single_stock(stock)
        return True
    
    def _fix_by_redownload(self, stock_list: List[str]) -> bool:
        """重新下载修复"""
        logger.info(f"重新下载 {len(stock_list)} 只股票")
        # 删除损坏数据
        for stock in stock_list:
            file_path = self.data_dir / f"{stock}.csv"
            if file_path.exists():
                file_path.unlink()
        
        # 重新下载
        from batch_download_enhanced import download_single_stock
        for stock in stock_list:
            download_single_stock(stock)
        
        return True
    
    def _fix_by_update(self, stock_list: List[str]) -> bool:
        """更新数据修复"""
        logger.info(f"更新 {len(stock_list)} 只股票数据")
        # 调用更新逻辑
        from stale_data_updater import update_stale_stocks
        result = update_stale_stocks(stock_list)
        return result.get('success', False)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_fixes'] / self.stats['total_fixes'] * 100
                if self.stats['total_fixes'] > 0 else 0
            )
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取修复历史"""
        return [asdict(r) for r in self.fix_history[-limit:]]
    
    def save_history(self, file_path: str = "reports/auto_fix_history.json"):
        """保存修复历史"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': self.get_stats(),
                'history': [asdict(r) for r in self.fix_history]
            }, f, indent=2, ensure_ascii=False)


# 便捷函数

def auto_fix_stale_data(stock_list: List[str]) -> bool:
    """自动修复陈旧数据"""
    manager = AutoFixManager()
    return manager.fix_problem(ProblemType.DATA_STALE, stock_list)


def auto_fix_download_failed(stock_list: List[str]) -> bool:
    """自动修复下载失败"""
    manager = AutoFixManager()
    return manager.fix_problem(ProblemType.DOWNLOAD_FAILED, stock_list)


def auto_fix_corrupted_data(stock_list: List[str]) -> bool:
    """自动修复损坏数据"""
    manager = AutoFixManager()
    return manager.fix_problem(ProblemType.DATA_CORRUPTED, stock_list)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("  自动修复管理器测试")
    print("=" * 60)
    
    manager = AutoFixManager()
    
    # 测试统计
    print("\n初始统计:")
    print(json.dumps(manager.get_stats(), indent=2, ensure_ascii=False))
    
    print("\n✅ 自动修复管理器已就绪")
