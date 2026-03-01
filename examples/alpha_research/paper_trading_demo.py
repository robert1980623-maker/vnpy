"""
模拟交易演示（使用模拟数据）

演示完整的模拟交易流程：
1. 生成模拟数据
2. 创建模拟账户
3. 执行交易
4. 查看持仓和盈亏
5. 保存交易记录
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import random

# 导入模拟交易模块
from paper_trading import PaperTradingAccount


def generate_demo_data(output_dir: str = "./data/mock"):
    """生成演示用的模拟数据"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成 3 只股票的模拟数据
    stocks = [
        ("000001.SZ", "平安银行", 8.0),
        ("600036.SH", "招商银行", 25.0),
        ("600519.SH", "贵州茅台", 1500.0),
    ]
    
    print("生成模拟数据...")
    
    for symbol, name, base_price in stocks:
        # 生成 1 年的日线数据
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq='B')
        
        data = []
        price = base_price
        
        for i, date in enumerate(dates):
            # 随机波动
            change = random.uniform(-0.03, 0.03)
            open_price = price * (1 + random.uniform(-0.01, 0.01))
            close_price = open_price * (1 + change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
            volume = random.randint(1000000, 10000000)
            
            data.append({
                'vt_symbol': symbol,
                'datetime': date,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'volume': volume,
                'turnover': volume * close_price
            })
            
            price = close_price
        
        df = pd.DataFrame(data)
        
        # 保存
        output_file = output_dir / f"{symbol.split('.')[0]}.csv"
        df.to_csv(output_file, index=False)
        print(f"  ✓ {symbol} ({name}): {len(df)} 条数据")
    
    print(f"\n模拟数据已保存到：{output_dir}")
    return output_dir


def run_paper_trading_demo():
    """运行模拟交易演示"""
    print("=" * 70)
    print("股票模拟交易演示")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. 生成模拟数据
    print("\n[1] 生成模拟数据")
    print("-" * 70)
    data_dir = generate_demo_data()
    
    # 2. 创建模拟账户
    print("\n[2] 创建模拟交易账户")
    print("-" * 70)
    account = PaperTradingAccount(
        initial_capital=1_000_000.0,
        data_dir="./data/mock",  # 使用模拟数据目录
        commission_rate=0.0003,  # 万分之三
        slippage=0.01  # 1% 滑点
    )
    
    # 3. 策略信号（简单示例）
    print("\n[3] 策略信号生成")
    print("-" * 70)
    
    # 简单策略：等权重买入 3 只股票
    stocks_to_buy = [
        ("000001.SZ", 0.3),  # 30% 资金
        ("600036.SH", 0.3),  # 30% 资金
        ("600519.SH", 0.4),  # 40% 资金
    ]
    
    # 4. 执行买入
    print("\n[4] 执行买入交易")
    print("-" * 70)
    
    for vt_symbol, weight in stocks_to_buy:
        # 获取价格
        price = account.get_current_price(vt_symbol)
        if price is None:
            print(f"✗ 无法获取 {vt_symbol} 价格")
            continue
        
        # 计算买入数量
        amount = account.initial_capital * weight
        volume = int(amount / price / 100) * 100  # 100 股的整数倍
        
        print(f"\n买入 {vt_symbol}:")
        print(f"  当前价：¥{price:.2f}")
        print(f"  分配资金：¥{amount:,.2f}")
        print(f"  买入数量：{volume}股")
        
        account.buy(vt_symbol, volume=volume)
    
    # 5. 查看持仓
    print("\n[5] 查看持仓")
    print("-" * 70)
    account.print_portfolio_summary()
    
    # 6. 模拟调仓（卖出部分，买入新的）
    print("\n[6] 模拟调仓")
    print("-" * 70)
    
    # 卖出平安银行的一半
    pos = account.get_position("000001.SZ")
    if pos and pos.volume > 0:
        sell_volume = int(pos.volume / 2 / 100) * 100
        print(f"\n卖出 000001.SZ: {sell_volume}股")
        account.sell("000001.SZ", volume=sell_volume)
    
    # 7. 最终概览
    print("\n[7] 最终组合概览")
    print("-" * 70)
    account.print_portfolio_summary()
    
    # 8. 成交历史
    print("\n[8] 成交历史")
    print("-" * 70)
    df = account.get_trade_history()
    if len(df) > 0:
        print(df[['vt_symbol', 'direction', 'price', 'volume', 'commission']].to_string())
    else:
        print("无成交记录")
    
    # 9. 保存记录
    print("\n[9] 保存交易记录")
    print("-" * 70)
    account.save_to_file("./paper_trading_demo")
    
    print("\n" + "=" * 70)
    print("模拟交易演示完成！")
    print("=" * 70)
    
    print("\n下一步:")
    print("  1. 修改策略逻辑（编辑本文件）")
    print("  2. 使用真实数据回测")
    print("  3. 连接 vnpy 主系统进行实盘测试")
    
    return account


if __name__ == "__main__":
    account = run_paper_trading_demo()
