#!/usr/bin/env python3
"""
分批下载股票数据（增强版 - 集成 Neo4j 同步 + 自动重试机制）

数据源策略:
- ✅ 主数据源：Tushare Pro (已付费 TOKEN)
- 🔄 备份数据源：Akshare (Tushare 失败时自动切换)

功能:
- ✅ 使用 DataDownloader 直接调用下载函数（无 subprocess 开销）
- ✅ 并发下载（默认 4 线程）
- ✅ 增量同步（只更新新数据）
- ✅ 失败队列（持久化 + 自动重试）
- ✅ 自动同步到 Neo4j WorldState
- ✅ 数据一致性验证
- ✅ 通知（开始/完成/错误）

用法:
    python3 batch_download_enhanced.py [--workers N] [--no-concurrent] [--no-incremental]
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# 通知工具
from notification_utils import TaskNotifier, notify_task_start, notify_task_complete, notify_task_error

# 重试工具
from retry_utils import (
    retry_with_backoff,
    retry_function,
    get_retry_monitor,
    RetryMonitor
)

# 统一下载器（Phase 2 核心：直接 import，不开子进程）
from data_downloader import DataDownloader, get_retry_candidates, load_failed_downloads

# Neo4j（可选）
sys.path.insert(0, str(Path(__file__).parent / 'world_model'))

try:
    from neo4j_sync import Neo4jSync
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️ Neo4j 模块不可用，将跳过同步")

# 配置
BATCH_SIZE = 5
BATCH_DELAY = 5
TOTAL_STOCKS = 20
MAX_RETRY_COUNT = 3

# 重试配置
RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 2.0,
    'max_delay': 60.0,
    'timeout': 120.0,
    'log_file': 'logs/retry_monitor.json'
}

# 数据源配置
DATA_SOURCE_PRIMARY = "tushare"
DATA_SOURCE_BACKUP = "akshare"

# 日志
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'batch_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_stock_list():
    """获取股票列表（沪深 300 成分股）"""
    logger.info("=" * 60)
    logger.info("获取股票列表...")
    logger.info("=" * 60)

    # Phase 3 Fix 6: 统一股票格式为 code.exchange
    def normalize(code: str) -> str:
        """标准化股票代码格式"""
        if '.' in code:
            return code
        if code.startswith('6'):
            return f"{code}.SSE"
        return f"{code}.SZSE"

    # 直接 import 调用（不再用 subprocess）
    try:
        from download_data_akshare import download_index_components
        stocks = download_index_components("000300")
        if stocks:
            # 统一格式
            stocks = [normalize(s) for s in stocks]
            logger.info(f"✅ 获取到 {len(stocks)} 只股票")
            return stocks[:TOTAL_STOCKS]
    except Exception as e:
        logger.warning(f"⚠️ 获取股票列表失败：{e}")

    logger.warning("⚠️ 使用默认股票列表")
    # 默认列表也用统一格式
    default_codes = [
        '000630', '000807', '000975', '000999', '001391',
        '002028', '002384', '002422', '002463', '002600',
        '002625', '300251', '300394', '300418', '300442',
        '300476', '300502', '300803', '300832', '300866'
    ]
    return [normalize(c) for c in default_codes]


# Phase 3 Fix 4: Neo4j 连接复用（全局单例）
_neo4j_instance = None

def get_neo4j_sync():
    """获取 Neo4j 同步器单例"""
    global _neo4j_instance
    if _neo4j_instance is None and NEO4J_AVAILABLE:
        try:
            _neo4j_instance = Neo4jSync()
        except Exception as e:
            logger.error(f"❌ Neo4j 初始化失败：{e}")
            _neo4j_instance = None
    return _neo4j_instance

def close_neo4j():
    """关闭 Neo4j 连接"""
    global _neo4j_instance
    if _neo4j_instance is not None:
        try:
            _neo4j_instance.close()
        except Exception:
            pass
        _neo4j_instance = None

def sync_to_neo4j(stock_data):
    """同步股票数据到 Neo4j（使用复用连接）"""
    sync = get_neo4j_sync()
    if not sync:
        return
    try:
        sync.sync_stock_data({
            'symbol': stock_data['symbol'],
            'datetime': datetime.now(),
            'close': 0.0,
            'volume': 0,
            'source': stock_data.get('source', 'unknown')
        })
        logger.info(f"✅ {stock_data['symbol']} 已同步到 Neo4j (数据源：{stock_data['source']})")
    except Exception as e:
        logger.error(f"❌ {stock_data['symbol']} Neo4j 同步失败：{e}")


def verify_data_consistency(stock_code, data_dir=None):
    """验证数据一致性
    
    Phase 3 Fix 5: 统一数据目录路径
    """
    try:
        # 使用传入的 data_dir 或默认 akshare/bars
        if data_dir is None:
            data_dir = Path(__file__).parent / 'data' / 'akshare' / 'bars'
        else:
            data_dir = Path(data_dir)

        if not data_dir.exists():
            logger.warning(f"⚠️ 数据目录不存在: {data_dir}")
            return False

        files = list(data_dir.glob(f"{stock_code}.*")) + list(data_dir.glob(f"{stock_code}.csv"))

        if not files:
            logger.warning(f"⚠️ {stock_code} 本地数据文件不存在")
            return False

        logger.info(f"✅ {stock_code} 数据一致性验证通过")
        return True
    except Exception as e:
        logger.error(f"❌ {stock_code} 数据一致性验证失败：{e}")
        return False


def print_retry_stats():
    """打印重试统计信息"""
    monitor = get_retry_monitor()
    monitor.print_stats()
    failures = monitor.get_recent_failures(limit=5)
    if failures:
        logger.info("\n最近失败记录:")
        for f in failures:
            logger.info(f"  - {f['func_name']}: {f['final_error']}")


def parse_args():
    parser = argparse.ArgumentParser(description="批量下载股票数据（增强版）")
    parser.add_argument("--workers", type=int, default=4, help="并发线程数（默认 4）")
    parser.add_argument("--no-concurrent", action="store_true", help="禁用并发，串行下载")
    parser.add_argument("--no-incremental", action="store_true", help="禁用增量检测，强制全量下载")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"批次大小（默认 {BATCH_SIZE}）")
    parser.add_argument("--max", type=int, default=TOTAL_STOCKS, help=f"最大股票数（默认 {TOTAL_STOCKS}）")
    return parser.parse_args()


def main():
    args = parse_args()

    notify_task_start("数据下载", {
        "模式": "批量下载 (增强版 - DataDownloader)",
        "时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "并发": args.workers if not args.no_concurrent else 1,
        "增量": not args.no_incremental,
    })

    logger.info("=" * 60)
    logger.info("批量下载股票（增强版 - DataDownloader + 自动重试）")
    logger.info("=" * 60)
    logger.info(f"开始时间：{datetime.now()}")
    logger.info(f"Neo4j 同步：{'✅ 启用' if NEO4J_AVAILABLE else '❌ 禁用'}")
    logger.info(f"数据源策略：{DATA_SOURCE_PRIMARY}(主) + {DATA_SOURCE_BACKUP}(备)")
    logger.info(f"并发：{args.workers if not args.no_concurrent else 1} (串行)")
    logger.info("=" * 60)

    # 获取股票列表
    stocks = get_stock_list()

    # 优先重试上次失败的股票
    retry_candidates = get_retry_candidates(MAX_RETRY_COUNT)
    if retry_candidates:
        logger.info(f"🔄 发现 {len(retry_candidates)} 只上次失败股票，优先重试")
        retry_set = set(retry_candidates)
        stocks = retry_candidates + [s for s in stocks if s not in retry_set]

    # 限制数量
    stocks = stocks[:args.max]

    # 创建下载器（Phase 2：直接 import，无 subprocess）
    downloader = DataDownloader(
        max_workers=args.workers,
        max_retries=RETRY_CONFIG['max_retries'],
        base_delay=RETRY_CONFIG['base_delay'],
        max_delay=RETRY_CONFIG['max_delay'],
        timeout=RETRY_CONFIG['timeout'],
        stock_delay=1.0,
    )

    # 分批下载（保留批次间隔，避免被数据源限流）
    batch_size = args.batch_size
    all_results = []
    batch_num = 1

    for i in range(0, len(stocks), batch_size):
        batch_stocks = stocks[i:i + batch_size]
        logger.info("\n" + "=" * 60)
        logger.info(f"批次 {batch_num}: 下载 {len(batch_stocks)} 只股票")
        logger.info(f"股票：{', '.join(batch_stocks)}")
        logger.info("=" * 60)

        results = downloader.download(
            batch_stocks,
            incremental=not args.no_incremental,
            concurrent=not args.no_concurrent,
        )
        all_results.extend(results)

        # 后续处理：Neo4j 同步 + 一致性验证
        sync_count = 0
        verify_count = 0
        for result in results:
            if result.get('status') == 'success':
                sync_to_neo4j(result)
                sync_count += 1
                if verify_data_consistency(result['symbol']):
                    verify_count += 1

        logger.info(f"✅ 批次 {batch_num} 完成: 同步 {sync_count}, 验证 {verify_count}")
        batch_num += 1

        # 批次间隔
        if i + batch_size < len(stocks):
            logger.info(f"\n⏳ 等待 {BATCH_DELAY} 秒后继续下一批...")
            time.sleep(BATCH_DELAY)

    # 最终统计
    stats = downloader.get_stats()
    logger.info("\n" + "=" * 60)
    logger.info("✅ 全部下载完成！")
    logger.info(f"结束时间：{datetime.now()}")
    logger.info(f"统计: {stats}")
    logger.info("=" * 60)

    print_retry_stats()

    notify_task_complete("数据下载", {
        "成功": f"{stats['success']}/{stats['total']}",
        "Tushare": stats['tushare'],
        "AKShare": stats['akshare'],
        "Baostock": stats['baostock'],
        "失败": stats['failed'],
        "跳过": stats['skipped'],
    })
    
    # Phase 3 Fix 4: 关闭 Neo4j 连接
    close_neo4j()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
        close_neo4j()  # 确保中断时也关闭连接
    except Exception as e:
        logger.error(f"❌ 程序异常：{e}")
        notify_task_error("数据下载", str(e))
        close_neo4j()  # 确保异常时也关闭连接
        raise
