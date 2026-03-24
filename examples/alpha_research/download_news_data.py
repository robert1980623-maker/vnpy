#!/usr/bin/env python3
# 通知工具
from notification_utils import notify_task_start, notify_task_complete, notify_task_error

"""
消息面数据下载器

集成 AKShare 和 Tushare Pro 获取：
- 个股新闻
- 个股公告
- 研报数据
- 财经新闻

数据持久化到 data/news/ 目录
"""

import os
import sys
import json
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

# ==================== Tushare Pro 配置 ====================

ENV_TOKEN = os.environ.get('TUSHARE_TOKEN', '')
print(f"TUSHARE_TOKEN 环境变量：{'已配置' if ENV_TOKEN else '未配置'}")

if ENV_TOKEN:
    try:
        import tushare as ts
        ts.set_token(ENV_TOKEN)
        pro = ts.pro_api()
        print("✓ Tushare Pro 已初始化")
        USE_TUSHARE = True
    except Exception as e:
        print(f"⚠️ Tushare Pro 初始化失败：{e}")
        USE_TUSHARE = False
else:
    print("ℹ️ 将仅使用 AKShare 获取消息面数据")
    USE_TUSHARE = False

# ==================== 配置 ====================

BASE_DIR = Path(__file__).parent
NEWS_DIR = BASE_DIR / "data" / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 新闻数据保存目录：{NEWS_DIR}")


# ==================== AKShare 数据获取 ====================

def get_stock_news_akshare(symbol: str, start_date: str = None, end_date: str = None):
    """使用 AKShare 获取个股新闻"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    print(f"\n📰 获取 {symbol} 的新闻 (AKShare)...")
    
    try:
        df = ak.stock_news_em(symbol=symbol)
        
        if df is not None and not df.empty:
            # 过滤日期范围
            if '发布时间' in df.columns:
                df['发布时间'] = pd.to_datetime(df['发布时间']).dt.strftime('%Y%m%d')
                df = df[(df['发布时间'] >= start_date) & (df['发布时间'] <= end_date)]
            
            print(f"✓ 成功：获取到 {len(df)} 条新闻")
            return df.to_dict('records')
        else:
            print(f"✗ 未获取到新闻")
            return []
    
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}: {e}")
        return []


def get_stock_announcement_akshare(symbol: str, start_date: str = None, end_date: str = None):
    """使用 AKShare 获取个股公告"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
    
    print(f"\n📋 获取 {symbol} 的公告 (AKShare)...")
    
    try:
        # 获取个股公告
        df = ak.stock_board_industry_name_em(symbol=symbol)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条公告")
            return df.to_dict('records')
        else:
            print(f"✗ 未获取到公告")
            return []
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return []


# ==================== Tushare Pro 数据获取 ====================

def get_news_tushare(start_date: str = None, end_date: str = None):
    """使用 Tushare Pro 获取财经新闻"""
    if not USE_TUSHARE:
        return []
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"\n📰 获取财经新闻 (Tushare Pro)...")
    
    try:
        # 获取财经新闻
        df = pro.news(src='cctv', start_date=start_date, end_date=end_date)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条新闻")
            return df.to_dict('records')
        else:
            print(f"✗ 未获取到新闻")
            return []
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return []


def get_report_daily_tushare(trade_date: str = None):
    """使用 Tushare Pro 获取研报数据"""
    if not USE_TUSHARE:
        return []
    
    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    print(f"\n📊 获取研报数据 (Tushare Pro)...")
    
    try:
        df = pro.report_daily(trade_date=trade_date)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 份研报")
            return df.to_dict('records')
        else:
            print(f"✗ 未获取到研报")
            return []
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return []


# ==================== 数据持久化 ====================

def save_news_data(data: list, filename: str):
    """保存新闻数据到 JSON 文件"""
    filepath = NEWS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 已保存到：{filepath}")
    return filepath


def load_news_data(filename: str) -> list:
    """加载新闻数据"""
    filepath = NEWS_DIR / filename
    
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 主函数 ====================

def download_all_news(stock_list: list = None):
    """下载所有股票的消息面数据"""
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 默认股票列表（可以从选股结果读取）
    if stock_list is None:
        stock_list = [
            "600519", "000858", "000001", "600036", "601318",
            "000333", "000651", "002415", "300750", "600276"
        ]
    
    print(f"\n{'='*60}")
    print(f"开始下载消息面数据")
    print(f"日期：{date_str}")
    print(f"股票数量：{len(stock_list)}")
    print(f"{'='*60}\n")
    
    all_news = {}
    
    # 获取个股新闻
    for symbol in stock_list:
        news = get_stock_news_akshare(symbol)
        if news:
            all_news[f"{symbol}_news"] = news
            save_news_data(news, f"{symbol}_news_{date_str}.json")
    
    # 获取财经新闻（Tushare）
    if USE_TUSHARE:
        finance_news = get_news_tushare()
        if finance_news:
            save_news_data(finance_news, f"finance_news_{date_str}.json")
        
        # 获取研报数据
        reports = get_report_daily_tushare()
        if reports:
            save_news_data(reports, f"reports_{date_str}.json")
    
    # 保存汇总
    summary = {
        "date": date_str,
        "stocks_count": len(stock_list),
        "news_count": sum(len(v) for v in all_news.values()),
        "use_tushare": USE_TUSHARE
    }
    
    save_news_data(summary, f"summary_{date_str}.json")
    
    print(f"\n{'='*60}")
    print(f"✅ 消息面数据下载完成")
    print(f"{'='*60}\n")
    
    # 发送完成通知
    notify_task_complete("消息面数据下载", {
        "股票数量": str(summary.get("stocks_count", 0)),
        "新闻数量": str(summary.get("news_count", 0))
    })
    
    return summary


if __name__ == "__main__":
    from logger import TaskLogger
    from datetime import datetime
    
    logger = TaskLogger(task_name='news_download')
    
    # 发送开始通知
    notify_task_start("消息面数据下载", {
        "日期": datetime.now().strftime("%Y-%m-%d"),
        "类型": "新闻/研报"
    })
    
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info('任务开始执行')
        logger = TaskLogger(task_name='news_download')
        start_time = datetime.now()
    
        try:
            logger.task_start()
            logger.info("开始下载消息面数据")
            download_all_news()
            duration = (datetime.now() - start_time).total_seconds()
            logger.task_end(success=True, duration=duration)
            logger.info("消息面数据下载完成")
        except Exception as e:
            logger.task_failed(e)
            logger.task_end(success=False)
            raise

    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)