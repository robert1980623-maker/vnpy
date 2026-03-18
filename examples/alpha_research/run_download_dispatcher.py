#!/usr/bin/env python3
"""
数据下载派遣任务

使用 SQLite 任务派遣系统管理并发下载任务
- 自动从持仓和股票池获取下载列表
- 并发下载（可配置 Worker 数量）
- 持久化下载状态
- 支持断点续跑

用法:
    python3 run_download_dispatcher.py [--full] [--holdings] [--workers 4]
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import logging

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlite_task_dispatcher import TaskDispatcher, Task, TaskStatus
from batch_download_enhanced import download_single_stock

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('DownloadDispatcher')


class DownloadTaskDispatcher:
    """数据下载派遣器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / 'data' / 'stock_data'
        self.db_path = str(self.project_root / 'download_tasks.db')
        
        self.dispatcher = TaskDispatcher(
            db_path=self.db_path,
            max_workers=max_workers,
            task_handler=self._download_handler
        )
        
        logger.info(f"下载派遣器初始化完成 (workers={max_workers})")
    
    def _download_handler(self, task: Task) -> Dict:
        """下载任务处理器"""
        symbol = task.payload['symbol']
        days = task.payload.get('days', 30)
        force = task.payload.get('force', False)
        
        logger.info(f"下载数据：{symbol} (最近{days}天)")
        
        try:
            # 调用现有下载逻辑
            result = download_single_stock(
                symbol=symbol,
                days=days,
                force=force
            )
            
            return {
                'symbol': symbol,
                'status': 'success',
                'rows': result.get('rows', 0),
                'start_date': result.get('start_date'),
                'end_date': result.get('end_date')
            }
            
        except Exception as e:
            logger.error(f"下载失败：{symbol} - {e}")
            raise
    
    def get_download_list(self, mode: str = 'holdings') -> List[str]:
        """获取需要下载的股票列表"""
        
        if mode == 'full':
            # 全量下载 - 从沪深 300 获取
            return self._get_hs300_stocks()
        
        elif mode == 'holdings':
            # 持仓股票
            return self._get_holdings_stocks()
        
        elif mode == 'stale':
            # 陈旧数据
            return self._get_stale_data_stocks()
        
        else:
            logger.warning(f"未知模式：{mode}, 使用 holdings")
            return self._get_holdings_stocks()
    
    def _get_hs300_stocks(self) -> List[str]:
        """获取沪深 300 成分股"""
        try:
            from vnpy.alpha.dataset.pool import IndexStockPool
            pool = IndexStockPool('000300.SH')
            stocks = pool.get_stocks()
            logger.info(f"沪深 300 成分股：{len(stocks)} 只")
            return stocks
        except Exception as e:
            logger.error(f"获取沪深 300 失败：{e}")
            return []
    
    def _get_holdings_stocks(self) -> List[str]:
        """获取持仓股票"""
        account_file = self.project_root / 'accounts' / 'virtual_2026_account.json'
        
        if not account_file.exists():
            logger.warning(f"账户文件不存在：{account_file}")
            return []
        
        with open(account_file, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        holdings = account.get('holdings', {})
        stocks = list(holdings.keys())
        
        logger.info(f"持仓股票：{len(stocks)} 只 - {stocks[:5]}...")
        return stocks
    
    def _get_stale_data_stocks(self, threshold_days: int = 2) -> List[str]:
        """获取数据陈旧的股票"""
        stale_stocks = []
        cutoff = datetime.now() - timedelta(days=threshold_days)
        
        if not self.data_dir.exists():
            return []
        
        for file in self.data_dir.glob('*.csv'):
            symbol = file.stem
            
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff:
                stale_stocks.append(symbol)
        
        logger.info(f"陈旧数据股票：{len(stale_stocks)} 只")
        return stale_stocks
    
    def run(self, mode: str = 'holdings', days: int = 30, 
            force: bool = False, timeout: int = 600) -> Dict:
        """运行下载任务"""
        
        logger.info("="*70)
        logger.info(f"开始数据下载派遣任务")
        logger.info(f"模式：{mode}, 天数：{days}, 强制：{force}")
        logger.info("="*70)
        
        # 获取下载列表
        symbols = self.get_download_list(mode)
        
        if not symbols:
            logger.warning("没有需要下载的股票")
            return {'status': 'no_symbols', 'downloaded': 0}
        
        # 启动派遣器
        self.dispatcher.start()
        
        # 创建并提交任务
        tasks = []
        timestamp = int(time.time())
        
        for i, symbol in enumerate(symbols):
            task = Task(
                task_id=f"dl_{symbol}_{timestamp}",
                task_type='download',
                payload={
                    'symbol': symbol,
                    'days': days,
                    'force': force
                },
                priority=self._calculate_priority(symbol, i)
            )
            tasks.append(task)
        
        self.dispatcher.submit_batch(tasks)
        logger.info(f"已提交 {len(tasks)} 个下载任务")
        
        # 等待完成
        logger.info(f"等待下载完成 (超时：{timeout}s)...")
        success = self.dispatcher.wait_completion(timeout=timeout)
        
        if not success:
            logger.warning("下载超时")
        
        # 获取结果统计
        status = self.dispatcher.get_status()
        
        # 停止派遣器
        self.dispatcher.stop()
        
        # 生成报告
        report = {
            'status': 'completed' if success else 'timeout',
            'mode': mode,
            'total_symbols': len(symbols),
            'downloaded': status['max_workers'] * 100 - status['pending_tasks'],  # 估算
            'pending': status['pending_tasks'],
            'duration': timeout if not success else 'unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("="*70)
        logger.info(f"下载完成")
        logger.info(f"总计：{len(symbols)}, 待处理：{report['pending']}")
        logger.info("="*70)
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _calculate_priority(self, symbol: str, index: int) -> int:
        """计算任务优先级"""
        # 持仓股票高优先级
        holdings = self._get_holdings_stocks()
        if symbol in holdings:
            return 10
        
        # 前 10 只高优先级
        if index < 10:
            return 5
        
        return 1
    
    def _save_report(self, report: Dict):
        """保存下载报告"""
        report_dir = self.project_root / 'reports' / 'download'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"download_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存：{report_file}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据下载派遣任务')
    parser.add_argument('--full', action='store_true', help='全量下载（沪深 300）')
    parser.add_argument('--holdings', action='store_true', help='下载持仓股票（默认）')
    parser.add_argument('--stale', action='store_true', help='下载陈旧数据')
    parser.add_argument('--days', type=int, default=30, help='下载天数')
    parser.add_argument('--force', action='store_true', help='强制重新下载')
    parser.add_argument('--workers', type=int, default=5, help='并发 Worker 数')
    parser.add_argument('--timeout', type=int, default=600, help='超时时间（秒）')
    
    args = parser.parse_args()
    
    # 确定模式
    if args.full:
        mode = 'full'
    elif args.stale:
        mode = 'stale'
    else:
        mode = 'holdings'
    
    # 运行
    dispatcher = DownloadTaskDispatcher(max_workers=args.workers)
    report = dispatcher.run(
        mode=mode,
        days=args.days,
        force=args.force,
        timeout=args.timeout
    )
    
    # 退出码
    sys.exit(0 if report['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
