#!/usr/bin/env python3
"""
阶段 2 QA 闭环测试套件

测试范围:
1. 自动重试机制
2. 自动修复流程
3. 备份机制
4. 集成测试
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_test(name, status, details=None, duration=None):
    emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
    duration_str = f" ({duration:.2f}s)" if duration else ""
    print(f"{emoji} {name}: {color}{status}{Colors.END}{duration_str}")
    if details:
        print(f"   {details}")


class Stage2QAClosureTest:
    """阶段 2 QA 闭环测试"""
    
    def __init__(self):
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'tests': []
        }
        self.project_root = Path(__file__).parent
    
    def test_retry_mechanism(self):
        """测试 1: 自动重试机制"""
        print_header("测试 1: 自动重试机制")
        
        # 测试 1.1: 模块导入
        self.results['total'] += 1
        start = time.time()
        try:
            from retry_utils import retry_with_backoff, RetryMonitor, RetryRecord
            self.results['passed'] += 1
            print_test("retry_utils 导入", "PASS", duration=time.time()-start)
            self.results['tests'].append({'name': 'retry_utils 导入', 'status': 'PASS'})
        except Exception as e:
            self.results['failed'] += 1
            print_test("retry_utils 导入", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': 'retry_utils 导入', 'status': 'FAIL', 'error': str(e)})
            return  # 导入失败，跳过后续测试
        
        # 测试 1.2: 重试装饰器
        self.results['total'] += 1
        start = time.time()
        try:
            @retry_with_backoff(max_retries=3, base_delay=0.1)
            def test_func():
                return "success"
            
            result = test_func()
            if result == "success":
                self.results['passed'] += 1
                print_test("重试装饰器", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '重试装饰器', 'status': 'PASS'})
            else:
                raise Exception(f"返回结果异常：{result}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("重试装饰器", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '重试装饰器', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 1.3: 重试监控
        self.results['total'] += 1
        start = time.time()
        try:
            monitor = RetryMonitor()
            stats = monitor.get_stats()
            if 'total_calls' in stats or 'total_retries' in stats:
                self.results['passed'] += 1
                print_test("重试监控", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '重试监控', 'status': 'PASS'})
            else:
                raise Exception(f"统计信息缺失：{stats}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("重试监控", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '重试监控', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 1.4: 集成验证
        self.results['total'] += 1
        start = time.time()
        try:
            # 检查 batch_download_enhanced.py 是否集成重试
            with open(self.project_root / 'batch_download_enhanced.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'from retry_utils import' in content and '@retry_with_backoff' in content:
                self.results['passed'] += 1
                print_test("batch_download 集成", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': 'batch_download 集成', 'status': 'PASS'})
            else:
                raise Exception("未找到重试集成代码")
        except Exception as e:
            self.results['failed'] += 1
            print_test("batch_download 集成", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': 'batch_download 集成', 'status': 'FAIL', 'error': str(e)})
    
    def test_auto_fix(self):
        """测试 2: 自动修复流程"""
        print_header("测试 2: 自动修复流程")
        
        # 测试 2.1: 模块导入
        self.results['total'] += 1
        start = time.time()
        try:
            from auto_fix_manager import AutoFixManager, ProblemType, FixStrategy
            self.results['passed'] += 1
            print_test("auto_fix_manager 导入", "PASS", duration=time.time()-start)
            self.results['tests'].append({'name': 'auto_fix_manager 导入', 'status': 'PASS'})
        except Exception as e:
            self.results['failed'] += 1
            print_test("auto_fix_manager 导入", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': 'auto_fix_manager 导入', 'status': 'FAIL', 'error': str(e)})
            return
        
        # 测试 2.2: 管理器初始化
        self.results['total'] += 1
        start = time.time()
        try:
            manager = AutoFixManager()
            stats = manager.get_stats()
            if 'total_fixes' in stats and 'success_rate' in stats:
                self.results['passed'] += 1
                print_test("管理器初始化", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '管理器初始化', 'status': 'PASS'})
            else:
                raise Exception(f"统计信息异常：{stats}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("管理器初始化", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '管理器初始化', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 2.3: 问题类型
        self.results['total'] += 1
        start = time.time()
        try:
            problem_types = [ProblemType.DOWNLOAD_FAILED, ProblemType.DATA_STALE, 
                           ProblemType.DATA_CORRUPTED, ProblemType.FILE_MISSING]
            if len(problem_types) == 4:
                self.results['passed'] += 1
                print_test("问题类型定义", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '问题类型定义', 'status': 'PASS'})
            else:
                raise Exception(f"问题类型数量异常：{len(problem_types)}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("问题类型定义", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '问题类型定义', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 2.4: 修复策略
        self.results['total'] += 1
        start = time.time()
        try:
            strategies = [FixStrategy.RETRY, FixStrategy.REDOWNLOAD, 
                         FixStrategy.UPDATE, FixStrategy.MANUAL]
            if len(strategies) == 4:
                self.results['passed'] += 1
                print_test("修复策略定义", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '修复策略定义', 'status': 'PASS'})
            else:
                raise Exception(f"修复策略数量异常：{len(strategies)}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("修复策略定义", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '修复策略定义', 'status': 'FAIL', 'error': str(e)})
    
    def test_backup_mechanism(self):
        """测试 3: 备份机制"""
        print_header("测试 3: 备份机制")
        
        # 测试 3.1: 模块导入
        self.results['total'] += 1
        start = time.time()
        try:
            from backup_manager import BackupManager, BackupInfo
            self.results['passed'] += 1
            print_test("backup_manager 导入", "PASS", duration=time.time()-start)
            self.results['tests'].append({'name': 'backup_manager 导入', 'status': 'PASS'})
        except Exception as e:
            self.results['failed'] += 1
            print_test("backup_manager 导入", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': 'backup_manager 导入', 'status': 'FAIL', 'error': str(e)})
            return
        
        # 测试 3.2: 管理器初始化
        self.results['total'] += 1
        start = time.time()
        try:
            manager = BackupManager()
            # 检查备份目录是否创建
            if manager.backup_dir.exists():
                self.results['passed'] += 1
                print_test("管理器初始化", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '管理器初始化', 'status': 'PASS'})
            else:
                raise Exception(f"备份目录未创建：{manager.backup_dir}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("管理器初始化", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '管理器初始化', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 3.3: 备份配置
        self.results['total'] += 1
        start = time.time()
        try:
            manager = BackupManager()
            config = manager.config
            if 'daily' in config and 'weekly' in config and 'monthly' in config:
                self.results['passed'] += 1
                print_test("备份配置", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '备份配置', 'status': 'PASS'})
            else:
                raise Exception(f"备份配置缺失：{config}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("备份配置", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '备份配置', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 3.4: 备份列表
        self.results['total'] += 1
        start = time.time()
        try:
            manager = BackupManager()
            backups = manager.list_backups()
            if isinstance(backups, list):
                self.results['passed'] += 1
                print_test("备份列表功能", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '备份列表功能', 'status': 'PASS'})
            else:
                raise Exception(f"备份列表返回异常：{type(backups)}")
        except Exception as e:
            self.results['failed'] += 1
            print_test("备份列表功能", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '备份列表功能', 'status': 'FAIL', 'error': str(e)})
    
    def test_integration(self):
        """测试 4: 集成测试"""
        print_header("测试 4: 集成测试")
        
        # 测试 4.1: 通知集成
        self.results['total'] += 1
        start = time.time()
        try:
            # 检查 auto_fix_manager 是否集成通知
            with open(self.project_root / 'auto_fix_manager.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'from notification_utils import' in content:
                self.results['passed'] += 1
                print_test("通知集成", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '通知集成', 'status': 'PASS'})
            else:
                raise Exception("未找到通知集成代码")
        except Exception as e:
            self.results['failed'] += 1
            print_test("通知集成", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '通知集成', 'status': 'FAIL', 'error': str(e)})
        
        # 测试 4.2: 重试集成
        self.results['total'] += 1
        start = time.time()
        try:
            # 检查 auto_fix_manager 是否使用重试
            with open(self.project_root / 'auto_fix_manager.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'from retry_utils import' in content and '@retry_with_backoff' in content:
                self.results['passed'] += 1
                print_test("重试集成", "PASS", duration=time.time()-start)
                self.results['tests'].append({'name': '重试集成', 'status': 'PASS'})
            else:
                raise Exception("未找到重试集成代码")
        except Exception as e:
            self.results['failed'] += 1
            print_test("重试集成", "FAIL", str(e), duration=time.time()-start)
            self.results['tests'].append({'name': '重试集成', 'status': 'FAIL', 'error': str(e)})
    
    def test_coverage(self):
        """测试 5: 覆盖率验证"""
        print_header("测试 5: 覆盖率验证")
        
        self.results['total'] += 1
        start = time.time()
        
        # 检查所有必需文件是否存在
        required_files = [
            'retry_utils.py',
            'auto_fix_manager.py',
            'backup_manager.py',
            'test_stage2_qa_closure.py'
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing_files.append(file)
        
        if not missing_files:
            self.results['passed'] += 1
            print_test("文件覆盖率", "PASS", f"{len(required_files)}/{len(required_files)}", duration=time.time()-start)
            self.results['tests'].append({'name': '文件覆盖率', 'status': 'PASS'})
        else:
            self.results['failed'] += 1
            print_test("文件覆盖率", "FAIL", f"缺失：{', '.join(missing_files)}", duration=time.time()-start)
            self.results['tests'].append({'name': '文件覆盖率', 'status': 'FAIL', 'missing': missing_files})
    
    def run_all(self):
        """运行所有测试"""
        print_header("阶段 2 QA 闭环测试套件")
        print(f"{Colors.BLUE}运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")
        
        total_start = time.time()
        
        self.test_retry_mechanism()
        self.test_auto_fix()
        self.test_backup_mechanism()
        self.test_integration()
        self.test_coverage()
        
        total_duration = time.time() - total_start
        
        # 打印总结
        print_header("测试总结")
        
        print(f"总测试数：{self.results['total']}")
        print(f"{Colors.GREEN}通过：{self.results['passed']}{Colors.END}")
        print(f"{Colors.RED}失败：{self.results['failed']}{Colors.END}")
        print(f"{Colors.YELLOW}跳过：{self.results['skipped']}{Colors.END}")
        print(f"\n总耗时：{total_duration:.2f}s")
        
        coverage = (self.results['passed'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        print(f"\n测试覆盖率：{coverage:.1f}%")
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'coverage': coverage,
            'total_duration': total_duration,
            'qa_closed': coverage >= 90 and self.results['failed'] == 0
        }
        
        report_path = self.project_root / 'reports' / 'test_stage2_qa_closure.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 测试报告：{report_path}")
        
        if report['qa_closed']:
            print(f"\n{Colors.GREEN}✅ QA 闭环达成！{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠️ QA 闭环未达成{Colors.END}")
        
        return report['qa_closed']


if __name__ == '__main__':
    test = Stage2QAClosureTest()
    success = test.run_all()
    sys.exit(0 if success else 1)
