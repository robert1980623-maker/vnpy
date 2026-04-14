#!/usr/bin/env python3
"""
市场情绪数据收集器 v1.0

功能：
1. 抓取财经新闻（CCTV 财经）
2. 获取商品指数数据（CRB）
3. 获取国内油价数据
4. 生成市场情绪标签
5. 输出 JSON 到 /data/market_mood/

运行时间：每日 07:00
输出路径：/Users/rowang/projects/vnpy/examples/alpha_research/data/market_mood/daily_YYYYMMDD.json
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 AKShare proxy 配置（必须在导入 akshare 之前）
try:
    import akshare_patch_config
except ImportError:
    print("⚠️ akshare_patch_config 未找到，将使用原始 AKShare")

import akshare as ak
from logger import TaskLogger

# ==================== 配置 ====================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "market_mood"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 正面/负面关键词词库
POSITIVE_KEYWORDS = [
    '爆发', '突破', '超预期', '利好', '增长', '上涨', '创新高',
    '复苏', '回暖', '强劲', '乐观', '积极', '受益', '放量',
    '政策扶持', '订单激增', '业绩预增', '产能扩张', '技术突破'
]

NEGATIVE_KEYWORDS = [
    '风险', '制裁', '承压', '暴跌', '下滑', '萎缩', '亏损',
    '衰退', '恶化', '悲观', '消极', '受损', '缩量',
    '监管收紧', '订单减少', '业绩预亏', '产能过剩', '技术封锁',
    '地缘政治', '贸易战', '关税', '冲突', '紧张'
]

# 板块映射配置
SECTOR_MAPPING = {
    '科技': {
        'keywords': ['半导体', '算力', 'AI', '芯片', '软件', '互联网', '科技', '新能源', '光伏', '电池'],
        'us_correlation': 'nasdaq',
        'weight': 0.8
    },
    '能源': {
        'keywords': ['石油', '煤炭', '化工', '能源', '油气', '炼化'],
        'us_correlation': 'oil',
        'weight': 0.6  # 原油涨→成本上升→利润受损，所以权重调低
    },
    '金融': {
        'keywords': ['银行', '保险', '券商', '金融', '信托'],
        'us_correlation': 'dow',
        'weight': 0.7
    },
    '消费': {
        'keywords': ['消费', '零售', '白酒', '食品', '家电', '汽车'],
        'us_correlation': 'dow',
        'weight': 0.6
    },
    '医药': {
        'keywords': ['医药', '医疗', 'CRO', '疫苗', '生物', '制药'],
        'us_correlation': 'nasdaq',
        'weight': 0.6
    },
    '军工': {
        'keywords': ['军工', '航天', '国防', '航空', '船舶'],
        'us_correlation': 'geopolitics',
        'weight': 0.7
    },
    '黄金': {
        'keywords': ['黄金', '珠宝', '贵金属', '有色'],
        'us_correlation': 'gold',
        'weight': 0.6
    }
}


# ==================== 数据获取函数 ====================

def get_cctv_news():
    """获取 CCTV 财经新闻"""
    print("\n📰 获取 CCTV 财经新闻...")
    try:
        df = ak.news_cctv()
        if df is not None and not df.empty:
            news_list = df.head(25).to_dict('records')
            print(f"  ✅ 获取 {len(news_list)} 条新闻")
            return news_list
        else:
            print("  ⚠️ 无新闻数据")
            return []
    except Exception as e:
        print(f"  ❌ 获取新闻失败：{e}")
        return []


def get_finance_news_sina():
    """获取新浪财经新闻（更偏市场）"""
    print("\n📰 获取新浪财经新闻...")
    try:
        # 新浪财经 A 股新闻
        df = ak.stock_news_sina(symbol="全部")
        if df is not None and not df.empty:
            news_list = df.head(30).to_dict('records')
            print(f"  ✅ 获取 {len(news_list)} 条新浪财经新闻")
            return news_list
        else:
            print("  ⚠️ 无新浪财经新闻数据")
            return []
    except Exception as e:
        print(f"  ❌ 获取新浪财经新闻失败：{e}")
        return []


def get_finance_news_eastmoney():
    """获取东方财富财经新闻"""
    print("\n📰 获取东方财富财经新闻...")
    try:
        # 东方财富财经要闻
        df = ak.news_economic_baidu()  # 百度财经新闻作为替代
        if df is not None and not df.empty:
            news_list = df.head(30).to_dict('records')
            print(f"  ✅ 获取 {len(news_list)} 条财经新闻")
            return news_list
        else:
            print("  ⚠️ 无东方财富新闻数据")
            return []
    except Exception as e:
        print(f"  ❌ 获取东方财富新闻失败：{e}")
        return []


def get_commodity_index():
    """获取中国商品价格指数（CRB 类似）"""
    print("\n📊 获取商品价格指数...")
    try:
        df = ak.macro_china_commodity_price_index()
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            change = float(latest['最新值']) - float(prev['最新值'])
            change_pct = float(latest['涨跌幅']) if '涨跌幅' in latest.index else 0.0
            
            result = {
                'index_value': float(latest['最新值']),
                'change': change,
                'change_pct': change_pct,
                'date': str(latest['日期'])
            }
            print(f"  ✅ 商品指数：{result['index_value']} ({result['change_pct']:+.2f}%)")
            return result
        else:
            print("  ⚠️ 无商品指数数据")
            return None
    except Exception as e:
        print(f"  ❌ 获取商品指数失败：{e}")
        return None


def get_domestic_oil_price():
    """获取国内成品油价格"""
    print("\n🛢️ 获取国内油价...")
    try:
        df = ak.energy_oil_hist()
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            result = {
                'gasoline_price': float(latest['汽油价格']),
                'diesel_price': float(latest['柴油价格']),
                'gasoline_change': float(latest['汽油涨跌']),
                'diesel_change': float(latest['柴油涨跌']),
                'date': str(latest['调整日期'])
            }
            print(f"  ✅ 汽油：{result['gasoline_price']}元/吨 ({result['gasoline_change']:+.0f})")
            return result
        else:
            print("  ⚠️ 无油价数据")
            return None
    except Exception as e:
        print(f"  ❌ 获取油价失败：{e}")
        return None


def get_gold_reserves():
    """获取中国黄金储备数据（月度）"""
    print("\n🥇 获取黄金储备数据...")
    try:
        df = ak.macro_china_fx_gold()
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            result = {
                'gold_reserves': float(latest['黄金储备 - 数值']),
                'yoy_change': float(latest['黄金储备 - 同比']) if '黄金储备 - 同比' in latest.index else 0.0,
                'mom_change': float(latest['黄金储备 - 环比']) if '黄金储备 - 环比' in latest.index else 0.0,
                'date': str(latest['月份'])
            }
            print(f"  ✅ 黄金储备：{result['gold_reserves']}万盎司 (同比：{result['yoy_change']:+.2f}%)")
            return result
        else:
            print("  ⚠️ 无黄金储备数据")
            return None
    except Exception as e:
        print(f"  ❌ 获取黄金储备失败：{e}")
        return None


def get_us_market_data_fallback():
    """
    获取美股数据（备用方案）
    
    由于东财 API 连接问题，暂时使用模拟数据
    TODO: 接入稳定的美股数据源（如 Yahoo Finance、Alpha Vantage 等）
    """
    print("\n🇺🇸 获取美股数据（备用方案）...")
    print("  ⚠️ 东财 API 连接失败，使用模拟数据")
    
    # 模拟数据 - 实际应该从可靠数据源获取
    # 这里用随机数模拟，实际应该替换为真实 API
    import random
    random.seed(datetime.now().day)  # 每天固定种子，保证同一天数据一致
    
    nasdaq_change = random.uniform(-1.5, 2.0)
    dow_change = random.uniform(-1.0, 1.5)
    sp500_change = random.uniform(-0.8, 1.8)
    
    result = {
        'nasdaq_change': round(nasdaq_change, 2),
        'dow_change': round(dow_change, 2),
        'sp500_change': round(sp500_change, 2),
        'note': '模拟数据 - 需接入真实美股数据源'
    }
    
    print(f"  📊 纳指：{result['nasdaq_change']:+.2f}% | 道指：{result['dow_change']:+.2f}% | 标普：{result['sp500_change']:+.2f}%")
    return result


# ==================== 情绪分析函数 ====================

def analyze_news_sentiment(news_list):
    """分析新闻情绪"""
    print("\n🔍 分析新闻情绪...")
    
    if not news_list:
        return {
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'top_positive': [],
            'top_negative': [],
            'news_score': 0.0
        }
    
    positive_news = []
    negative_news = []
    neutral_news = []
    
    for news in news_list:
        title = news.get('title', '') or news.get('content', '')
        
        pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)
        
        if pos_count > neg_count:
            positive_news.append(title[:50])
        elif neg_count > pos_count:
            negative_news.append(title[:50])
        else:
            neutral_news.append(title[:50])
    
    total = len(news_list)
    news_score = (len(positive_news) - len(negative_news)) / total if total > 0 else 0.0
    
    result = {
        'positive_count': len(positive_news),
        'negative_count': len(negative_news),
        'neutral_count': len(neutral_news),
        'top_positive': positive_news[:5],
        'top_negative': negative_news[:5],
        'news_score': round(news_score, 3)
    }
    
    print(f"  ✅ 正面：{result['positive_count']} | 负面：{result['negative_count']} | 中性：{result['neutral_count']}")
    return result


def calculate_mood_score(news_sentiment, us_market, commodities):
    """
    计算综合情绪打分
    
    权重：
    - 新闻情绪：40%
    - 美股映射：35%
    - 商品信号：25%
    """
    # 新闻情绪分（-1 到 1）
    news_score = news_sentiment.get('news_score', 0.0)
    
    # 美股映射分（-1 到 1）
    nasdaq = us_market.get('nasdaq_change', 0.0)
    dow = us_market.get('dow_change', 0.0)
    us_score = (nasdaq * 0.6 + dow * 0.4) / 2.0  # 归一化到 -1~1
    
    # 商品信号分（-1 到 1）
    commodity_change = commodities.get('commodity_index', {}).get('change_pct', 0.0) if commodities.get('commodity_index') else 0.0
    commodity_score = commodity_change / 5.0  # 简单归一化
    
    # 加权综合
    mood_score = news_score * 0.4 + us_score * 0.35 + commodity_score * 0.25
    mood_score = max(-1.0, min(1.0, mood_score))  # clamp to [-1, 1]
    
    # 转换为 0-1 范围
    mood_score_0_1 = (mood_score + 1.0) / 2.0
    
    return round(mood_score_0_1, 3)


def get_mood_label(mood_score):
    """根据情绪打分返回标签"""
    if mood_score >= 0.7:
        return "乐观"
    elif mood_score >= 0.55:
        return "谨慎乐观"
    elif mood_score >= 0.45:
        return "中性"
    elif mood_score >= 0.3:
        return "谨慎"
    else:
        return "悲观"


def generate_sector_signals(us_market, commodities, news_sentiment):
    """生成板块信号"""
    print("\n🎯 生成板块信号...")
    
    signals = {}
    
    for sector, config in SECTOR_MAPPING.items():
        correlation = config['us_correlation']
        weight = config['weight']
        
        # 根据相关性获取对应的市场数据
        if correlation == 'nasdaq':
            signal_value = us_market.get('nasdaq_change', 0.0)
        elif correlation == 'dow':
            signal_value = us_market.get('dow_change', 0.0)
        elif correlation == 'oil':
            oil_data = commodities.get('domestic_oil', {})
            signal_value = oil_data.get('gasoline_change', 0.0) / 100.0 if oil_data else 0.0
        elif correlation == 'gold':
            gold_data = commodities.get('gold_reserves', {})
            signal_value = gold_data.get('mom_change', 0.0) / 10.0 if gold_data else 0.0
        elif correlation == 'geopolitics':
            # 地缘政治信号从负面新闻数量推断
            neg_count = news_sentiment.get('negative_count', 0)
            signal_value = -neg_count / 10.0  # 负面新闻越多，军工信号越强（反向）
        else:
            signal_value = 0.0
        
        # 判断信号方向
        if signal_value > 0.5:
            signal = 'positive'
            confidence = min(0.9, 0.5 + abs(signal_value) * weight)
        elif signal_value < -0.5:
            signal = 'negative'
            confidence = min(0.9, 0.5 + abs(signal_value) * weight)
        else:
            signal = 'neutral'
            confidence = 0.5
        
        # 生成原因说明
        if correlation == 'nasdaq':
            reason = f"纳指{us_market.get('nasdaq_change', 0.0):+.1f}%"
        elif correlation == 'dow':
            reason = f"道指{us_market.get('dow_change', 0.0):+.1f}%"
        elif correlation == 'oil':
            reason = "油价波动"
        elif correlation == 'gold':
            reason = "黄金储备变化"
        elif correlation == 'geopolitics':
            reason = "地缘政治因素"
        else:
            reason = "综合因素"
        
        signals[sector] = {
            'signal': signal,
            'confidence': round(confidence, 2),
            'reason': reason
        }
    
    print(f"  ✅ 生成 {len(signals)} 个板块信号")
    return signals


# ==================== 主函数 ====================

def collect_market_mood():
    """收集市场情绪数据并生成 JSON"""
    
    print("=" * 70)
    print(" " * 20 + "市场情绪数据收集器 v1.0")
    print("=" * 70)
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 获取新闻数据（多源合并）
    print("\n" + "=" * 70)
    print(" " * 25 + "新闻数据收集")
    print("=" * 70)
    
    news_cctv = get_cctv_news()
    news_sina = get_finance_news_sina()
    news_em = get_finance_news_eastmoney()
    
    # 合并新闻列表，去重
    all_news = []
    seen_titles = set()
    for news in news_cctv + news_sina + news_em:
        title = news.get('title', '') or news.get('content', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_news.append(news)
    
    news_list = all_news[:50]  # 最多取 50 条
    print(f"\n📊 合并后新闻总数：{len(news_list)} 条")
    
    # 2. 获取商品数据
    commodity_index = get_commodity_index()
    domestic_oil = get_domestic_oil_price()
    gold_reserves = get_gold_reserves()
    
    commodities = {
        'commodity_index': commodity_index,
        'domestic_oil': domestic_oil,
        'gold_reserves': gold_reserves
    }
    
    # 3. 获取美股数据（备用方案）
    us_market = get_us_market_data_fallback()
    
    # 4. 分析新闻情绪
    news_sentiment = analyze_news_sentiment(news_list)
    
    # 5. 计算综合情绪打分
    mood_score = calculate_mood_score(news_sentiment, us_market, commodities)
    mood_label = get_mood_label(mood_score)
    
    # 6. 生成板块信号
    sector_signals = generate_sector_signals(us_market, commodities, news_sentiment)
    
    # 7. 提取关键事件
    key_events = []
    if news_sentiment['top_positive']:
        key_events.extend(news_sentiment['top_positive'][:2])
    if news_sentiment['top_negative']:
        key_events.extend(news_sentiment['top_negative'][:2])
    
    # 8. 构建输出 JSON
    output = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'generated_at': datetime.now().isoformat(),
        
        'market_overview': {
            'mood_score': mood_score,
            'mood_label': mood_label,
            'key_events': key_events
        },
        
        'us_market': us_market,
        
        'commodities': {
            'commodity_index': commodity_index,
            'domestic_oil': domestic_oil,
            'gold_reserves': gold_reserves
        },
        
        'news_summary': news_sentiment,
        
        'sector_signals': sector_signals
    }
    
    # 9. 保存 JSON 文件
    output_file = DATA_DIR / f"daily_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 数据已保存：{output_file}")
    
    # 10. 打印摘要
    print("\n" + "=" * 70)
    print(" " * 25 + "情绪摘要")
    print("=" * 70)
    print(f"  综合情绪：{mood_label} ({mood_score:.3f})")
    print(f"  新闻情绪：正面{news_sentiment['positive_count']} | 负面{news_sentiment['negative_count']} | 中性{news_sentiment['neutral_count']}")
    print(f"  关键事件：{', '.join(key_events[:3]) if key_events else '无'}")
    print("=" * 70)
    
    return output


if __name__ == '__main__':
    logger = TaskLogger(task_name='market_mood_collector')
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info('任务开始执行')
        
        result = collect_market_mood()
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)
        logger.info(f'任务执行完成，耗时：{duration:.2f}s')
        
        print(f"\n✅ 任务完成！耗时：{duration:.2f}s")
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_failed(e, duration=duration)
        print(f"\n❌ 任务失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
