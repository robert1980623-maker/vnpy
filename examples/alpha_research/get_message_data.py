"""
获取消息面数据

支持：
- 个股新闻
- 个股公告
- 财经新闻
- 个股资讯
- 龙虎榜数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta


# ==================== 个股新闻 ====================

def get_stock_news(symbol: str = "000001", start_date: str = "20240101", end_date: str = None):
    """
    获取个股新闻
    
    Args:
        symbol: 股票代码 (如 "000001")
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 新闻列表
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"\n获取 {symbol} 的新闻...")
    print(f"时间范围：{start_date} - {end_date}")
    
    try:
        df = ak.stock_news_em(symbol=symbol)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条新闻")
            print(f"列名：{df.columns.tolist()}")
            return df
        else:
            print(f"✗ 未获取到新闻")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}: {e}")
        return None


# ==================== 个股公告 ====================

def get_stock_announcement(symbol: str = "000001", start_date: str = "20240101", end_date: str = None):
    """
    获取个股公告
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 公告列表
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"\n获取 {symbol} 的公告...")
    
    try:
        # 获取公告列表
        df = ak.stock_board_industry_name_em(symbol=symbol)
        
        # 或使用其他接口
        # df = ak.stock_report_fund_hold(symbol=symbol)
        
        print(f"✓ 成功：获取到 {len(df)} 条公告")
        return df
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 财经新闻 ====================

def get_finance_news(news_type: str = "全部", start_date: str = None, end_date: str = None):
    """
    获取财经新闻
    
    Args:
        news_type: 新闻类型 (全部/个股/行业/宏观)
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 新闻列表
    """
    print(f"\n获取财经新闻...")
    print(f"类型：{news_type}")
    
    try:
        # 获取新浪财经-财经新闻
        df = ak.stock_info_global_em(symbol="全部")
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条新闻")
            return df
        else:
            print(f"✗ 未获取到新闻")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 个股资讯 ====================

def get_stock_info(symbol: str = "000001"):
    """
    获取个股基本信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        pd.DataFrame: 股票基本信息
    """
    print(f"\n获取 {symbol} 的基本信息...")
    
    try:
        # 获取股票基本信息
        df = ak.stock_individual_info_em(symbol=symbol)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到基本信息")
            print(df)
            return df
        else:
            print(f"✗ 未获取到信息")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 龙虎榜数据 ====================

def get_stock_billboard(start_date: str = None, end_date: str = None):
    """
    获取龙虎榜数据
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 龙虎榜数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"\n获取龙虎榜数据...")
    print(f"时间范围：{start_date} - {end_date}")
    
    try:
        df = ak.stock_lhb_detail_em(
            start_date=start_date,
            end_date=end_date
        )
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条龙虎榜数据")
            print(f"列名：{df.columns.tolist()}")
            return df
        else:
            print(f"✗ 未获取到数据")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 机构调研 ====================

def get_institution_survey(symbol: str = None, start_date: str = None, end_date: str = None):
    """
    获取机构调研数据
    
    Args:
        symbol: 股票代码 (可选，不传获取全部)
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 机构调研数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    print(f"\n获取机构调研数据...")
    if symbol:
        print(f"股票：{symbol}")
    print(f"时间范围：{start_date} - {end_date}")
    
    try:
        if symbol:
            df = ak.stock_jgdy_detail_em(symbol=symbol)
        else:
            df = ak.stock_jgdy_em(start_date=start_date, end_date=end_date)
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条调研数据")
            return df
        else:
            print(f"✗ 未获取到数据")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 研报数据 ====================

def get_research_report(symbol: str = None, start_date: str = None, end_date: str = None):
    """
    获取研报数据
    
    Args:
        symbol: 股票代码 (可选)
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        pd.DataFrame: 研报数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    print(f"\n获取研报数据...")
    if symbol:
        print(f"股票：{symbol}")
    print(f"时间范围：{start_date} - {end_date}")
    
    try:
        # 获取个股研报
        if symbol:
            df = ak.stock_research_report_em(symbol=symbol)
        else:
            # 获取最新研报
            df = ak.stock_research_report_em()
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条研报")
            return df
        else:
            print(f"✗ 未获取到数据")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 主力持仓 ====================

def get_main_hold(symbol: str = None, quarter: str = None):
    """
    获取主力持仓数据
    
    Args:
        symbol: 股票代码 (可选)
        quarter: 季度 (如 "20241")
        
    Returns:
        pd.DataFrame: 主力持仓数据
    """
    print(f"\n获取主力持仓数据...")
    if symbol:
        print(f"股票：{symbol}")
    if quarter:
        print(f"季度：{quarter}")
    
    try:
        if symbol:
            df = ak.stock_report_fund_hold(symbol=symbol)
        else:
            # 获取基金持仓
            df = ak.fund_portfolio_hold_em()
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条持仓数据")
            return df
        else:
            print(f"✗ 未获取到数据")
            return None
    
    except Exception as e:
        print(f"✗ 失败：{e}")
        return None


# ==================== 主函数 ====================

if __name__ == "__main__":
    print("=" * 70)
    print("消息面数据获取")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 测试数据
    test_symbol = "000001"
    
    # 1. 获取个股新闻
    print("\n" + "=" * 70)
    print("[1] 个股新闻")
    print("=" * 70)
    news_df = get_stock_news(symbol=test_symbol, start_date="20240101", end_date="20241231")
    if news_df is not None and len(news_df) > 0:
        print("\n最新新闻:")
        print(news_df.head(3).to_string())
    
    # 2. 获取个股基本信息
    print("\n" + "=" * 70)
    print("[2] 个股基本信息")
    print("=" * 70)
    info_df = get_stock_info(symbol=test_symbol)
    
    # 3. 获取龙虎榜数据
    print("\n" + "=" * 70)
    print("[3] 龙虎榜数据")
    print("=" * 70)
    billboard_df = get_stock_billboard()
    if billboard_df is not None and len(billboard_df) > 0:
        print("\n最新龙虎榜:")
        print(billboard_df.head(3).to_string())
    
    # 4. 获取机构调研
    print("\n" + "=" * 70)
    print("[4] 机构调研")
    print("=" * 70)
    survey_df = get_institution_survey(symbol=test_symbol)
    if survey_df is not None and len(survey_df) > 0:
        print("\n最新调研:")
        print(survey_df.head(3).to_string())
    
    # 5. 获取研报数据
    print("\n" + "=" * 70)
    print("[5] 研报数据")
    print("=" * 70)
    report_df = get_research_report(symbol=test_symbol)
    if report_df is not None and len(report_df) > 0:
        print("\n最新研报:")
        print(report_df.head(3).to_string())
    
    # 6. 获取主力持仓
    print("\n" + "=" * 70)
    print("[6] 主力持仓")
    print("=" * 70)
    hold_df = get_main_hold(symbol=test_symbol)
    if hold_df is not None and len(hold_df) > 0:
        print("\n主力持仓:")
        print(hold_df.head(3).to_string())
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    print("\n可用接口总结:")
    print("""
消息面数据类型:
  1. 个股新闻 - stock_news_em
  2. 个股公告 - 需要特定接口
  3. 财经新闻 - stock_info_global_em
  4. 个股资讯 - stock_individual_info_em
  5. 龙虎榜 - stock_lhb_detail_em
  6. 机构调研 - stock_jgdy_em / stock_jgdy_detail_em
  7. 研报数据 - stock_research_report_em
  8. 主力持仓 - stock_report_fund_hold

使用方法:
  python get_message_data.py
    """)
    print("=" * 70)
