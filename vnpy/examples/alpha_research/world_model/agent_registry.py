#!/usr/bin/env python3
"""vnpy Agent 注册同步模块"""

import sys, os, re, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except:
    NEO4J_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRegistry:
    def __init__(self, neo4j_uri="bolt://localhost:7687", user="neo4j", password="admin_robert"):
        if not NEO4J_AVAILABLE:
            raise Exception("Neo4j 不可用")
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        self.driver.verify_connectivity()
        
        self.agent_type_map = {
            'health_check': 'monitoring', 'error_handler': 'monitoring',
            'decision_maker': 'decision', 'risk_officer': 'risk',
            'compliance': 'risk', 'data': 'data', 'log_analyzer': 'monitoring',
            'dispatcher': 'coordinator', 'quant': 'trading',
            'report': 'reporting', 'trading': 'trading', 'review': 'review'
        }
        logger.info("✅ Agent 注册管理器初始化完成")
    
    def scan_agents(self, project_dir: str) -> List[Dict]:
        project_path = Path(project_dir)
        agents = []
        patterns = ['*agent*.py', '*officer*.py', '*decision*.py']
        
        for pattern in patterns:
            for file in project_path.glob(pattern):
                if file.name.startswith('test_') or file.name.startswith('__'):
                    continue
                agent_info = self._parse_agent_file(file)
                if agent_info:
                    agents.append(agent_info)
        
        logger.info(f"📊 扫描到 {len(agents)} 个 Agent 文件")
        return agents
    
    def _parse_agent_file(self, file_path: Path) -> Optional[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            name_match = re.search(r'class\s+(\w+)\s*[:\(]', content)
            agent_name = name_match.group(1) if name_match else file_path.stem
            
            agent_type = 'unknown'
            for keyword, atype in self.agent_type_map.items():
                if keyword in file_path.name.lower():
                    agent_type = atype
                    break
            
            desc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            description = desc_match.group(1).strip().split('\n')[0] if desc_match else ''
            
            return {
                'agent_id': file_path.stem,
                'agent_name': agent_name,
                'file_name': file_path.name,
                'file_path': str(file_path),
                'type': agent_type,
                'description': description[:200],
                'status': 'active'
            }
        except Exception as e:
            logger.error(f"解析 {file_path} 失败：{e}")
            return None
    
    def register_agent(self, agent_info: Dict) -> str:
        with self.driver.session() as session:
            cypher = """
            MERGE (a:Agent {id: $agent_id})
            SET a.name = $agent_name,
                a.type = $agent_type,
                a.description = $description,
                a.status = $status,
                a.file_name = $file_name,
                a.file_path = $file_path,
                a.updated_at = datetime()
            RETURN a
            """
            
            session.run(cypher, {
                'agent_id': agent_info['agent_id'],
                'agent_name': agent_info['agent_name'],
                'agent_type': agent_info['type'],
                'description': agent_info['description'],
                'status': agent_info['status'],
                'file_name': agent_info['file_name'],
                'file_path': agent_info['file_path']
            })
            
            logger.info(f"✅ 注册 Agent: {agent_info['agent_name']} ({agent_info['type']})")
            return agent_info['agent_id']
    
    def sync_all_agents(self, project_dir: str) -> Dict:
        logger.info("=" * 60)
        logger.info("开始同步 vnpy Agent...")
        logger.info("=" * 60)
        
        agents = self.scan_agents(project_dir)
        registered = 0
        failed = 0
        
        for agent in agents:
            try:
                self.register_agent(agent)
                registered += 1
            except Exception as e:
                logger.error(f"注册 {agent['agent_name']} 失败：{e}")
                failed += 1
        
        stats = {
            'total_scanned': len(agents),
            'registered': registered,
            'failed': failed,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("=" * 60)
        logger.info(f"同步完成：{registered}/{len(agents)} 个 Agent")
        logger.info("=" * 60)
        
        return stats
    
    def get_agent_stats(self) -> Dict:
        with self.driver.session() as session:
            result = session.run("MATCH (a:Agent) RETURN a.type as type, count(a) as count")
            stats = {'total': 0, 'by_type': {}}
            for record in result:
                stats['by_type'][record['type']] = record['count']
                stats['total'] += record['count']
            return stats
    
    def close(self):
        if self.driver:
            self.driver.close()


if __name__ == "__main__":
    print("=" * 60)
    print("测试 Agent 注册同步")
    print("=" * 60)
    
    registry = AgentRegistry()
    project_dir = Path(__file__).parent.parent
    stats = registry.sync_all_agents(str(project_dir))
    
    print("\nAgent 统计:")
    agent_stats = registry.get_agent_stats()
    print(f"  总数：{agent_stats['total']}")
    for atype, count in agent_stats['by_type'].items():
        print(f"  - {atype}: {count} 个")
    
    registry.close()
    print("\n✅ 测试完成")
