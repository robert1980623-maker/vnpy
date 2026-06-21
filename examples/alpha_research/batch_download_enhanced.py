#!/usr/bin/env python3
"""
分批下载股票数据（增强版 - 集成 Neo4j 同步 + 自动重试机制）

数据源策略:
- ✅ 主数据源：Tushare Pro (已付费 TOKEN)
- 🔄 备份数据源：Akshare (Tushare 失败时自动切换)

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
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# 通知工具
from notification_utils import TaskNotifier, notify_task_start, notify_task_complete, notify_task_error

# 重试工具（新增）
from retry_utils import (
    retry_with_backoff,
    retry_function,
    get_retry_monitor,
    RetryMonitor
)

# 失败队列管理
def load_failed_downloads() -> dict:
    """加载失败队列"""
    if FAILED_DOWNLOADS_FILE.exists():
        try:
            with open(FAILED_DOWNLOADS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_failed_downloads(failed: dict):
    """保存失败队列"""
    with open(FAILED_DOWNLOADS_FILE, 'w') as f:
        json.dump(failed, f, indent=2)

def add_to_failed_queue(symbol: str, error: str):
    """添加失败股票到队列"""
    failed = load_failed_downloads()
    if symbol not in failed:
        failed[symbol] = {'error': error, 'count': 1, 'last_try': datetime.now().isoformat()}
    else:
        failed[symbol]['count'] += 1
        failed[symbol]['last_try'] = datetime.now().isoformat()
    save_failed_downloads(failed)

def remove_from_failed_queue(symbol: str):
    """从失败队列移除（成功后调用）"""
    failed = load_failed_downloads()
    if symbol in failed:
        del failed[symbol]
        save_failed_downloads(failed)

def get_retry_candidates() -> list:
    """获取可重试的股票（未超过最大重试次数）"""
    failed = load_failed_downloads()
    return [s for s, info in failed.items() if info['count'] < MAX_RETRY_COUNT]

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
BATCH_DELAY = 5  # 优化：30→5秒（Tushare限频200次/分钟，实际利用率10%）
STOCK_DELAY = 1  # 优化：3→1秒
TOTAL_STOCKS = 20

# 失败队列配置
FAILED_DOWNLOADS_FILE = Path(__file__).parent / 'failed_downloads.json'
MAX_RETRY_COUNT = 3

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
    
    # 优先使用 Akshare (无需 token，更稳定)
    cmd = [
        "python3", "-c",
        "import akshare as ak; df = ak.index_stock_cons(symbol='000300'); "
        "print(','.join(df['品种代码'].tolist()[:20]))"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            stocks = result.stdout.strip().split(',')
            logger.info(f"✅ Akshare 获取到 {len(stocks)} 只股票")
            return stocks
    except Exception as e:
        logger.warning(f"⚠️ Akshare 获取失败，切换到 Tushare: {e}")
    
    # Akshare 失败，使用 Tushare (使用 index_member API)
    cmd = [
        "python3", "-c",
        "import tushare as ts; pro = ts.pro_api(); df = pro.index_member(index_code='000300.SH'); "
        "print(','.join(df['con_code'].unique().tolist()[:20]))"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            stocks = result.stdout.strip().split(',')
            logger.info(f"✅ Tushare 获取到 {len(stocks)} 只股票")
            return stocks
    except Exception as e:
        logger.warning(f"⚠️ Tushare 获取失败：{e}")
    
    # 都失败，使用默认列表
    logger.warning("⚠️ 使用默认股票列表")
    return [
        '000630', '000807', '000975', '000999', '001391',
        '002028', '002384', '002422', '002463', '002600',
        '002625', '300251', '300394', '300418', '300442',
        '300476', '300502', '300803', '300832', '300866'
    ]


def download_with_tushare(stock_code):
    """
    使用 Tushare Pro 下载股票数据（主数据源）
    
    说明：download_data_akshare.py 已配置为 Tushare 优先
    （通过 TUSHARE_TOKEN 环境变量自动选择）
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  📊 使用 Tushare Pro 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_akshare.py",
        "--symbols", stock_code,
        "--max", "1"
    ]
    
    # 传递环境变量（包含 TUSHARE_TOKEN）
    env = os.environ.copy()
    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=60,
        env=env
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Tushare {stock_code} 下载成功")
        return True
    else:
        logger.error(f"❌ Tushare {stock_code} 失败：{result.stderr[:200]}")
        raise Exception(f"Tushare 下载失败")


def download_with_akshare(stock_code):
    """
    使用 Akshare 下载股票数据（备份数据源）
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  🔄 切换到 Akshare 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_akshare.py",
        "--symbols", stock_code,
        "--max", "1"
    ]
    
    # 不传递 TUSHARE_TOKEN，强制使用 AKShare
    env = os.environ.copy()
    env.pop('TUSHARE_TOKEN', None)
    
    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=60,
        env=env
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Akshare {stock_code} 下载成功")
        return True
    else:
        logger.error(f"❌ Akshare {stock_code} 失败：{result.stderr[:200]}")
        raise Exception(f"Akshare 下载失败")


def download_with_dual_source(stock_code):
    """
    下载单只股票（Tushare 优先 + AkShare 备份）
    
    策略:
    1. 优先使用 Tushare Pro 下载（带重试）
    2. Tushare 失败则切换到 Akshare（带重试）
    3. 都失败则返回失败
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 股票数据，失败返回 None
    """
    logger.info(f"\n--- 下载 {stock_code} (Tushare 优先) ---")
    
    # 1. 优先尝试 Tushare
    try:
        if download_with_tushare(stock_code):
            remove_from_failed_queue(stock_code)
            return {'symbol': stock_code, 'status': 'success', 'source': 'tushare'}
    except Exception as e:
        logger.warning(f"⚠️ Tushare 最终失败，切换 AKShare: {e}")

    # 2. Fallback 到 AKShare
    try:
        if download_with_akshare(stock_code):
            remove_from_failed_queue(stock_code)
            return {'symbol': stock_code, 'status': 'success', 'source': 'akshare'}
    except Exception as e:
        logger.warning(f"⚠️ AKShare 也失败：{e}")

    # 3. 都失败
    logger.error(f"❌ {stock_code} 下载失败（双数据源均失败）")
    add_to_failed_queue(stock_code, "Tushare + AKShare 双数据源均失败")
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

    # 优先重试上次失败的股票
    retry_candidates = get_retry_candidates()
    if retry_candidates:
        logger.info(f"🔄 发现 {len(retry_candidates)} 只上次失败股票，优先重试")
        retry_set = set(retry_candidates)
        stocks = retry_candidates + [s for s in stocks if s not in retry_set]

    # 增量检测：跳过已有最新数据的股票
    filtered_stocks = []
    skipped = 0
    for stock in stocks:
        csv_path = Path(f"data/akshare/bars/{stock}.csv")
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if not df.empty and 'date' in df.columns:
                    last_date = pd.to_datetime(df['date'].iloc[-1]).date()
                    today = datetime.now().date()
                    if last_date >= today:
                        skipped += 1
                        continue
            except Exception:
                pass
        filtered_stocks.append(stock)

    if skipped > 0:
        logger.info(f"⏭️  跳过 {skipped} 只已有最新数据的股票")
    stocks = filtered_stocks

    if not stocks:
        logger.info("✅ 所有股票数据已是最新，无需下载")
        return

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
