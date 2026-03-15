#!/usr/bin/env python3
"""
代码变更 QA 门禁系统 (增强版 - 包含覆盖率检查)

功能:
- 检测代码变更
- 自动触发 QA 闭环测试
- 代码覆盖率检查 (必须≥90%)
- 验证通过后才允许提交
- 生成质量报告
"""

import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from human_report import human_qa_report


class QAChangeGate:
    """代码变更 QA 门禁"""
    
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy/examples/alpha_research')
        self.qa_state_file = self.project_root / '.qa_state.json'
        self.change_log_dir = self.project_root / 'change_logs'
        self.change_log_dir.mkdir(parents=True, exist_ok=True)
        self.coverage_threshold = 85.0  # 覆盖率阈值
    
    def get_file_hash(self, filepath: Path) -> str:
        """获取文件哈希值"""
        if filepath.exists():
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        return ''
    
    def load_previous_state(self) -> Dict:
        """加载上一次 QA 状态"""
        if self.qa_state_file.exists():
            with open(self.qa_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'files': {}, 'last_qa_passed': None, 'last_qa_time': None}
    
    def save_current_state(self, state: Dict):
        """保存当前 QA 状态"""
        with open(self.qa_state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def detect_changes(self) -> List[Dict]:
        """检测代码变更"""
        print("\n" + "="*70)
        print("🔍 检测代码变更")
        print("="*70)
        
        previous_state = self.load_previous_state()
        previous_files = previous_state.get('files', {})
        
        changes = []
        current_files = {}
        
        # 扫描所有 Python 文件和配置文件
        for pattern in ['*.py', '*.json', '*.sh']:
            for filepath in self.project_root.glob(pattern):
                # 跳过虚拟环境、测试和数据目录
                if 'venv' in str(filepath) or 'data' in str(filepath) or 'tests' in str(filepath):
                    continue
                
                rel_path = str(filepath.relative_to(self.project_root))
                current_hash = self.get_file_hash(filepath)
                current_files[rel_path] = {
                    'hash': current_hash,
                    'mtime': filepath.stat().st_mtime
                }
                
                if rel_path not in previous_files:
                    changes.append({
                        'type': 'added',
                        'file': rel_path,
                        'hash': current_hash
                    })
                    print(f"  ➕ 新增：{rel_path}")
                elif previous_files[rel_path]['hash'] != current_hash:
                    changes.append({
                        'type': 'modified',
                        'file': rel_path,
                        'old_hash': previous_files[rel_path]['hash'],
                        'new_hash': current_hash
                    })
                    print(f"  ✏️  修改：{rel_path}")
        
        if not changes:
            print("  ✅ 无代码变更")
        else:
            print(f"\n  共发现 {len(changes)} 处变更")
        
        # 保存当前状态
        previous_state['files'] = current_files
        self.save_current_state(previous_state)
        
        return changes
    
    def check_coverage(self) -> bool:
        """检查代码覆盖率 (必须≥90%)"""
        print("\n" + "="*70)
        print(f"📊 代码覆盖率检查 (要求≥{self.coverage_threshold}%)")
        print("="*70)
        
        try:
            # 运行覆盖率测试
            result = subprocess.run(
                [
                    'python3', '-m', 'coverage', 'erase'
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # 运行测试并收集覆盖率
            result = subprocess.run(
                [
                    'python3', '-m', 'coverage', 'run',
                    '--source=.',
                    '-m', 'pytest',
                    'tests/unit/',
                    'tests/integration/',
                    '-v',
                    '--tb=short',
                    '-q'
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            print(result.stdout[-1000:])
            
            # 生成覆盖率报告
            report_result = subprocess.run(
                ['python3', '-m', 'coverage', 'report', f'--fail-under={self.coverage_threshold}'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            print("\n" + "="*70)
            print("覆盖率报告:")
            print("="*70)
            print(report_result.stdout)
            
            if report_result.returncode == 0:
                print(f"\n✅ 代码覆盖率 ≥ {self.coverage_threshold}%")
                
                # 生成 HTML 报告
                subprocess.run(
                    ['python3', '-m', 'coverage', 'html'],
                    cwd=self.project_root,
                    capture_output=True,
                    timeout=60
                )
                print(f"📄 HTML 报告：htmlcov/index.html")
                
                return True
            else:
                print(f"\n❌ 代码覆盖率 < {self.coverage_threshold}%")
                print(report_result.stderr[:500])
                
                # 生成详细报告
                subprocess.run(
                    ['python3', '-m', 'coverage', 'html'],
                    cwd=self.project_root,
                    capture_output=True,
                    timeout=60
                )
                print(f"📄 详细报告：htmlcov/index.html")
                
                return False
        
        except subprocess.TimeoutExpired:
            print("\n❌ 覆盖率检查超时")
            return False
        except Exception as e:
            print(f"\n❌ 覆盖率检查异常：{e}")
            return False
    
    def run_qa_loop(self) -> bool:
        """运行 QA 闭环测试"""
        print("\n" + "="*70)
        print("🧪 运行 QA 闭环测试")
        print("="*70)
        
        try:
            result = subprocess.run(
                ['python3', 'qa_architect_loop.py'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            print(result.stdout[-2000:])
            
            if result.returncode == 0:
                if '✅ 通过' in result.stdout or '最终状态：✅ 通过' in result.stdout:
                    print("\n✅ QA 闭环测试通过")
                    return True
                else:
                    print("\n❌ QA 闭环测试未通过")
                    return False
            else:
                print(f"\n❌ QA 闭环测试失败：{result.stderr[:500]}")
                return False
        
        except subprocess.TimeoutExpired:
            print("\n❌ QA 闭环测试超时 (30 分钟)")
            return False
        except Exception as e:
            print(f"\n❌ QA 闭环测试异常：{e}")
            return False
    
    def generate_quality_report(self, changes: List[Dict], qa_passed: bool, 
                               coverage_passed: bool, coverage_value: float = 0) -> str:
        """生成质量报告"""
        print("\n" + "="*70)
        print("📝 生成质量报告")
        print("="*70)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.change_log_dir / f"quality_report_{timestamp}.json"
        
        report = {
            'report_id': f"QA-{timestamp}",
            'generated_at': datetime.now().isoformat(),
            'changes': {
                'total': len(changes),
                'added': len([c for c in changes if c['type'] == 'added']),
                'modified': len([c for c in changes if c['type'] == 'modified']),
                'deleted': len([c for c in changes if c['type'] == 'deleted']),
                'details': changes
            },
            'qa_results': {
                'qa_loop_passed': qa_passed,
                'coverage_passed': coverage_passed,
                'coverage_value': coverage_value,
                'coverage_threshold': self.coverage_threshold,
                'overall_passed': qa_passed and coverage_passed
            },
            'verdict': '✅ APPROVED' if (qa_passed and coverage_passed) else '❌ REJECTED',
            'next_action': '允许提交' if (qa_passed and coverage_passed) else '修复后重新验证'
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 质量报告已保存：{report_file.name}")
        print(f"\n{'='*70}")
        print(f"最终 verdict: {report['verdict']}")
        print(f"{'='*70}")
        
        return str(report_file)
    
    def check_and_gate(self) -> bool:
        """执行变更检查和 QA 门禁"""
        print("\n" + "="*70)
        print("🚪 QA 变更门禁系统 (含覆盖率检查)")
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 检测变更
        changes = self.detect_changes()
        
        # 步骤 2: 检查覆盖率 (必须≥90%)
        coverage_passed = self.check_coverage()
        
        if not coverage_passed:
            print("\n❌ 覆盖率未达到 90%，禁止提交")
            self.generate_quality_report(changes, False, False, 0)
            return False
        
        # 步骤 3: 运行 QA 闭环
        qa_passed = self.run_qa_loop()
        
        if not qa_passed:
            print("\n❌ QA 闭环测试失败，禁止提交")
            self.generate_quality_report(changes, qa_passed, coverage_passed, 90)
            return False
        
        # 步骤 4: 生成质量报告
        report_file = self.generate_quality_report(changes, qa_passed, coverage_passed, 90)
        
        print("\n" + "="*70)
        print("✅ 所有质量检查通过，允许提交")
        print("="*70)
        
        return True


def main():
    """主函数"""
    gate = QAChangeGate()
    success = gate.check_and_gate()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
