#!/usr/bin/env python3
"""
Slack Stream 模式 - 定时摘要报告生成器

功能:
- 晨间简报 (09:00)
- 午间更新 (12:00)
- 收盘报告 (17:30)
- 晚间复盘 (20:00)

用法:
    python3 slack_digest.py --type morning
    python3 slack_digest.py --type noon
    python3 slack_digest.py --type market_close
    python3 slack_digest.py --type evening
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'world_model'))

try:
    import requests
    from smart_alert import SmartAlertSystem
except Exception as e:
    print(f"⚠️ 导入失败：{e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackDigestReporter:
    """Slack 摘要报告生成器"""
    
    def __init__(self):
        self.webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        self.stream_mode = os.environ.get('SLACK_STREAM_MODE', '1') == '1'
        self.project_dir = Path(__file__).parent
        self.report_dir = self.project_dir / 'reports' / 'slack_digest'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Slack 摘要报告生成器初始化完成")
    
    def send_to_slack(self, message: str, blocks: List[Dict] = None):
        """发送消息到 Slack"""
        if not self.webhook_url:
            logger.warning("⚠️ SLACK_WEBHOOK_URL 未配置，跳过 Slack 发送")
            print(message)
            return
        
        try:
            payload = {"text": message}
            if blocks:
                payload["blocks"] = blocks
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Slack 消息已发送")
            else:
                logger.error(f"❌ Slack 发送失败：{response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Slack 发送异常：{e}")
    
    def get_cron_status(self) -> Dict:
        """获取 cron 任务状态"""
        try:
            # 通过 openclaw 命令获取
            import subprocess
            result = subprocess.run(
                ['openclaw', 'cron', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                total = len(lines) - 1  # 减去标题行
                ok_count = sum(1 for line in lines[1:] if 'ok' in line.lower())
                error_count = sum(1 for line in lines[1:] if 'error' in line.lower())
                
                return {
                    'total': total,
                    'ok': ok_count,
                    'error': error_count,
                    'idle': total - ok_count - error_count
                }
        except Exception as e:
            logger.error(f"获取 cron 状态失败：{e}")
        
        return {'total': 0, 'ok': 0, 'error': 0, 'idle': 0}
    
    def get_account_status(self) -> Dict:
        """获取账户状态"""
        account_file = self.project_dir / 'accounts' / 'virtual_2026_account.json'
        
        if not account_file.exists():
            return {'cash': 0, 'positions': 0, 'total_value': 0}
        
        try:
            with open(account_file, 'r') as f:
                account = json.load(f)
            
            cash = account.get('cash', 0)
            positions = account.get('positions', [])
            total_value = cash + sum(p.get('market_value', 0) for p in positions)
            
            return {
                'cash': cash,
                'positions': len(positions),
                'total_value': total_value
            }
        except Exception as e:
            logger.error(f"读取账户文件失败：{e}")
            return {'cash': 0, 'positions': 0, 'total_value': 0}
    
    def get_today_trades(self) -> List[Dict]:
        """获取今日交易"""
        # TODO: 从交易记录文件读取
        return []
    
    def generate_morning_digest(self) -> str:
        """生成晨间简报"""
        cron_status = self.get_cron_status()
        account_status = self.get_account_status()
        
        message = f"""📊 晨间简报 ({datetime.now().strftime('%m-%d %H:%M')})
━━━━━━━━━━━━━━━━━━━━
✅ Agent 状态：{cron_status['ok']}/{cron_status['total']} 正常
💰 账户总资产：¥{account_status['total_value']:,.2f}
📈 持仓数量：{account_status['positions']} 只
💵 可用现金：¥{account_status['cash']:,.2f}

今日计划:
• 09:00 每日选股
• 09:35 自动交易
• 17:30 每日调仓
• 20:00 每日复盘

祝交易顺利！🍀
━━━━━━━━━━━━━━━━━━━━"""
        
        return message
    
    def generate_noon_digest(self) -> str:
        """生成午间更新"""
        cron_status = self.get_cron_status()
        trades = self.get_today_trades()
        
        message = f"""📊 午间更新 ({datetime.now().strftime('%m-%d %H:%M')})
━━━━━━━━━━━━━━━━━━━━
✅ 上午运行状态：{cron_status['ok']}/{cron_status['total']} 正常

上午交易:
• 买入：{len([t for t in trades if t.get('action') == 'buy'])} 只
• 卖出：{len([t for t in trades if t.get('action') == 'sell'])} 只

下午关注:
• 13:00 市场开盘
• 14:00 QA-Architect 检查
• 15:00 止盈止损检查
• 16:00 止盈止损执行
━━━━━━━━━━━━━━━━━━━━"""
        
        return message
    
    def generate_market_close_digest(self) -> str:
        """生成收盘报告"""
        cron_status = self.get_cron_status()
        account_status = self.get_account_status()
        trades = self.get_today_trades()
        
        message = f"""📊 收盘报告 ({datetime.now().strftime('%m-%d %H:%M')})
━━━━━━━━━━━━━━━━━━━━
✅ 今日 Agent 运行：{cron_status['ok']}/{cron_status['total']} 正常

今日交易:
• 买入：{len([t for t in trades if t.get('action') == 'buy'])} 只
• 卖出：{len([t for t in trades if t.get('action') == 'sell'])} 只

账户状态:
• 总资产：¥{account_status['total_value']:,.2f}
• 持仓：{account_status['positions']} 只
• 现金：¥{account_status['cash']:,.2f}

晚间安排:
• 17:00 数据下载
• 20:00 每日复盘
━━━━━━━━━━━━━━━━━━━━"""
        
        return message
    
    def generate_evening_digest(self) -> str:
        """生成晚间复盘"""
        cron_status = self.get_cron_status()
        account_status = self.get_account_status()
        
        message = f"""📊 晚间复盘 ({datetime.now().strftime('%m-%d %H:%M')})
━━━━━━━━━━━━━━━━━━━━
✅ 系统健康度：{cron_status['ok']}/{cron_status['total']} Agent 正常

账户概览:
• 总资产：¥{account_status['total_value']:,.2f}
• 持仓：{account_status['positions']} 只
• 现金：¥{account_status['cash']:,.2f}

明日计划:
• 01:00 数据下载
• 09:00 每日选股
• 09:35 自动交易

晚安！😴
━━━━━━━━━━━━━━━━━━━━"""
        
        return message
    
    def send_digest(self, digest_type: str = 'morning'):
        """发送摘要报告"""
        logger.info(f"📝 生成 {digest_type} 摘要报告...")
        
        # 根据类型生成报告
        if digest_type == 'morning':
            message = self.generate_morning_digest()
        elif digest_type == 'noon':
            message = self.generate_noon_digest()
        elif digest_type == 'market_close':
            message = self.generate_market_close_digest()
        elif digest_type == 'evening':
            message = self.generate_evening_digest()
        else:
            logger.error(f"❌ 未知的摘要类型：{digest_type}")
            return
        
        # 发送到 Slack
        self.send_to_slack(message)
        
        # 保存到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.report_dir / f"digest_{digest_type}_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(message)
        
        logger.info(f"✅ 摘要报告已保存：{report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Slack 摘要报告生成器')
    parser.add_argument('--type', type=str, 
                       choices=['morning', 'noon', 'market_close', 'evening'],
                       default='morning',
                       help='摘要类型')
    
    args = parser.parse_args()
    
    reporter = SlackDigestReporter()
    reporter.send_digest(args.type)


if __name__ == '__main__':
    main()
