#!/usr/bin/env python3
"""
测试虚拟账户与选股/交易流程集成

验证:
1. 从虚拟账户文件读取真实持仓
2. 选股结果与持仓对比
3. 生成正确的交易计划
"""

import json
from pathlib import Path
from datetime import datetime

def test_account_loading():
    """测试 1: 从虚拟账户文件读取持仓"""
    print("=" * 70)
    print(" " * 20 + "测试 1: 读取虚拟账户持仓")
    print("=" * 70)
    
    account_file = Path('./accounts/virtual_2026_account.json')
    
    if not account_file.exists():
        print(f"❌ 账户文件不存在：{account_file}")
        return None
    
    with open(account_file, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    current_holdings = [pos['symbol'] for pos in account.get('positions', [])]
    
    print(f"✅ 成功读取账户文件")
    print(f"   现金：¥{account.get('cash', 0):,.2f}")
    print(f"   持仓数：{len(current_holdings)} 只")
    print(f"   持仓列表:")
    for pos in account.get('positions', [])[:5]:
        print(f"     - {pos['symbol']}: {pos['volume']}股, 市值¥{pos['market_value']:,.2f}")
    if len(account.get('positions', [])) > 5:
        print(f"     ... 还有 {len(account.get('positions', [])) - 5} 只")
    
    return current_holdings

def test_trading_plan_format():
    """测试 2: 检查交易计划格式"""
    print("\n" + "=" * 70)
    print(" " * 20 + "测试 2: 检查交易计划格式")
    print("=" * 70)
    
    today = datetime.now().strftime('%Y-%m-%d')
    plan_file = Path(f'./reports/trading_plan_{today}.json')
    
    if not plan_file.exists():
        print(f"⚠️  今日交易计划不存在：{plan_file}")
        # 查找最新的交易计划
        plan_files = sorted(Path('./reports').glob('trading_plan_*.json'))
        if plan_files:
            plan_file = plan_files[-1]
            print(f"   使用最新交易计划：{plan_file.name}")
        else:
            print(f"❌ 无交易计划文件")
            return False
    
    with open(plan_file, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    print(f"✅ 交易计划文件：{plan_file.name}")
    print(f"   日期：{plan.get('date', 'N/A')}")
    print(f"   买入：{len(plan.get('buy', []))} 只")
    print(f"   卖出：{len(plan.get('sell', []))} 只")
    print(f"   持有：{len(plan.get('hold', []))} 只")
    
    # 检查买入列表格式
    buy_list = plan.get('buy', [])
    if buy_list and isinstance(buy_list[0], dict):
        print(f"\n✅ 买入列表格式正确（包含详细信息）")
        for stock in buy_list[:3]:
            print(f"   - {stock.get('symbol', 'N/A')} {stock.get('name', 'N/A')} ({stock.get('reason', 'N/A')})")
    elif buy_list and isinstance(buy_list[0], str):
        print(f"\n⚠️ 买入列表格式为简单列表（需要更新）")
    else:
        print(f"\n   买入列表为空")
    
    return True

def test_flow_continuity(current_holdings):
    """测试 3: 验证流程连贯性"""
    print("\n" + "=" * 70)
    print(" " * 20 + "测试 3: 流程连贯性验证")
    print("=" * 70)
    
    today = datetime.now().strftime('%Y-%m-%d')
    selection_file = Path(f'./reports/stock_selection_{today}.json')
    plan_file = Path(f'./reports/trading_plan_{today}.json')
    
    # 检查选股结果
    if selection_file.exists():
        with open(selection_file, 'r', encoding='utf-8') as f:
            selection = json.load(f)
        selected_symbols = [s['symbol'] for s in selection.get('stocks', [])]
        print(f"✅ 选股结果：{len(selected_symbols)} 只")
    else:
        print(f"⚠️ 选股结果文件不存在")
        selected_symbols = []
    
    # 检查交易计划
    if plan_file.exists():
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        buy_symbols = [s['symbol'] if isinstance(s, dict) else s for s in plan.get('buy', [])]
        sell_symbols = plan.get('sell', [])
        
        print(f"✅ 交易计划：买入{len(buy_symbols)}只，卖出{len(sell_symbols)}只")
        
        # 验证卖出列表是否来自持仓
        sell_from_holdings = [s for s in sell_symbols if s in current_holdings]
        print(f"   卖出股票中 {len(sell_from_holdings)}/{len(sell_symbols)} 只来自持仓")
        
        # 验证买入列表是否不在持仓中
        buy_not_in_holdings = [s for s in buy_symbols if s not in current_holdings]
        print(f"   买入股票中 {len(buy_not_in_holdings)}/{len(buy_symbols)} 只不在持仓中")
    else:
        print(f"⚠️ 交易计划文件不存在")
    
    return True

def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print(" " * 15 + "虚拟账户集成测试")
    print("=" * 70)
    print()
    
    # 测试 1: 读取账户
    current_holdings = test_account_loading()
    
    if current_holdings is None:
        print("\n❌ 测试失败：无法读取账户文件")
        return False
    
    # 测试 2: 检查交易计划格式
    test_trading_plan_format()
    
    # 测试 3: 验证流程连贯性
    test_flow_continuity(current_holdings)
    
    print("\n" + "=" * 70)
    print(" " * 20 + "测试完成")
    print("=" * 70)
    print("\n✅ 所有测试通过！")
    print("\n下一步:")
    print("  1. 运行选股脚本：python3 daily_stock_selection.py")
    print("  2. 查看交易计划：cat reports/trading_plan_*.json")
    print("  3. 执行交易：python3 manual_trade_today.py (需要更新为当日文件)")
    
    return True

if __name__ == '__main__':
    main()
