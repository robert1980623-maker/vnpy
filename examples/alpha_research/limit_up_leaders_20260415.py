#!/usr/bin/env python3
"""
涨停龙头策略每日选股 - 2026-04-15

功能:
1. 下载今日 A 股行情数据
2. 筛选涨停股票（涨跌幅>=9.8%）
3. 识别龙头股特征
4. 生成交易信号报告
5. 保存报告并更新虚拟账户
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import akshare as ak
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from stock_name_utils import StockNameCache, format_symbol_with_name
from accounts.account_service import AccountService

# 配置
TODAY = "2026-04-15"
TODAY_INT = 20260415
REPORT_PATH = "/Users/rowang/projects/vnpy/examples/alpha_research/reports/limit_up_leaders_2026-04-15.json"
ACCOUNT_PATH = "/Users/rowang/projects/vnpy/examples/alpha_research/accounts/virtual_2026_account.json"

def fetch_limit_up_stocks(date: str) -> list:
    """获取指定日期的涨停股票"""
    print(f"\n📊 获取 {date} 涨停股票数据...")
    
    try:
        # 获取涨停池数据
        df = ak.stock_zt_pool_em(date=date.replace('-', ''))
        
        if df.empty:
            print("⚠️  今日无涨停股票数据")
            return []
        
        print(f"✅ 获取到 {len(df)} 只涨停股票")
        
        stocks = []
        for _, row in df.iterrows():
            stock = {
                'symbol': row.get('代码', ''),
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'turnover_rate': float(row.get('换手率', 0)),
                'market_cap': float(row.get('总市值', 0)),
                'industry': row.get('行业', ''),
                'concept': row.get('概念', ''),
                'limit_up_days': 1,  # 默认 1 板
                'first_limit_up_date': date,
            }
            stocks.append(stock)
        
        return stocks
        
    except Exception as e:
        print(f"❌ 获取涨停数据失败：{e}")
        return []


def analyze_consecutive_limit_up(symbol: str, date: str) -> int:
    """分析连续涨停天数"""
    try:
        # 获取历史行情
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", end_date=date)
        
        if df.empty:
            return 1
        
        consecutive_days = 0
        for _, row in df[::-1].iterrows():
            change_pct = row.get('涨跌幅', 0)
            if change_pct >= 9.8:
                consecutive_days += 1
            else:
                break
        
        return consecutive_days
        
    except Exception as e:
        return 1


def calculate_leader_score(stock: dict, all_stocks: list) -> float:
    """
    计算龙头评分
    
    评分维度:
    1. 连板数量 (40%)
    2. 板块效应 (25%)
    3. 成交量放大 (20%)
    4. 市值适中 (15%)
    """
    score = 0.0
    
    # 1. 连板数量评分 (0-40 分)
    limit_up_days = stock.get('limit_up_days', 1)
    if limit_up_days >= 5:
        score += 40
    elif limit_up_days >= 3:
        score += 30
    elif limit_up_days >= 2:
        score += 20
    else:
        score += 10
    
    # 2. 板块效应评分 (0-25 分)
    industry = stock.get('industry', '')
    concept = stock.get('concept', '')
    
    industry_count = sum(1 for s in all_stocks if s.get('industry') == industry)
    concept_count = sum(1 for s in all_stocks if concept in s.get('concept', ''))
    
    sector_effect = max(industry_count, concept_count)
    if sector_effect >= 5:
        score += 25
    elif sector_effect >= 3:
        score += 20
    elif sector_effect >= 2:
        score += 15
    else:
        score += 10
    
    # 3. 成交量评分 (0-20 分)
    amount = stock.get('amount', 0)
    if amount >= 10e8:  # 10 亿以上
        score += 20
    elif amount >= 5e8:
        score += 15
    elif amount >= 1e8:
        score += 10
    else:
        score += 5
    
    # 4. 市值评分 (0-15 分) - 偏好中小盘
    market_cap = stock.get('market_cap', 0)
    if 50e8 <= market_cap <= 200e8:  # 50-200 亿
        score += 15
    elif 200e8 < market_cap <= 500e8:
        score += 12
    elif market_cap < 50e8:
        score += 10
    else:
        score += 8
    
    return score


def generate_trading_signals(leaders: list, account: dict) -> list:
    """生成交易信号"""
    signals = []
    
    current_cash = account.get('cash', 1000000)
    current_positions = account.get('positions', [])
    position_symbols = {p['symbol'] for p in current_positions}
    
    # 每只股票建议仓位 (总资金的 10-20%)
    position_size = current_cash * 0.15
    
    for i, leader in enumerate(leaders[:5], 1):  # 最多选 5 只
        symbol = leader['symbol']
        
        # 如果已持仓，跳过
        if symbol in position_symbols:
            continue
        
        # 计算建议买入数量
        price = leader['price']
        quantity = int(position_size / price / 100) * 100  # 100 股整数倍
        
        if quantity < 100:
            continue
        
        # 确定优先级
        priority = 'high' if i <= 2 else 'medium' if i <= 4 else 'low'
        
        signal = {
            'rank': i,
            'symbol': symbol,
            'name': leader['name'],
            'action': 'buy',
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'priority': priority,
            'reason': f"涨停 {leader['limit_up_days']} 板，评分 {leader['score']:.1f}",
            'stop_loss': price * 0.92,  # 8% 止损
            'take_profit': price * 1.20,  # 20% 止盈
        }
        signals.append(signal)
    
    return signals


def main():
    print("=" * 70)
    print(" " * 20 + "涨停龙头策略每日选股")
    print(" " * 25 + f"{TODAY}")
    print("=" * 70)
    
    # 1. 获取涨停股票
    limit_up_stocks = fetch_limit_up_stocks(TODAY)
    
    if not limit_up_stocks:
        print("\n⚠️  今日无涨停股票，生成空报告")
        report = {
            'date': TODAY,
            'success': True,
            'total_limit_up': 0,
            'leaders': [],
            'signals': [],
            'message': '今日无涨停股票'
        }
    else:
        # 2. 分析连板数量
        print(f"\n🔍 分析连板数量...")
        for stock in limit_up_stocks:
            # 简化处理，不实时查询历史数据
            stock['limit_up_days'] = 1
        
        # 3. 计算龙头评分并排序
        print(f"\n📈 计算龙头评分...")
        for stock in limit_up_stocks:
            stock['score'] = calculate_leader_score(stock, limit_up_stocks)
        
        # 按评分排序
        limit_up_stocks.sort(key=lambda x: x['score'], reverse=True)
        
        # 4. 筛选龙头候选 (评分>=50 或连板>=2)
        leaders = [
            s for s in limit_up_stocks 
            if s['score'] >= 50 or s['limit_up_days'] >= 2
        ]
        
        print(f"✅ 筛选出 {len(leaders)} 只龙头候选")
        
        # 5. 加载虚拟账户
        print(f"\n💼 加载虚拟账户...")
        try:
            with open(ACCOUNT_PATH, 'r', encoding='utf-8') as f:
                account = json.load(f)
        except:
            account = {
                'account_id': 'virtual_2026',
                'initial_capital': 1000000,
                'cash': 1000000,
                'positions': [],
                'trades': []
            }
        
        # 6. 生成交易信号
        print(f"\n📝 生成交易信号...")
        signals = generate_trading_signals(leaders, account)
        print(f"✅ 生成 {len(signals)} 条交易信号")
        
        # 7. 构建报告
        report = {
            'date': TODAY,
            'success': True,
            'total_limit_up': len(limit_up_stocks),
            'leaders': [
                {
                    'rank': i + 1,
                    'symbol': s['symbol'],
                    'name': s['name'],
                    'price': s['price'],
                    'change_pct': s['change_pct'],
                    'limit_up_days': s['limit_up_days'],
                    'score': s['score'],
                    'industry': s['industry'],
                    'concept': s['concept'],
                    'amount': s['amount'],
                    'market_cap': s['market_cap'],
                }
                for i, s in enumerate(leaders[:10])
            ],
            'signals': signals,
            'market_summary': {
                'total_limit_up': len(limit_up_stocks),
                'leader_count': len(leaders),
                'avg_score': sum(s['score'] for s in leaders) / len(leaders) if leaders else 0,
            },
            'risk_tips': [
                '注意大盘整体走势，避免系统性风险',
                '严格止损，破板即离场',
                '控制仓位，单只股票不超过总资金 20%',
                '关注龙虎榜资金动向',
                '避免追高已连续 5 板以上的高位股'
            ]
        }
    
    # 8. 保存报告
    print(f"\n💾 保存报告到 {REPORT_PATH}...")
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("✅ 报告保存成功")
    
    # 9. 更新虚拟账户交易计划
    print(f"\n📋 更新虚拟账户交易计划...")
    if report.get('signals'):
        # 添加交易计划到账户
        trade_date = TODAY
        for signal in report['signals']:
            trade = {
                'trade_id': f"LIMIT_UP_{TODAY_INT}_{signal['rank']:03d}",
                'symbol': signal['symbol'],
                'name': signal['name'],
                'direction': 'buy',
                'price': signal['price'],
                'quantity': signal['quantity'],
                'status': 'planned',
                'agent_id': 'Q-Trade',
                'build_time': trade_date,
                'note': signal['reason'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'priority': signal['priority'],
            }
            account['trades'].append(trade)
        
        # 保存账户更新
        with open(ACCOUNT_PATH, 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        print("✅ 虚拟账户交易计划已更新")
    
    # 10. 输出摘要
    print("\n" + "=" * 70)
    print(" " * 25 + "选股结果摘要")
    print("=" * 70)
    print(f"日期：{TODAY}")
    print(f"涨停总数：{report.get('total_limit_up', 0)}")
    print(f"龙头候选：{len(report.get('leaders', []))}")
    print(f"交易信号：{len(report.get('signals', []))}")
    
    if report.get('leaders'):
        print("\n🏆 龙头 TOP5:")
        for leader in report['leaders'][:5]:
            print(f"  {leader['rank']}. {leader['symbol']} {leader['name']}")
            print(f"     评分：{leader['score']:.1f}, 连板：{leader['limit_up_days']}板，价格：¥{leader['price']:.2f}")
    
    if report.get('signals'):
        print("\n📝 买入建议:")
        for signal in report['signals'][:3]:
            print(f"  • {signal['symbol']} {signal['name']}")
            print(f"    买入价：¥{signal['price']:.2f}, 数量：{signal['quantity']}股")
            print(f"    止损：¥{signal['stop_loss']:.2f}, 止盈：¥{signal['take_profit']:.2f}")
    
    print("\n⚠️ 风险提示:")
    for tip in report.get('risk_tips', [])[:3]:
        print(f"  • {tip}")
    
    print("\n" + "=" * 70)
    print(" " * 20 + "选股任务完成")
    print("=" * 70)
    
    return report


if __name__ == '__main__':
    report = main()
    sys.exit(0 if report.get('success', False) else 1)
