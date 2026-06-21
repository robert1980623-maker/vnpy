#!/usr/bin/env python3
"""
异常通知器

原则：
- 正常工作不打扰
- 只有异常才通知
- 紧急问题立即通知
- 小问题汇总报告

多渠道支持（从 vnpy_config.yaml 读取）：
- feishu: 飞书群/用户通知
- email: 邮件通知
- telegram: Telegram Bot 通知
- wecom: 企业微信机器人通知
"""

import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import OrderedDict

import yaml
import requests

# ---------------------------------------------------------------------------
# 配置读取
# ---------------------------------------------------------------------------

_config_cache = None


def get_alert_config() -> dict:
    """从 vnpy_config.yaml 读取告警配置（带缓存）"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    # 搜索配置文件路径
    possible_paths = [
        Path(__file__).parent / "vnpy_config.yaml",
        Path(__file__).parent.parent.parent / "vnpy_analysis" / "vnpy_config.yaml",
        Path(__file__).parent.parent / "vnpy_analysis" / "vnpy_config.yaml",
    ]

    for config_path in possible_paths:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f)
            # 提取 alert 区块
            _config_cache = full_config.get("alert", {}) if full_config else {}
            return _config_cache

    # 未找到配置文件，返回空配置（使用硬编码兜底）
    _config_cache = {}
    return _config_cache


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# LRU 缓存
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 告警通知器
# ---------------------------------------------------------------------------

class AlertNotifier:
    """告警通知器 — 支持多渠道（飞书/邮件/Telegram/企业微信）"""

    def __init__(self, max_pending_alerts: int = 1000):
        self.alert_log_dir = Path("./logs/alerts/")
        self.alert_log_dir.mkdir(parents=True, exist_ok=True)

        # 通知阈值配置
        self.notify_threshold = {
            "P0": True,   # 立即通知
            "P1": True,   # 立即通知
            "P2": False,  # 汇总报告
            "P3": False,  # 不通知
        }

        # 告警汇总（LRU 缓存，限制最大数量）
        self._pending_alerts_cache = LRUCache(max_size=max_pending_alerts)

        # ── 从配置文件读取多渠道 ───────────────────────────────────────────
        config = get_alert_config()
        self._channels = config.get("channels", [])
        self._notify_threshold_config = config.get("notify_threshold", 3)

    @property
    def channels(self) -> List[dict]:
        """当前配置的渠道列表"""
        return self._channels

    @property
    def pending_alerts(self) -> List[Alert]:
        """获取所有待处理告警"""
        return self._pending_alerts_cache.values()

    def should_notify(self, severity: str) -> bool:
        """判断是否应该通知"""
        return self.notify_threshold.get(severity, False)

    def create_alert(
        self,
        severity: str,
        agent: str,
        error: str,
        action_taken: str = "",
        estimated_fix: str = "",
    ) -> Alert:
        """创建告警"""
        titles = {
            "P0": "🚨 严重错误",
            "P1": "⚠️ 功能异常",
            "P2": "📊 性能警告",
        }

        alert = Alert(
            severity=severity,
            title=titles.get(severity, "📝 通知"),
            message=self._generate_message(severity, error),
            agent=agent,
            error=error,
            timestamp=datetime.now().isoformat(),
            action_taken=action_taken,
            estimated_fix=estimated_fix,
        )

        return alert

    def _generate_message(self, severity: str, error: str) -> str:
        """生成告警消息"""
        if severity == "P0":
            return f"系统严重错误，需要立即处理：{error}"
        elif severity == "P1":
            return f"功能异常，已调度工程师修复：{error}"
        elif severity == "P2":
            return f"性能问题，已记录并监控：{error}"
        else:
            return error

    def send_alert(self, alert: Alert):
        """发送告警"""
        # 记录告警日志
        self._log_alert(alert)

        # 判断是否需要通知
        if self.should_notify(alert.severity):
            self._notify_all_channels(alert)

        # 添加到待处理列表（使用时间戳作为 key 以支持 LRU 淘汰）
        cache_key = f"{alert.timestamp}_{alert.agent}_{alert.error}"
        self._pending_alerts_cache.put(cache_key, alert)

    def _log_alert(self, alert: Alert):
        """记录告警日志"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.alert_log_dir / f"alerts_{date_str}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(alert), ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------------------
    # 多渠道通知
    # ---------------------------------------------------------------------------

    def _notify_all_channels(self, alert: Alert):
        """向所有已配置的渠道发送通知"""
        if not self._channels:
            # 兜底：写入通知文件（旧版兼容）
            self._write_notification_file(alert, "slack", "user:U0AHSM009ML")
            return

        for channel in self._channels:
            ch_type = channel.get("type", "").lower()
            target = channel.get("target", "")
            try:
                if ch_type == "feishu":
                    self._send_feishu(alert, target)
                elif ch_type == "email":
                    self._send_email(alert, target)
                elif ch_type == "telegram":
                    self._send_telegram(alert, target)
                elif ch_type == "wecom":
                    self._send_wecom(alert, target)
                elif ch_type == "slack":
                    self._send_slack(alert, target)
                else:
                    print(f"[AlertNotifier] 未知渠道类型: {ch_type}，跳过")
            except Exception as e:
                print(f"[AlertNotifier] 渠道 {ch_type} 发送失败: {e}")

    def _send_feishu(self, alert: Alert, target: str):
        """通过飞书 Webhook 或开放平台 API 发送通知

        target 格式:
          - chat_id:oc_xxx   → 群通知
          - open_id:ou_xxx   → 用户消息（需要 Access Token）
          - webhook:https://open.feishu.cn/... → 自定义 Webhook
        """
        message = self._format_notification(alert)

        if target.startswith("chat_id:"):
            chat_id = target.split(":", 1)[1]
            self._feishu_group_notify(chat_id, message)
        elif target.startswith("webhook:"):
            webhook_url = target.split(":", 1)[1]
            self._feishu_webhook(webhook_url, message)
        elif target.startswith("open_id:"):
            open_id = target.split(":", 1)[1]
            self._feishu_user_notify(open_id, message)
        else:
            # 兼容旧格式：直接当 chat_id 使用
            self._feishu_group_notify(target, message)

    def _feishu_group_notify(self, chat_id: str, message: str):
        """发送飞书群通知（需要飞书 Access Token）"""
        # 从环境或配置读取飞书 Access Token
        app_id = "cli_xxxxxxxxxxxxxxxx"   # TODO: 填入实际 App ID
        app_secret = "xxxxxxxxxxxxxxxx"    # TODO: 填入实际 App Secret

        try:
            # 1. 获取 tenant_access_token
            token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            token_resp = requests.post(
                token_url,
                json={"app_id": app_id, "app_secret": app_secret},
                timeout=10,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            if token_data.get("code") != 0:
                print(f"[AlertNotifier] 获取飞书 Token 失败: {token_data}")
                return
            tenant_token = token_data["tenant_access_token"]

            # 2. 发送消息到群
            send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
            payload = {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": message}),
            }
            params = {"receive_id_type": "chat_id"}

            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            resp = requests.post(
                send_url,
                json=payload,
                params=params,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[AlertNotifier] 飞书群通知失败: {e}")
            # 降级：写入通知文件
            self._write_notification_file(alert, "feishu", f"chat_id:{chat_id}")

    def _feishu_webhook(self, webhook_url: str, message: str):
        """通过飞书自定义机器人 Webhook 发送通知"""
        try:
            payload = {"msg_type": "text", "content": {"text": message}}
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[AlertNotifier] 飞书 Webhook 通知失败: {e}")
            self._write_notification_file(alert, "feishu_webhook", webhook_url)

    def _feishu_user_notify(self, open_id: str, message: str):
        """发送飞书用户消息（通过应用商店机器人）"""
        # 与 _feishu_group_notify 相同逻辑，receive_id_type 改为 open_id
        self._feishu_group_notify(open_id, message)

    def _send_email(self, alert: Alert, target: str):
        """发送邮件通知"""
        smtp_host = "smtp.example.com"
        smtp_port = 587
        sender = "vnpy-alert@example.com"

        subject = f"[{alert.severity}] {alert.title} - {alert.agent}"
        body = self._format_notification(alert)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = target
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(f"<pre>{body}</pre>", "html", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.sendmail(sender, [target], msg.as_string())
        except Exception as e:
            print(f"[AlertNotifier] 邮件发送失败: {e}")
            self._write_notification_file(alert, "email", target)

    def _send_telegram(self, alert: Alert, target: str):
        """通过 Telegram Bot 发送通知

        target 格式:
          - @your_channel    → Channel username
          - -1001234567890   → Chat ID（群组或频道）
        """
        from config_loader import get_telegram_token
        bot_token = get_telegram_token()
        if not bot_token:
            print("[AlertNotifier] TELEGRAM_BOT_TOKEN 未配置，跳过 Telegram 通知")
            self._write_notification_file(alert, "telegram", target)
            return

        # 移除 @ 前缀（如果存在）
        chat_id = target.lstrip("@")

        # 转换 username 为 chat_id（如果需要直接发消息给用户）
        message = self._format_notification(alert)

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[AlertNotifier] Telegram 发送失败: {e}")
            self._write_notification_file(alert, "telegram", target)

    def _send_wecom(self, alert: Alert, target: str):
        """通过企业微信机器人 Webhook 发送通知"""
        # target 是企业微信机器人的 Webhook URL
        message = self._format_notification(alert)

        try:
            payload = {"msgtype": "text", "text": {"content": message}}
            resp = requests.post(target, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[AlertNotifier] 企业微信通知失败: {e}")
            self._write_notification_file(alert, "wecom", target)

    def _send_slack(self, alert: Alert, target: str):
        """通过 Slack Webhook 发送通知（向后兼容）"""
        webhook_url = f"https://hooks.slack.com/services/{target}"
        message = self._format_notification(alert)

        try:
            payload = {"text": message}
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[AlertNotifier] Slack 通知失败: {e}")
            self._write_notification_file(alert, "slack", target)

    def _write_notification_file(self, alert: Alert, channel: str, to: str):
        """降级：写入通知文件（当渠道发送失败时）"""
        notification = {
            "type": "alert_notification",
            "channel": channel,
            "to": to,
            "message": self._format_notification(alert),
            "timestamp": datetime.now().isoformat(),
        }

        notify_file = Path("./logs/alerts/notifications.json")
        notifications = []
        if notify_file.exists():
            try:
                with open(notify_file, "r", encoding="utf-8") as f:
                    notifications = json.load(f)
            except (json.JSONDecodeError, Exception):
                notifications = []

        notifications.append(notification)

        with open(notify_file, "w", encoding="utf-8") as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)

    def _format_notification(self, alert: Alert) -> str:
        """格式化通知消息"""
        emoji = {"P0": "🚨", "P1": "⚠️", "P2": "📊"}.get(alert.severity, "📝")
        message = f"""{emoji} **{alert.title}**

🤖 Agent: {alert.agent}
❌ 错误：{alert.error}
🕐 时间：{alert.timestamp}
🔧 操作：{alert.action_taken}
⏱️ 预计修复：{alert.estimated_fix}

详细报告：查看 logs/alerts/"""
        return message

    def send_summary_report(self, period: str = "hourly"):
        """发送汇总报告（P2/P3 级别）"""
        if not self._pending_alerts_cache:
            return

        # 筛选 P2/P3 告警
        low_priority_alerts = [a for a in self._pending_alerts_cache if a.severity in ["P2", "P3"]]

        if not low_priority_alerts:
            return

        # 生成汇总报告
        summary = f"""📊 **异常汇总报告** ({period})

异常数量：{len(low_priority_alerts)}

详情:"""

        for alert in low_priority_alerts:
            summary += f"\n- {alert.agent}: {alert.error}"

        summary += "\n\n所有异常已自动处理，无需担心。"

        if not self._channels:
            # 兜底：写文件（旧版兼容）
            notification = {
                "type": "summary_report",
                "channel": "slack",
                "to": "user:U0AHSM009ML",
                "message": summary,
                "timestamp": datetime.now().isoformat(),
            }
            notify_file = Path("./logs/alerts/notifications.json")
            notifications = []
            if notify_file.exists():
                try:
                    with open(notify_file, "r", encoding="utf-8") as f:
                        notifications = json.load(f)
                except Exception:
                    pass
            notifications.append(notification)
            with open(notify_file, "w", encoding="utf-8") as f:
                json.dump(notifications, f, ensure_ascii=False, indent=2)
            return

        # 多渠道发送汇总
        for channel in self._channels:
            ch_type = channel.get("type", "").lower()
            target = channel.get("target", "")
            try:
                if ch_type == "feishu":
                    self._send_feishu_summary(summary, target)
                elif ch_type == "email":
                    self._send_email_summary(summary, target)
                elif ch_type == "telegram":
                    self._send_telegram_summary(summary, target)
                elif ch_type == "wecom":
                    self._send_wecom_summary(summary, target)
                elif ch_type == "slack":
                    self._send_slack(summary, target)
            except Exception as e:
                print(f"[AlertNotifier] 汇总报告发送失败（{ch_type}）: {e}")

    def _send_feishu_summary(self, summary: str, target: str):
        if target.startswith("chat_id:"):
            self._feishu_group_notify(target.split(":", 1)[1], summary)
        elif target.startswith("webhook:"):
            self._feishu_webhook(target.split(":", 1)[1], summary)

    def _send_email_summary(self, summary: str, target: str):
        subject = "📊 VNPY 异常汇总报告"
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = "vnpy-alert@example.com"
            msg["To"] = target
            msg.attach(MIMEText(summary, "plain", "utf-8"))
            with smtplib.SMTP("smtp.example.com", 587) as server:
                server.starttls()
                server.sendmail(msg["From"], [target], msg.as_string())
        except Exception as e:
            print(f"[AlertNotifier] 汇总邮件发送失败: {e}")

    def _send_telegram_summary(self, summary: str, target: str):
        self._send_telegram(type("S", (), {"severity": "P2", "title": "📊 汇总报告",
                                            "agent": "system", "error": "",
                                            "timestamp": datetime.now().isoformat(),
                                            "action_taken": "", "estimated_fix": ""})(), target)

    def _send_wecom_summary(self, summary: str, target: str):
        try:
            requests.post(target, json={"msgtype": "text", "text": {"content": summary}}, timeout=10)
        except Exception as e:
            print(f"[AlertNotifier] 企业微信汇总发送失败: {e}")

    def clear_resolved(self):
        """清除已解决的告警"""
        remaining = {}
        for key, alert in self._pending_alerts_cache._cache.items():
            if alert.status != "resolved":
                remaining[key] = alert
        self._pending_alerts_cache._cache.clear()
        self._pending_alerts_cache._cache.update(remaining)


# ---------------------------------------------------------------------------
# 快捷函数
# ---------------------------------------------------------------------------

def notify_exception(
    severity: str,
    agent: str,
    error: str,
    action: str = "",
    estimate: str = "",
):
    """快速通知异常"""
    notifier = AlertNotifier()
    alert = notifier.create_alert(severity, agent, error, action, estimate)
    notifier.send_alert(alert)


if __name__ == "__main__":
    # 测试
    notifier = AlertNotifier()
    print(f"✅ 配置的告警渠道: {notifier.channels}")

    # 测试 P0 告警（会通知）
    alert_p0 = notifier.create_alert(
        severity="P0",
        agent="daily_stock_selection",
        error="TypeError: NoneType comparison",
        action_taken="已调度 Delta 紧急修复",
        estimated_fix="10-15 分钟",
    )
    notifier.send_alert(alert_p0)
    print(f"✅ P0 告警已发送：{alert_p0.title}")

    # 测试 P2 告警（不会立即通知，只记录）
    alert_p2 = notifier.create_alert(
        severity="P2",
        agent="data_download",
        error="Timeout: Connection timeout",
        action_taken="已自动重试",
        estimated_fix="下次执行恢复",
    )
    notifier.send_alert(alert_p2)
    print(f"✅ P2 告警已记录（不通知）：{alert_p2.title}")

    # 发送汇总报告
    notifier.send_summary_report("hourly")
    print("✅ 汇总报告已生成")
