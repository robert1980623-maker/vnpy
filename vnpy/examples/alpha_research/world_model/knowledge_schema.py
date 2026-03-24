#!/usr/bin/env python3
"""
交易规则 Knowledge Schema 定义

定义 vnpy 交易规则的 Knowledge 结构和版本管理
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import json


class RuleCategory:
    """规则分类"""
    RISK_CONTROL = "risk_control"      # 风控规则
    TRADING = "trading"                # 交易规则
    DATA_QUALITY = "data_quality"      # 数据质量规则
    POSITION = "position"              # 持仓规则
    COMPLIANCE = "compliance"          # 合规规则


class KnowledgeSchema:
    """Knowledge Schema 基类"""
    
    @staticmethod
    def create_rule_id(rule_name: str, version: str) -> str:
        """生成规则 ID"""
        content = f"{rule_name}_{version}_{datetime.now().isoformat()}"
        return f"rule_{hashlib.md5(content.encode()).hexdigest()[:12]}"
    
    @staticmethod
    def validate_rule(rule: Dict) -> bool:
        """验证规则完整性"""
        required_fields = ['name', 'category', 'logic', 'priority']
        for field in required_fields:
            if field not in rule:
                return False
        return True


class TradingRule:
    """交易规则类"""
    
    def __init__(self, name: str, category: str, logic: str, 
                 priority: int = 1, version: str = "1.0.0",
                 tags: List[str] = None, metadata: Dict = None):
        self.rule_id = KnowledgeSchema.create_rule_id(name, version)
        self.name = name
        self.category = category
        self.logic = logic
        self.priority = priority
        self.version = version
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.status = "active"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'category': self.category,
            'logic': self.logic,
            'priority': self.priority,
            'version': self.version,
            'tags': self.tags,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'status': self.status
        }
    
    def to_knowledge(self) -> Dict:
        """转换为 Neo4j Knowledge 格式"""
        return {
            'knowledge_id': self.rule_id,
            'title': self.name,
            'content': self.logic,
            'type': 'trading_rule',
            'category': self.category,
            'tags': self.tags + [f"v{self.version}"],
            'confidence': 0.9,
            'metadata': json.dumps(self.metadata),
            'priority': self.priority,
            'version': self.version
        }


class RuleVersionManager:
    """规则版本管理器"""
    
    def __init__(self):
        self.versions: Dict[str, List[Dict]] = {}  # rule_name -> versions
    
    def add_version(self, rule: TradingRule):
        """添加新版本"""
        if rule.name not in self.versions:
            self.versions[rule.name] = []
        
        # 检查版本是否已存在
        for v in self.versions[rule.name]:
            if v['version'] == rule.version:
                raise ValueError(f"版本 {rule.version} 已存在")
        
        self.versions[rule.name].append(rule.to_dict())
        self.versions[rule.name].sort(key=lambda x: x['version'])
    
    def get_version(self, rule_name: str, version: str) -> Optional[Dict]:
        """获取指定版本"""
        if rule_name not in self.versions:
            return None
        
        for v in self.versions[rule_name]:
            if v['version'] == version:
                return v
        return None
    
    def get_latest_version(self, rule_name: str) -> Optional[Dict]:
        """获取最新版本"""
        if rule_name not in self.versions or not self.versions[rule_name]:
            return None
        
        return self.versions[rule_name][-1]
    
    def get_version_history(self, rule_name: str) -> List[Dict]:
        """获取版本历史"""
        return self.versions.get(rule_name, [])


class RuleConflictDetector:
    """规则冲突检测器"""
    
    def __init__(self):
        self.conflicts = []
    
    def detect_conflicts(self, rules: List[TradingRule]) -> List[Dict]:
        """
        检测规则冲突
        
        冲突类型:
        1. 条件冲突：相同条件下不同动作
        2. 优先级冲突：相同优先级
        3. 逻辑冲突：逻辑矛盾
        """
        self.conflicts = []
        
        # 按分类分组
        rules_by_category = {}
        for rule in rules:
            if rule.category not in rules_by_category:
                rules_by_category[rule.category] = []
            rules_by_category[rule.category].append(rule)
        
        # 检测每类中的冲突
        for category, category_rules in rules_by_category.items():
            self._detect_category_conflicts(category, category_rules)
        
        return self.conflicts
    
    def _detect_category_conflicts(self, category: str, rules: List[TradingRule]):
        """检测同类规则冲突"""
        # 检查优先级冲突
        priority_map = {}
        for rule in rules:
            if rule.priority in priority_map:
                self.conflicts.append({
                    'type': 'priority_conflict',
                    'category': category,
                    'rules': [priority_map[rule.priority], rule.name],
                    'priority': rule.priority,
                    'severity': 'medium'
                })
            else:
                priority_map[rule.priority] = rule.name
        
        # 检查逻辑冲突（简化版：检查相同关键词）
        logic_keywords = {}
        for rule in rules:
            keywords = self._extract_keywords(rule.logic)
            for kw in keywords:
                if kw in logic_keywords:
                    self.conflicts.append({
                        'type': 'logic_conflict',
                        'category': category,
                        'rules': [logic_keywords[kw], rule.name],
                        'keyword': kw,
                        'severity': 'high'
                    })
                else:
                    logic_keywords[kw] = rule.name
    
    def _extract_keywords(self, logic: str) -> List[str]:
        """提取逻辑关键词"""
        keywords = []
        # 提取条件关键词
        if 'if' in logic.lower():
            keywords.append('condition')
        if 'stop_loss' in logic.lower():
            keywords.append('stop_loss')
        if 'take_profit' in logic.lower():
            keywords.append('take_profit')
        if 'position' in logic.lower():
            keywords.append('position')
        return keywords


# 预定义规则模板
RULE_TEMPLATES = {
    'stop_loss': {
        'name': '止损规则',
        'category': RuleCategory.RISK_CONTROL,
        'logic': '当持仓亏损率达到 -15% 时，触发止损',
        'priority': 1,
        'tags': ['risk', 'stop_loss']
    },
    'take_profit': {
        'name': '止盈规则',
        'category': RuleCategory.RISK_CONTROL,
        'logic': '当持仓盈利率达到 +30% 时，触发止盈',
        'priority': 1,
        'tags': ['risk', 'take_profit']
    },
    'position_limit': {
        'name': '持仓限制规则',
        'category': RuleCategory.POSITION,
        'logic': '单只股票持仓不超过总资产的 15%',
        'priority': 2,
        'tags': ['position', 'limit']
    },
    'data_price_range': {
        'name': '数据价格范围规则',
        'category': RuleCategory.DATA_QUALITY,
        'logic': '股票价格应在 0.01-10000 元之间',
        'priority': 3,
        'tags': ['data', 'quality']
    }
}


def create_rule_from_template(template_name: str, **kwargs) -> TradingRule:
    """从模板创建规则"""
    if template_name not in RULE_TEMPLATES:
        raise ValueError(f"未知模板：{template_name}")
    
    template = RULE_TEMPLATES[template_name].copy()
    template.update(kwargs)
    
    return TradingRule(
        name=template['name'],
        category=template['category'],
        logic=template['logic'],
        priority=template.get('priority', 1),
        tags=template.get('tags', [])
    )


if __name__ == "__main__":
    print("=" * 60)
    print("测试 Knowledge Schema")
    print("=" * 60)
    
    # 创建规则
    print("\n1. 创建交易规则...")
    rule1 = TradingRule(
        name="止损规则",
        category=RuleCategory.RISK_CONTROL,
        logic="当持仓亏损率达到 -15% 时，触发止损",
        priority=1,
        tags=['risk', 'stop_loss']
    )
    print(f"   规则 ID: {rule1.rule_id}")
    print(f"   规则名称：{rule1.name}")
    print(f"   分类：{rule1.category}")
    
    # 版本管理
    print("\n2. 测试版本管理...")
    version_mgr = RuleVersionManager()
    version_mgr.add_version(rule1)
    
    rule1_v2 = TradingRule(
        name="止损规则",
        category=RuleCategory.RISK_CONTROL,
        logic="当持仓亏损率达到 -20% 时，触发止损",
        priority=1,
        version="1.1.0",
        tags=['risk', 'stop_loss']
    )
    version_mgr.add_version(rule1_v2)
    
    latest = version_mgr.get_latest_version("止损规则")
    print(f"   最新版本：{latest['version']}")
    print(f"   版本历史：{len(version_mgr.get_version_history('止损规则'))} 个")
    
    # 冲突检测
    print("\n3. 测试冲突检测...")
    detector = RuleConflictDetector()
    rules = [
        TradingRule("规则 A", "risk", "if stop_loss", priority=1),
        TradingRule("规则 B", "risk", "if stop_loss", priority=1),  # 优先级冲突
        TradingRule("规则 C", "risk", "if take_profit", priority=2)
    ]
    conflicts = detector.detect_conflicts(rules)
    print(f"   检测到 {len(conflicts)} 个冲突")
    for conflict in conflicts:
        print(f"   - {conflict['type']}: {conflict['rules']}")
    
    print("\n✅ 测试完成")
