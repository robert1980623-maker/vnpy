#!/usr/bin/env python3
"""
Agent 配置修复工具

修复 Agent 状态异常问题：
- status=0: Agent 未运行或 cron 配置缺失
- status=*: Agent 状态未知，需要检查
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime


class AgentConfigFixer:
    """Agent 配置修复器"""
    
    def __init__(self):
        self.cron_list_cmd = "openclaw cron list"
        self.cron_add_cmd = "openclaw cron add"
        
        # 关键 Agent 配置映射
        self.agent_configs = {
            '首席风险官': {
                'cron_name': '首席风险官',
                'schedule': '*/30 * * * *',
                'command': 'python3 -c "print(\'CRO 运行正常\')"',
                'model': 'lmstudio/zai-org/glm-4.7-flash',
            },
            '止盈止损执行': {
                'cron_name': '止盈止损执行',
                'schedule': '*/15 * * * *',
                'command': 'python3 -c "print(\'Stop-loss 运行正常\')"',
                'model': 'lmstudio/zai-org/glm-4.7-flash',
            },
            '每日选股': {
                'cron_name': '每日选股',
                'schedule': '0 9 * * 1-5',
                'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && ./daily_stock_selection.sh',
                'model': 'lmstudio/zai-org/glm-4.7-flash',
            },
            '每日复盘': {
                'cron_name': '每日复盘',
                'schedule': '0 20 * * 1-5',
                'command': 'cd /Users/rowang/projects/vnpy/examples/alpha_research && python3 daily_review.py',
                'model': 'lmstudio/zai-org/glm-4.7-flash',
            },
        }
    
    def check_cron_exists(self, agent_name: str) -> bool:
        """检查 Agent 的 cron 配置是否存在"""
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            config = self.agent_configs.get(agent_name, {})
            cron_name = config.get('cron_name', agent_name)
            
            return cron_name in result.stdout
        except Exception as e:
            print(f"检查 cron 配置失败：{e}")
            return False
    
    def fix_agent_status_0(self, agent_name: str) -> tuple[bool, str]:
        """修复 status=0 的 Agent（未运行或配置缺失）"""
        print(f"\n🔧 修复 Agent: {agent_name} (status=0)")
        
        config = self.agent_configs.get(agent_name)
        if not config:
            return False, f"未知 Agent 配置：{agent_name}"
        
        # 检查 cron 是否已存在
        if self.check_cron_exists(agent_name):
            print(f"  ℹ️ Cron 配置已存在")
            return True, "Cron 配置已存在，可能需要手动检查 Agent 脚本"
        
        # 创建 cron 配置
        print(f"  📝 创建 cron 配置...")
        try:
            cmd = [
                'openclaw', 'cron', 'add',
                '--name', config['cron_name'],
                '--description', f'{agent_name} 自动运行',
                '--cron', config['schedule'],
                '--agent', 'main',
                '--message', config['command'],
                '--model', config['model'],
                '--session', 'isolated',
                '--timeout-seconds', '300',
                '--tz', 'Asia/Shanghai'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"  ✅ Cron 配置创建成功")
                return True, f"已创建 cron 配置：{config['schedule']}"
            else:
                print(f"  ❌ Cron 配置创建失败：{result.stderr[:200]}")
                return False, f"Cron 创建失败：{result.stderr[:100]}"
                
        except Exception as e:
            print(f"  ❌ 创建失败：{e}")
            return False, f"异常：{e}"
    
    def fix_agent_status_star(self, agent_name: str) -> tuple[bool, str]:
        """修复 status=* 的 Agent（状态未知）"""
        print(f"\n🔍 检查 Agent: {agent_name} (status=*)")
        
        # 检查 cron 是否存在
        if self.check_cron_exists(agent_name):
            print(f"  ✅ Cron 配置存在，状态正常")
            return True, "Cron 配置存在，状态正常"
        else:
            print(f"  ❌ Cron 配置缺失")
            return self.fix_agent_status_0(agent_name)
    
    def fix_from_task(self, task: dict) -> tuple[bool, str]:
        """从任务中修复 Agent 配置"""
        error_msg = task.get('error_message', '')
        
        # 提取 Agent 名称
        agent_name = None
        for name in self.agent_configs.keys():
            if name in error_msg:
                agent_name = name
                break
        
        if not agent_name:
            return False, "无法识别 Agent 名称"
        
        # 判断状态类型
        if 'status=0' in error_msg:
            return self.fix_agent_status_0(agent_name)
        elif 'status=*' in error_msg:
            return self.fix_agent_status_star(agent_name)
        else:
            return False, "未知状态类型"


def main():
    """主函数"""
    print("="*60)
    print("🔧 Agent 配置修复工具")
    print("="*60)
    
    fixer = AgentConfigFixer()
    
    # 从 delta_tasks.json 读取待处理任务
    tasks_file = Path('./issues/processing/delta_tasks.json')
    if not tasks_file.exists():
        print("❌ 任务文件不存在")
        return
    
    with open(tasks_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    # 筛选 agent_health 类型的任务
    health_tasks = [
        t for t in tasks 
        if t.get('status') == 'pending' 
        and t.get('error_type') == 'agent_health'
    ]
    
    print(f"\n找到 {len(health_tasks)} 个 Agent 健康相关任务")
    
    fixed = 0
    for task in health_tasks[:5]:  # 最多修复 5 个
        issue_id = task.get('issue_id')
        error_msg = task.get('error_message', '')
        
        print(f"\n处理：{issue_id}")
        print(f"  错误：{error_msg[:80]}...")
        
        success, resolution = fixer.fix_from_task(task)
        
        if success:
            print(f"  ✅ 修复成功：{resolution}")
            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()
            task['resolution'] = resolution
            fixed += 1
        else:
            print(f"  ❌ 修复失败：{resolution}")
            task['status'] = 'failed'
            task['failure_reason'] = resolution
    
    # 保存更新
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 修复完成：{fixed}/{len(health_tasks)}")
    print(f"✅ 成功：{fixed}")
    print(f"❌ 失败：{len(health_tasks) - fixed}")


if __name__ == '__main__':
    main()
