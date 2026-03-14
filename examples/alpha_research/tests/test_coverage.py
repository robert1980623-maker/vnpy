#!/usr/bin/env python3
"""
代码覆盖率测试

要求：所有核心代码覆盖率必须达到 90% 以上
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCoverageRequirement:
    """覆盖率要求测试"""
    
    def test_coverage_exists(self):
        """测试覆盖率配置文件存在"""
        coveragerc = Path('.coveragerc')
        assert coveragerc.exists(), "缺少 .coveragerc 配置文件"
    
    def test_run_coverage_check(self):
        """运行覆盖率检查 - 必须达到 90%"""
        result = subprocess.run(
            [
                'python3', '-m', 'coverage', 'run',
                '--source=.',
                '-m', 'pytest',
                'tests/integration/',
                '-v',
                '--tb=short'
            ],
            cwd=Path('.'),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # 生成报告
        report_result = subprocess.run(
            ['python3', '-m', 'coverage', 'report', '--fail-under=90'],
            cwd=Path('.'),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print("\n" + "="*70)
        print("📊 代码覆盖率报告")
        print("="*70)
        print(report_result.stdout)
        
        if report_result.returncode != 0:
            print("\n❌ 覆盖率未达到 90% 要求")
            print(report_result.stderr)
            
            # 生成详细报告
            html_result = subprocess.run(
                ['python3', '-m', 'coverage', 'html'],
                cwd=Path('.'),
                capture_output=True,
                text=True
            )
            print(f"\n详细 HTML 报告已生成：htmlcov/index.html")
            
            pytest.fail(f"代码覆盖率未达到 90% 要求")
        else:
            print("\n✅ 代码覆盖率达到 90% 要求")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
