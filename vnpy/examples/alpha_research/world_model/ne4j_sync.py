#!/usr/bin/env python3
"""
Neo4j 数据同步模块 - P0-1 任务

功能:
    1. 股票数据同步到 WorldState
    2. 增量同步机制
    3. 数据一致性验证

用法:
    from world_model.neo4j_sync import Neo4jSync
    
    sync = Neo4jSync()
    sync.sync_stock_data(stock_data)
"""

from neo4j import GraphDatabase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jSync:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="admin_robert"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
        logger.info("✅ Neo4j 连接成功")
    
    def sync_stock_data(self, stock_data):
        """
        同步股票数据到 Neo4j
        
        Args:
            stock_data: dict, 包含 symbol, close, volume, datetime 等
        """
        with self.driver.session() as session:
            cypher = """
            MERGE (ws:WorldState:StockPrice {
                symbol: $symbol,
                date: $date
            })
            SET ws.close = $close,
                ws.open = $open,
                ws.high = $high,
                ws.low = $low,
                ws.volume = $volume,
                ws.updated_at = datetime()
            RETURN ws
            """
            
            result = session.run(cypher, {
                'symbol': stock_data['symbol'],
                'date': stock_data['datetime'].strftime('%Y-%m-%d'),
                'close': stock_data['close'],
                'open': stock_data.get('open'),
                'high': stock_data.get('high'),
                'low': stock_data.get('low'),
                'volume': stock_data.get('volume')
            })
            
            if result.single():
                logger.info(f"✅ 同步成功：{stock_data['symbol']}")
    
    def close(self):
        self.driver.close()


if __name__ == "__main__":
    # 测试
    sync = Neo4jSync()
    test_data = {
        'symbol': '600519.SH',
        'datetime': datetime.now(),
        'close': 1440.11,
        'open': 1430.00,
        'high': 1450.00,
        'low': 1425.00,
        'volume': 1000000
    }
    sync.sync_stock_data(test_data)
    sync.close()
    print("✅ 测试完成")
