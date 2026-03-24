#!/usr/bin/env python3
"""
vnpy 交易规则提取模块

从 vnpy 代码中自动提取交易规则并转换为 Knowledge
"""

import sys
import re
import ast
import logging
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from knowledge_schema import TradingRule, RuleCategory, RuleVersionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RuleExtractor:
    """规则提取器"""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.version_mgr = RuleVersionManager()
        self.extracted_rules = []
        
        # 规则模式定义
        self.patterns = {
            'stop_loss': {
                'keywords': ['stop_loss', '止损', '亏损'],
                'category': RuleCategory.RISK_CONTROL,
                'priority': 1
            },
            'take_profit': {
                'keywords': ['take_profit', '止盈', '盈利'],
                'category': RuleCategory.RISK_CONTROL,
                'priority': 1
            },
            'position_limit': {
                'keywords': ['position', '持仓', '仓位'],
                'category': RuleCategory.POSITION,
                'priority': 2
            },
            'data_quality': {
                'keywords': ['quality', '质量', 'validate'],
                'category': RuleCategory.DATA_QUALITY,
                'priority': 3
            }
        }
        
        logger.info("✅ 规则提取器初始化完成")
    
    def extract_from_file(self, file_path: Path) -> List[TradingRule]:
        """从单个文件提取规则"""
        rules = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 逐行分析
            for i, line in enumerate(lines):
                rule = self._analyze_line(line, i + 1, file_path.name)
                if rule:
                    rules.append(rule)
            
            logger.info(f"📄 从 {file_path.name} 提取到 {len(rules)} 个规则")
            
        except Exception as e:
            logger.error(f"读取 {file_path} 失败：{e}")
        
        return rules
    
    def _analyze_line(self, line: str, line_num: int, file_name: str) -> Optional[TradingRule]:
        """分析单行代码，提取规则"""
        line_lower = line.lower()
        
        for rule_type, config in self.patterns.items():
            for keyword in config['keywords']:
                if keyword in line_lower:
                    # 提取规则逻辑
                    logic = self._extract_logic(line, line_num)
                    
                    if logic:
                        rule = TradingRule(
                            name=f"{file_name}.{line_num}.{rule_type}",
                            category=config['category'],
                            logic=logic,
                            priority=config['priority'],
                            tags=[rule_type, file_name.replace('.py', '')],
                            metadata={
                                'file': file_name,
                                'line': line_num,
                                'source': 'code_analysis'
                            }
                        )
                        return rule
        
        return None
    
    def _extract_logic(self, line: str, line_num: int) -> str:
        """提取规则逻辑"""
        # 清理代码
        logic = line.strip()
        
        # 如果是赋值语句，提取完整逻辑
        if '=' in logic and not logic.startswith('#'):
            # 提取条件部分
            if 'if' in logic.lower():
                return logic
            # 提取配置
            elif ':' in logic:
                return f"配置：{logic}"
        
        return logic[:200]  # 限制长度
    
    def extract_all(self) -> List[TradingRule]:
        """提取项目中所有规则"""
        logger.info("=" * 60)
        logger.info("开始提取 vnpy 交易规则...")
        logger.info("=" * 60)
        
        # 扫描关键文件
        key_files = [
            'ai_decision_maker.py',
            'chief_risk_officer.py',
            'compliance_agent.py',
            'check_data_quality.py',
            'daily_trading.py'
        ]
        
        all_rules = []
        
        for file_name in key_files:
            file_path = self.project_dir / file_name
            if file_path.exists():
                rules = self.extract_from_file(file_path)
                all_rules.extend(rules)
                
                # 添加到版本管理
                for rule in rules:
                    try:
                        self.version_mgr.add_version(rule)
                    except ValueError:
                        pass  # 版本已存在
        
        self.extracted_rules = all_rules
        
        logger.info("=" * 60)
        logger.info(f"提取完成：共 {len(all_rules)} 个规则")
        logger.info("=" * 60)
        
        return all_rules
    
    def save_rules_to_neo4j(self, rules: List[TradingRule], neo4j_client):
        """保存规则到 Neo4j"""
        logger.info(f"💾 保存 {len(rules)} 个规则到 Neo4j...")
        
        saved = 0
        for rule in rules:
            try:
                knowledge = rule.to_knowledge()
                neo4j_client.create_knowledge(**knowledge)
                saved += 1
                logger.info(f"   ✅ 保存：{rule.name}")
            except Exception as e:
                logger.error(f"   ❌ 保存失败 {rule.name}: {e}")
        
        logger.info(f"保存完成：{saved}/{len(rules)} 个规则")
        return saved
    
    def get_statistics(self) -> Dict:
        """获取规则统计"""
        stats = {
            'total': len(self.extracted_rules),
            'by_category': {},
            'by_priority': {},
            'by_file': {}
        }
        
        for rule in self.extracted_rules:
            # 按分类统计
            cat = rule.category
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # 按优先级统计
            pri = rule.priority
            stats['by_priority'][pri] = stats['by_priority'].get(pri, 0) + 1
            
            # 按文件统计
            file_name = rule.metadata.get('file', 'unknown')
            stats['by_file'][file_name] = stats['by_file'].get(file_name, 0) + 1
        
        return stats


if __name__ == "__main__":
    print("=" * 60)
    print("测试规则提取模块")
    print("=" * 60)
    
    project_dir = Path(__file__).parent.parent
    extractor = RuleExtractor(str(project_dir))
    
    # 提取规则
    rules = extractor.extract_all()
    
    # 显示统计
    print("\n规则统计:")
    stats = extractor.get_statistics()
    print(f"  总数：{stats['total']}")
    print(f"  按分类:")
    for cat, count in stats['by_category'].items():
        print(f"    - {cat}: {count}")
    print(f"  按优先级:")
    for pri, count in stats['by_priority'].items():
        print(f"    - P{pri}: {count}")
    
    print("\n✅ 测试完成")
