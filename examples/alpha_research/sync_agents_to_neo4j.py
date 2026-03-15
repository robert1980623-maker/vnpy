#!/usr/bin/env python3
"""
Agent 注册同步到 Neo4j

功能:
- 扫描项目中的所有 Agent
- 自动注册到 Neo4j
- 更新 Agent 状态
- 生成同步报告

用法:
    python3 sync_agents_to_neo4j.py --auto
    python3 sync_agents_to_neo4j.py --scan
    python3 sync_agents_to_neo4j.py --report
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from world_model.agent_registry import AgentRegistry


class AgentSyncToNeo4j:
    """Agent Neo4j 同步器"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.report_dir = self.project_dir / 'reports' / 'agent_sync'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.registry = AgentRegistry()
            self.neo4j_available = True
        except Exception as e:
            print(f"⚠️  Neo4j 不可用：{e}")
            self.neo4j_available = False
            self.registry = None
    
    def scan_agents(self) -> list:
        """扫描 Agent"""
        print("\n📊 扫描 Agent 文件")
        print("=" * 70)
        
        if not self.registry:
            print("❌ AgentRegistry 不可用")
            return []
        
        agents = self.registry.scan_agents(str(self.project_dir))
        
        print(f"  发现 Agent: {len(agents)} 个")
        for agent in agents[:10]:  # 只显示前 10 个
            print(f"    • {agent['agent_name']} ({agent['type']})")
        
        if len(agents) > 10:
            print(f"    ... 还有 {len(agents) - 10} 个")
        
        return agents
    
    def sync_to_neo4j(self, agents: list) -> dict:
        """同步到 Neo4j"""
        print("\n🔄 同步到 Neo4j")
        print("=" * 70)
        
        if not self.registry or not self.neo4j_available:
            print("❌ Neo4j 不可用，跳过同步")
            return {'success': 0, 'failed': 0}
        
        success_count = 0
        failed_count = 0
        
        for agent in agents:
            try:
                self.registry.register_agent(agent)
                success_count += 1
                print(f"  ✅ {agent['agent_name']}")
            except Exception as e:
                failed_count += 1
                print(f"  ❌ {agent['agent_name']}: {e}")
        
        print(f"\n同步完成：{success_count} 成功，{failed_count} 失败")
        
        return {'success': success_count, 'failed': failed_count}
    
    def generate_report(self, agents: list, sync_result: dict) -> str:
        """生成同步报告"""
        report = f"""## Agent Neo4j 同步报告

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 统计
- 扫描 Agent: {len(agents)} 个
- 同步成功：{sync_result['success']} 个
- 同步失败：{sync_result['failed']} 个

### Agent 列表
"""
        
        for agent in agents:
            report += f"- {agent['agent_name']} ({agent['type']})\n"
        
        # 保存报告
        report_file = self.report_dir / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 报告已保存：{report_file}")
        
        return report
    
    def run_auto(self):
        """自动模式：扫描 + 同步 + 报告"""
        print("\n" + "=" * 70)
        print("🤖 Agent Neo4j 自动同步")
        print("=" * 70)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Neo4j 状态：{'✅ 可用' if self.neo4j_available else '❌ 不可用'}")
        
        # 扫描
        agents = self.scan_agents()
        
        if not agents:
            print("\n❌ 未发现 Agent")
            return False
        
        # 同步
        sync_result = self.sync_to_neo4j(agents)
        
        # 报告
        self.generate_report(agents, sync_result)
        
        print("\n" + "=" * 70)
        print("✅ Agent 同步完成！")
        print("=" * 70)
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Agent Neo4j 同步工具')
    parser.add_argument('--auto', action='store_true', help='自动模式')
    parser.add_argument('--scan', action='store_true', help='只扫描')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    syncer = AgentSyncToNeo4j()
    
    if args.scan:
        syncer.scan_agents()
    elif args.auto:
        syncer.run_auto()
    else:
        syncer.run_auto()


if __name__ == '__main__':
    main()
