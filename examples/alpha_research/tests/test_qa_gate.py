#!/usr/bin/env python3
"""
QA 门禁测试

在代码变更或 Manager 任务更新时自动运行，确保质量

用法:
    python3 tests/test_qa_gate.py
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


class QAGateTester:
    """QA 门禁测试器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = []
    
    def run_test(self, test_file: str) -> dict:
        """运行单个测试"""
        print(f"\n🧪 运行测试：{test_file}")
        print("-" * 70)
        
        try:
            result = subprocess.run(
                ['python3', test_file],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            passed = result.returncode == 0
            
            return {
                'test': test_file,
                'passed': passed,
                'returncode': result.returncode,
                'output': result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
                'error': result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
            }
        
        except subprocess.TimeoutExpired:
            return {
                'test': test_file,
                'passed': False,
                'returncode': -1,
                'error': '测试超时 (5 分钟)'
            }
        except Exception as e:
            return {
                'test': test_file,
                'passed': False,
                'returncode': -1,
                'error': str(e)
            }
    
    def run_all_tests(self):
        """运行所有 QA 测试"""
        print("\n" + "=" * 70)
        print("🔒 QA 门禁检查")
        print("=" * 70)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 测试列表
        tests = [
            'tests/test_manager_closed_loop.py',
        ]
        
        # 运行测试
        results = []
        for test in tests:
            result = self.run_test(test)
            results.append(result)
        
        # 统计
        passed_count = len([r for r in results if r['passed']])
        total_count = len(results)
        pass_rate = passed_count / total_count * 100 if total_count > 0 else 0
        
        # 报告
        print("\n" + "=" * 70)
        print("📊 QA 测试报告")
        print("=" * 70)
        print(f"\n总览:")
        print(f"  通过：{passed_count}/{total_count}")
        print(f"  通过率：{pass_rate:.1f}%")
        print()
        
        for result in results:
            status = "✅ 通过" if result['passed'] else "❌ 失败"
            print(f"  {status}: {result['test']}")
        
        print("\n" + "=" * 70)
        
        # 结论
        if pass_rate == 100:
            print("🎉 所有测试通过，可以发布！")
            return True
        else:
            print("⚠️  有测试失败，请修复后再发布！")
            return False


if __name__ == '__main__':
    tester = QAGateTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
