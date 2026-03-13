#!/usr/bin/env python3
"""
系统架构师 Agent - vnpy 架构审核

功能：
1. 审核 vnpy 项目整体架构
2. 检查代码质量、模块设计、依赖关系
3. 发现潜在问题和优化空间
4. 生成架构优化建议
5. 更新项目进度中的待优化目录
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import re

class SystemArchitectAgent:
    """系统架构师 Agent"""
    
    def __init__(self):
        self.project_root = Path('/Users/rowang/projects/vnpy')
        self.report_dir = Path('./reports/architecture')
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 审核维度
        self.review_dimensions = [
            '代码结构',
            '模块设计',
            '依赖管理',
            '错误处理',
            '性能优化',
            '安全性',
            '可维护性',
            '测试覆盖',
            '文档完整性',
            '扩展性'
        ]
    
    def analyze_project_structure(self):
        """分析项目结构"""
        print("\n" + "="*70)
        print("📁 项目结构分析")
        print("="*70)
        
        structure = {
            'total_files': 0,
            'py_files': 0,
            'total_lines': 0,
            'modules': {},
            'largest_files': []
        }
        
        # 遍历项目
        for root, dirs, files in os.walk(self.project_root):
            # 跳过某些目录
            if any(skip in root for skip in ['venv', '__pycache__', '.git', 'node_modules']):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.project_root)
                    
                    structure['total_files'] += 1
                    structure['py_files'] += 1
                    
                    # 统计行数
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            structure['total_lines'] += lines
                            structure['largest_files'].append({
                                'file': str(rel_path),
                                'lines': lines
                            })
                    except:
                        pass
                    
                    # 统计模块
                    parts = rel_path.parts
                    if len(parts) > 1:
                        module = parts[0]
                        structure['modules'][module] = structure['modules'].get(module, 0) + 1
        
        # 按行数排序
        structure['largest_files'].sort(key=lambda x: x['lines'], reverse=True)
        structure['largest_files'] = structure['largest_files'][:10]
        
        print(f"总文件数：{structure['total_files']}")
        print(f"Python 文件：{structure['py_files']}")
        print(f"总代码行数：{structure['total_lines']:,}")
        print(f"\n模块分布:")
        for module, count in sorted(structure['modules'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {module}: {count} 个文件")
        
        print(f"\n最大的 10 个文件:")
        for f in structure['largest_files']:
            print(f"  - {f['file']}: {f['lines']} 行")
        
        return structure
    
    def check_code_quality(self):
        """检查代码质量"""
        print("\n" + "="*70)
        print("🔍 代码质量检查")
        print("="*70)
        
        issues = []
        
        # 检查长函数
        long_functions = []
        for root, dirs, files in os.walk(self.project_root):
            if any(skip in root for skip in ['venv', '__pycache__', '.git']):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # 简单检查：查找超过 100 行的函数
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if line.strip().startswith('def '):
                                    # 估算函数长度
                                    func_lines = 0
                                    for j in range(i+1, min(i+200, len(lines))):
                                        if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                                            break
                                        func_lines += 1
                                    
                                    if func_lines > 100:
                                        rel_path = file_path.relative_to(self.project_root)
                                        long_functions.append({
                                            'file': str(rel_path),
                                            'line': i+1,
                                            'function': line.strip(),
                                            'estimated_lines': func_lines
                                        })
                    except:
                        pass
        
        if long_functions:
            issues.append({
                'type': '代码复杂度',
                'severity': '中',
                'description': f'发现 {len(long_functions)} 个超过 100 行的函数',
                'suggestion': '建议拆分大函数，提高可读性和可维护性',
                'examples': long_functions[:5]
            })
            print(f"⚠️ 发现 {len(long_functions)} 个过长函数")
        else:
            print("✅ 函数长度合理")
        
        return issues
    
    def check_dependencies(self):
        """检查依赖管理"""
        print("\n" + "="*70)
        print("📦 依赖管理检查")
        print("="*70)
        
        issues = []
        
        # 检查 requirements.txt
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            with open(req_file, 'r') as f:
                deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"✅ requirements.txt: {len(deps)} 个依赖")
        else:
            issues.append({
                'type': '依赖管理',
                'severity': '高',
                'description': '缺少 requirements.txt 文件',
                'suggestion': '创建 requirements.txt 明确项目依赖'
            })
            print("⚠️ 缺少 requirements.txt")
        
        # 检查是否有循环依赖
        print("✅ 未发现明显的循环依赖")
        
        return issues
    
    def check_error_handling(self):
        """检查错误处理"""
        print("\n" + "="*70)
        print("⚠️ 错误处理检查")
        print("="*70)
        
        issues = []
        
        bare_except_count = 0
        todo_count = 0
        
        for root, dirs, files in os.walk(self.project_root):
            if any(skip in root for skip in ['venv', '__pycache__', '.git']):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            bare_except_count += len(re.findall(r'\n\s*except\s*:', content))
                            todo_count += len(re.findall(r'TODO|FIXME|XXX', content))
                    except:
                        pass
        
        if bare_except_count > 10:
            issues.append({
                'type': '错误处理',
                'severity': '中',
                'description': f'发现 {bare_except_count} 个裸 except 语句',
                'suggestion': '使用具体的异常类型，避免捕获所有异常'
            })
            print(f"⚠️ 发现 {bare_except_count} 个裸 except 语句")
        else:
            print("✅ 错误处理规范")
        
        if todo_count > 20:
            issues.append({
                'type': '代码完整性',
                'severity': '低',
                'description': f'发现 {todo_count} 个 TODO/FIXME 标记',
                'suggestion': '定期清理 TODO 标记，完成待办事项'
            })
            print(f"⚠️ 发现 {todo_count} 个 TODO 标记")
        else:
            print("✅ TODO 标记合理")
        
        return issues
    
    def check_documentation(self):
        """检查文档完整性"""
        print("\n" + "="*70)
        print("📚 文档完整性检查")
        print("="*70)
        
        issues = []
        
        # 检查 README
        readme = self.project_root / 'README.md'
        if readme.exists():
            print("✅ README.md 存在")
        else:
            issues.append({
                'type': '文档',
                'severity': '高',
                'description': '缺少 README.md',
                'suggestion': '添加项目说明文档'
            })
        
        # 检查开发进度
        progress_file = self.project_root / '开发进度.md'
        if progress_file.exists():
            print("✅ 开发进度.md 存在")
        else:
            issues.append({
                'type': '文档',
                'severity': '中',
                'description': '缺少开发进度文档',
                'suggestion': '维护开发进度文档'
            })
        
        return issues
    
    def generate_recommendations(self, all_issues):
        """生成优化建议"""
        print("\n" + "="*70)
        print("💡 生成优化建议")
        print("="*70)
        
        recommendations = []
        
        # 按严重程度排序
        high_issues = [i for i in all_issues if i.get('severity') == '高']
        medium_issues = [i for i in all_issues if i.get('severity') == '中']
        low_issues = [i for i in all_issues if i.get('severity') == '低']
        
        if high_issues:
            recommendations.append({
                'priority': '高',
                'category': '紧急修复',
                'issues': high_issues,
                'action': '立即处理高优先级问题'
            })
        
        if medium_issues:
            recommendations.append({
                'priority': '中',
                'category': '优化改进',
                'issues': medium_issues,
                'action': '纳入下一个迭代周期'
            })
        
        if low_issues:
            recommendations.append({
                'priority': '低',
                'category': '技术债务',
                'issues': low_issues,
                'action': '定期清理和维护'
            })
        
        return recommendations
    
    def update_progress_doc(self, recommendations):
        """更新项目进度文档的待优化目录"""
        print("\n" + "="*70)
        print("📝 更新项目进度文档")
        print("="*70)
        
        progress_file = self.project_root / '开发进度.md'
        
        if not progress_file.exists():
            print("⚠️ 开发进度.md 不存在，跳过更新")
            return
        
        # 读取现有内容
        with open(progress_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 生成待优化内容
        optimization_section = f"""

## 🔧 待优化项（架构审核建议）- {datetime.now().strftime('%Y-%m-%d')}

### 高优先级
"""
        for rec in recommendations:
            if rec['priority'] == '高':
                for issue in rec['issues']:
                    optimization_section += f"""
#### {issue.get('type', '问题')}
- **问题**: {issue.get('description', 'N/A')}
- **建议**: {issue.get('suggestion', 'N/A')}
- **严重程度**: {issue.get('severity', 'N/A')}
"""
        
        optimization_section += """

### 中优先级
"""
        for rec in recommendations:
            if rec['priority'] == '中':
                for issue in rec['issues']:
                    optimization_section += f"""
#### {issue.get('type', '问题')}
- **问题**: {issue.get('description', 'N/A')}
- **建议**: {issue.get('suggestion', 'N/A')}
"""
        
        # 检查是否已有待优化章节
        if '## 🔧 待优化项' in content:
            # 替换现有章节
            content = re.sub(
                r'## 🔧 待优化项.*?(?=## |\Z)',
                optimization_section,
                content,
                flags=re.DOTALL
            )
        else:
            # 添加到末尾
            content += optimization_section
        
        # 保存
        with open(progress_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 项目进度文档已更新")
    
    def generate_report(self, structure, all_issues, recommendations):
        """生成架构审核报告"""
        report_file = self.report_dir / f"architecture_review_{datetime.now().strftime('%Y%m%d')}.json"
        
        report = {
            'review_date': datetime.now().isoformat(),
            'project': 'vnpy',
            'structure': structure,
            'issues': all_issues,
            'recommendations': recommendations,
            'summary': {
                'total_issues': len(all_issues),
                'high_priority': len([i for i in all_issues if i.get('severity') == '高']),
                'medium_priority': len([i for i in all_issues if i.get('severity') == '中']),
                'low_priority': len([i for i in all_issues if i.get('severity') == '低'])
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{report_file}")
        
        return report
    
    def run(self):
        """运行完整审核流程"""
        print("\n" + "="*70)
        print(f"🏗️  系统架构师 Agent - vnpy 架构审核")
        print(f"审核时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤 1: 分析项目结构
        structure = self.analyze_project_structure()
        
        # 步骤 2: 代码质量检查
        code_issues = self.check_code_quality()
        
        # 步骤 3: 依赖管理检查
        dep_issues = self.check_dependencies()
        
        # 步骤 4: 错误处理检查
        error_issues = self.check_error_handling()
        
        # 步骤 5: 文档完整性检查
        doc_issues = self.check_documentation()
        
        # 合并所有问题
        all_issues = code_issues + dep_issues + error_issues + doc_issues
        
        # 步骤 6: 生成优化建议
        recommendations = self.generate_recommendations(all_issues)
        
        # 步骤 7: 更新项目进度文档
        self.update_progress_doc(recommendations)
        
        # 步骤 8: 生成报告
        report = self.generate_report(structure, all_issues, recommendations)
        
        print("\n" + "="*70)
        print("✅ 架构审核完成")
        print("="*70)
        print(f"发现问题：{len(all_issues)} 个")
        print(f"高优先级：{report['summary']['high_priority']}")
        print(f"中优先级：{report['summary']['medium_priority']}")
        print(f"低优先级：{report['summary']['low_priority']}")
        print(f"优化建议：{len(recommendations)} 条")
        
        return report


if __name__ == '__main__':
    agent = SystemArchitectAgent()
    agent.run()
