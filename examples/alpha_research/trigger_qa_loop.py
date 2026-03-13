#!/usr/bin/env python3
"""
触发器 - Delta 完成后自动触发 QA-Architect 迭代

在 Delta 制定完优化计划后自动调用 QA 生成测试用例并启动审核流程
"""

import subprocess
from pathlib import Path
from datetime import datetime

def main():
    print("\n" + "="*70)
    print(f"🚀 触发 QA-Architect 审核流程")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    project_root = Path(__file__).parent
    
    try:
        # 运行 QA-Architect 迭代协调器
        result = subprocess.run(
            ['python3', 'qa_architect_loop.py'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("\n✅ QA-Architect 流程完成")
        else:
            print(f"\n⚠️ QA-Architect 流程异常：{result.stderr[:200]}")
    
    except subprocess.TimeoutExpired:
        print("\n⚠️ QA-Architect 流程超时")
    except Exception as e:
        print(f"\n❌ 触发失败：{e}")

if __name__ == '__main__':
    main()
