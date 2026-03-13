#!/usr/bin/env python3
"""
Agent 错误处理器

功能:
- 统一错误处理装饰器
- 错误自动分类 (P0/P1/P2/P3)
- 自动写入错误日志
- 自动写入问题队列
- P0 错误立即触发 Manager
"""

import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from functools import wraps
from issue_queue import IssueQueue, report_issue


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.error_log_dir = Path('./logs/errors/')
        self.error_log_dir.mkdir(parents=True, exist_ok=True)
        self.issue_queue = IssueQueue()
        self.consecutive_errors = 0
    
    def classify_error(self, error: Exception) -> str:
        """
        分类错误严重性
        
        P0: 系统崩溃、数据丢失、连续失败 3 次+
        P1: TypeError, KeyError, ImportError 等功能异常
        P2: Timeout, 网络错误等性能问题
        P3: Warning, 配置建议等
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # P0: 系统崩溃、数据丢失
        if error_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError']:
            return 'P0'
        if 'data loss' in error_msg or 'corruption' in error_msg:
            return 'P0'
        if self.consecutive_errors >= 3:
            return 'P0'
        
        # P1: 功能异常
        if error_type in ['TypeError', 'KeyError', 'IndexError', 'AttributeError', 
                         'ImportError', 'ModuleNotFoundError', 'NameError']:
            return 'P1'
        
        # P2: 性能问题
        if error_type in ['TimeoutError', 'ConnectionError', 'Timeout', 
                         'ConnectionRefusedError', 'ConnectionResetError']:
            return 'P2'
        if 'timeout' in error_msg or 'connection' in error_msg:
            return 'P2'
        
        # P3: 警告
        return 'P3'
    
    def log_error(self, error: Exception, severity: str, 
                 context: Optional[Dict] = None):
        """写入错误日志"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.error_log_dir / f"errors_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'agent': self.agent_name,
            'severity': severity,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'context': context or {},
            'consecutive_errors': self.consecutive_errors,
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_data, ensure_ascii=False) + '\n')
    
    def handle_error(self, error: Exception, context: Optional[Dict] = None):
        """处理错误"""
        # 分类
        severity = self.classify_error(error)
        
        # 记录日志
        self.log_error(error, severity, context)
        
        # 更新连续错误计数
        if severity in ['P0', 'P1']:
            self.consecutive_errors += 1
        else:
            self.consecutive_errors = 0
        
        # 写入问题队列
        issue_id = report_issue(
            agent=self.agent_name,
            severity=severity,
            error_type=type(error).__name__,
            error_message=str(error)
        )
        
        # P0 错误立即触发 Manager
        if severity == 'P0':
            self.trigger_manager_immediately(issue_id, error)
        
        return {
            'status': 'error',
            'severity': severity,
            'issue_id': issue_id,
            'error': str(error),
        }
    
    def trigger_manager_immediately(self, issue_id: str, error: Exception):
        """P0 错误立即触发 Manager"""
        # 这里可以通过 OpenClaw API 或消息队列触发 Manager
        # 简化实现：写入紧急触发文件
        trigger_file = Path('./issues/pending/P0_TRIGGER.json')
        trigger_data = {
            'type': 'P0_emergency',
            'issue_id': issue_id,
            'agent': self.agent_name,
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'action_required': 'immediate_response'
        }
        with open(trigger_file, 'w', encoding='utf-8') as f:
            json.dump(trigger_data, f, ensure_ascii=False, indent=2)
    
    def reset_counter(self):
        """重置连续错误计数（成功执行后调用）"""
        self.consecutive_errors = 0


def with_error_handling(agent_name: str):
    """
    错误处理装饰器
    
    用法:
    @with_error_handling('daily_stock_selection')
    def my_function():
        # 业务逻辑
        pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(agent_name)
            try:
                result = func(*args, **kwargs)
                handler.reset_counter()
                return {'status': 'success', 'result': result}
            except Exception as e:
                return handler.handle_error(e, {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                })
        return wrapper
    return decorator


# 使用示例
if __name__ == '__main__':
    # 测试错误处理
    handler = ErrorHandler('test_agent')
    
    # 测试 P1 错误
    try:
        result = None > 5  # TypeError
    except Exception as e:
        result = handler.handle_error(e)
        print(f"P1 错误处理：{result['severity']} - {result['issue_id']}")
    
    # 测试 P2 错误
    try:
        raise TimeoutError("Connection timeout")
    except Exception as e:
        result = handler.handle_error(e)
        print(f"P2 错误处理：{result['severity']} - {result['issue_id']}")
    
    # 测试装饰器
    @with_error_handling('decorated_agent')
    def test_function():
        return "Success"
    
    result = test_function()
    print(f"装饰器测试：{result['status']}")
