#!/usr/bin/env python3
"""
飞书通知工具 v2 - 支持详细选股通知
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path(__file__).parent / "config" / "feishu_notification_config.json"


class FeishuNotifier:
    """飞书任务通知器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.config = self._load_config()
        self.chat_id = self.config.get("chat_id", "oc_21ccc3d7355ceabbdfb1e027af5441e5")
        self.account_id = self.config.get("account_id", "default")
        self.enabled = self.config.get("enabled", True)
    
    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载配置文件失败：{e}")
            return {}
    
    def send(self, task_name: str, status: str, title: str = None, 
             content: str = None, details: dict = None, emoji: str = None,
             stocks: list = None, top_n: int = 10):
        if not self.enabled:
            print("ℹ️ 飞书通知已禁用")
            return False
        
        task_config = self.config.get("tasks", {}).get(task_name, {})
        emoji = emoji or task_config.get("emoji", "📢")
        
        if not title:
            status_text = {
                'start': '开始执行',
                'complete': '执行完成',
                'success': '执行成功',
                'error': '执行失败',
                'warning': '执行警告',
                'info': '执行通知'
            }.get(status, '状态更新')
            title = f"{task_name} - {status_text}"
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"{emoji} **{title}**\n"
        message += f"⏰ 时间：{now}\n"
        
        if content:
            message += f"\n{content}\n"
        
        # 添加股票列表（如果是选股任务）
        if stocks and task_name in ["每日选股", "每日精选选股", "涨停龙头策略 - 每日选股"]:
            message += self._format_stocks_message(stocks, top_n)
        elif details:
            message += "\n📊 详细信息:\n"
            for key, value in details.items():
                message += f"· {key}: {value}\n"
        
        footer = self.config.get("message_format", {}).get("footer", "自动通知 by OpenClaw 量化系统")
        message += f"\n---\n_{footer}_"
        
        print(f"\n📤 发送飞书通知到群：{self.chat_id}")
        print("-" * 60)
        print(message)
        print("-" * 60)
        
        try:
            cmd = [
                "openclaw", "message", "send",
                "--account", self.account_id,
                "--channel", "feishu",
                "--target", f"chat:{self.chat_id}",
                "-m", message
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.home() / ".openclaw" / "workspace"
            )
            
            if result.returncode == 0:
                print("✅ 飞书通知发送成功")
                return True
            else:
                print(f"❌ 飞书通知发送失败：{result.stderr}")
                self._save_to_log(message)
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 发送超时")
            self._save_to_log(message)
            return False
        except Exception as e:
            print(f"❌ 发送异常：{e}")
            self._save_to_log(message)
            return False
    
    def _format_stocks_message(self, stocks: list, top_n: int = 10) -> str:
        message = "\n📈 **选股结果**:\n"
        message += f"· 候选股票数：{len(stocks)} 只\n"
        message += f"· 入选股票数：{min(top_n, len(stocks))} 只\n"
        message += f"· 通过率：{min(top_n, len(stocks)) / len(stocks) * 100:.1f}%\n\n"
        
        message += "🏆 **入选股票**:\n\n"
        
        for i, stock in enumerate(stocks[:top_n], 1):
            symbol = stock.get('symbol', '')
            name = stock.get('name', '未知')
            score = stock.get('score', 0)
            strategies = stock.get('strategies', [])
            reasons = stock.get('reasons', [])
            
            strategy_tags = ' '.join([f"[{s}]" for s in strategies])
            
            message += f"**{i}. {symbol} {name}** {strategy_tags}\n"
            message += f"   评分：{score} 分\n"
            
            if reasons:
                message += "   入选原因:\n"
                for reason in reasons:
                    message += f"   · {reason}\n"
            
            pe = stock.get('pe')
            roe = stock.get('roe')
            revenue_growth = stock.get('revenue_growth')
            profit_growth = stock.get('profit_growth')
            dividend_yield = stock.get('dividend_yield')
            
            indicators = []
            if pe is not None:
                indicators.append(f"PE={pe:.1f}")
            if roe is not None:
                indicators.append(f"ROE={roe:.1f}%")
            if revenue_growth is not None:
                indicators.append(f"营收增长={revenue_growth:.1f}%")
            if profit_growth is not None:
                indicators.append(f"利润增长={profit_growth:.1f}%")
            if dividend_yield is not None and dividend_yield > 0:
                indicators.append(f"股息率={dividend_yield:.1f}%")
            
            if indicators:
                message += "   关键指标：" + ", ".join(indicators) + "\n"
            
            message += "\n"
        
        if len(stocks) > top_n:
            message += f"💡 还有 {len(stocks) - top_n} 只股票，详见报告文件\n"
        
        return message
    
    def _save_to_log(self, message: str):
        print("💾 保存到通知日志文件")
        log_file = Path(__file__).parent / "logs" / "feishu_notifications.log"
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"{datetime.now().isoformat()}\n")
            f.write(f"{message}\n")
    
    def notify_start(self, task_name: str, details: dict = None):
        task_config = self.config.get("tasks", {}).get(task_name, {})
        if "start" in task_config.get("notify_on", []):
            return self.send(task_name, "start", details=details)
        return False
    
    def notify_complete(self, task_name: str, content: str = None, details: dict = None, stocks: list = None, top_n: int = 10):
        task_config = self.config.get("tasks", {}).get(task_name, {})
        if "complete" in task_config.get("notify_on", []):
            return self.send(task_name, "complete", content=content, details=details, stocks=stocks, top_n=top_n)
        return False
    
    def notify_error(self, task_name: str, error_msg: str, details: dict = None):
        task_config = self.config.get("tasks", {}).get(task_name, {})
        if "error" in task_config.get("notify_on", []):
            return self.send(task_name, "error", content=f"错误信息：{error_msg}", details=details)
        return False
    
    def notify_warning(self, task_name: str, warning_msg: str, details: dict = None):
        task_config = self.config.get("tasks", {}).get(task_name, {})
        if "warning" in task_config.get("notify_on", []):
            return self.send(task_name, "warning", content=f"警告：{warning_msg}", details=details)
        return False


def notify_task_start(task_name: str, **kwargs):
    notifier = FeishuNotifier()
    return notifier.notify_start(task_name, **kwargs)


def notify_task_complete(task_name: str, **kwargs):
    notifier = FeishuNotifier()
    return notifier.notify_complete(task_name, **kwargs)


def notify_task_error(task_name: str, error_msg: str, **kwargs):
    notifier = FeishuNotifier()
    return notifier.notify_error(task_name, error_msg, **kwargs)


if __name__ == "__main__":
    notifier = FeishuNotifier()
    test_stocks = [
        {
            "symbol": "603893.SH",
            "name": "瑞芯微",
            "strategies": ["成长", "质量"],
            "score": 5,
            "reasons": ["营收增长=45.5%, 利润增长=121.7%", "ROE=18.4%"],
            "pe": 68.1,
            "roe": 18.39,
            "revenue_growth": 45.46,
            "profit_growth": 121.65
        },
        {
            "symbol": "300476.SZ",
            "name": "胜宏科技",
            "strategies": ["成长", "质量"],
            "score": 5,
            "reasons": ["营收增长=79.8%, 利润增长=273.5%", "ROE=25.9%"],
            "pe": 56.66,
            "roe": 25.95,
            "revenue_growth": 79.77,
            "profit_growth": 273.52
        }
    ]
    notifier.notify_complete("每日选股", content="选股完成", stocks=test_stocks)
