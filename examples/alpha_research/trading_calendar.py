#!/usr/bin/env python3
"""
A 股交易日历工具

功能:
- 判断是否为交易日
- 获取最近交易日
- 判断数据是否已发布
"""

import requests
from datetime import datetime, timedelta
from pathlib import Path
import json

class TradingCalendar:
    """交易日历管理器"""
    
    def __init__(self):
        self.cache_file = Path('./cache/trading_calendar.json')
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.calendar = self._load_calendar()
    
    def _load_calendar(self) -> dict:
        """加载交易日历缓存"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 缓存有效期 7 天
            if datetime.now().timestamp() - data.get('updated_at', 0) < 7 * 86400:
                return data
        return {'trading_days': [], 'updated_at': 0}
    
    def _fetch_trading_days(self, year: int = None):
        """获取交易日历（使用 AkShare）"""
        if year is None:
            year = datetime.now().year
        
        try:
            import akshare as ak
            # 获取中国节假日
            df = ak.holiday_info()
            holidays = set(df['日期'].tolist()) if not df.empty else set()
            
            # 生成交易日列表（简单版本：排除周末和节假日）
            trading_days = []
            start = datetime(year, 1, 1)
            end = datetime(year, 12, 31)
            
            current = start
            while current <= end:
                # 排除周末
                if current.weekday() < 5:
                    date_str = current.strftime('%Y-%m-%d')
                    if date_str not in holidays:
                        trading_days.append(date_str)
                current += timedelta(days=1)
            
            self.calendar = {
                'trading_days': trading_days,
                'holidays': list(holidays),
                'updated_at': datetime.now().timestamp()
            }
            self._save_calendar()
            
        except Exception as e:
            print(f"⚠️ 获取交易日历失败：{e}")
            # 使用简单逻辑
            self._simple_calendar()
    
    def _simple_calendar(self):
        """简单交易日历（仅排除周末）"""
        year = datetime.now().year
        trading_days = []
        
        start = datetime(year, 1, 1)
        end = datetime(year, 12, 31)
        current = start
        
        while current <= end:
            if current.weekday() < 5:  # 周一到周五
                trading_days.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        self.calendar = {
            'trading_days': trading_days,
            'updated_at': datetime.now().timestamp()
        }
        self._save_calendar()
    
    def _save_calendar(self):
        """保存交易日历"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.calendar, f, ensure_ascii=False, indent=2)
    
    def is_trading_day(self, date: datetime = None) -> bool:
        """判断是否为交易日"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # 确保日历已加载
        if not self.calendar.get('trading_days'):
            self._fetch_trading_days(date.year)
        
        return date_str in self.calendar.get('trading_days', [])
    
    def get_last_trading_day(self, date: datetime = None) -> datetime:
        """获取最近一个交易日"""
        if date is None:
            date = datetime.now()
        
        # 确保日历已加载
        if not self.calendar.get('trading_days'):
            self._fetch_trading_days(date.year)
        
        trading_days = sorted(self.calendar.get('trading_days', []), reverse=True)
        date_str = date.strftime('%Y-%m-%d')
        
        # 如果今天是交易日，返回今天
        if date_str in trading_days:
            return date
        
        # 返回之前的交易日
        for day in trading_days:
            if day < date_str:
                return datetime.strptime(day, '%Y-%m-%d')
        
        # 如果当年找不到，找去年
        return self.get_last_trading_day(date - timedelta(days=365))
    
    def is_data_published(self, date: datetime = None) -> bool:
        """
        判断当日数据是否已发布
        
        A 股数据通常在交易日 16:00-17:00 后发布
        """
        if date is None:
            date = datetime.now()
        
        # 非交易日不需要数据
        if not self.is_trading_day(date):
            return True
        
        # 16:30 后认为数据已发布
        return date.hour >= 16 or date.weekday() >= 5


# 便捷函数
def is_trading_day(date: datetime = None) -> bool:
    """判断是否为交易日"""
    cal = TradingCalendar()
    return cal.is_trading_day(date)

def get_last_trading_day(date: datetime = None) -> datetime:
    """获取最近交易日"""
    cal = TradingCalendar()
    return cal.get_last_trading_day(date)

def is_data_published(date: datetime = None) -> bool:
    """判断数据是否已发布"""
    cal = TradingCalendar()
    return cal.is_data_published(date)


if __name__ == '__main__':
    # 测试
    cal = TradingCalendar()
    today = datetime.now()
    
    print("=" * 60)
    print("交易日历测试")
    print("=" * 60)
    print(f"今天：{today.strftime('%Y-%m-%d %A')}")
    print(f"是否交易日：{cal.is_trading_day(today)}")
    print(f"数据是否已发布：{cal.is_data_published(today)}")
    
    last_day = cal.get_last_trading_day(today)
    print(f"最近交易日：{last_day.strftime('%Y-%m-%d %A')}")
