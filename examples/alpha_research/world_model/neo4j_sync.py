#!/usr/bin/env python3
"""Neo4j 数据同步模块"""

from neo4j import GraphDatabase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jSync:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="admin_robert"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
    
    def sync_stock_data(self, stock_data):
        with self.driver.session() as session:
            cypher = """
            MERGE (ws:WorldState:StockPrice {symbol: $symbol, date: $date})
            SET ws.close = $close, ws.volume = $volume, ws.updated_at = datetime()
            RETURN ws
            """
            session.run(cypher, {
                'symbol': stock_data['symbol'],
                'date': stock_data['datetime'].strftime('%Y-%m-%d'),
                'close': stock_data['close'],
                'volume': stock_data.get('volume')
            })
            logger.info(f"✅ 同步：{stock_data['symbol']}")
    
    def close(self):
        self.driver.close()

if __name__ == "__main__":
    sync = Neo4jSync()
    sync.sync_stock_data({
        'symbol': '600519.SH',
        'datetime': datetime.now(),
        'close': 1440.11,
        'volume': 1000000
    })
    sync.close()
    print("✅ 测试完成")
