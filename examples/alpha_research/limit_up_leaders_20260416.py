#!/usr/bin/env python3
"""
涨停龙头策略每日选股 - 2026-04-16

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
TODAY = "2026-04-16"
TODAY_INT = 20260416
REPORT_PATH = "/Users/rowang/projects/vnpy/examples/alpha_research/reports/limit_up_leaders_2026-04-16.json"
ACCOUNT_PATH = "/Users/rowang/projects/vnpy/examples/alpha_research/accounts/virtual_2026_account.json"
CACHE_PATH = "/Users/rowang/projects/vnpy/examples/alpha_research/cache/limit_up_strategy/leaders_20260416.json"

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
    elif 500e8 < market_cap <= 1000e8:
        score += 8
    else:
        score += 5
    
    return score


def generate_trading_signals(leaders: list, account: dict, max_signals: int = 5) -> list:
    """生成交易信号"""
    signals = []
    
    total_capital = account.get('cash', 0)
    position_size = total_capital / max_signals  # 平均分配
    
    for leader in leaders[:max_signals]:
        price = leader.get('price', 0)
        if price <= 0:
            continue
        
        # 计算买入数量（100 股的整数倍）
        quantity = int((position_size * 0.95) / price / 100) * 100
        if quantity <= 0:
            continue
        
        # 计算止损止盈
        stop_loss = price * 0.92  # -8%
        take_profit = price * 1.20  # +20%
        
        signal = {
            'symbol': leader.get('symbol'),
            'name': leader.get('name'),
            'action': 'buy',
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'reason': f"龙头评分：{leader.get('score', 0):.1f}, 连板：{leader.get('limit_up_days', 1)}板",
            'confidence': min(0.9, 0.5 + leader.get('score', 0) / 200),
            'timestamp': datetime.now().isoformat()
        }
        signals.append(signal)
    
    return signals


def main():
    print("=" * 70)
    print(" " * 20 + "涨停龙头策略每日选股")
    print(" " * 25 + TODAY)
    print("=" * 70)
    
    # 1. 获取涨停股票
    limit_up_stocks = fetch_limit_up_stocks(TODAY)
    
    if not limit_up_stocks:
        print("\n⚠️  今日无涨停股票，跳过龙头分析")
        # 保存空报告
        report = {
            'date': TODAY,
            'limit_up_count': 0,
            'leaders': [],
            'signals': [],
            'timestamp': datetime.now().isoformat()
        }
        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 空报告已保存到 {REPORT_PATH}")
        return
    
    # 2. 分析连板数量
    print("\n🔍 分析连板数量...")
    for stock in limit_up_stocks:
        symbol = stock['symbol']
        if symbol:
            consecutive_days = analyze_consecutive_limit_up(symbol, TODAY)
            stock['limit_up_days'] = consecutive_days
    
    # 3. 筛选龙头候选（连续涨停>=2 天）
    leader_candidates = [s for s in limit_up_stocks if s.get('limit_up_days', 1) >= 2]
    print(f"✅ 筛选出 {len(leader_candidates)} 只龙头候选")
    
    # 4. 计算龙头评分
    print("\n📈 计算龙头评分...")
    for stock in leader_candidates:
        score = calculate_leader_score(stock, limit_up_stocks)
        stock['score'] = score
    
    # 按评分排序
    leader_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 5. 加载虚拟账户
    print("\n💼 加载虚拟账户...")
    try:
        with open(ACCOUNT_PATH, 'r', encoding='utf-8') as f:
            account = json.load(f)
    except:
        account = {'cash': 1000000, 'positions': [], 'trades': []}
    
    # 6. 生成交易信号
    print("\n📝 生成交易信号...")
    signals = generate_trading_signals(leader_candidates, account)
    print(f"✅ 生成 {len(signals)} 条交易信号")
    
    # 7. 保存报告
    print(f"\n💾 保存报告到 {REPORT_PATH}...")
    report = {
        'date': TODAY,
        'limit_up_count': len(limit_up_stocks),
        'leader_candidates_count': len(leader_candidates),
        'leaders': leader_candidates[:10],  # TOP10
        'signals': signals,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("✅ 报告保存成功")
    
    # 8. 更新虚拟账户交易计划
    print("\n📋 更新虚拟账户交易计划...")
    account['trading_plan'] = {
        'date': TODAY,
        'strategy': 'limit_up_leader',
        'signals': signals,
        'created_at': datetime.now().isoformat()
    }
    
    with open(ACCOUNT_PATH, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    print("✅ 虚拟账户交易计划已更新")
    
    # 9. 保存缓存
    cache_data = {
        'date': TODAY.replace('-', ''),
        'leaders': leader_candidates[:10],
        'timestamp': datetime.now().isoformat()
    }
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    # 10. 输出摘要
    print("\n" + "=" * 70)
    print(" " * 25 + "选股结果摘要")
    print("=" * 70)
    print(f"日期：{TODAY}")
    print(f"涨停总数：{len(limit_up_stocks)}")
    print(f"龙头候选：{len(leader_candidates)}")
    print(f"交易信号：{len(signals)}")
    
    if leader_candidates:
        print(f"\n🏆 龙头 TOP5:")
        for i, leader in enumerate(leader_candidates[:5], 1):
            print(f"  {i}. {leader.get('symbol')} {leader.get('name')}")
            print(f"     评分：{leader.get('score', 0):.1f}, 连板：{leader.get('limit_up_days', 1)}板，价格：¥{leader.get('price', 0):.2f}")
    
    if signals:
        print(f"\n📝 买入建议:")
        for signal in signals:
            print(f"  • {signal.get('symbol')} {signal.get('name')}")
            print(f"    买入价：¥{signal.get('price', 0):.2f}, 数量：{signal.get('quantity', 0)}股")
            print(f"    止损：¥{signal.get('stop_loss', 0):.2f}, 止盈：¥{signal.get('take_profit', 0):.2f}")
    else:
        print("\n⚠️ 无符合买入条件的标的")
    
    print("\n⚠️ 风险提示:")
    print("  • 注意大盘整体走势，避免系统性风险")
    print("  • 严格止损，破板即离场")
    print("  • 控制仓位，单只股票不超过总资金 20%")
    
    print("\n" + "=" * 70)
    print(" " * 25 + "选股任务完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
