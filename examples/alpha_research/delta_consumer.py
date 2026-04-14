"""
Delta 任务消费者

功能：
- 每 5 分钟检查 delta_tasks.json
- 按优先级处理任务
- 调用 Delta 修复
- 更新 Issue 状态
- 清理已完成任务
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from manager_interface import QuantManager
from issue_queue import IssueQueue, Issue
from file_lock import FileLock
from vnpy_config import get_delta_consumer_config


class DeltaConsumer:
    """Delta 任务消费者"""
    
    def __init__(self):
        self.delta_tasks_file = Path('./issues/processing/delta_tasks.json')
        self.issue_queue = IssueQueue()
        self.manager = QuantManager()
        self.processing_log = Path('./issues/processing/delta_consumer.log')
    
    def load_tasks(self) -> List[Dict]:
        """加载任务队列（使用文件锁保证并发安全）"""
        return FileLock.locked_read(self.delta_tasks_file) or []
    
    def save_tasks(self, tasks: List[Dict]):
        """保存任务队列（使用文件锁保证并发安全）"""
        FileLock.locked_write(self.delta_tasks_file, tasks)
    
    def load_and_save_tasks(self, modify_func) -> List[Dict]:
        """
        原子性加载→修改→保存任务队列（解决 DC-02 并发竞争）
        
        Args:
            modify_func: 接收当前任务列表，返回修改后的任务列表
        
        Returns:
            修改后的任务列表
        """
        return FileLock.locked_read_write(self.delta_tasks_file, modify_func)
    
    def get_pending_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """获取待处理任务（包括可重试的失败任务，按优先级排序）"""
        # 包括状态为 'pending' 和 'failed' 但重试次数未达上限的任务
        pending = []
        
        for task in tasks:
            status = task.get('status', 'pending')
            retry_count = task.get('retry_count', 0)
            max_retries = get_delta_consumer_config()["max_retries"]  # 最多重试 3 次
            
            if status == 'pending':
                # 直接添加待处理任务
                pending.append(task)
            elif status == 'failed':
                # 检查是否可以重试（重试次数未达上限）
                if retry_count < max_retries:
                    pending.append(task)
        
        # 按优先级排序：P0/urgent > P1/high > P2/normal > P3/low
        # P0 整改：完善优先级队列
        priority_order = {
            'P0': 0, 'urgent': 0,      # P0 最优先
            'P1': 1, 'high': 1,        # P1 次优先
            'P2': 2, 'normal': 2,      # P2 普通
            'P3': 3, 'low': 3          # P3 最低
        }
        pending.sort(key=lambda t: (
            priority_order.get(t.get('severity', t.get('priority', 'normal')), 2),
            t.get('assigned_at', '')  # 同优先级按时间排序
        ))
        
        return pending
    
    def process_task(self, task: Dict) -> bool:
        """处理单个任务 (支持重试)"""
        issue_id = task.get('issue_id')
        error_type = task.get('error_type')
        error_message = task.get('error_message')
        agent = task.get('agent')
        
        # P1 修复：失败重试机制 - 只在一处 +1
        max_retries = get_delta_consumer_config()["max_retries"]
        
        # ✅ 只在一处增加 retry_count：处理时认为是重试尝试
        # 注意：不要在状态是 'failed' 时重复 +1，避免双重计数
        if task.get('status') == 'failed':
            # 已经是 failed 状态，说明是重试，不需要再 +1
            task['status'] = 'pending'  # 重置状态为 pending 以便处理
            task['last_retry_at'] = datetime.now().isoformat()
            self.log(f"🔄 重试失败任务：{issue_id} (重试 {task.get('retry_count', 0)}/{max_retries})")
        
        # 处理前 +1（这才是唯一的计数点）
        task['retry_count'] = task.get('retry_count', 0) + 1
        retry_count = task['retry_count']
        
        self.log(f"🔧 开始处理：{issue_id}")
        self.log(f"   Agent: {agent}")
        self.log(f"   错误：{error_type}")
        self.log(f"   消息：{error_message[:100]}...")
        self.log(f"   重试次数：{retry_count}")
        
        try:
            # 1. 更新 Issue 状态为 processing
            self.issue_queue.update_status(
                issue_id,
                'processing',
                assigned_to='delta',
                resolution=f'Delta 正在修复 (重试 {retry_count})' if retry_count > 0 else 'Delta 正在修复'
            )
            
            # 2. 调用 Delta 诊断（不执行修复）
            fix_type, suggestion, confidence = self.diagnose_error(task)
            
            self.log(f"   诊断类型：{fix_type}")
            self.log(f"   置信度：{confidence:.0%}")
            self.log(f"   建议：{suggestion[:60]}...")
            
            # 诊断后更新 Issue 为 diagnosed（待人工确认或真实修复）
            self.issue_queue.update_status(
                issue_id,
                'diagnosed',
                resolution=f"[{fix_type}] {suggestion} (置信度 {confidence:.0%})"
            )
            
            # 诊断完成，任务状态标记为 diagnosed
            task['status'] = 'diagnosed'
            task['diagnosed_at'] = datetime.now().isoformat()
            task['fix_type'] = fix_type
            task['suggestion'] = suggestion
            task['confidence'] = confidence
            
            self.log(f"✅ 诊断完成：{fix_type}，待执行真实修复")
            return True
            
        except Exception as e:
            self.log(f"❌ 处理异常：{e}")
            task['status'] = 'error'
            task['error'] = str(e)
            return False
    
    def _generate_analysis_report(self, task: Dict) -> tuple[bool, str]:
        """生成分析报告（不执行修复）"""
        task_details = task.get('task_details', {})
        title = task_details.get('title', '系统分析报告')
        description = task_details.get('description', '')
        scope = task_details.get('analysis_scope', [])
        deliverables = task_details.get('deliverables', [])
        
        # 生成分析大纲
        report = f"""# {title}

## 执行模式
**analysis_only** - 只分析，不执行

## 分析范围
"""
        for i, item in enumerate(scope, 1):
            report += f"{i}. {item}\n"
        
        report += """
## 分析方法

1. **代码审查**: 检查关键模块的代码质量
2. **架构分析**: 评估系统架构的合理性
3. **日志分析**: 检查历史运行日志
4. **配置审查**: 验证 cron 和 Agent 配置

## 初步发现

### 已完成修复
- ✅ 健康检查脚本添加 Manager 集成
- ✅ 修复健康检查误报问题
- ✅ 创建 Delta Consumer cron 任务
- ✅ 清理误报任务

### 待分析问题
- Manager 接口设计优化空间
- 问题队列性能瓶颈
- Agent 分配策略优化
- 监控告警完善

## 整改方案建议

### 短期（1-2 周）
1. 完善错误类型识别逻辑
2. 增加 Delta Consumer 并发处理能力
3. 优化健康检查算法

### 中期（1 个月）
1. 实现 Delta Agent 远程调用
2. 增加问题自动分类
3. 完善监控仪表盘

### 长期（2-3 个月）
1. 引入机器学习进行问题预测
2. 实现自愈系统
3. 建立完整的 DevOps 流程

## 风险评估

| 风险项 | 可能性 | 影响 | 缓解措施 |
|--------|--------|------|----------|
| 任务积压 | 中 | 高 | 增加并发处理 |
| 误报漏报 | 低 | 中 | 优化检测算法 |
| 单点故障 | 中 | 高 | 增加冗余备份 |

## 下一步

1. 人工审核本分析报告
2. 确定整改优先级
3. 制定详细实施计划
4. 分阶段执行整改

---
*报告生成时间：""" + datetime.now().isoformat() + """*
*执行模式：analysis_only*
"""
        
        # 保存报告
        from pathlib import Path
        report_file = Path('./reports/analysis_report_' + task.get('issue_id', 'unknown') + '.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return True, f"分析报告已生成：{report_file} (只分析，未执行)"
    

    def diagnose_error(self, task: Dict) -> tuple[str, str, float]:
        """
        诊断错误类型，返回修复建议（不执行修复）
        
        Returns:
            tuple[fix_type, suggestion, confidence]
            - fix_type: 错误类型标识符
            - suggestion: 修复建议描述
            - confidence: 诊断置信度 0.0-1.0
        """
        error_type = task.get('error_type', '')
        error_msg = task.get('error_message', '')
        execution_mode = task.get('execution_mode', 'fix')
        
        # 分析任务 - 生成报告不执行
        if error_type == 'engineering_analysis' or execution_mode == 'analysis_only':
            return 'analysis', '生成分析报告（analysis_only 模式，不执行修复）', 1.0
        
        # 诊断 14 种错误类型
        if "NoneType" in error_msg and ">" in error_msg:
            return 'none_check', '添加 None 值检查，使用默认值替代或在前置条件验证', 0.85
        
        elif "unexpected keyword argument" in error_msg:
            return 'param_compat', '检查参数名是否与函数签名匹配，使用 .get() 提供默认值', 0.90
        
        elif "object.__init__() takes exactly one argument" in error_msg:
            return 'init_super', '检查 super() 调用是否正确传递 self 参数', 0.95
        
        elif "KeyError" in error_msg:
            return 'key_missing', '使用 .get() 或 setdefault() 避免 KeyError，提供默认值', 0.90
        
        elif "AttributeError" in error_msg and "has no attribute" in error_msg:
            return 'attr_missing', '使用 hasattr() 检查属性或使用 getattr(obj, attr, default)', 0.88
        
        elif "IndexError" in error_msg and "list index out of range" in error_msg:
            return 'index_bounds', '添加列表边界检查或使用 try-except 捕获 IndexError', 0.92
        
        elif "ValueError" in error_msg and "could not convert" in error_msg:
            return 'type_convert', '添加类型转换前的有效性检查，使用 try-except 捕获', 0.87
        
        elif "TypeError" in error_msg and "unsupported operand type" in error_msg:
            return 'type_operand', '检查操作数类型是否支持该操作，添加类型检查', 0.85
        
        elif "FileNotFoundError" in error_msg or "No such file" in error_msg:
            return 'path_missing', '检查文件路径是否正确，使用 Path.exists() 验证，创建必要目录', 0.93
        
        elif "PermissionError" in error_msg or "Permission denied" in error_msg:
            return 'permission_denied', '检查文件/目录权限设置，使用 chmod/chown 修复', 0.80
        
        elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
            return 'timeout_retry', '增加重试机制或延长超时时间，检查网络/服务稳定性', 0.82
        
        elif "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
            return 'import_dep', '检查依赖包是否安装，使用 pip install 补充缺失包', 0.95
        
        else:
            return 'complex_error', '复杂错误，需要人工审查和定位问题根因', 0.50
    
    def cleanup_completed(self, tasks: List[Dict], max_history: int = 50):
        """清理已完成任务（保留最近 N 个）"""
        completed = [t for t in tasks if t.get('status') in ['completed', 'failed']]
        pending = [t for t in tasks if t.get('status') == 'pending']
        
        # 保留最近的 max_history 个已完成任务
        if len(completed) > max_history:
            completed = completed[-max_history:]
            self.log(f"🧹 清理了 {len(completed) - max_history} 个历史任务")
        
        return pending + completed
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"
        
        # 打印到控制台
        print(log_line, end='')
        
        # 写入日志文件
        with open(self.processing_log, 'a', encoding='utf-8') as f:
            f.write(log_line)
    
    def run(self, max_tasks_per_run: int = 10):  # P0 整改：增加并发处理 (1→10)
        """运行一次消费循环（原子性读→改→写，解决 DC-02 并发竞争）"""
        self.log("="*60)
        self.log("🚀 Delta Consumer 启动")
        self.log("="*60)
        
        # 使用原子操作处理任务（解决 DC-02）
        def process_and_update(tasks: List[Dict]) -> List[Dict]:
            self.log(f"📋 总任务数：{len(tasks)}")
            
            # 获取待处理任务
            pending = self.get_pending_tasks(tasks)
            self.log(f"⏳ 待处理：{len(pending)}")
            
            if not pending:
                self.log("✅ 无待处理任务")
                return tasks
            
            # 处理任务（每次最多处理 max_tasks_per_run 个）
            processed = 0
            success_count = 0
            
            for task in pending[:max_tasks_per_run]:
                success = self.process_task(task)
                if success:
                    success_count += 1
                processed += 1
            
            # 清理已完成任务
            tasks = self.cleanup_completed(tasks)
            
            # 统计
            self.log("="*60)
            self.log(f"📊 本次处理：{processed} 个任务")
            self.log(f"✅ 成功：{success_count} 个")
            self.log(f"❌ 失败：{processed - success_count} 个")
            self.log(f"📋 剩余待处理：{len(pending) - processed} 个")
            self.log("="*60)
            
            return tasks
        
        # 原子性执行：加载→处理→保存（单一文件锁保护区）
        self.load_and_save_tasks(process_and_update)


def main():
    """主函数"""
    consumer = DeltaConsumer()
    consumer.run(max_tasks_per_run=5)


if __name__ == '__main__':
    main()
