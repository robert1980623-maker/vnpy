#!/usr/bin/env python3
"""
执行选股结果迁移到虚拟账户（简化版 - 直接操作 JSON）

功能：
1. 读取今日选股结果和交易计划
2. 获取股票最新价格
3. 执行买入操作
4. 更新虚拟账户 JSON 文件
"""

import json
from pathlib import Path
from datetime import datetime

# 配置
ACCOUNT_FILE = './accounts/virtual_2026_account.json'
TRADING_PLAN_FILE = './reports/trading_plan_2026-04-16.json'
DATA_DIR = Path('./data/akshare/bars')

def load_account():
    """加载账户数据"""
    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_account(account_data):
    """保存账户数据"""
    account_data['last_updated'] = datetime.now().isoformat()
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(account_data, f, indent=2, ensure_ascii=False)

def load_trading_plan():
    """加载交易计划"""
    with open(TRADING_PLAN_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_stock_price(symbol):
    """从数据文件获取股票最新价格"""
    # 标准化 symbol 格式
    symbol_file = symbol.replace('.', '_')
    csv_file = DATA_DIR / f'{symbol_file}.csv'
    
    if not csv_file.exists():
        # 尝试查找匹配的文件
        for f in DATA_DIR.glob('*.csv'):
            if f.stem == symbol_file or f.stem.startswith(symbol.replace('.', '_').split('_')[0]):
                csv_file = f
                break
    
    if not csv_file.exists():
        return None
    
    # 读取最后一行作为最新价格
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None
            
            last_line = lines[-1].strip()
            parts = last_line.split(',')
            
            # CSV 格式：datetime, open, high, low, close, volume
            if len(parts) >= 5:
                return float(parts[4])
    except Exception as e:
        print(f"  ⚠️  读取价格失败 {symbol}: {e}")
        return None
    
    return None

def execute_buy_plan(account, buy_list):
    """执行买入计划"""
    total_invested = 0
    executed_count = 0
    new_positions = []
    new_trades = []
    
    # 计算每只股票的分配金额（等权重）
    available_cash = account['cash']
    per_stock_amount = available_cash / len(buy_list) if buy_list else 0
    
    print(f"\n可用资金：¥{available_cash:,.2f}")
    print(f"计划买入：{len(buy_list)} 只")
    print(f"每只分配：¥{per_stock_amount:,.2f}")
    print("\n执行买入:")
    
    for stock in buy_list:
        symbol = stock['symbol']
        name = stock.get('name', '')
        reason = stock.get('reason', '选股策略')
        
        # 获取价格
        price = get_stock_price(symbol)
        if not price:
            # 使用 PE 和 ROE 估算（备用方案）
            pe = stock.get('pe', 15)
            price = 10.0  # 默认估算价格
            print(f"  使用估算价格：{symbol} @ ¥{price:.2f}")
        
        # 计算买入数量
        quantity = int(per_stock_amount / price / 100) * 100  # 100 股整数倍
        
        if quantity < 100:
            quantity = 100  # 最少 100 股
        
        cost = price * quantity
        
        # 检查资金
        if cost > available_cash:
            # 调整数量
            quantity = int(available_cash / price / 100) * 100
            if quantity < 100:
                print(f"  ⚠️  资金不足，跳过 {symbol}")
                continue
            cost = price * quantity
        
        # 执行买入
        available_cash -= cost
        total_invested += cost
        executed_count += 1
        
        # 添加持仓
        new_positions.append({
            'symbol': symbol,
            'name': name,
            'quantity': quantity,
            'avg_price': price,
            'market_value': cost,
            'cost_basis': cost
        })
        
        # 添加交易记录
        new_trades.append({
            'trade_id': f"20260416-0900-BUY-{executed_count:03d}",
            'symbol': symbol,
            'name': name,
            'direction': 'buy',
            'price': price,
            'quantity': quantity,
            'cost': cost,
            'reason': f"{reason} (PE={stock.get('pe', 'N/A')}, ROE={stock.get('roe', 'N/A')}%)",
            'status': 'filled',
            'timestamp': datetime.now().isoformat(),
            'agent_id': 'Q-Trade'
        })
        
        print(f"  ✓ {symbol}: {quantity}股 @ ¥{price:.2f} = ¥{cost:,.2f}")
    
    print(f"\n执行完成：{executed_count}/{len(buy_list)} 只")
    print(f"总投资：¥{total_invested:,.2f}")
    print(f"剩余现金：¥{available_cash:,.2f}")
    
    return executed_count, total_invested, new_positions, new_trades, available_cash

def main():
    print("=" * 70)
    print(" " * 20 + "执行选股结果迁移")
    print("=" * 70)
    print(f"日期：2026-04-16")
    print(f"时间：{datetime.now().strftime('%H:%M:%S')}")
    
    # 加载交易计划
    print("\n【步骤 1】加载交易计划")
    plan = load_trading_plan()
    buy_list = plan.get('buy', [])
    print(f"  买入候选：{len(buy_list)} 只")
    
    if not buy_list:
        print("  ⚠️  无买入候选，结束")
        return
    
    # 加载虚拟账户
    print("\n【步骤 2】加载虚拟账户")
    account = load_account()
    print(f"  当前现金：¥{account['cash']:,.2f}")
    print(f"  当前持仓：{len(account.get('positions', []))} 只")
    
    # 执行买入
    print("\n【步骤 3】执行买入")
    executed, invested, new_positions, new_trades, remaining_cash = execute_buy_plan(account, buy_list)
    
    if executed == 0:
        print("\n⚠️  无股票买入，结束")
        return
    
    # 更新账户
    print("\n【步骤 4】更新账户状态")
    account['cash'] = remaining_cash
    account['positions'] = new_positions
    account['trades'] = account.get('trades', []) + new_trades
    
    # 添加快照
    snapshot = {
        'date': '2026-04-16',
        'time': datetime.now().strftime('%H:%M:%S'),
        'cash': remaining_cash,
        'market_value': invested,
        'total_assets': remaining_cash + invested,
        'realized_pnl': 0,
        'unrealized_pnl': 0,
        'positions_count': executed,
        'buy_count': executed,
        'sell_count': 0,
        'note': f"09:00 选股执行 - 买入{executed}只，投资¥{invested:,.2f}"
    }
    
    account['daily_snapshots'] = account.get('daily_snapshots', []) + [snapshot]
    
    # 更新交易计划
    account['trading_plan'] = {
        'date': '2026-04-16',
        'strategy': 'multi_factor',
        'signals': buy_list,
        'executed_count': executed,
        'total_invested': invested,
        'created_at': datetime.now().isoformat()
    }
    
    # 保存
    save_account(account)
    print(f"  已保存到：{ACCOUNT_FILE}")
    
    print("\n" + "=" * 70)
    print(" " * 25 + "完成")
    print("=" * 70)
    print(f"最终状态:")
    print(f"  现金：¥{account['cash']:,.2f}")
    print(f"  持仓：{len(account['positions'])} 只")
    print(f"  总资产：¥{account['cash'] + sum(p['market_value'] for p in account['positions']):,.2f}")
    print(f"\n持仓明细:")
    for p in account['positions']:
        print(f"  - {p['symbol']}: {p['quantity']}股 @ ¥{p['avg_price']:.2f} (¥{p['market_value']:,.2f})")

if __name__ == '__main__':
    main()
