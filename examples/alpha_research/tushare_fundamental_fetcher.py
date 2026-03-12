#!/usr/bin/env python3
"""
Tushare 财务数据获取器

从 Tushare 获取真实的财务指标数据，支持缓存
"""

import os
import json
import tushare as ts
from pathlib import Path
from datetime import datetime, timedelta
import time


def safe_float(value, default=None):
    """安全转换为 float"""
    if value is None or value == '' or (isinstance(value, float) and str(value) == 'nan'):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class TushareFundamentalFetcher:
    """Tushare 财务数据获取器"""
    
    def __init__(self, cache_dir: str = './cache/fundamental'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'fundamental_cache.json'
        self.cache_meta_file = self.cache_dir / 'cache_meta.json'
        
        # 初始化 Tushare
        token = os.environ.get('TUSHARE_TOKEN', '')
        if token:
            ts.set_token(token)
            self.pro = ts.pro_api()
            self.use_tushare = True
        else:
            self.pro = None
            self.use_tushare = False
        
        # 加载缓存元数据
        self.cache_meta = self._load_meta()
    
    def _load_meta(self) -> dict:
        """加载缓存元数据"""
        if self.cache_meta_file.exists():
            with open(self.cache_meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_meta(self):
        """保存缓存元数据"""
        with open(self.cache_meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache_meta, f, ensure_ascii=False, indent=2)
    
    def _get_cache_key(self, symbol: str) -> str:
        """获取缓存键"""
        return f"{symbol}_{datetime.now().strftime('%Y%m%d')}"
    
    def _is_cache_valid(self, symbol: str, max_age_hours: int = 24) -> bool:
        """检查缓存是否有效"""
        cache_key = self._get_cache_key(symbol)
        meta = self.cache_meta.get(cache_key)
        if not meta:
            return False
        
        cache_time = datetime.fromisoformat(meta['cache_time'])
        age = datetime.now() - cache_time
        return age.total_seconds() < max_age_hours * 3600
    
    def _load_from_cache(self, symbol: str) -> dict:
        """从缓存加载"""
        cache_key = self._get_cache_key(symbol)
        cache_file = self.cache_dir / f"{symbol}.json"
        
        if cache_file.exists() and self._is_cache_valid(symbol):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _save_to_cache(self, symbol: str, data: dict):
        """保存到缓存"""
        cache_key = self._get_cache_key(symbol)
        cache_file = self.cache_dir / f"{symbol}.json"
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.cache_meta[cache_key] = {
            'cache_time': datetime.now().isoformat(),
            'symbol': symbol
        }
        self._save_meta()
    
    def get_daily_basic(self, symbol: str, trade_date: str = None) -> dict:
        """获取每日基本指标（PE、股息率等）"""
        if not self.use_tushare:
            return {}
        
        # 检查缓存
        cached = self._load_from_cache(f"{symbol}_daily")
        if cached:
            return cached
        
        try:
            # 不指定日期时获取最新数据
            if trade_date:
                df = self.pro.daily_basic(ts_code=symbol, trade_date=trade_date)
            else:
                df = self.pro.daily_basic(ts_code=symbol)  # 获取最新数据
            
            if df is not None and len(df) > 0:
                data = {
                    'pe_ttm': safe_float(df.iloc[0].get('pe_ttm')),
                    'pe': safe_float(df.iloc[0].get('pe')),
                    'pb': safe_float(df.iloc[0].get('pb')),
                    'dividend_yield': safe_float(df.iloc[0].get('dv_ttm')),
                    'total_mv': safe_float(df.iloc[0].get('total_mv')),
                }
                self._save_to_cache(f"{symbol}_daily", data)
                return data
        except Exception as e:
            print(f"  ⚠️ 获取 {symbol} 每日指标失败：{e}")
        
        return {}
    
    def get_financial_indicator(self, symbol: str, end_date: str = None) -> dict:
        """获取财务指标（ROE、营收增长、利润增长）"""
        if not self.use_tushare:
            return {}
        
        # 检查缓存
        cached = self._load_from_cache(f"{symbol}_fina")
        if cached:
            return cached
        
        try:
            # 获取最近一年的数据
            if end_date:
                start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=365)).strftime('%Y%m%d')
            else:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            df = self.pro.fina_indicator(ts_code=symbol, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                latest = df.iloc[0]  # 最新一期
                data = {
                    'roe': safe_float(latest.get('roe')),
                    'roe_waa': safe_float(latest.get('roe_waa')),
                    'revenue_growth': safe_float(latest.get('or_yoy')),
                    'profit_growth': safe_float(latest.get('netprofit_yoy')),
                    'report_date': latest.get('ann_date'),
                }
                self._save_to_cache(f"{symbol}_fina", data)
                return data
        except Exception as e:
            print(f"  ⚠️ 获取 {symbol} 财务指标失败：{e}")
        
        return {}
    
    def get_fundamentals(self, symbol: str, trade_date: str = None) -> dict:
        """获取完整的财务指标数据"""
        # 检查缓存
        cached = self._load_from_cache(symbol)
        if cached:
            return cached
        
        # 获取每日基本指标
        daily = self.get_daily_basic(symbol, trade_date)
        
        # 获取财务指标
        fina = self.get_financial_indicator(symbol, trade_date)
        
        # 合并数据
        fundamentals = {
            'symbol': symbol,
            'pe': daily.get('pe_ttm'),
            'pe_static': daily.get('pe'),
            'pb': daily.get('pb'),
            'dividend_yield': daily.get('dividend_yield'),
            'roe': fina.get('roe_waa') or fina.get('roe'),
            'revenue_growth': fina.get('revenue_growth'),
            'profit_growth': fina.get('profit_growth'),
            'total_mv': daily.get('total_mv'),
            'report_date': fina.get('report_date'),
            'fetch_time': datetime.now().isoformat(),
        }
        
        # 保存到缓存
        self._save_to_cache(symbol, fundamentals)
        
        return fundamentals
    
    def get_batch_fundamentals(self, symbols: list, trade_date: str = None) -> dict:
        """批量获取财务数据"""
        fundamentals = {}
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] 获取 {symbol} 财务数据...", end=' ')
            
            # 添加延迟，避免 API 限流
            if i > 1:
                time.sleep(0.3)
            
            data = self.get_fundamentals(symbol, trade_date)
            fundamentals[symbol] = data
            
            if data.get('pe'):
                print(f"✓ PE={data['pe']:.2f}, ROE={data.get('roe', 0):.1f}%")
            else:
                print("⚠️ 数据不完整")
        
        return fundamentals


if __name__ == '__main__':
    # 测试
    fetcher = TushareFundamentalFetcher()
    
    test_symbols = ['300059.SZ', '600160.SH', '300750.SZ']
    fundamentals = fetcher.get_batch_fundamentals(test_symbols)
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    for symbol, data in fundamentals.items():
        print(f"\n{symbol}:")
        print(f"  PE(TTM): {data.get('pe', 'N/A')}")
        print(f"  ROE: {data.get('roe', 'N/A')}%")
        print(f"  股息率：{data.get('dividend_yield', 'N/A')}%")
        print(f"  营收增长：{data.get('revenue_growth', 'N/A')}%")
        print(f"  利润增长：{data.get('profit_growth', 'N/A')}%")
