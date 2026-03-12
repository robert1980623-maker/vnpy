#!/usr/bin/env python3
"""
统一日志系统

功能:
1. 统一日志格式
2. 任务执行失败自动记录
3. 日志分级 (INFO/WARNING/ERROR/CRITICAL)
4. 日志轮转 (按天)
5. 异常堆栈追踪
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime
import sys
import traceback


class TaskLogger:
    """任务日志记录器"""
    
    def __init__(self, log_dir: str = './logs', task_name: str = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.task_name = task_name or 'unknown_task'
        self.task_id = f"{self.task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 日志文件
        today = datetime.now().strftime('%Y-%m-%d')
        self.log_file = self.log_dir / f"{today}.log"
        self.error_log_file = self.log_dir / f"errors_{today}.jsonl"
        
        # 配置日志
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志记录器"""
        self.logger = logging.getLogger(self.task_name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件 handler
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 控制台 handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # 格式
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def info(self, message: str, **kwargs):
        """记录 INFO 日志"""
        msg = f"{message} {json.dumps(kwargs, ensure_ascii=False) if kwargs else ''}"
        self.logger.info(msg)
    
    def warning(self, message: str, **kwargs):
        """记录 WARNING 日志"""
        msg = f"{message} {json.dumps(kwargs, ensure_ascii=False) if kwargs else ''}"
        self.logger.warning(msg)
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """记录 ERROR 日志"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'task_id': self.task_id,
            'task_name': self.task_name,
            'level': 'ERROR',
            'message': message,
            'kwargs': kwargs
        }
        
        if exception:
            error_data['exception_type'] = type(exception).__name__
            error_data['exception_message'] = str(exception)
            error_data['stack_trace'] = traceback.format_exc()
            msg = f"{message} - {type(exception).__name__}: {exception}"
        else:
            msg = message
        
        self.logger.error(msg)
        
        # 同时记录到错误日志文件 (JSONL 格式)
        self._write_error_log(error_data)
        
        return error_data
    
    def critical(self, message: str, exception: Exception = None, **kwargs):
        """记录 CRITICAL 日志"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'task_id': self.task_id,
            'task_name': self.task_name,
            'level': 'CRITICAL',
            'message': message,
            'kwargs': kwargs
        }
        
        if exception:
            error_data['exception_type'] = type(exception).__name__
            error_data['exception_message'] = str(exception)
            error_data['stack_trace'] = traceback.format_exc()
            msg = f"{message} - {type(exception).__name__}: {exception}"
        else:
            msg = message
        
        self.logger.critical(msg)
        
        # 同时记录到错误日志文件
        self._write_error_log(error_data)
        
        return error_data
    
    def _write_error_log(self, error_data: dict):
        """写入错误日志文件 (JSONL)"""
        with open(self.error_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_data, ensure_ascii=False) + '\n')
    
    def task_start(self, **kwargs):
        """记录任务开始"""
        self.info(f"🚀 任务开始：{self.task_name}", **kwargs)
    
    def task_end(self, success: bool = True, duration: float = None, **kwargs):
        """记录任务结束"""
        if success:
            emoji = "✅"
            level = 'info'
        else:
            emoji = "❌"
            level = 'error'
        
        msg = f"{emoji} 任务结束：{self.task_name}"
        if duration:
            msg += f" (耗时：{duration:.2f}s)"
        
        if level == 'info':
            self.info(msg, **kwargs)
        else:
            self.error(msg, **kwargs)
    
    def task_failed(self, exception: Exception, **kwargs):
        """记录任务失败"""
        return self.error(f"❌ 任务失败：{self.task_name}", exception=exception, **kwargs)


def log_task_execution(task_name: str):
    """任务执行日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = TaskLogger(task_name=task_name)
            start_time = datetime.now()
            
            try:
                logger.task_start()
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.task_end(success=True, duration=duration)
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.task_failed(e, duration=duration)
                raise
        return wrapper
    return decorator


# 快捷函数
def get_logger(task_name: str) -> TaskLogger:
    """获取日志记录器"""
    return TaskLogger(task_name=task_name)


def log_error(task_name: str, message: str, exception: Exception = None, **kwargs):
    """快捷记录错误"""
    logger = TaskLogger(task_name=task_name)
    return logger.error(message, exception=exception, **kwargs)


if __name__ == '__main__':
    # 测试
    logger = TaskLogger(task_name='test_task')
    logger.task_start()
    logger.info('测试 INFO')
    logger.warning('测试 WARNING')
    
    try:
        raise ValueError('测试错误')
    except Exception as e:
        logger.task_failed(e)
    
    logger.task_end(success=False)
