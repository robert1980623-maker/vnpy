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
        print("="*70)
        print(" " * 20 + "统一数据下载 Agent")
        print("="*70)
        print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. 下载日线数据
        print("【1/4】下载日线数据...")
        self.download_daily_bars(symbols)
        print()
        
        # 2. 下载政策数据
        print("【2/4】下载政策数据...")
        self.download_policy_data()
        print()
        
        # 3. 下载新闻数据
        print("【3/4】下载新闻数据...")
        self.download_news_data()
        print()
        
        # 4. 下载财务数据
        print("【4/4】下载财务数据...")
        self.download_fundamental_data(symbols)
        print()
        
        # 生成报告
        self.generate_report()
        
        print("="*70)
        print(" " * 25 + "完成")
        print("="*70)
    
    def download_daily_bars(self, symbols: List[str] = None):
        """下载日线数据"""
        if not symbols:
            # 从账户读取持仓
            account_file = Path('./accounts/virtual_2026_account.json')
            if account_file.exists():
                with open(account_file, 'r', encoding='utf-8') as f:
                    account = json.load(f)
                    symbols = [pos['symbol'] for pos in account.get('positions', [])]
        
        if not symbols:
            print("⚠️ 无股票数据可下载")
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
            print(f"⚠️ 政策数据下载失败：{e}")
            self.stats['policy_data']['success'] = False
    
    def download_news_data(self):
        """下载新闻数据"""
        try:
            # 导入新闻数据下载器
            from download_news_data import NewsDataDownloader
            
            downloader = NewsDataDownloader()
            downloader.download_all()
            
            self.stats['news_data']['success'] = True
            
        except Exception as e:
            print(f"⚠️ 新闻数据下载失败：{e}")
            self.stats['news_data']['success'] = False
    
    def download_fundamental_data(self, symbols: List[str] = None):
        """下载财务数据"""
        if not symbols:
            symbols = ['600519.SH', '000858.SZ', '300750.SZ']  # 默认测试股票
        
        try:
            # 获取财务数据
            data = self.fundamental_fetcher.fetch_all(symbols)
            
            if data:
                print(f"✅ 财务数据下载成功：{len(data)} 只股票")
                self.stats['fundamental']['success'] = True
            else:
                print("⚠️ 财务数据下载失败")
                self.stats['fundamental']['success'] = False
                
        except Exception as e:
            print(f"⚠️ 财务数据下载失败：{e}")
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
        print(f"\n📊 下载摘要:")
        print(f"  日线数据：{report['summary']['daily_bars_success_rate']:.1f}% 成功")
        print(f"  政策数据：{report['summary']['policy_data']}")
        print(f"  新闻数据：{report['summary']['news_data']}")
        print(f"  财务数据：{report['summary']['fundamental']}")
        print(f"\n📄 报告已保存：{self.report_file}")


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
    
    args = parser.parse_args()
    
    agent = UnifiedDataAgent()
    
    if args.all or (not args.daily and not args.policy and not args.news and not args.fundamental):
        # 下载所有数据
        agent.run_all(args.symbols)
    else:
        # 下载指定数据
        if args.daily:
            print("【日线数据】")
            agent.download_daily_bars(args.symbols)
        if args.policy:
            print("【政策数据】")
            agent.download_policy_data()
        if args.news:
            print("【新闻数据】")
            agent.download_news_data()
        if args.fundamental:
            print("【财务数据】")
            agent.download_fundamental_data(args.symbols)


if __name__ == '__main__':
    main()
