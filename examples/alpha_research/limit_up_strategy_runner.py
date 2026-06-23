#!/usr/bin/env python3
"""
涨停龙头策略执行器

功能:
1. 每日收盘后运行策略选股
2. 生成龙头候选列表
3. 发送信号到交易执行模块
4. 生成策略报告

使用方式:
    python3 limit_up_strategy_runner.py --date 20260318
    python3 limit_up_strategy_runner.py --auto  # 自动检测日期
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from strategies.limit_up_leader import LimitUpLeaderStrategy, run_daily_strategy
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account
from notification_utils import send_to_group

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/limit_up_strategy.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class LimitUpStrategyRunner:
    """涨停龙头策略运行器"""
    
    def __init__(self, config: dict = None):
        """初始化运行器"""
        self.config = config or {}
        self.strategy = LimitUpLeaderStrategy(config)
        # 确保账户存在并初始化 AccountService
        db = AccountDB()
        if not db.get_account("virtual_2026"):
            from accounts.account_db import Account
            acct = Account(
                account_id="virtual_2026",
                account_name="虚拟账户",
                initial_capital=1_000_000,
                cash=1_000_000,
            )
            db.create_account(acct)
        self.account = AccountService("virtual_2026")

        # 报告目录
        self.report_dir = Path(__file__).parent / 'reports' / 'limit_up_strategy'
        self.report_dir.mkdir(parents=True, exist_ok=True)

        logger.info("涨停龙头策略运行器初始化完成")
    
    def run_selection(self, date: str = None) -> dict:
        """
        运行选股逻辑
        
        Args:
            date: 日期，格式 YYYYMMDD
            
        Returns:
            选股结果
        """
        if date is None:
            date = self._get_last_trading_date()
        
        logger.info(f"开始运行涨停龙头选股，日期：{date}")
        
        try:
            # 1. 筛选龙头
            leaders = self.strategy.select_leaders(date)
            
            if not leaders:
                logger.warning("未筛选到龙头候选")
                return {'success': False, 'reason': 'no_leaders', 'date': date}
            
            # 2. 生成交易信号
            # 获取当前价格 (这里简化处理，实际应从行情系统获取)
            current_prices = {}
            for leader in leaders:
                # TODO: 从行情系统获取实时价格
                current_prices[leader.symbol] = leader.price if hasattr(leader, 'price') else 0
            
            signals = self.strategy.generate_signals(current_prices)
            
            # 3. 执行信号 (模拟/实盘)
            executed_signals = []
            for signal in signals:
                if self.config.get('auto_execute', False):
                    success = self.strategy.execute_signal(signal)
                    if success:
                        executed_signals.append({
                            'symbol': signal.symbol,
                            'action': signal.action,
                            'price': signal.price,
                            'quantity': signal.quantity,
                        })
                else:
                    # 仅生成信号，不执行
                    executed_signals.append({
                        'symbol': signal.symbol,
                        'action': signal.action,
                        'price': signal.price,
                        'quantity': signal.quantity,
                        'status': 'pending',
                    })
            
            # 4. 生成报告
            report = self.strategy.get_daily_report(date)
            report['signals'] = executed_signals
            report['success'] = True
            
            # 5. 保存报告
            report_file = self.report_dir / f'report_{date}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"选股完成，生成 {len(leaders)} 只龙头候选，报告已保存：{report_file}")
            
            # 6. 发送通知
            if self.config.get('send_notification', True):
                self._send_notification(report)
            
            return report
            
        except Exception as e:
            logger.error(f"选股失败：{e}", exc_info=True)
            return {'success': False, 'error': str(e), 'date': date}
    
    def _send_notification(self, report: dict):
        """发送通知"""
        try:
            date = report.get('date', 'unknown')
            leaders = report.get('leaders', [])
            
            if not leaders:
                return
            
            # 构建通知消息
            top_3 = leaders[:3]
            message = f"🐉 涨停龙头策略报告 ({date})\n\n"
            message += f"涨停总数：{report.get('total_limit_up', 0)}\n"
            message += f"龙头候选：{len(leaders)}\n"
            message += f"当前持仓：{report.get('current_positions', 0)}\n\n"
            message += "📊 龙头 TOP3:\n"
            
            for i, leader in enumerate(top_3, 1):
                message += f"{i}. {leader['symbol']} {leader['name']}\n"
                message += f"   评分：{leader['score']}, 连板：{leader['limit_up_days']}天, 量比：{leader['volume_ratio']:.2f}\n"
            
            # 发送 Slack 通知
            send_to_group(message)
            logger.info("通知已发送")
            
        except Exception as e:
            logger.error(f"发送通知失败：{e}")
    
    def _get_last_trading_date(self) -> str:
        """获取最近交易日"""
        # 简单实现：如果是周末则返回周五
        today = datetime.now()
        if today.weekday() == 5:  # 周六
            last_trading = today - timedelta(days=1)
        elif today.weekday() == 6:  # 周日
            last_trading = today - timedelta(days=2)
        else:
            last_trading = today - timedelta(days=1)
        
        return last_trading.strftime('%Y%m%d')
    
    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            'total_limit_up': len(self.strategy.limit_up_stocks),
            'leader_candidates': len(self.strategy.leader_candidates),
            'positions': len(self.strategy.positions),
            'trade_history': len(self.strategy.trade_history),
            'config': self.strategy.config,
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='涨停龙头策略运行器')
    parser.add_argument('--date', type=str, help='日期 (YYYYMMDD)')
    parser.add_argument('--auto', action='store_true', help='自动检测日期')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--execute', action='store_true', help='自动执行交易信号')
    parser.add_argument('--notify', action='store_true', help='发送通知')
    
    args = parser.parse_args()
    
    # 加载配置
    config = {}
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    config['auto_execute'] = args.execute
    config['send_notification'] = args.notify
    
    # 创建运行器
    runner = LimitUpStrategyRunner(config)
    
    # 确定日期
    date = args.date if args.date else (None if args.auto else None)
    
    # 运行选股
    result = runner.run_selection(date)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 返回状态码
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
