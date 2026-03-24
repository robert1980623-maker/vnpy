#!/usr/bin/env python3
"""
问题发现与解决闭环协调器

完整流程：
1. 日志分析 Agent 分析问题
2. 提交问题报告给主 Agent
3. 主 Agent 调度合适 Agent 解决
4. 验证所有问题是否解决
5. 生成最终报告
"""

import subprocess
from pathlib import Path
from datetime import datetime

def main():
    print("\n" + "="*70)
    print(f"🔄 问题发现与解决闭环")
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    project_root = Path(__file__).parent
    
    # 步骤 1: 日志分析
    print("\n【步骤 1/4】日志分析 Agent 分析问题")
    print("="*70)
    result1 = subprocess.run(
        ['python3', 'log_analyzer_enhanced.py'],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=600
    )
    print(result1.stdout[-1500:])
    
    if result1.returncode != 0:
        print(f"❌ 日志分析失败：{result1.stderr[:200]}")
        return
    
    # 步骤 2: 主 Agent 调度
    print("\n【步骤 2/4】主 Agent 调度 Agent 解决问题")
    print("="*70)
    result2 = subprocess.run(
        ['python3', 'main_agent_dispatcher.py'],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=3600
    )
    print(result2.stdout[-2000:])
    
    if result2.returncode != 0:
        print(f"❌ 主 Agent 调度失败：{result2.stderr[:200]}")
        return
    
    # 步骤 3: 再次日志分析（验证）
    print("\n【步骤 3/4】再次日志分析验证问题解决")
    print("="*70)
    result3 = subprocess.run(
        ['python3', 'log_analyzer_enhanced.py'],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=600
    )
    print(result3.stdout[-1000:])
    
    # 步骤 4: 生成最终报告
    print("\n【步骤 4/4】生成最终闭环报告")
    print("="*70)
    
    final_report = {
        'report_id': f"CLOSED-LOOP-{datetime.now().strftime('%Y%m%d-%H%M')}",
        'completed_at': datetime.now().isoformat(),
        'steps': [
            {'step': 1, 'name': '日志分析', 'status': 'completed' if result1.returncode == 0 else 'failed'},
            {'step': 2, 'name': '主 Agent 调度', 'status': 'completed' if result2.returncode == 0 else 'failed'},
            {'step': 3, 'name': '验证分析', 'status': 'completed' if result3.returncode == 0 else 'failed'}
        ],
        'all_steps_completed': all([
            result1.returncode == 0,
            result2.returncode == 0,
            result3.returncode == 0
        ])
    }
    
    print(f"\n✅ 闭环流程完成")
    print(f"   步骤 1（日志分析）: {'✅' if result1.returncode == 0 else '❌'}")
    print(f"   步骤 2（主 Agent 调度）: {'✅' if result2.returncode == 0 else '❌'}")
    print(f"   步骤 3（验证分析）: {'✅' if result3.returncode == 0 else '❌'}")
    
    return final_report

if __name__ == '__main__':
    main()
