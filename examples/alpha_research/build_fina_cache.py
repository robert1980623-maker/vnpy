#!/usr/bin/env python3
"""
构建全市场财务指标缓存 (一次性运行，约 10 分钟)

从 Tushare 拉取 4627 只股票的财务指标 (ROE/营收增长/利润增长)，
写入本地 JSON 缓存，之后选股直接读缓存，0 秒。

用法:
    TUSHARE_TOKEN=xxx python3 build_fina_cache.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta


def symbol_to_tushare(symbol: str) -> str:
    """CSV 文件名 → Tushare 格式
    002583_sz → 002583.SZ
    300498_SZ → 300498.SZ
    603612_sh → 603612.SH
    603612_SH → 603612.SH
    """
    # 已经是标准格式
    if '.' in symbol:
        return symbol.upper()
    # 带 _sz / _SZ / _sh / _SH 后缀
    sym = symbol.upper()
    if sym.endswith('_SZ'):
        return symbol.replace('_SZ', '.SZ').replace('_sz', '.SZ').replace('_Sz', '.SZ')
    if sym.endswith('_SH'):
        return symbol.replace('_SH', '.SH').replace('_sh', '.SH').replace('_Sh', '.SH')
    # 兜底：按代码判断
    code = symbol.split('_')[0]
    if code.startswith(('6', '9')):
        return f"{code}.SH"
    return f"{code}.SZ"


def safe_float(value, default=None):
    if value is None or value == '' or (isinstance(value, float) and str(value) == 'nan'):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def main():
    cache_dir = Path('./cache/fundamental')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化 Tushare
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        print("❌ 请设置环境变量 TUSHARE_TOKEN")
        return
    
    import tushare as ts
    ts.set_token(token)
    pro = ts.pro_api()
    print("✓ Tushare 已连接")
    
    # 读取股票池
    bars_dir = Path('./data/akshare/bars')
    csv_files = list(bars_dir.glob('*.csv'))
    symbols = [f.stem for f in csv_files]
    print(f"📊 股票池: {len(symbols)} 只")
    
    # 转换为 Tushare 格式
    ts_symbols = {s: symbol_to_tushare(s) for s in symbols}
    
    # 检查是否有旧缓存
    now = datetime.now()
    current_quarter = f"{now.year}Q{(now.month - 1) // 3 + 1}"
    cache_file = cache_dir / f"fina_cache_{current_quarter}.json"
    
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            old_cache = json.load(f)
        print(f"⚠️  已存在缓存 {current_quarter} ({len(old_cache)} 只)")
        resp = input("是否重建？(y/N): ").strip().lower()
        if resp != 'y':
            print("跳过重建")
            return
    
    # 批量拉取
    cache = {}
    start_date = (now - timedelta(days=365)).strftime('%Y%m%d')
    end_date = now.strftime('%Y%m%d')
    
    print(f"🚀 开始拉取财务指标 (start={start_date}, end={end_date})")
    print(f"   预计耗时: ~{len(symbols) * 0.1:.0f} 秒")
    
    t0 = time.time()
    success_count = 0
    fail_count = 0
    
    for i, (sym, ts_code) in enumerate(ts_symbols.items(), 1):
        try:
            df = pro.fina_indicator(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,ann_date,end_date,roe,roe_waa,'
                       'or_yoy,netprofit_yoy,dtprofit_yoy,debt_to_assets,eqt_turnover'
            )
            
            if df is not None and len(df) > 0:
                latest = df.iloc[0]
                cache[sym] = {
                    'ts_code': ts_code,
                    'roe': safe_float(latest.get('roe_waa')) or safe_float(latest.get('roe')),
                    'revenue_growth': safe_float(latest.get('or_yoy')),
                    'profit_growth': safe_float(latest.get('netprofit_yoy')) or safe_float(latest.get('dtprofit_yoy')),
                    'debt_to_assets': safe_float(latest.get('debt_to_assets')),
                    'report_date': str(latest.get('end_date', '')),
                }
                success_count += 1
            else:
                fail_count += 1
            
            # 进度打印
            if i % 500 == 0 or i == len(symbols):
                elapsed = time.time() - t0
                speed = i / elapsed if elapsed > 0 else 0
                eta = (len(symbols) - i) / speed if speed > 0 else 0
                print(f"  [{i}/{len(symbols)}] 成功={success_count}, 失败={fail_count}, 速度={speed:.1f}/s, ETA={eta:.0f}s")
            
            # 延迟 100ms，避免限流（Tushare 免费版限制约 200 次/分钟）
            time.sleep(0.1)
            
        except Exception as e:
            fail_count += 1
            # 如果是限流，等待更久
            if '每分钟' in str(e) or 'limit' in str(e).lower():
                print(f"  ⚠️ 限流，等待 30 秒...")
                time.sleep(30)
                continue
    
    # 写入缓存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    # 写入 meta
    meta_path = cache_dir / "fina_cache_meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, 'r') as f:
            meta = json.load(f)
    meta[current_quarter] = {
        'cached_at': datetime.now().isoformat(),
        'count': len(cache),
        'total_stocks': len(symbols),
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"✅ 缓存构建完成!")
    print(f"   总股票: {len(symbols)}")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")
    print(f"   有财务数据: {len(cache)}")
    print(f"   总耗时: {elapsed:.0f}s ({elapsed/60:.1f} 分钟)")
    print(f"   缓存文件: {cache_file}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
