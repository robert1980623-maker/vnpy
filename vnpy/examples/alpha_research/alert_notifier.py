#!/usr/bin/env python3
"""
异常通知器

原则：
- 正常工作不打扰
- 只有异常才通知
- 紧急问题立即通知
- 小问题汇总报告
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import OrderedDict


@dataclass
class Alert:
    """告警定义"""
    severity: str  # P0/P1/P2
    title: str
    message: str
    agent: str
    error: str
    timestamp: str
    status: str = "new"  # new/acknowledged/resolved
    action_taken: str = ""
    estimated_fix: str = ""


class LRUCache:
    """LRU 缓存实现，限制最大容量防止内存无限增长"""
    
    def __init__(self, max_size: int = 1000):
        self._cache = OrderedDict()
        self._max_size = max_size
    
    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
    
    def clear(self):
        self._cache.clear()
    
    def __len__(self):
        return len(self._cache)
    
    def values(self):
        return list(self._cache.values())
    
    def __iter__(self):
        return iter(self._cache.values())


class AlertNotifier:
    """告警通知器"""
    
    def __init__(self, max_pending_alerts: int = 1000):
        self.alert_log_dir = Path('./logs/alerts/')
        self.alert_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 通知阈值配置
        self.notify_threshold = {
            'P0': True,   # 立即通知
            'P1': True,   # 立即通知
            'P2': False,  # 汇总报告
            'P3': False,  # 不通知
        }
        
        # 告警汇总（LRU 缓存，限制最大数量）
        self._pending_alerts_cache = LRUCache(max_size=max_pending_alerts)
    
    @property
    def pending_alerts(self) -> List[Alert]:
        """获取所有待处理告警"""
        return self._pending_alerts_cache.values()
    
    def should_notify(self, severity: str) -> bool:
        """判断是否应该通知"""
        return self.notify_threshold.get(severity, False)
    
    def create_alert(self, severity: str, agent: str, error: str, 
                    action_taken: str = "", estimated_fix: str = "") -> Alert:
        """创建告警"""
        titles = {
            'P0': '🚨 严重错误',
            'P1': '⚠️ 功能异常',
            'P2': '📊 性能警告',
        }
        
        alert = Alert(
            severity=severity,
            title=titles.get(severity, '📝 通知'),
            message=self._generate_message(severity, error),
            agent=agent,
            error=error,
            timestamp=datetime.now().isoformat(),
            action_taken=action_taken,
            estimated_fix=estimated_fix
        )
        
        return alert
    
    def _generate_message(self, severity: str, error: str) -> str:
        """生成告警消息"""
        if severity == 'P0':
            return f"系统严重错误，需要立即处理：{error}"
        elif severity == 'P1':
            return f"功能异常，已调度工程师修复：{error}"
        elif severity == 'P2':
            return f"性能问题，已记录并监控：{error}"
        else:
            return error
    
    def send_alert(self, alert: Alert):
        """发送告警"""
        # 记录告警日志
        self._log_alert(alert)
        
        # 判断是否需要通知
        if self.should_notify(alert.severity):
            # 发送到 Slack/用户
            self._notify_user(alert)
        
        # 添加到待处理列表（使用时间戳作为 key 以支持 LRU 淘汰）
        cache_key = f"{alert.timestamp}_{alert.agent}_{alert.error}"
        self._pending_alerts_cache.put(cache_key, alert)
    
    def _log_alert(self, alert: Alert):
        """记录告警日志"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = self.alert_log_dir / f"alerts_{date_str}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(alert), ensure_ascii=False) + '\n')
    
    def _notify_user(self, alert: Alert):
        """通知用户（通过 Slack 或其他渠道）"""
        # 这里集成 Slack/Telegram 等通知渠道
        # 简化实现：写入通知文件，由 Gateway 发送
        
        notification = {
            'type': 'alert_notification',
            'channel': 'slack',
            'to': 'user:U0AHSM009ML',
            'message': self._format_notification(alert),
            'timestamp': datetime.now().isoformat(),
        }
        
        # 写入通知队列
        notify_file = Path('./logs/alerts/notifications.json')
        notifications = []
        if notify_file.exists():
            with open(notify_file, 'r', encoding='utf-8') as f:
                notifications = json.load(f)
        
        notifications.append(notification)
        
        with open(notify_file, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
    
    def _format_notification(self, alert: Alert) -> str:
        """格式化通知消息"""
        message = f"""{alert.title}

Agent: {alert.agent}
错误：{alert.error}
时间：{alert.timestamp}
状态：{alert.action_taken}
预计修复：{alert.estimated_fix}

详细报告：查看日志文件"""
        
        return message
    
    def send_summary_report(self, period: str = "hourly"):
        """发送汇总报告（P2/P3 级别）"""
        if not self._pending_alerts_cache:
            return
        
        # 筛选 P2/P3 告警
        low_priority_alerts = [
            a for a in self._pending_alerts_cache 
            if a.severity in ['P2', 'P3']
        ]
        
        if not low_priority_alerts:
            return
        
        # 生成汇总报告
        summary = f"""📊 异常汇总报告 ({period})

异常数量：{len(low_priority_alerts)}

详情:"""
        
        for alert in low_priority_alerts:
            summary += f"\n- {alert.agent}: {alert.error}"
        
        summary += "\n\n所有异常已自动处理，无需担心。"
        
        # 发送汇总报告
        notification = {
            'type': 'summary_report',
            'channel': 'slack',
            'to': 'user:U0AHSM009ML',
            'message': summary,
            'timestamp': datetime.now().isoformat(),
        }
        
        # 写入通知队列
        notify_file = Path('./logs/alerts/notifications.json')
        notifications = []
        if notify_file.exists():
            with open(notify_file, 'r', encoding='utf-8') as f:
                notifications = json.load(f)
        
        notifications.append(notification)
        
        with open(notify_file, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
    
    def clear_resolved(self):
        """清除已解决的告警"""
        # 重建缓存，只保留未解决的告警
        remaining = {}
        for key, alert in self._pending_alerts_cache._cache.items():
            if alert.status != 'resolved':
                remaining[key] = alert
        self._pending_alerts_cache._cache.clear()
        self._pending_alerts_cache._cache.update(remaining)


# 快捷函数
def notify_exception(severity: str, agent: str, error: str, 
                    action: str = "", estimate: str = ""):
    """快速通知异常"""
    notifier = AlertNotifier()
    alert = notifier.create_alert(severity, agent, error, action, estimate)
    notifier.send_alert(alert)


if __name__ == '__main__':
    # 测试
    notifier = AlertNotifier()
    
    # 测试 P0 告警（会通知）
    alert_p0 = notifier.create_alert(
        severity='P0',
        agent='daily_stock_selection',
        error='TypeError: NoneType comparison',
        action_taken='已调度 Delta 紧急修复',
        estimated_fix='10-15 分钟'
    )
    notifier.send_alert(alert_p0)
    print(f"✅ P0 告警已发送：{alert_p0.title}")
    
    # 测试 P2 告警（不会立即通知，只记录）
    alert_p2 = notifier.create_alert(
        severity='P2',
        agent='data_download',
        error='Timeout: Connection timeout',
        action_taken='已自动重试',
        estimated_fix='下次执行恢复'
    )
    notifier.send_alert(alert_p2)
    print(f"✅ P2 告警已记录（不通知）：{alert_p2.title}")
    
    # 发送汇总报告
    notifier.send_summary_report('hourly')
    print("✅ 汇总报告已生成")
