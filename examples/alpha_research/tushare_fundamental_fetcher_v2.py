#!/usr/bin/env python3
"""
财务数据批量获取器 v2.1 - daily_basic + 本地缓存

优化策略：
1. daily_basic: 1 次 API 拉全市场 PE/PB/股息率/总市值 (0.25s)
2. fina_indicator: 财务指标季度更新，使用本地 JSON 缓存 (0s)
   - 缓存文件：cache/fundamental/fina_cache_2026Q2.json
   - 缓存有效期：当前季度数据，72 小时

整体耗时：~1 秒（vs 旧版 20-40 分钟）
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


def safe_float(value, default=None):
    if value is None or value == '' or (isinstance(value, float) and str(value) == 'nan'):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def symbol_to_tushare(symbol: str) -> str:
    """CSV 文件名 → Tushare 格式
    002583_sz → 002583.SZ
    300498_SZ → 300498.SZ
    603612_sh → 603612.SH
    603612_SH → 603612.SH
    """
    if '.' in symbol:
        return symbol.upper()
    sym = symbol.upper()
    if sym.endswith('_SZ'):
        return symbol.replace('_SZ', '.SZ').replace('_sz', '.SZ').replace('_Sz', '.SZ')
    if sym.endswith('_SH'):
        return symbol.replace('_SH', '.SH').replace('_sh', '.SH').replace('_Sh', '.SH')
    code = symbol.split('_')[0] if '_' in symbol else symbol
    if code.startswith(('6', '9')):
        return f"{code}.SH"
    return f"{code}.SZ"


class TushareBatchFetcher:
    """Tushare 批量财务数据获取器"""
    
    def __init__(self, cache_dir: str = './cache/fundamental'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        token = os.environ.get('TUSHARE_TOKEN', '').strip()
        
        # Fallback: load from .env file (needed when running in cron/isolated sessions)
        if not token:
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                try:
                    from dotenv import dotenv_values
                    env_vars = dotenv_values(str(env_path))
                    token = env_vars.get('TUSHARE_TOKEN', '').strip()
                    if token:
                        print(f"✓ TUSHARE_TOKEN 从 .env 文件加载")
                except ImportError:
                    # If dotenv not available, try manual parsing
                    try:
                        with open(env_path) as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('TUSHARE_TOKEN=') and not line.startswith('#'):
                                    token = line.split('=', 1)[1].strip().strip('"').strip("'")
                                    if token:
                                        print(f"✓ TUSHARE_TOKEN 从 .env 文件加载（手动解析）")
                                    break
                    except Exception:
                        pass
        
        if not token:
            raise ValueError("环境变量 TUSHARE_TOKEN 未设置（也未在 .env 文件中找到）")
        
        import tushare as ts
        ts.set_token(token)
        self.pro = ts.pro_api()
        print("✓ Tushare 数据源已初始化（批量模式）")
        
        # 财务指标缓存（懒加载）
        self._fina_cache: Optional[dict] = None
    
    # ------------------------------------------------------------------ #
    #  批量获取入口
    # ------------------------------------------------------------------ #
    def get_batch_fundamentals(self, symbols: list, trade_date: str = None) -> dict:
        """
        批量获取财务数据
        
        Args:
            symbols: 股票代码列表（支持 CSV 文件名格式：002583_sz）
            trade_date: 交易日期 YYYYMMDD，默认自动找最近交易日
        
        Returns:
            {symbol: {pe, roe, revenue_growth, profit_growth, dividend_yield, ...}}
        """
        trade_date = trade_date or self._find_latest_trading_date()
        print(f"\n  📥 批量获取财务数据 (交易日：{trade_date})")
        
        # 1. 拉取 daily_basic（全市场 1 次 API）
        daily_map = self._fetch_daily_basic(trade_date)
        
        # 2. 加载财务指标缓存
        fina_map = self._load_fina_cache()
        
        # 3. 合并
        result = {}
        for sym in symbols:
            ts_sym = symbol_to_tushare(sym)
            daily = daily_map.get(ts_sym, {})
            fina = fina_map.get(sym, {})  # 缓存用原始 symbol
            
            merged = {
                'symbol': sym,
                'ts_code': ts_sym,
                'pe': daily.get('pe_ttm') or daily.get('pe'),
                'pe_static': daily.get('pe'),
                'pb': daily.get('pb'),
                'dividend_yield': daily.get('dividend_yield') or daily.get('dv_ttm'),
                'total_mv': daily.get('total_mv'),
                'circ_mv': daily.get('circ_mv'),
                'roe': fina.get('roe'),
                'revenue_growth': fina.get('revenue_growth'),
                'profit_growth': fina.get('profit_growth'),
                'debt_to_assets': fina.get('debt_to_assets'),
                'report_date': fina.get('report_date'),
                'fetch_time': datetime.now().isoformat(),
                'data_source': 'tushare_batch_v2',
            }
            result[sym] = merged
        
        return result
    
    # ------------------------------------------------------------------ #
    #  daily_basic - 全市场 1 次 API
    # ------------------------------------------------------------------ #
    def _fetch_daily_basic(self, trade_date: str) -> dict:
        """拉取全市场 daily_basic"""
        print(f"    [1/2] 拉取 daily_basic 全市场...", end=' ')
        try:
            df = self.pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,pe,pe_ttm,pb,dv_ttm,total_mv,circ_mv'
            )
            if df is not None and len(df) > 0:
                result = {}
                for _, row in df.iterrows():
                    code = row.get('ts_code', '')
                    if code:
                        result[code] = {
                            'pe_ttm': safe_float(row.get('pe_ttm')),
                            'pe': safe_float(row.get('pe')),
                            'pb': safe_float(row.get('pb')),
                            'dividend_yield': safe_float(row.get('dv_ttm')),
                            'total_mv': safe_float(row.get('total_mv')),
                            'circ_mv': safe_float(row.get('circ_mv')),
                        }
                print(f"✅ {len(result)} 只")
                return result
            else:
                print("⚠️ 无数据（可能非交易日）")
                return {}
        except Exception as e:
            print(f"❌ {e}")
            return {}
    
    # ------------------------------------------------------------------ #
    #  财务指标缓存
    # ------------------------------------------------------------------ #
    def _load_fina_cache(self) -> dict:
        """加载财务指标缓存"""
        if self._fina_cache is not None:
            return self._fina_cache
        
        now = datetime.now()
        current_quarter = f"{now.year}Q{(now.month - 1) // 3 + 1}"
        cache_file = self.cache_dir / f"fina_cache_{current_quarter}.json"
        
        # 尝试加载缓存
        if cache_file.exists():
            try:
                meta_path = self.cache_dir / "fina_cache_meta.json"
                if meta_path.exists():
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    cached_at = meta.get(current_quarter, {}).get('cached_at', '')
                    if cached_at:
                        cache_dt = datetime.fromisoformat(cached_at)
                        if now - cache_dt < timedelta(hours=72):
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                self._fina_cache = json.load(f)
                            print(f"    [2/2] 财务指标缓存命中 ({current_quarter}), {len(self._fina_cache)} 只 ✅")
                            return self._fina_cache
            except Exception as e:
                print(f"    ⚠️  读取缓存失败：{e}")
        
        # 缓存不存在或过期，返回空（选股时跳过 ROE 等指标）
        print(f"    [2/2] 财务指标缓存未找到或过期，将使用纯 daily_basic 选股")
        return {}
    
    # ------------------------------------------------------------------ #
    #  交易日查询 (带缓存)
    # ------------------------------------------------------------------ #
    def _find_latest_trading_date(self) -> str:
        """找最近的交易日 (带 24 小时缓存)"""
        # 先查缓存
        cache_file = self.cache_dir / "trading_date_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                cached_date = cache.get('latest_date', '')
                cached_at = cache.get('cached_at', 0)
                # 缓存有效期 24 小时
                if cached_date and (datetime.now().timestamp() - cached_at) < 86400:
                    print(f"    📅 交易日缓存命中：{cached_date}")
                    return cached_date
            except Exception as e:
                print(f"    ⚠️  读取交易日缓存失败：{e}")
        
        # 缓存未命中，执行查询
        print(f"    📅 查询最近交易日...", end=' ')
        for d in range(0, 7):
            date = (datetime.now() - timedelta(days=d)).strftime('%Y%m%d')
            try:
                df = self.pro.daily_basic(trade_date=date, fields='ts_code')
                if df is not None and len(df) > 0:
                    # 写入缓存
                    with open(cache_file, 'w') as f:
                        json.dump({
                            'latest_date': date,
                            'cached_at': datetime.now().timestamp()
                        }, f)
                    print(f"✅ {date} (已缓存)")
                    return date
            except Exception:
                continue
        
        fallback_date = datetime.now().strftime('%Y%m%d')
        print(f"⚠️  使用当前日期：{fallback_date}")
        return fallback_date
    
    # ------------------------------------------------------------------ #
    #  单只查询（兼容旧接口）
    # ------------------------------------------------------------------ #
    def get_fundamentals(self, symbol: str, trade_date: str = None) -> dict:
        symbol = symbol_to_tushare(symbol)
        batch = self.get_batch_fundamentals([symbol], trade_date)
        return batch.get(symbol, {})
    
    # ------------------------------------------------------------------ #
    #  缓存管理
    # ------------------------------------------------------------------ #
    def clear_old_cache(self, keep_quarters: int = 2):
        """清理过期季度缓存"""
        now = datetime.now()
        current_q = (now.year, (now.month - 1) // 3 + 1)
        
        for f in self.cache_dir.glob("fina_cache_*.json"):
            name = f.stem.replace("fina_cache_", "")
            try:
                y, q = name.split('Q')
                cache_q = (int(y), int(q))
                q_diff = (current_q[0] - cache_q[0]) * 4 + (current_q[1] - cache_q[1])
                if q_diff > keep_quarters:
                    f.unlink()
                    print(f"  🧹 清理过期缓存：{f.name}")
            except Exception:
                pass


# ------------------------------------------------------------------ #
#  CLI 测试
# ------------------------------------------------------------------ #
if __name__ == '__main__':
    import time
    
    fetcher = TushareBatchFetcher()
    
    # 测试：拉 10 只股票（CSV 格式）
    test_symbols = ['600519_SH', '000001_SZ', '600036_SH', '000858_SZ', '601318_SH',
                    '600276_SH', '300750_SZ', '002475_SZ', '601888_SH', '000333_SZ']
    
    t0 = time.time()
    data = fetcher.get_batch_fundamentals(test_symbols)
    elapsed = time.time() - t0
    
    print(f"\n⏱️  总耗时：{elapsed:.2f}s")
    print(f"\n{'代码':<15} {'PE':>8} {'ROE':>8} {'股息率':>8} {'营收增长':>10}")
    print("-" * 55)
    for sym in test_symbols:
        d = data.get(sym, {})
        pe = d.get('pe')
        if pe:
            roe_str = f"{d.get('roe') or 0:>7.1f}%" if d.get('roe') else "N/A"
            div_str = f"{(d.get('dividend_yield') or 0):>7.1f}%" if d.get('dividend_yield') else "N/A"
            rev_str = f"{(d.get('revenue_growth') or 0):>9.1f}%" if d.get('revenue_growth') else "N/A"
            print(f"{sym:<15} {pe:>8.1f} {roe_str:>8} {div_str:>8} {rev_str:>10}")
        else:
            print(f"{sym:<15} PE=N/A")
