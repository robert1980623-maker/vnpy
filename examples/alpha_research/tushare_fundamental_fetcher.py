#!/usr/bin/env python3
"""
财务数据获取器 (支持 Tushare 和 AKShare)

从 Tushare 或 AKShare 获取真实的财务指标数据，支持缓存
优先使用 Tushare，如果未配置则自动回退到 AKShare
"""

import os
import json
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
    """财务数据获取器 (支持 Tushare 和 AKShare)"""
    
    def __init__(self, cache_dir: str = './cache/fundamental'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'fundamental_cache.json'
        self.cache_meta_file = self.cache_dir / 'cache_meta.json'
        
        # 初始化 Tushare
        token = os.environ.get('TUSHARE_TOKEN', '')
        if token:
            import tushare as ts
            ts.set_token(token)
            self.pro = ts.pro_api()
            self.use_tushare = True
            print("✓ 使用 Tushare 数据源")
        else:
            self.pro = None
            self.use_tushare = False
            print("ℹ Tushare 未配置，将使用 AKShare 数据源")
        
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
    
    def get_daily_basic_tushare(self, symbol: str, trade_date: str = None) -> dict:
        """从 Tushare 获取每日基本指标"""
        if not self.use_tushare:
            return {}
        
        try:
            df = self.pro.daily_basic(ts_code=symbol)
            if df is not None and len(df) > 0:
                return {
                    'pe_ttm': safe_float(df.iloc[0].get('pe_ttm')),
                    'pe': safe_float(df.iloc[0].get('pe')),
                    'pb': safe_float(df.iloc[0].get('pb')),
                    'dividend_yield': safe_float(df.iloc[0].get('dv_ttm')),
                    'total_mv': safe_float(df.iloc[0].get('total_mv')),
                }
        except Exception as e:
            print(f"  ⚠️ Tushare 获取 {symbol} 每日指标失败：{e}")
        
        return {}
    
    def get_daily_basic_akshare(self, symbol: str) -> dict:
        """从 AKShare 获取每日基本指标"""
        try:
            import akshare as ak
            # AKShare 需要去除交易所后缀 (600519.SH -> 600519)
            symbol_no_suffix = symbol.split('.')[0] if '.' in symbol else symbol
            # 获取估值指标
            df = ak.stock_value_em(symbol=symbol_no_suffix)
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                return {
                    'pe_ttm': safe_float(latest.get('PE(TTM)')),
                    'pe': safe_float(latest.get('PE(静)')),
                    'pb': safe_float(latest.get('市净率')),
                    'dividend_yield': None,  # AKShare 不直接提供股息率
                    'total_mv': safe_float(latest.get('总市值')),
                }
        except Exception as e:
            print(f"  ⚠️ AKShare 获取 {symbol} 每日指标失败：{e}")
        
        return {}
    
    def get_daily_basic(self, symbol: str, trade_date: str = None) -> dict:
        """获取每日基本指标（PE、股息率等）"""
        # 检查缓存
        cached = self._load_from_cache(f"{symbol}_daily")
        if cached:
            return cached
        
        # 优先使用 Tushare
        if self.use_tushare:
            data = self.get_daily_basic_tushare(symbol, trade_date)
            if data.get('pe_ttm'):
                self._save_to_cache(f"{symbol}_daily", data)
                return data
        
        # 回退到 AKShare
        data = self.get_daily_basic_akshare(symbol)
        if data.get('pe_ttm'):
            self._save_to_cache(f"{symbol}_daily", data)
        
        return data
    
    def get_financial_indicator_akshare(self, symbol: str) -> dict:
        """从 AKShare 获取财务指标"""
        try:
            import akshare as ak
            # 获取财务分析指标
            df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year='2024')
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                return {
                    'roe': safe_float(latest.get('净资产收益率(%)')),
                    'roe_waa': safe_float(latest.get('净资产收益率(%)')),
                    'revenue_growth': safe_float(latest.get('主营业务收入增长率(%)')),
                    'profit_growth': safe_float(latest.get('净利润增长率(%)')),
                    'report_date': str(latest.get('日期')) if latest.get('日期') is not None else None,
                }
        except Exception as e:
            print(f"  ⚠️ AKShare 获取 {symbol} 财务指标失败：{e}")
        
        return {}
    
    def get_financial_indicator(self, symbol: str, end_date: str = None) -> dict:
        """获取财务指标（ROE、营收增长、利润增长）"""
        # 检查缓存
        cached = self._load_from_cache(f"{symbol}_fina")
        if cached:
            return cached
        
        # Tushare 方式
        if self.use_tushare and self.pro:
            try:
                if end_date:
                    start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=365)).strftime('%Y%m%d')
                else:
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                
                df = self.pro.fina_indicator(ts_code=symbol, start_date=start_date, end_date=end_date)
                if df is not None and len(df) > 0:
                    latest = df.iloc[0]
                    data = {
                        'roe': safe_float(latest.get('roe')),
                        'roe_waa': safe_float(latest.get('roe_waa')),
                        'revenue_growth': safe_float(latest.get('or_yoy')),
                        'profit_growth': safe_float(latest.get('netprofit_yoy')),
                        'report_date': str(latest.get('ann_date')) if latest.get('ann_date') is not None else None,
                    }
                    self._save_to_cache(f"{symbol}_fina", data)
                    return data
            except Exception as e:
                print(f"  ⚠️ Tushare 获取 {symbol} 财务指标失败：{e}")
        
        # 回退到 AKShare
        data = self.get_financial_indicator_akshare(symbol)
        if data.get('roe'):
            self._save_to_cache(f"{symbol}_fina", data)
        
        return data
    
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
            'report_date': str(fina.get('report_date')) if fina.get('report_date') else None,
            'fetch_time': datetime.now().isoformat(),
            'data_source': 'tushare' if self.use_tushare else 'akshare',
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
                print(f"✓ PE={float(data.get('pe', 0) or 0):.2f}, ROE={float(data.get('roe', 0) or 0):.1f}%")
            else:
                print("⚠️ 数据不完整")
        
        return fundamentals


if __name__ == '__main__':
    # 测试
    fetcher = TushareFundamentalFetcher()
    
    test_symbols = ['600066.SH', '600519.SH', '000975.SZ']
    fundamentals = fetcher.get_batch_fundamentals(test_symbols)
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    for symbol, data in fundamentals.items():
        print(f"\n{symbol}:")
        print(f"  数据源：{data.get('data_source', 'unknown')}")
        print(f"  PE(TTM): {data.get('pe', 'N/A')}")
        print(f"  ROE: {data.get('roe', 'N/A')}%")
        print(f"  股息率：{data.get('dividend_yield', 'N/A')}%")
        print(f"  营收增长：{data.get('revenue_growth', 'N/A')}%")
        print(f"  利润增长：{data.get('profit_growth', 'N/A')}%")
