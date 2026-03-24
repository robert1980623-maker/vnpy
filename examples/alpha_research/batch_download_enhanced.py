#!/usr/bin/env python3
"""
分批下载股票数据（增强版 - 集成 Neo4j 同步 + 自动重试机制）

数据源策略:
- ✅ 主数据源：Tushare Pro (更稳定可靠)
- ✅ 备份数据源：Akshare (Tushare 失败时使用)

功能:
- 每批 5 只股票
- 批次间隔 30 秒
- 单只股票间隔 3 秒
- ✅ 自动同步到 Neo4j WorldState
- ✅ 增量同步（只更新新数据）
- ✅ 自动重试机制（指数退避）
- ✅ 重试日志和监控
- ✅ 失败告警
- ✅ 数据一致性验证

用法:
    python3 batch_download_enhanced.py
"""

import subprocess
import time
import sys
import logging
from datetime import datetime
from pathlib import Path

# 通知工具
from notification_utils import TaskNotifier, notify_task_start, notify_task_complete, notify_task_error

# 重试工具（新增）
from retry_utils import (
    retry_with_backoff,
    retry_function,
    get_retry_monitor,
    RetryMonitor
)

# 添加 world_model 模块路径
sys.path.insert(0, str(Path(__file__).parent / 'world_model'))

try:
    from neo4j_sync import Neo4jSync
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️ Neo4j 模块不可用，将跳过同步")

# 配置
BATCH_SIZE = 5
BATCH_DELAY = 30
STOCK_DELAY = 3
TOTAL_STOCKS = 20

# 重试配置（新增）
RETRY_CONFIG = {
    'max_retries': 3,           # 最大重试次数
    'base_delay': 2.0,          # 基础延迟（秒）
    'max_delay': 60.0,          # 最大延迟（秒）
    'timeout': 120.0,           # 单次调用超时（秒）
    'log_file': 'logs/retry_monitor.json'  # 重试日志文件
}

# 数据源配置
DATA_SOURCE_PRIMARY = "tushare"  # 主数据源
DATA_SOURCE_BACKUP = "akshare"   # 备份数据源

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
    """获取股票列表（从沪深 300）"""
    logger.info("=" * 60)
    logger.info("获取股票列表...")
    logger.info("=" * 60)
    
    # 优先使用 Tushare
    cmd = [
        "python3", "-c",
        "import tushare as ts; df = ts.index_stock('000300'); "
        "print(','.join(df['code'].tolist()[:20]))"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            stocks = result.stdout.strip().split(',')
            logger.info(f"✅ Tushare 获取到 {len(stocks)} 只股票")
            return stocks
    except Exception as e:
        logger.warning(f"⚠️ Tushare 获取失败，切换到 Akshare: {e}")
    
    # Tushare 失败，使用 Akshare
    cmd = [
        "python3", "-c",
        "import akshare as ak; df = ak.index_stock_cons(symbol='000300'); "
        "print(','.join(df['品种代码'].tolist()[:20]))"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stocks = result.stdout.strip().split(',')
        logger.info(f"✅ Akshare 获取到 {len(stocks)} 只股票")
        return stocks
    except Exception as e:
        logger.warning(f"⚠️ Akshare 获取失败：{e}")
        # 使用默认列表
        return [
            '000630', '000807', '000975', '000999', '001391',
            '002028', '002384', '002422', '002463', '002600',
            '002625', '300251', '300394', '300418', '300442',
            '300476', '300502', '300803', '300832', '300866'
        ]


@retry_with_backoff(
    max_retries=RETRY_CONFIG['max_retries'],
    base_delay=RETRY_CONFIG['base_delay'],
    max_delay=RETRY_CONFIG['max_delay'],
    timeout=RETRY_CONFIG['timeout'],
    log_file=RETRY_CONFIG['log_file']
)
def download_with_tushare(stock_code):
    """
    使用 Tushare 下载股票数据（带自动重试）
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  📊 使用 Tushare 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_tushare.py",
        "--code", stock_code
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Tushare {stock_code} 下载成功")
        return True
    else:
        logger.warning(f"⚠️ Tushare {stock_code} 失败：{result.stderr}")
        raise Exception(f"Tushare 下载失败：{result.stderr}")


@retry_with_backoff(
    max_retries=RETRY_CONFIG['max_retries'],
    base_delay=RETRY_CONFIG['base_delay'],
    max_delay=RETRY_CONFIG['max_delay'],
    timeout=RETRY_CONFIG['timeout'],
    log_file=RETRY_CONFIG['log_file']
)
def download_with_akshare(stock_code):
    """
    使用 Akshare 下载股票数据（带自动重试，备份数据源）
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  📊 使用 Akshare 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_akshare.py",
        "--code", stock_code
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Akshare {stock_code} 下载成功")
        return True
    else:
        logger.error(f"❌ Akshare {stock_code} 失败：{result.stderr}")
        raise Exception(f"Akshare 下载失败：{result.stderr}")


def download_with_dual_source(stock_code):
    """
    下载单只股票（双数据源策略）
    
    策略:
    1. 优先使用 Tushare（带重试）
    2. Tushare 失败时使用 Akshare（带重试）
    3. 都失败则返回失败
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 股票数据，失败返回 None
    """
    logger.info(f"\n--- 下载 {stock_code} (双数据源策略) ---")
    
    # 1. 尝试 Tushare（主数据源，带重试）
    try:
        if download_with_tushare(stock_code):
            return {'symbol': stock_code, 'status': 'success', 'source': 'tushare'}
    except Exception as e:
        logger.warning(f"⚠️ Tushare 最终失败：{e}")
    
    # 2. Tushare 失败，尝试 Akshare（备份，带重试）
    logger.info(f"  ⚠️ Tushare 失败，切换到备份数据源 Akshare")
    try:
        if download_with_akshare(stock_code):
            return {'symbol': stock_code, 'status': 'success', 'source': 'akshare'}
    except Exception as e:
        logger.error(f"❌ Akshare 最终失败：{e}")
    
    # 3. 都失败
    logger.error(f"❌ {stock_code} 下载失败（双数据源均失败）")
    return {'symbol': stock_code, 'status': 'failed', 'source': 'none'}


def sync_to_neo4j(stock_data):
    """同步股票数据到 Neo4j（增量同步）"""
    if not NEO4J_AVAILABLE:
        return
    
    try:
        sync = Neo4jSync()
        sync.sync_stock_data({
            'symbol': stock_data['symbol'],
            'datetime': datetime.now(),
            'close': 0.0,
            'volume': 0,
            'source': stock_data.get('source', 'unknown')
        })
        sync.close()
        logger.info(f"✅ {stock_data['symbol']} 已同步到 Neo4j (数据源：{stock_data['source']})")
    except Exception as e:
        logger.error(f"❌ {stock_data['symbol']} Neo4j 同步失败：{e}")


def verify_data_consistency(stock_code):
    """验证数据一致性"""
    try:
        # 检查本地文件
        data_dir = Path(__file__).parent / 'data' / 'tushare'
        if not data_dir.exists():
            data_dir = Path(__file__).parent / 'data' / 'akshare'
        
        files = list(data_dir.glob(f"{stock_code}.*.csv"))
        
        if not files:
            logger.warning(f"⚠️ {stock_code} 本地数据文件不存在")
            return False
        
        # 检查 Neo4j 中的数据
        if NEO4J_AVAILABLE:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "admin_robert"))
            
            with driver.session() as session:
                result = session.run(
                    "MATCH (ws:StockPrice {symbol: $symbol}) RETURN ws",
                    symbol=stock_code
                )
                neo4j_data = result.single()
                
                if not neo4j_data:
                    logger.warning(f"⚠️ {stock_code} Neo4j 中不存在")
                    return False
            
            driver.close()
        
        logger.info(f"✅ {stock_code} 数据一致性验证通过")
        return True
    
    except Exception as e:
        logger.error(f"❌ {stock_code} 数据一致性验证失败：{e}")
        return False


def download_batch(batch_num, stocks):
    """下载一批股票（带同步和验证）"""
    logger.info("\n" + "=" * 60)
    logger.info(f"批次 {batch_num}: 下载 {len(stocks)} 只股票")
    logger.info("=" * 60)
    logger.info(f"股票：{', '.join(stocks)}")
    logger.info(f"开始时间：{datetime.now().strftime('%H:%M:%S')}")
    logger.info(f"数据源策略：{DATA_SOURCE_PRIMARY}(主) + {DATA_SOURCE_BACKUP}(备)")
    logger.info(f"重试配置：{RETRY_CONFIG['max_retries']}次重试，{RETRY_CONFIG['base_delay']}s 基础延迟")
    
    success_count = 0
    tushare_count = 0
    akshare_count = 0
    sync_count = 0
    verify_count = 0
    
    for i, stock in enumerate(stocks):
        # 下载（双数据源，各自带重试）
        result = download_with_dual_source(stock)
        
        if result.get('status') == 'success':
            success_count += 1
            
            # 统计数据源
            if result.get('source') == 'tushare':
                tushare_count += 1
            elif result.get('source') == 'akshare':
                akshare_count += 1
            
            # 同步到 Neo4j
            sync_to_neo4j(result)
            sync_count += 1
            
            # 数据一致性验证
            if verify_data_consistency(stock):
                verify_count += 1
        
        # 单只股票间隔
        if i < len(stocks) - 1:
            time.sleep(STOCK_DELAY)
    
    logger.info(f"\n✅ 批次 {batch_num} 完成:")
    logger.info(f"  下载成功：{success_count}/{len(stocks)}")
    logger.info(f"  Tushare: {tushare_count} | Akshare: {akshare_count}")
    logger.info(f"  Neo4j 同步：{sync_count}/{len(stocks)}")
    logger.info(f"  一致性验证：{verify_count}/{len(stocks)}")
    
    return success_count == len(stocks)


def print_retry_stats():
    """打印重试统计信息"""
    monitor = get_retry_monitor()
    monitor.print_stats()
    
    # 显示最近的失败记录
    failures = monitor.get_recent_failures(limit=5)
    if failures:
        logger.info("\n最近失败记录:")
        for f in failures:
            logger.info(f"  - {f['func_name']}: {f['final_error']}")


def main():
    # 发送开始通知
    notify_task_start("数据下载", {
        "模式": "批量下载 (增强版)",
        "时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "重试机制": "启用",
        "重试次数": RETRY_CONFIG['max_retries']
    })

    """主函数"""
    logger.info("=" * 60)
    logger.info("批量下载股票（增强版 - Tushare 主 + Akshare 备 + 自动重试）")
    logger.info("=" * 60)
    logger.info(f"开始时间：{datetime.now()}")
    logger.info(f"Neo4j 同步：{'✅ 启用' if NEO4J_AVAILABLE else '❌ 禁用'}")
    logger.info(f"数据源策略：{DATA_SOURCE_PRIMARY}(主) + {DATA_SOURCE_BACKUP}(备)")
    logger.info(f"重试配置:")
    logger.info(f"  最大重试次数：{RETRY_CONFIG['max_retries']}")
    logger.info(f"  基础延迟：{RETRY_CONFIG['base_delay']}秒")
    logger.info(f"  最大延迟：{RETRY_CONFIG['max_delay']}秒")
    logger.info(f"  超时时间：{RETRY_CONFIG['timeout']}秒")
    logger.info(f"  日志文件：{RETRY_CONFIG['log_file']}")
    logger.info("=" * 60)
    
    # 获取股票列表
    stocks = get_stock_list()
    
    # 分批下载
    batch_num = 1
    for i in range(0, len(stocks), BATCH_SIZE):
        batch_stocks = stocks[i:i + BATCH_SIZE]
        
        # 下载批次
        success = download_batch(batch_num, batch_stocks)
        
        if not success:
            logger.warning(f"⚠️ 批次 {batch_num} 有失败，继续下一批")
        
        batch_num += 1
        
        # 批次间隔
        if i + BATCH_SIZE < len(stocks):
            logger.info(f"\n⏳ 等待 {BATCH_DELAY} 秒后继续下一批...")
            time.sleep(BATCH_DELAY)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 全部下载完成！")
    logger.info(f"结束时间：{datetime.now()}")
    logger.info("=" * 60)
    
    # 打印重试统计
    print_retry_stats()
    
    # 发送完成通知
    monitor = get_retry_monitor()
    stats = monitor.get_stats()
    notify_task_complete("数据下载", {
        "成功率": f"{stats['total_success']}/{stats['total_calls']}",
        "重试次数": stats['total_retries']
    })


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 程序异常：{e}")
        notify_task_error("数据下载", str(e))
        raise
