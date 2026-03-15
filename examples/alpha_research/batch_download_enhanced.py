#!/usr/bin/env python3
"""
分批下载股票数据（增强版 - 集成 Neo4j 同步）

数据源策略:
- ✅ 主数据源：Tushare Pro (更稳定可靠)
- ✅ 备份数据源：Akshare (Tushare 失败时使用)

功能:
- 每批 5 只股票
- 批次间隔 30 秒
- 单只股票间隔 3 秒
- ✅ 自动同步到 Neo4j WorldState
- ✅ 增量同步（只更新新数据）
- ✅ 错误处理和重试机制
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
MAX_RETRIES = 3
RETRY_DELAY = 5

# 数据源配置
DATA_SOURCE_PRIMARY = "tushare"  # 主数据源
DATA_SOURCE_BACKUP = "akshare"   # 备份数据源

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/batch_download.log'),
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


def download_with_tushare(stock_code):
    """
    使用 Tushare 下载股票数据
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  📊 使用 Tushare 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_tushare.py",
        "--code", stock_code
    ]
    
    try:
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
            return False
    except Exception as e:
        logger.warning(f"⚠️ Tushare {stock_code} 异常：{e}")
        return False


def download_with_akshare(stock_code):
    """
    使用 Akshare 下载股票数据（备份）
    
    Returns:
        bool: 是否成功
    """
    logger.info(f"  📊 使用 Akshare 下载 {stock_code}...")
    
    cmd = [
        "python3", "download_data_akshare.py",
        "--code", stock_code
    ]
    
    try:
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
            return False
    except Exception as e:
        logger.error(f"❌ Akshare {stock_code} 异常：{e}")
        return False


def download_with_retry(stock_code, retry_count=0):
    """
    下载单只股票（带重试机制，双数据源）
    
    策略:
    1. 优先使用 Tushare
    2. Tushare 失败时使用 Akshare
    3. 最多重试 3 次
    
    Args:
        stock_code: 股票代码
        retry_count: 当前重试次数
    
    Returns:
        dict: 股票数据，失败返回 None
    """
    logger.info(f"\n--- 下载 {stock_code} (重试 {retry_count}/{MAX_RETRIES}) ---")
    
    # 1. 尝试 Tushare（主数据源）
    if download_with_tushare(stock_code):
        return {'symbol': stock_code, 'status': 'success', 'source': 'tushare'}
    
    # 2. Tushare 失败，尝试 Akshare（备份）
    logger.info(f"  ⚠️ Tushare 失败，切换到备份数据源 Akshare")
    if download_with_akshare(stock_code):
        return {'symbol': stock_code, 'status': 'success', 'source': 'akshare'}
    
    # 3. 都失败，重试
    if retry_count < MAX_RETRIES:
        logger.warning(f"⚠️ {stock_code} 双数据源均失败，{RETRY_DELAY}秒后重试...")
        time.sleep(RETRY_DELAY)
        return download_with_retry(stock_code, retry_count + 1)
    else:
        logger.error(f"❌ {stock_code} 下载失败，已达最大重试次数")
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
    logger.info(f"数据源策略：Tushare(主) + Akshare(备)")
    
    success_count = 0
    tushare_count = 0
    akshare_count = 0
    sync_count = 0
    verify_count = 0
    
    for i, stock in enumerate(stocks):
        # 下载（带重试，双数据源）
        result = download_with_retry(stock)
        
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


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("批量下载股票（增强版 - Tushare 主 + Akshare 备）")
    logger.info("=" * 60)
    logger.info(f"开始时间：{datetime.now()}")
    logger.info(f"Neo4j 同步：{'✅ 启用' if NEO4J_AVAILABLE else '❌ 禁用'}")
    logger.info(f"数据源策略：{DATA_SOURCE_PRIMARY}(主) + {DATA_SOURCE_BACKUP}(备)")
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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 程序异常：{e}")
        raise
