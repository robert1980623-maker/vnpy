#!/usr/bin/env python3
"""修复 agent_health_check.py 的名称匹配问题"""

with open('agent_health_check.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换 critical_agents 为关键词字典
old_text = """self.critical_agents = [
            '每日选股',
            '虚拟账户 - 每日自动交易',
            '每日复盘',
            '数据下载',
            '首席风险官 (CRO)',
            '止盈止损执行 Agent',
        ]"""

new_text = """self.critical_agents_keywords = {
            '每日选股': ['每日选股', '选股'],
            '虚拟账户交易': ['虚拟账户', '自动交易', '每日交易'],
            '每日复盘': ['每日复盘', '复盘'],
            '数据下载': ['数据下载', '下载'],
            '首席风险官': ['首席风险官', 'CRO', '风险官'],
            '止盈止损执行': ['止盈止损执行', '止损执行'],
        }"""

content = content.replace(old_text, new_text)

# 2. 添加辅助方法
insert_pos = content.find('    def get_cron_status')
helper_method = '''    def _is_critical_agent(self, name: str) -> bool:
        """检查是否是关键 Agent (使用关键词模糊匹配)"""
        for keywords in self.critical_agents_keywords.values():
            if any(kw in name for kw in keywords):
                return True
        return False
    
'''

if insert_pos > 0:
    content = content[:insert_pos] + helper_method + content[insert_pos:]

# 3. 替换所有 self.critical_agents 的引用
content = content.replace(
    "'is_critical': name in self.critical_agents",
    "'is_critical': self._is_critical_agent(name)"
)

content = content.replace(
    "if name in self.critical_agents:",
    "if self._is_critical_agent(name):"
)

content = content.replace(
    "len(self.critical_agents)",
    "len(self.critical_agents_keywords)"
)

# 4. 替换 missing_critical 逻辑
old_missing = """critical_agents_found = [name for name in self.critical_agents 
                                if any(t['name'] == name for t in tasks)]
        missing_critical = [name for name in self.critical_agents 
                          if name not in critical_agents_found]"""

new_missing = """critical_agents_found = {}
        for task in tasks:
            task_name = task['name']
            for key, keywords in self.critical_agents_keywords.items():
                if any(kw in task_name for kw in keywords):
                    critical_agents_found[key] = task_name
                    break
        missing_critical = [key for key in self.critical_agents_keywords 
                          if key not in critical_agents_found]"""

content = content.replace(old_missing, new_missing)

# 保存
with open('agent_health_check.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成")
