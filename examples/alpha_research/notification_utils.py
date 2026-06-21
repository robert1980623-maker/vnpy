#!/usr/bin/env python3
"""
通知工具模块 v4 - 基于 OpenClaw message send 命令（飞书集成）

功能:
1. 使用 openclaw message send 发送消息到飞书群
2. 支持任务开始/完成/错误通知
3. 自动格式化消息内容
4. 无需 Webhook，直接使用 OpenClaw 渠道

版本更新:
- v4: 从企业微信迁移到飞书 (2026-03-21)
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

# 飞书群 ID
FEISHU_CHAT_ID = "oc_21ccc3d7355ceabbdfb1e027af5441e5"


class TaskNotifier:
    """任务通知器（v4 - 使用 openclaw message send 发送到飞书）"""
    
    def __init__(self, task_name: str, chat_id: str = None):
        """
        初始化通知器
        
        Args:
            task_name: 任务名称
            chat_id: 飞书群 ID
        """
        self.task_name = task_name
        self.chat_id = chat_id or FEISHU_CHAT_ID
        self.messages = []
    
    def send(self, status: str, title: str = None, content: str = None, 
             details: dict = None, emoji: str = None):
        """
        发送通知消息
        
        Args:
            status: 状态（success/error/warning/info）
            title: 消息标题
            content: 消息内容
            details: 详细信息字典
            emoji: 表情符号
        """
        # 默认表情
        emojis = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': '📋'
        }
        emoji = emoji or emojis.get(status, '📢')
        
        # 默认标题
        title = title or self.task_name
        
        # 构建消息
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 状态文本
        status_text = {
            'success': '执行成功',
            'error': '执行失败',
            'warning': '执行警告',
            'info': '执行通知'
        }.get(status, '执行通知')
        
        # 构建消息体
        message = f"{emoji} **{title}** - {status_text}\n"
        message += f"⏰ 时间：{now}\n"
        
        if content:
            message += f"\n{content}\n"
        
        if details:
            message += "\n📊 详细信息:\n"
            for key, value in details.items():
                message += f"· {key}: {value}\n"
        
        message += f"\n---\n_自动通知 by OpenClaw_"
        
        # 保存消息
        self.messages.append({
            'status': status,
            'title': title,
            'content': content,
            'details': details,
            'message': message,
            'timestamp': now
        })
        
        # 发送消息
        print(f"\n📤 发送通知到飞书群:")
        print("-" * 60)
        print(message)
        print("-" * 60)
        
        return self._send_via_openclaw(message)
    
    def _send_via_openclaw(self, message: str):
        """通过 openclaw message send 发送"""
        try:
            # 使用完整路径，避免 cron 环境中 PATH 问题
            import shutil
            openclaw_path = shutil.which('openclaw') or '/usr/local/bin/openclaw'
            
            cmd = [
                openclaw_path,
                'message',
                'send',
                '--channel', 'feishu',
                '--target', self.chat_id,
                '--message', message
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ 通知发送成功")
                return {'success': True}
            else:
                print(f"❌ 通知发送失败：{result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            print(f"❌ 异常：{e}")
            return {'success': False, 'error': str(e)}
    
    def send_success(self, title: str = None, content: str = None, details: dict = None):
        """发送成功通知"""
        return self.send('success', title, content, details, emoji='✅')
    
    def send_error(self, title: str = None, content: str = None, details: dict = None):
        """发送失败通知"""
        return self.send('error', title, content, details, emoji='❌')
    
    def send_warning(self, title: str = None, content: str = None, details: dict = None):
        """发送警告通知"""
        return self.send('warning', title, content, details, emoji='⚠️')
    
    def send_info(self, title: str = None, content: str = None, details: dict = None):
        """发送信息通知"""
        return self.send('info', title, content, details, emoji='📋')


def notify_task_start(task_name: str, details: dict = None):
    """发送任务开始通知"""
    notifier = TaskNotifier(task_name)
    return notifier.send_info(
        title=f"🚀 {task_name} 启动",
        content="任务开始执行...",
        details=details
    )


def notify_task_complete(task_name: str, details: dict = None):
    """发送任务完成通知"""
    notifier = TaskNotifier(task_name)
    return notifier.send_success(
        title=f"✅ {task_name} 完成",
        content="任务执行成功！",
        details=details
    )


def notify_task_error(task_name: str, error_msg: str, details: dict = None):
    """发送任务错误通知"""
    notifier = TaskNotifier(task_name)
    return notifier.send_error(
        title=f"❌ {task_name} 失败",
        content=f"错误信息：{error_msg}",
        details=details
    )


def send_to_group(message: str, chat_id: str = None):
    """直接发送消息到群"""
    notifier = TaskNotifier("自定义通知", chat_id)
    return notifier.send('info', content=message, emoji='📢')


if __name__ == "__main__":
    print("=" * 60)
    print("  通知工具模块 v4 测试（openclaw message send - 飞书）")
    print("=" * 60)
    
    # 测试 1: 任务开始
    notify_task_start("测试任务", {"测试 ID": "001"})
    
    # 测试 2: 任务完成
    notify_task_complete("测试任务", {"耗时": "5.2s", "结果": "成功"})
    
    # 测试 3: 自定义消息
    send_to_group("""
🧪 **通知系统测试 v4**

使用 openclaw message send 发送消息到飞书群。

✅ 测试项目:
· OpenClaw 命令调用
· 飞书群发送
· Markdown 格式

---
_测试完成_
    """)
    
    print("\n✅ 所有测试完成！")
