#!/usr/bin/env python3
"""
性能测试脚本 - 验证优化效果

使用方法:
    python3 test_performance_optimization.py
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from daily_stock_selection import DailyStockSelector


def test_trading_date_cache():
    """测试交易日缓存"""
    print("\n" + "=" * 70)
    print("测试 1: 交易日缓存")
    print("=" * 70)
    
    from tushare_fundamental_fetcher_v2 import TushareBatchFetcher
    
    try:
        fetcher = TushareBatchFetcher()
        
        # 第一次调用 (缓存未命中)
        print("\n【第一次调用】(缓存未命中)")
        start = time.time()
        date1 = fetcher._find_latest_trading_date()
        elapsed1 = time.time() - start
        print(f"耗时：{elapsed1:.3f}秒，结果：{date1}")
        
        # 第二次调用 (缓存命中)
        print("\n【第二次调用】(缓存命中)")
        start = time.time()
        date2 = fetcher._find_latest_trading_date()
        elapsed2 = time.time() - start
        print(f"耗时：{elapsed2:.3f}秒，结果：{date2}")
        
        # 计算性能提升
        if elapsed1 > 0:
            improvement = (1 - elapsed2 / elapsed1) * 100
            print(f"\n✅ 性能提升：{improvement:.1f}%")
        
        return {
            'test': 'trading_date_cache',
            'first_call': elapsed1,
            'second_call': elapsed2,
            'improvement': improvement if elapsed1 > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return {'test': 'trading_date_cache', 'error': str(e)}


def test_batch_fundamentals():
    """测试批量财务数据获取"""
    print("\n" + "=" * 70)
    print("测试 2: 批量财务数据获取")
    print("=" * 70)
    
    from tushare_fundamental_fetcher_v2 import TushareBatchFetcher
    
    try:
        fetcher = TushareBatchFetcher()
        
        # 测试 50 只股票
        test_symbols = [
            '600519_SH', '000001_SZ', '600036_SH', '000858_SZ', '601318_SH',
            '600276_SH', '300750_SZ', '002475_SZ', '601888_SH', '000333_SZ',
            '600000_SH', '600016_SH', '600030_SH', '600048_SH', '600050_SH',
            '600104_SH', '600276_SH', '600309_SH', '600346_SH', '600426_SH',
            '600519_SH', '600547_SH', '600690_SH', '600809_SH', '600887_SH',
            '600900_SH', '601012_SH', '601066_SH', '601088_SH', '601166_SH',
            '601211_SH', '601225_SH', '601288_SH', '601318_SH', '601328_SH',
            '601398_SH', '601601_SH', '601628_SH', '601668_SH', '601688_SH',
            '601766_SH', '601857_SH', '601888_SH', '601919_SH', '601988_SH',
            '603259_SH', '603288_SH', '603606_SH', '603799_SH', '603833_SH'
        ]
        
        print(f"\n测试股票数量：{len(test_symbols)}")
        start = time.time()
        data = fetcher.get_batch_fundamentals(test_symbols)
        elapsed = time.time() - start
        
        print(f"耗时：{elapsed:.3f}秒")
        print(f"成功获取：{len(data)} 只股票数据")
        print(f"平均耗时：{elapsed/len(test_symbols)*1000:.2f}ms/只")
        
        # 显示示例数据
        if data:
            first_symbol = list(data.keys())[0]
            first_data = data[first_symbol]
            print(f"\n示例数据 ({first_symbol}):")
            print(f"  PE: {first_data.get('pe', 'N/A')}")
            print(f"  ROE: {first_data.get('roe', 'N/A')}")
            print(f"  股息率：{first_data.get('dividend_yield', 'N/A')}")
        
        return {
            'test': 'batch_fundamentals',
            'symbols_count': len(test_symbols),
            'elapsed': elapsed,
            'avg_per_symbol_ms': elapsed / len(test_symbols) * 1000,
            'success_count': len(data)
        }
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return {'test': 'batch_fundamentals', 'error': str(e)}


def test_full_selection_flow():
    """测试完整选股流程"""
    print("\n" + "=" * 70)
    print("测试 3: 完整选股流程 (优化后)")
    print("=" * 70)
    
    try:
        selector = DailyStockSelector()
        
        # 步骤 1: 加载股票池
        print("\n【步骤 1】加载股票池")
        start = time.time()
        symbols = selector.load_stocks()
        elapsed = time.time() - start
        print(f"耗时：{elapsed:.3f}秒，加载 {len(symbols)} 只股票")
        
        # 步骤 2: 获取财务数据 (只测试前 50 只)
        print("\n【步骤 2】获取财务数据")
        start = time.time()
        fundamentals = selector.get_real_fundamentals(symbols[:50])
        elapsed = time.time() - start
        print(f"耗时：{elapsed:.3f}秒")
        
        # 步骤 3: 选股
        print("\n【步骤 3】多策略选股")
        start = time.time()
        selector.multi_strategy_selection(symbols[:50], fundamentals, target_count=10)
        elapsed = time.time() - start
        print(f"耗时：{elapsed:.3f}秒")
        
        # 步骤 4: 生成报告
        print("\n【步骤 4】生成报告")
        start = time.time()
        selection_report = selector.save_reports(output_dir='./reports/test')
        elapsed = time.time() - start
        print(f"耗时：{elapsed:.3f}秒")
        
        # 步骤 5: 异步同步 (不等待)
        print("\n【步骤 5】异步同步到飞书")
        start = time.time()
        selector.sync_to_feishu(selection_report)
        elapsed = time.time() - start
        print(f"耗时：{elapsed:.3f}秒 (立即返回)")
        
        total_elapsed = time.time() - start
        print(f"\n✅ 总耗时：{total_elapsed:.3f}秒")
        print(f"✅ 选出股票：{len(selector.selected_stocks)} 只")
        
        return {
            'test': 'full_selection_flow',
            'total_symbols': len(symbols),
            'tested_symbols': 50,
            'selected_count': len(selector.selected_stocks),
            'total_elapsed': total_elapsed
        }
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return {'test': 'full_selection_flow', 'error': str(e)}


def generate_report(results):
    """生成性能测试报告"""
    print("\n" + "=" * 70)
    print("性能测试报告")
    print("=" * 70)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'tests': results,
        'summary': {}
    }
    
    # 总结关键指标
    if 'trading_date_cache' in [r.get('test') for r in results]:
        cache_test = next(r for r in results if r.get('test') == 'trading_date_cache')
        if 'improvement' in cache_test:
            report['summary']['trading_date_cache_improvement'] = f"{cache_test['improvement']:.1f}%"
    
    if 'batch_fundamentals' in [r.get('test') for r in results]:
        batch_test = next(r for r in results if r.get('test') == 'batch_fundamentals')
        if 'elapsed' in batch_test:
            report['summary']['batch_fundamentals_elapsed'] = f"{batch_test['elapsed']:.3f}s"
    
    if 'full_selection_flow' in [r.get('test') for r in results]:
        flow_test = next(r for r in results if r.get('test') == 'full_selection_flow')
        if 'total_elapsed' in flow_test:
            report['summary']['full_flow_elapsed'] = f"{flow_test['total_elapsed']:.3f}s"
    
    # 打印报告
    print("\n📊 关键指标:")
    for key, value in report['summary'].items():
        print(f"  - {key}: {value}")
    
    # 保存报告
    report_file = Path('./reports/performance_test_report.json')
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存：{report_file}")
    
    return report


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "性能优化验证测试")
    print("=" * 70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 运行测试
    results.append(test_trading_date_cache())
    results.append(test_batch_fundamentals())
    results.append(test_full_selection_flow())
    
    # 生成报告
    generate_report(results)
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
