"""
简化版回测测试

快速验证选股策略功能
"""

from datetime import datetime
from pathlib import Path
import pandas as pd
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.dataset import FundamentalData, FinancialIndicator


def test_strategy_screening():
    """测试策略筛选功能"""
    print("=" * 60)
    print("测试选股策略筛选功能")
    print("=" * 60)
    
    # 1. 加载财务数据
    print("\n1. 加载财务数据...")
    data_dir = Path("./data/mock")
    fundamental_path = data_dir / "fundamental.json"
    
    with open(fundamental_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fd = FundamentalData()
    for vt_symbol, reports in data.items():
        for report_date, ind in reports.items():
            indicator = FinancialIndicator(
                vt_symbol=vt_symbol,
                report_date=ind.get("report_date", report_date),
                pe_ratio=ind.get("pe_ratio"),
                pb_ratio=ind.get("pb_ratio"),
                dividend_yield=ind.get("dividend_yield"),
                roe=ind.get("roe")
            )
            fd.add(indicator)
    
    print(f"  加载了 {fd.get_stock_count()} 只股票")
    
    # 显示所有股票的基本面
    print("\n股票基本面:")
    for symbol in fd.get_symbols():
        ind = fd.get_latest(symbol)
        print(f"  {symbol}: PE={ind.pe_ratio:.1f}, PB={ind.pb_ratio:.1f}, "
              f"股息率={ind.dividend_yield:.1f}%, ROE={ind.roe:.1f}%")
    
    # 2. 创建价值股策略
    print("\n2. 创建价值股策略...")
    strategy = ValueStockStrategy(
        max_pe=20,
        max_pb=3,
        min_dividend_yield=2,
        min_roe=8,
        max_positions=5
    )
    
    print(f"  筛选条件:")
    print(f"    - PE < {strategy.max_pe}")
    print(f"    - PB < {strategy.max_pb}")
    print(f"    - 股息率 > {strategy.min_dividend_yield}%")
    print(f"    - ROE > {strategy.min_roe}%")
    print(f"    - 最大持仓：{strategy.max_positions}")
    
    # 3. 筛选股票
    print("\n3. 执行筛选...")
    stock_pool = fd.get_symbols()
    fundamental_data = {s: fd.get_latest(s) for s in stock_pool}
    
    selected = strategy.screen_stocks(
        stock_pool=stock_pool,
        fundamental_data=fundamental_data,
        current_date=datetime(2024, 6, 1)
    )
    
    print(f"\n  筛选结果：{len(selected)} 只股票")
    for symbol in selected:
        ind = fundamental_data[symbol]
        print(f"    ✓ {symbol}: PE={ind.pe_ratio:.1f}, PB={ind.pb_ratio:.1f}, "
              f"股息率={ind.dividend_yield:.1f}%, ROE={ind.roe:.1f}%")
    
    # 4. 统计
    print("\n" + "=" * 60)
    print("筛选统计")
    print("=" * 60)
    print(f"  候选股票：{len(stock_pool)} 只")
    print(f"  入选股票：{len(selected)} 只")
    print(f"  入选比例：{len(selected)/len(stock_pool)*100:.1f}%")
    
    if selected:
        avg_pe = sum(fundamental_data[s].pe_ratio for s in selected) / len(selected)
        avg_roe = sum(fundamental_data[s].roe for s in selected) / len(selected)
        avg_div = sum(fundamental_data[s].dividend_yield for s in selected) / len(selected)
        print(f"  平均 PE: {avg_pe:.1f}")
        print(f"  平均 ROE: {avg_roe:.1f}%")
        print(f"  平均股息率：{avg_div:.1f}%")
    
    print("\n✓ 策略筛选测试完成！")
    return selected


if __name__ == "__main__":
    test_strategy_screening()
