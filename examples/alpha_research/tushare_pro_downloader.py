#!/usr/bin/env python3
"""
Tushare Pro 主力数据下载器

功能:
- 使用 Tushare Pro 下载日线数据
- 自动切换到 AKShare 备用
- 增量更新 (只下载未更新的数据)
- 数据过期管理
"""

import os
import json
import time
import tushare as ts
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class TushareProDownloader:
    """Tushare Pro 数据下载器"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Tushare
        token = os.environ.get('TUSHARE_TOKEN', '')
        if token:
            ts.set_token(token)
            self.pro = ts.pro_api()
            self.use_tushare = True
            print(f"✅ Tushare Pro 已初始化 (Token: {token[:20]}...)")
        else:
            self.pro = None
            self.use_tushare = False
            print("⚠️ Tushare Token 未配置，将使用 AKShare")
        
        # 下载统计
        self.stats = {
            'tushare_success': 0,
            'tushare_failed': 0,
            'akshare_fallback': 0,
            'skipped': 0
        }
    
    def get_symbols_to_update(self, symbols: List[str]) -> List[str]:
        """获取需要更新的股票列表 (增量更新)"""
        today = datetime.now().date()
        to_update = []
        
        for symbol in symbols:
            csv_file = self._get_csv_file(symbol)
            
            if not csv_file.exists():
                to_update.append(symbol)
                continue
            
            mtime = datetime.fromtimestamp(csv_file.stat().st_mtime).date()
            
            if mtime < today:
                to_update.append(symbol)
            else:
                self.stats['skipped'] += 1
        
        return to_update
    
    def _get_csv_file(self, symbol: str) -> Path:
        """获取 CSV 文件路径"""
        code = symbol.split('.')[0]
        suffix = symbol.split('.')[1].lower()
        return self.data_dir / f'{code}_{suffix}.csv'
    
    def download_daily_bars(self, symbols: List[str], trade_date: str = None) -> bool:
        """下载日线数据"""
        if not trade_date:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n{'='*60}")
        print(f"  数据下载 (Tushare Pro + AKShare)")
        print(f"{'='*60}")
        print(f"交易日期：{trade_date}")
        print(f"股票数量：{len(symbols)}")
        print()
        
        # 获取需要更新的股票
        to_update = self.get_symbols_to_update(symbols)
        
        if not to_update:
            print("✅ 所有数据已最新，无需更新")
            return True
        
        print(f"需要更新：{len(to_update)} 只股票")
        print()
        
        # 使用 Tushare Pro 下载
        if self.use_tushare:
            try:
                print("📥 使用 Tushare Pro 下载...")
                
                # 逐个下载 (避免批量接口问题)
                success_count = 0
                for symbol in to_update:
                    if self._download_single_tushare(symbol, trade_date):
                        success_count += 1
                        time.sleep(0.1)  # 避免请求过快
                
                if success_count > 0:
                    self.stats['tushare_success'] = success_count
                    print(f"✅ Tushare Pro 下载成功：{success_count}/{len(to_update)}只")
                    
                    # 剩余的切换到 AKShare
                    if success_count < len(to_update):
                        remaining = [s for s in to_update if not self._get_csv_file(s).exists()]
                        if remaining:
                            print(f"\n🔄 {len(remaining)} 只股票切换到 AKShare...")
                            self._akshare_fallback(remaining)
                    return True
                else:
                    print("⚠️ Tushare Pro 全部失败，切换到 AKShare")
                    self.stats['tushare_failed'] = len(to_update)
                    
            except Exception as e:
                print(f"⚠️ Tushare Pro 异常：{e}")
                self.stats['tushare_failed'] = len(to_update)
        
        # Tushare 失败或不可用，使用 AKShare
        if self.stats['tushare_failed'] > 0 or not self.use_tushare:
            self._akshare_fallback(to_update)
        
        self._print_stats()
        return True
    
    def _download_single_tushare(self, symbol: str, trade_date: str) -> bool:
        """下载单只股票 (Tushare)"""
        try:
            ts_code = symbol.replace('.', '')
            
            # 使用 daily 接口
            df = self.pro.daily(ts_code=ts_code, trade_date=trade_date)
            
            if df is not None and not df.empty:
                # 保存数据
                self._save_single(symbol, df)
                print(f"  ✅ {symbol}")
                return True
            else:
                print(f"  ⚠️ {symbol}: 空数据")
                return False
                
        except Exception as e:
            print(f"  ❌ {symbol}: {str(e)[:50]}")
            return False
    
    def _save_single(self, symbol: str, df: pd.DataFrame):
        """保存单只股票数据"""
        try:
            # 转换为需要的格式
            ohlcv = df[['trade_date', 'open', 'high', 'low', 'close', 'vol']].copy()
            ohlcv.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # 追加到现有文件
            csv_file = self._get_csv_file(symbol)
            
            if csv_file.exists():
                # 读取现有数据
                existing = pd.read_csv(csv_file)
                # 合并 (去重)
                combined = pd.concat([existing, ohlcv]).drop_duplicates(subset=['datetime'], keep='last')
                combined.to_csv(csv_file, index=False)
            else:
                # 新文件
                ohlcv.to_csv(csv_file, index=False)
                
        except Exception as e:
            print(f"  ⚠️ 保存失败：{e}")
    
    def _akshare_fallback(self, symbols: List[str]):
        """AKShare 备用下载"""
        try:
            import akshare as ak
            
            print(f"\n📥 使用 AKShare 下载 {len(symbols)} 只股票...")
            
            for i, symbol in enumerate(symbols, 1):
                print(f"[{i}/{len(symbols)}] {symbol}...", end=' ')
                
                code = symbol.split('.')[0]
                df = ak.stock_zh_a_hist(symbol=code, period="daily")
                
                if df is not None and not df.empty:
                    # 转换格式
                    ohlcv = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']].copy()
                    ohlcv.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                    
                    # 保存
                    csv_file = self._get_csv_file(symbol)
                    ohlcv.to_csv(csv_file, index=False)
                    print("✅")
                    self.stats['akshare_fallback'] += 1
                else:
                    print("❌")
                
                time.sleep(0.3)  # 避免请求过快
                
        except Exception as e:
            print(f"\n⚠️ AKShare 下载失败：{e}")
    
    def _print_stats(self):
        """打印统计"""
        print(f"\n{'='*60}")
        print(f"  下载统计")
        print(f"{'='*60}")
        print(f"  Tushare 成功：{self.stats['tushare_success']}")
        print(f"  Tushare 失败：{self.stats['tushare_failed']}")
        print(f"  AKShare 备用：{self.stats['akshare_fallback']}")
        print(f"  跳过 (已更新): {self.stats['skipped']}")
        print(f"{'='*60}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare Pro 数据下载器')
    parser.add_argument('--symbols', nargs='+', help='股票代码列表')
    parser.add_argument('--date', help='交易日期 (YYYYMMDD)', default=None)
    parser.add_argument('--all', action='store_true', help='下载所有持仓股票')
    
    args = parser.parse_args()
    
    downloader = TushareProDownloader()
    
    if args.all:
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                account = json.load(f)
                symbols = [pos['symbol'] for pos in account.get('positions', [])]
        else:
            print("❌ 账户文件不存在")
            return
    elif args.symbols:
        symbols = args.symbols
    else:
        print("❌ 请指定股票代码或使用 --all")
        return
    
    downloader.download_daily_bars(symbols, args.date)


if __name__ == '__main__':
    main()
