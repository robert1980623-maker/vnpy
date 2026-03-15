#!/usr/bin/env python3
"""
无人值守模式辅助函数

用法:
    from non_interactive_helper import setup_non_interactive_mode
    
    # 在 argparse 配置中添加
    parser.add_argument('--non-interactive', action='store_true', 
                       help='无人值守模式：禁用所有交互式提示，使用默认值')
    
    # 在主函数中调用
    setup_non_interactive_mode(args.non_interactive)
"""

import os
import sys

def setup_non_interactive_mode(enabled: bool = False):
    """
    配置无人值守模式
    
    当启用时:
    1. 设置环境变量 NON_INTERACTIVE=1
    2. 禁用所有 input() 调用
    3. 使用默认配置而非询问用户
    4. 减少日志输出噪音
    """
    if enabled:
        os.environ['NON_INTERACTIVE'] = '1'
        print("🤖 已启用无人值守模式 (NON_INTERACTIVE=1)")
    else:
        os.environ['NON_INTERACTIVE'] = '0'


def is_non_interactive() -> bool:
    """检查是否处于无人值守模式"""
    return os.environ.get('NON_INTERACTIVE', '0') == '1'


def safe_input(prompt: str, default: str = None) -> str:
    """
    安全的 input 函数
    
    在无人值守模式下返回默认值，而非阻塞等待用户输入
    """
    if is_non_interactive():
        if default:
            print(f"⚠️  无人值守模式，使用默认值：{default}")
            return default
        else:
            raise ValueError(f"无人值守模式下需要输入：{prompt}")
    else:
        if default:
            return input(f"{prompt} [{default}]: ") or default
        else:
            return input(f"{prompt}: ")


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    安全的确认函数
    
    在无人值守模式下返回默认值
    """
    if is_non_interactive():
        print(f"⚠️  无人值守模式，自动确认：{default}")
        return default
    else:
        response = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").lower().strip()
        if not response:
            return default
        return response in ('y', 'yes')
