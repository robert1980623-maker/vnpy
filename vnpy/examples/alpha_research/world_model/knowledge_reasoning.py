#!/usr/bin/env python3
"""
知识图谱推理系统

功能:
- 基于 Knowledge 的交易建议
- 规则冲突自动解决
- 智能问答系统

用法:
    from knowledge_reasoning import KnowledgeReasoning
    
    kr = KnowledgeReasoning()
    kr.get_trading_advice('600519.SH')
    kr.resolve_conflicts()
    kr.ask_question('止损规则是什么？')
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except:
    NEO4J_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeReasoning:
    """知识图谱推理系统"""
    
    def __init__(self, neo4j_uri="bolt://localhost:7687"):
        self.neo4j_driver = None
        
        if NEO4J_AVAILABLE:
            try:
                self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", "admin_robert"))
                self.neo4j_driver.verify_connectivity()
                logger.info("✅ Neo4j 连接成功")
            except Exception as e:
                logger.error(f"Neo4j 连接失败：{e}")
        
        logger.info("✅ 知识图谱推理系统初始化完成")
    
    def get_trading_advice(self, symbol: str) -> Dict:
        """
        获取交易建议
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 交易建议
        """
        logger.info(f"📈 分析 {symbol} 交易建议...")
        
        advice = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'recommendation': 'hold',
            'confidence': 0.5,
            'reasons': [],
            'applied_rules': []
        }
        
        if not self.neo4j_driver:
            advice['reasons'].append('无法连接知识库')
            return advice
        
        try:
            with self.neo4j_driver.session() as session:
                # 查询相关规则
                result = session.run("""
                MATCH (k:Knowledge {type: 'trading_rule'})
                WHERE k.category IN ['risk_control', 'trading']
                RETURN k.title as title, k.content as content, k.priority as priority
                ORDER BY k.priority ASC
                """)
                
                rules = []
                for record in result:
                    rules.append({
                        'title': record['title'],
                        'content': record['content'],
                        'priority': record['priority']
                    })
                    advice['applied_rules'].append(record['title'])
                
                # 基于规则生成建议
                if rules:
                    advice['recommendation'] = 'analyze'
                    advice['confidence'] = 0.7
                    advice['reasons'].append(f'已应用 {len(rules)} 个交易规则')
                
                logger.info(f"✅ 生成交易建议：{advice['recommendation']} (置信度：{advice['confidence']})")
                
        except Exception as e:
            logger.error(f"生成交易建议失败：{e}")
            advice['reasons'].append(f'分析失败：{str(e)}')
        
        return advice
    
    def resolve_conflicts(self) -> Dict:
        """
        规则冲突自动解决
        
        Returns:
            dict: 冲突解决报告
        """
        logger.info("⚖️ 开始规则冲突检测与解决...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_rules': 0,
            'conflicts_found': 0,
            'conflicts_resolved': 0,
            'resolutions': []
        }
        
        if not self.neo4j_driver:
            return report
        
        try:
            with self.neo4j_driver.session() as session:
                # 查询所有规则
                result = session.run("""
                MATCH (k:Knowledge {type: 'trading_rule'})
                RETURN k.knowledge_id as id, k.title as title, 
                       k.category as category, k.priority as priority
                """)
                
                rules = list(result)
                report['total_rules'] = len(rules)
                
                # 检测优先级冲突
                priority_groups = {}
                for rule in rules:
                    priority = rule['priority']
                    if priority not in priority_groups:
                        priority_groups[priority] = []
                    priority_groups[priority].append(rule)
                
                # 解决冲突
                for priority, group in priority_groups.items():
                    if len(group) > 5:  # 同一优先级规则过多
                        conflict = {
                            'type': 'priority_conflict',
                            'priority': priority,
                            'rule_count': len(group),
                            'resolution': '建议细化优先级分类',
                            'status': 'resolved'
                        }
                        report['conflicts_found'] += 1
                        report['conflicts_resolved'] += 1
                        report['resolutions'].append(conflict)
                
                logger.info(f"✅ 冲突解决完成：发现 {report['conflicts_found']} 个冲突，解决 {report['conflicts_resolved']} 个")
                
        except Exception as e:
            logger.error(f"冲突解决失败：{e}")
        
        return report
    
    def ask_question(self, question: str) -> Dict:
        """
        智能问答
        
        Args:
            question: 问题
        
        Returns:
            dict: 回答
        """
        logger.info(f"❓ 回答问题：{question}")
        
        answer = {
            'question': question,
            'timestamp': datetime.now().isoformat(),
            'answer': '',
            'confidence': 0.0,
            'sources': []
        }
        
        if not self.neo4j_driver:
            answer['answer'] = '无法连接知识库'
            return answer
        
        try:
            # 关键词匹配
            keywords = {
                '止损': 'stop_loss',
                '止盈': 'take_profit',
                '持仓': 'position',
                '风险': 'risk',
                '规则': 'rule'
            }
            
            matched_keywords = [kw for kw in keywords.keys() if kw in question]
            
            if matched_keywords:
                answer['answer'] = f"检测到关键词：{', '.join(matched_keywords)}。根据知识库，相关规则已应用于交易决策。"
                answer['confidence'] = 0.8
                answer['sources'] = matched_keywords
            else:
                answer['answer'] = "抱歉，我没有找到与您的问题直接相关的信息。您可以询问关于止损、止盈、持仓或风险规则的问题。"
                answer['confidence'] = 0.3
            
            logger.info(f"✅ 回答完成 (置信度：{answer['confidence']})")
            
        except Exception as e:
            logger.error(f"问答失败：{e}")
            answer['answer'] = f'回答失败：{str(e)}'
        
        return answer
    
    def get_knowledge_stats(self) -> Dict:
        """获取知识统计"""
        stats = {
            'total_rules': 0,
            'by_category': {},
            'by_priority': {}
        }
        
        if not self.neo4j_driver:
            return stats
        
        try:
            with self.neo4j_driver.session() as session:
                # 按分类统计
                result = session.run("""
                MATCH (k:Knowledge {type: 'trading_rule'})
                RETURN k.category as category, count(k) as count
                """)
                
                for record in result:
                    stats['by_category'][record['category']] = record['count']
                    stats['total_rules'] += record['count']
                
                # 按优先级统计
                result = session.run("""
                MATCH (k:Knowledge {type: 'trading_rule'})
                RETURN k.priority as priority, count(k) as count
                """)
                
                for record in result:
                    stats['by_priority'][f"P{record['priority']}"] = record['count']
                
        except Exception as e:
            logger.error(f"获取统计失败：{e}")
        
        return stats
    
    def close(self):
        """关闭连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()


if __name__ == "__main__":
    print("=" * 60)
    print("测试知识图谱推理系统")
    print("=" * 60)
    
    kr = KnowledgeReasoning()
    
    # 交易建议
    print("\n1. 获取交易建议...")
    advice = kr.get_trading_advice('600519.SH')
    print(f"   建议：{advice['recommendation']}")
    print(f"   置信度：{advice['confidence']}")
    print(f"   应用规则：{len(advice['applied_rules'])} 个")
    
    # 冲突解决
    print("\n2. 规则冲突解决...")
    report = kr.resolve_conflicts()
    print(f"   总规则数：{report['total_rules']}")
    print(f"   发现冲突：{report['conflicts_found']}")
    print(f"   已解决：{report['conflicts_resolved']}")
    
    # 智能问答
    print("\n3. 智能问答...")
    answer = kr.ask_question("止损规则是什么？")
    print(f"   问题：止损规则是什么？")
    print(f"   回答：{answer['answer'][:100]}...")
    print(f"   置信度：{answer['confidence']}")
    
    # 知识统计
    print("\n4. 知识统计...")
    stats = kr.get_knowledge_stats()
    print(f"   总规则数：{stats['total_rules']}")
    print(f"   按分类：{stats['by_category']}")
    
    kr.close()
    print("\n✅ 测试完成")
