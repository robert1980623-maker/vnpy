#!/usr/bin/env python3
"""
统一数据下载 Agent

整合所有数据下载任务:
- 日线数据 (Tushare Pro + AKShare)
- 政策数据 (Tushare Pro)
- 新闻数据 (多渠道)
- 财务数据 (Tushare Pro)

由一个 Agent 统一调度和执行
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 导入各下载器
from tushare_pro_downloader import TushareProDownloader
from tushare_fundamental_fetcher import TushareFundamentalFetcher
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive
from agent_report import create_report
from human_report import HumanReporter


class UnifiedDataAgent:
    """统一数据下载 Agent"""
    
    def __init__(self):
        self.data_dir = Path('./data')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各下载器
        self.tushare_downloader = TushareProDownloader()
        self.fundamental_fetcher = TushareFundamentalFetcher()
        
        # 下载统计
        self.stats = {
            'daily_bars': {'success': 0, 'failed': 0},
            'policy_data': {'success': False},
            'news_data': {'success': False},
            'fundamental': {'success': False}
        }
        
        # 报告文件
        self.report_file = self.data_dir / f"data_download_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    def run_all(self, symbols: List[str] = None):
        """运行所有数据下载任务"""
        reporter = create_report("统一数据下载 Agent")
        
        logger.info("="*70)
        logger.info(" " * 20 + "统一数据下载 Agent")
        logger.info("="*70)
        logger.info(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info()
        
        all_results = []
        
        # 1. 下载日线数据
        logger.info("【1/4】下载日线数据...")
        self.download_daily_bars(symbols)
        logger.info()
        
        # 2. 下载政策数据
        logger.info("【2/4】下载政策数据...")
        self.download_policy_data()
        logger.info()
        
        # 3. 下载新闻数据
        logger.info("【3/4】下载新闻数据...")
        self.download_news_data()
        logger.info()
        
        # 4. 下载财务数据
        logger.info("【4/4】下载财务数据...")
        self.download_fundamental_data(symbols)
        logger.info()
        
        # 生成报告
        reporter.add_section("下载结果", all_results, 'table')
        reporter.update_metric('items_processed', len(all_results))
        reporter.update_metric('items_success', len([r for r in all_results if r.get('status') == 'success']))
        reporter.update_metric('items_failed', len([r for r in all_results if r.get('status') == 'failed']))
        
        result = reporter.finish('success')
        logger.info(f"✅ 报告已保存：{result['filepath']}")
        
        logger.info("="*70)
        logger.info(" " * 25 + "完成")
        logger.info("="*70)
    
    def download_daily_bars(self, symbols: List[str] = None):
        """下载日线数据"""
        if not symbols:
            # 从账户读取持仓
            account_file = Path('./accounts/virtual_2026_account.json')
            if account_file.exists():
                with open(account_file, 'r', encoding='utf-8') as f:
                    account = json.load(f)
                    symbols = [pos.get('symbol') or pos.get('stock_code', '') for pos in account.get('positions', [])]
        
        if not symbols:
            logger.info("⚠️ 无股票数据可下载")
            return
        
        # 使用 Tushare Pro 下载
        success = self.tushare_downloader.download_daily_bars(symbols)
        
        self.stats['daily_bars']['success'] = self.tushare_downloader.stats['tushare_success']
        self.stats['daily_bars']['failed'] = self.tushare_downloader.stats['tushare_failed']
    
    def download_policy_data(self):
        """下载政策数据"""
        try:
            # 导入政策数据下载器
            from download_policy_data_tushare import PolicyDataDownloader
            
            downloader = PolicyDataDownloader()
            
            # 下载宏观经济数据
            downloader.download_macro_data()
            
            # 下载财经新闻
            # downloader.download_finance_news()  # 需要权限
            
            self.stats['policy_data']['success'] = True
            
        except Exception as e:
            logger.error(f"⚠️ 政策数据下载失败：{e}")
            self.stats['policy_data']['success'] = False
    
    def download_news_data(self):
        """下载新闻数据"""
        try:
            # 导入新闻数据下载器
            from download_news_data import download_all_news
            
            download_all_news()
            
            self.stats['news_data']['success'] = True
            
        except Exception as e:
            logger.error(f"⚠️ 新闻数据下载失败：{e}")
            self.stats['news_data']['success'] = False
    
    def download_fundamental_data(self, symbols: List[str] = None):
        """下载财务数据"""
        if not symbols:
            symbols = ['600519.SH', '000858.SZ', '300750.SZ']  # 默认测试股票
        
        try:
            # 获取财务数据
            data = self.fundamental_fetcher.get_batch_fundamentals(symbols)
            
            if data:
                logger.info(f"✅ 财务数据下载成功：{len(data)} 只股票")
                self.stats['fundamental']['success'] = True
            else:
                logger.error("⚠️ 财务数据下载失败")
                self.stats['fundamental']['success'] = False
                
        except Exception as e:
            logger.error(f"⚠️ 财务数据下载失败：{e}")
            self.stats['fundamental']['success'] = False
    
    def generate_report(self):
        """生成下载报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'summary': {
                'daily_bars_total': self.stats['daily_bars']['success'] + self.stats['daily_bars']['failed'],
                'daily_bars_success_rate': self.stats['daily_bars']['success'] / max(1, self.stats['daily_bars']['success'] + self.stats['daily_bars']['failed']) * 100,
                'policy_data': '✅' if self.stats['policy_data']['success'] else '❌',
                'news_data': '✅' if self.stats['news_data']['success'] else '❌',
                'fundamental': '✅' if self.stats['fundamental']['success'] else '❌'
            }
        }
        
        # 保存报告
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        logger.info(f"\n📊 下载摘要:")
        logger.info(f"  日线数据：{report['summary']['daily_bars_success_rate']:.1f}% 成功")
        logger.info(f"  政策数据：{report['summary']['policy_data']}")
        logger.info(f"  新闻数据：{report['summary']['news_data']}")
        logger.info(f"  财务数据：{report['summary']['fundamental']}")
        logger.info(f"\n📄 报告已保存：{self.report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='统一数据下载 Agent')
    parser.add_argument('--symbols', nargs='+', help='股票代码列表')
    parser.add_argument('--all', action='store_true', help='下载所有数据')
    parser.add_argument('--daily', action='store_true', help='只下载日线数据')
    parser.add_argument('--policy', action='store_true', help='只下载政策数据')
    parser.add_argument('--news', action='store_true', help='只下载新闻数据')
    parser.add_argument('--fundamental', action='store_true', help='只下载财务数据')
    parser.add_argument('--non-interactive', action='store_true', help='无人值守模式：禁用所有交互式提示')
    
    args = parser.parse_args()
    
    agent = UnifiedDataAgent()
    
    if args.all or (not args.daily and not args.policy and not args.news and not args.fundamental):
        # 下载所有数据
        agent.run_all(args.symbols)
    else:
        # 下载指定数据
        if args.daily:
            logger.info("【日线数据】")
            agent.download_daily_bars(args.symbols)
        if args.policy:
            logger.info("【政策数据】")
            agent.download_policy_data()
        if args.news:
            logger.info("【新闻数据】")
            agent.download_news_data()
        if args.fundamental:
            logger.info("【财务数据】")
            agent.download_fundamental_data(args.symbols)


if __name__ == '__main__':
    main()
