#!/usr/bin/env python3
"""
涨停龙头策略演示脚本

快速测试策略核心功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategies.limit_up_leader import (
    LimitUpLeaderStrategy,
    StockInfo,
    LimitUpStock,
)


def demo_leader_scoring():
    """演示龙头评分计算"""
    print("=" * 60)
    print("🐉 涨停龙头策略 - 评分体系演示")
    print("=" * 60)
    
    strategy = LimitUpLeaderStrategy()
    
    # 创建 3 只不同的涨停股票
    stocks_data = [
        {
            'symbol': '000001',
            'name': '股票 A - 强势龙头',
            'limit_up_days': 5,
            'industry': '人工智能',
            'volume_ratio': 2.5,
            'market_cap': 150e8,
        },
        {
            'symbol': '000002',
            'name': '股票 B - 中等强度',
            'limit_up_days': 3,
            'industry': '人工智能',
            'volume_ratio': 1.8,
            'market_cap': 100e8,
        },
        {
            'symbol': '000003',
            'name': '股票 C - 较弱',
            'limit_up_days': 2,
            'industry': '银行',
            'volume_ratio': 1.2,
            'market_cap': 500e8,
        },
    ]
    
    # 模拟涨停股票列表（用于板块效应计算）
    limit_up_list = [
        StockInfo('000001', 'A', 10, 10, 0, 0, 0, 0, 0, 0, '人工智能', 'AI'),
        StockInfo('000002', 'B', 20, 10, 0, 0, 0, 0, 0, 0, '人工智能', 'AI'),
        StockInfo('000003', 'C', 30, 10, 0, 0, 0, 0, 0, 0, '人工智能', 'AI'),
        StockInfo('000004', 'D', 40, 10, 0, 0, 0, 0, 0, 0, '人工智能', 'AI'),
        StockInfo('000005', 'E', 50, 10, 0, 0, 0, 0, 0, 0, '银行', '金融'),
    ]
    
    print("\n📊 龙头评分计算:\n")
    print(f"{'股票代码':<12} {'股票名称':<20} {'连板数':<8} {'量比':<8} {'市值 (亿)':<10} {'评分':<8}")
    print("-" * 70)
    
    scores = []
    for data in stocks_data:
        stock = LimitUpStock(
            symbol=data['symbol'],
            name=data['name'],
            limit_up_days=data['limit_up_days'],
            first_limit_up_date='',
            last_limit_up_date='20260318',
            industry=data['industry'],
            concept='',
            volume_ratio=data['volume_ratio'],
            amount=0,
            market_cap=data['market_cap'],
        )
        
        score = strategy.calculate_leader_score(stock, limit_up_list)
        stock.score = score
        scores.append(stock)
        
        market_cap_yi = data['market_cap'] / 1e8
        print(f"{data['symbol']:<12} {data['name']:<20} {data['limit_up_days']:<8} "
              f"{data['volume_ratio']:<8.2f} {market_cap_yi:<10.1f} {score:<8.2f}")
    
    # 排序
    scores.sort(key=lambda x: x.score, reverse=True)
    
    print("\n🏆 龙头排名:")
    for i, stock in enumerate(scores, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else ""
        print(f"  {medal} TOP{i}: {stock.symbol} {stock.name.split('-')[0]} - 评分 {stock.score:.2f}")
    
    print("\n💡 评分分析:")
    winner = scores[0]
    print(f"  • 最高评分：{winner.name} ({winner.score:.2f}分)")
    print(f"  • 优势：{winner.limit_up_days}连板 + 量比{winner.volume_ratio:.2f}倍")
    
    loser = scores[-1]
    print(f"  • 最低评分：{loser.name} ({loser.score:.2f}分)")
    print(f"  • 劣势：仅{loser.limit_up_days}连板 + 量比{loser.volume_ratio:.2f}倍 + 市值过大")
    
    return scores


def demo_strategy_config():
    """演示策略配置"""
    print("\n" + "=" * 60)
    print("⚙️  策略配置参数")
    print("=" * 60)
    
    strategy = LimitUpLeaderStrategy()
    config = strategy.config
    
    print(f"""
📋 选股条件:
  • 最小连续涨停天数：{config['min_limit_up_days']}天
  • 成交量放大阈值：{config['volume_ratio_threshold']}倍
  • 市值范围：{config['min_market_cap']/1e8:.0f}亿 - {config['max_market_cap']/1e8:.0f}亿
  • 最大持仓数量：{config['max_position_count']}只

📊 评分权重:
  • 连续涨停天数：{config['leader_score_weights']['limit_up_days']*100:.0f}%
  • 板块效应：{config['leader_score_weights']['industry_effect']*100:.0f}%
  • 成交量放大：{config['leader_score_weights']['volume_ratio']*100:.0f}%
  • 市值偏好：{config['leader_score_weights']['market_cap']*100:.0f}%

💰 风控参数:
  • 止损线：{config['stop_loss_pct']}%
  • 止盈线：{config['take_profit_pct']}%
""")


def demo_signals():
    """演示交易信号生成"""
    print("=" * 60)
    print("📡 交易信号演示")
    print("=" * 60)
    
    strategy = LimitUpLeaderStrategy()
    
    # 模拟持仓
    strategy.positions = {
        '000001': {
            'symbol': '000001',
            'cost_price': 10.0,
            'quantity': 1000,
            'entry_date': '2026-03-17T17:00:00',
        }
    }
    
    # 模拟龙头候选
    strategy.leader_candidates = [
        LimitUpStock('000002', '新股 1', 3, '', '20260318', '科技', '', 2.0, 0, 100e8, 80.0),
        LimitUpStock('000003', '新股 2', 2, '', '20260318', '科技', '', 1.8, 0, 80e8, 70.0),
    ]
    
    # 模拟当前价格
    current_prices = {
        '000001': 9.0,   # 亏损 10%，触发止损
        '000002': 20.0,
        '000003': 15.0,
    }
    
    signals = strategy.generate_signals(current_prices)
    
    print(f"\n生成 {len(signals)} 个交易信号:\n")
    
    for signal in signals:
        action_icon = "🟢 买入" if signal.action == 'buy' else "🔴 卖出"
        print(f"{action_icon}: {signal.symbol}")
        print(f"  价格：¥{signal.price:.2f}")
        print(f"  数量：{signal.quantity}股")
        print(f"  原因：{signal.reason}")
        print(f"  置信度：{signal.confidence*100:.0f}%")
        print()


if __name__ == '__main__':
    print("\n" + "🚀" * 30)
    print("涨停龙头策略演示系统")
    print("🚀" * 30 + "\n")
    
    # 演示 1: 评分体系
    scores = demo_leader_scoring()
    
    # 演示 2: 配置参数
    demo_strategy_config()
    
    # 演示 3: 交易信号
    demo_signals()
    
    print("=" * 60)
    print("✅ 演示完成")
    print("=" * 60)
    print("\n📚 更多信息请查看：docs/LIMIT_UP_STRATEGY.md")
    print("🚀 运行策略：python3 limit_up_strategy_runner.py --auto --notify\n")
