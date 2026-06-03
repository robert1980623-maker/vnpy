#!/usr/bin/env python3
"""
17:00 数据下载 - 快速版
1. 全市场日线 (Tushare Pro 一次性)
2. CSV → Parquet
3. 消息面数据
4. 宏观政策数据
5. 国际形势数据
"""
import os, sys, json, time
from pathlib import Path
from datetime import datetime

os.environ['TUSHARE_TOKEN'] = '612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5'

import tushare as ts
ts.set_token(os.environ['TUSHARE_TOKEN'])
pro = ts.pro_api()

project_dir = Path(__file__).parent
results = {'start': datetime.now().isoformat(), 'tasks': {}, 'errors': []}
today = datetime.now().strftime('%Y%m%d')
today_fmt = datetime.now().strftime('%Y-%m-%d')

def log_task(name, status, details=None):
    icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {name}: {status}")
    results['tasks'][name] = {'status': status, 'details': details or {}}

# ============================================================
# 1. 全市场日线数据 (Tushare Pro 一次性获取)
# ============================================================
log_task("A股全市场日线", "进行中")
try:
    daily = pro.daily(trade_date=today)
    print(f"  📥 获取 {len(daily)} 条日线数据")
    
    # 保存到 JSON
    data_dir = project_dir / 'data' / 'stock_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    output_file = data_dir / f'daily_{today}.json'
    daily.to_json(output_file, orient='records', force_ascii=False)
    print(f"  💾 保存: {output_file}")
    
    # 更新 CSV 数据
    csv_dir = project_dir / 'data' / 'akshare' / 'bars'
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    updated = 0
    skipped = 0
    for _, row in daily.iterrows():
        code = row['ts_code']
        if '.' in code:
            c, suffix = code.split('.')
            suffix = suffix.lower()
            if suffix == 'sh':
                suffix = 'sh'
            elif suffix == 'sz':
                suffix = 'sz'
            elif suffix == 'bj':
                suffix = 'bj'
            else:
                suffix = 'sh' if c.startswith('6') else 'sz'
        else:
            c = code
            suffix = 'sh' if c.startswith('6') else 'sz'
        
        csv_file = csv_dir / f'{c}_{suffix}.csv'
        
        new_row = {
            'datetime': row['trade_date'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['vol']
        }
        
        import pandas as pd
        new_df = pd.DataFrame([new_row])
        
        if csv_file.exists():
            existing = pd.read_csv(csv_file)
            # 去重: 如果同一天已存在则跳过
            if 'datetime' in existing.columns and existing['datetime'].astype(str).str.contains(row['trade_date']).any():
                skipped += 1
                continue
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined.to_csv(csv_file, index=False)
        else:
            new_df.to_csv(csv_file, index=False)
        updated += 1
    
    # 转换为 Parquet
    print(f"  🔄 CSV → Parquet...")
    lab_dir = Path('/Users/rowang/projects/vnpy/examples/alpha_research/lab/test/daily')
    lab_dir.mkdir(parents=True, exist_ok=True)
    
    parquet_updated = 0
    parquet_errors = 0
    for csv_file in csv_dir.glob('*.csv'):
        try:
            df = pd.read_csv(csv_file)
            if df.empty:
                continue

            # ---- 统一日期列名为 datetime（修复 date/datetime 双列 bug）----
            has_date = 'date' in df.columns
            has_datetime = 'datetime' in df.columns

            if has_date and has_datetime:
                # 脏数据：两列都有，优先用 datetime，缺失用 date 补
                dt_new = pd.to_datetime(
                    df['datetime'].astype(str).str.replace('.0', '', regex=False),
                    format='%Y%m%d', errors='coerce')
                dt_old = pd.to_datetime(
                    df['date'].astype(str).str.replace('.0', '', regex=False),
                    format='%Y%m%d', errors='coerce')
                df['datetime'] = dt_new.combine_first(dt_old)
                df = df.drop(columns=['date'])
            elif has_datetime:
                df['datetime'] = pd.to_datetime(
                    df['datetime'].astype(str).str.replace('.0', '', regex=False),
                    format='%Y%m%d', errors='coerce')
            elif has_date:
                df['datetime'] = pd.to_datetime(
                    df['date'].astype(str).str.replace('.0', '', regex=False),
                    format='%Y%m%d', errors='coerce')
                df = df.drop(columns=['date'])

            if 'datetime' not in df.columns:
                continue
            df = df.dropna(subset=['datetime'])
            if df.empty:
                continue

            # 只保留标准列，排序去重
            needed = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            available = [c for c in needed if c in df.columns]
            df = df[available].copy()
            df = df.sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
            # ---- 日期列统一完毕 ----
            
            code = csv_file.stem  # e.g. "000001_sz"
            c = code.split('_')[0]
            suffix = code.split('_')[1] if '_' in code else ''
            
            if suffix == 'sh':
                parquet_name = f'{c}.SSE.parquet'
            elif suffix == 'sz':
                parquet_name = f'{c}.SZSE.parquet'
            elif suffix == 'bj':
                parquet_name = f'{c}.BSE.parquet'
            else:
                parquet_name = f'{c}.SSE.parquet' if c.startswith('6') else f'{c}.SZSE.parquet'
            
            parquet_file = lab_dir / parquet_name
            df.to_parquet(parquet_file, index=False)
            parquet_updated += 1
        except Exception as e:
            parquet_errors += 1
            if parquet_errors <= 5:
                print(f"    ⚠️ Parquet 转换失败 {csv_file.name}: {e}")
    
    log_task("A股全市场日线", "success", {
        'records': len(daily),
        'csv_updated': updated,
        'csv_skipped': skipped,
        'parquet_updated': parquet_updated,
        'parquet_errors': parquet_errors,
        'trade_date': today_fmt
    })
except Exception as e:
    log_task("A股全市场日线", "error", {'error': str(e)})
    results['errors'].append(f"日线下载失败: {e}")
    print(f"  ❌ {e}")

# ============================================================
# 2. 消息面数据
# ============================================================
log_task("消息面数据", "进行中")
try:
    news_dir = project_dir / 'data' / 'news'
    news_dir.mkdir(parents=True, exist_ok=True)
    
    import akshare as ak
    
    # 财经新闻
    news_items = []
    try:
        # 新浪财经新闻
        df_news = ak.stock_news_em(symbol="300750")  # 用宁德时代作为样本
        if df_news is not None and not df_news.empty:
            news_items = df_news.head(20).to_dict('records')
            print(f"  📰 获取 {len(news_items)} 条财经新闻")
    except Exception as e:
        print(f"  ⚠️ 财经新闻获取异常: {e}")
    
    # 市场新闻 (新浪财经)
    try:
        df_market = ak.stock_info_global_em()
        if df_market is not None and not df_market.empty:
            market_news = df_market.head(30).to_dict('records')
            print(f"  📰 获取 {len(market_news)} 条市场新闻")
    except Exception as e:
        print(f"  ⚠️ 市场新闻获取异常: {e}")
        market_news = []
    
    # 保存
    news_file = news_dir / f'news_{today}.json'
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump({'news': news_items, 'market': market_news, 'date': today_fmt}, f, ensure_ascii=False, indent=2)
    
    log_task("消息面数据", "success", {
        'news_count': len(news_items) + len(market_news),
        'news_file': str(news_file)
    })
except Exception as e:
    log_task("消息面数据", "error", {'error': str(e)})
    results['errors'].append(f"新闻下载失败: {e}")
    print(f"  ❌ {e}")

# ============================================================
# 3. 宏观政策数据
# ============================================================
log_task("宏观政策数据", "进行中")
try:
    from download_daily_policy_data import DailyPolicyDataDownloader
    downloader = DailyPolicyDataDownloader()
    result = downloader.download_all()
    
    log_task("宏观政策数据", "success", {
        'data_types': list(result.get('data', {}).keys()) if isinstance(result, dict) else [],
        'data_dir': str(project_dir / 'data' / 'policy')
    })
except Exception as e:
    log_task("宏观政策数据", "error", {'error': str(e)})
    results['errors'].append(f"政策数据下载失败: {e}")
    print(f"  ❌ {e}")

# ============================================================
# 4. 国际形势数据
# ============================================================
log_task("国际形势数据", "进行中")
try:
    from download_geopolitics_data import GeopoliticsDataDownloader
    geo_downloader = GeopoliticsDataDownloader()
    geo_result = geo_downloader.download_all()
    
    log_task("国际形势数据", "success", {
        'geopolitics_news': geo_result.get('news_count', 0) if geo_result else 0,
        'data_dir': str(project_dir / 'data' / 'geopolitics')
    })
except Exception as e:
    log_task("国际形势数据", "error", {'error': str(e)})
    results['errors'].append(f"国际形势数据下载失败: {e}")
    print(f"  ❌ {e}")

# ============================================================
# 5. 保存日志
# ============================================================
results['end'] = datetime.now().isoformat()
results['duration_seconds'] = (datetime.now() - datetime.fromisoformat(results['start'])).total_seconds()

# 总体状态
success_count = sum(1 for t in results['tasks'].values() if t['status'] == 'success')
total_count = len(results['tasks'])
results['overall'] = 'success' if success_count == total_count else 'partial_success'

log_dir = project_dir / 'logs' / 'daily_download_1700'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f'download_log_{today}.json'
with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

# 更新最新日志
latest_log = log_dir / 'latest_download_log.json'
with open(latest_log, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

# ============================================================
# 打印摘要
# ============================================================
print(f"\n{'='*60}")
print(f"  下载任务摘要")
print(f"{'='*60}")
print(f"  总体状态: {results['overall']}")
print(f"  成功任务: {success_count}/{total_count}")
print(f"  耗时: {results['duration_seconds']:.1f} 秒")

for name, info in results['tasks'].items():
    icon = "✅" if info['status'] == 'success' else "❌"
    print(f"  {icon} {name}: {info['status']}")

if results['errors']:
    print(f"\n  ⚠️ 错误:")
    for e in results['errors']:
        print(f"    - {e}")

print(f"\n  📄 日志: {log_file}")
print(f"{'='*60}")
