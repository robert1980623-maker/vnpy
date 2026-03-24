#!/usr/bin/env python3
"""
股票名称查询工具

功能:
- 查询 A 股股票名称
- 缓存查询结果
- 支持批量查询
"""

import json
from pathlib import Path
from datetime import datetime, timedelta


class StockNameCache:
    """股票名称缓存"""
    
    def __init__(self, cache_file='data/stock_names.json'):
        self.cache_file = Path(cache_file)
        self.cache_data = {}
        self.load_cache()
    
    def load_cache(self):
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查缓存是否过期 (7 天)
                    cache_time = datetime.fromisoformat(data.get('cache_time', '2000-01-01'))
                    if datetime.now() - cache_time < timedelta(days=7):
                        self.cache_data = data.get('names', {})
                        print(f"✅ 加载股票名称缓存：{len(self.cache_data)} 只")
                    else:
                        print("⚠️ 缓存已过期，将重新获取")
            except Exception as e:
                print(f"⚠️ 加载缓存失败：{e}")
    
    def save_cache(self):
        """保存缓存"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cache_time': datetime.now().isoformat(),
                    'names': self.cache_data
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ 保存股票名称缓存：{len(self.cache_data)} 只")
        except Exception as e:
            print(f"⚠️ 保存缓存失败：{e}")
    
    def get_name(self, symbol):
        """获取股票名称"""
        # 移除交易所后缀
        code = symbol.split('.')[0]
        return self.cache_data.get(code, '')
    
    def set_name(self, symbol, name):
        """设置股票名称"""
        code = symbol.split('.')[0]
        self.cache_data[code] = name
    
    def get_names(self, symbols):
        """批量获取股票名称"""
        return {symbol: self.get_name(symbol) for symbol in symbols}


def fetch_stock_names():
    """从 AKShare 获取股票名称"""
    try:
        import akshare as ak
        print("📡 从 AKShare 获取股票名称...")
        
        # 获取 A 股股票列表
        stock_info = ak.stock_info_a_code_name()
        
        names = {}
        for _, row in stock_info.iterrows():
            code = str(row['code'])
            name = row['name']
            names[code] = name
        
        print(f"✅ 获取 {len(names)} 只股票名称")
        return names
    
    except Exception as e:
        print(f"⚠️ 获取股票名称失败：{e}")
        return {}


def update_stock_names():
    """更新股票名称缓存"""
    # 获取最新数据
    names = fetch_stock_names()
    
    if names:
        # 保存缓存
        cache = StockNameCache()
        cache.cache_data = names
        cache.save_cache()
        return True
    
    return False


def get_stock_name(symbol, use_cache=True):
    """获取单个股票名称"""
    cache = StockNameCache()
    
    # 先查缓存
    name = cache.get_name(symbol)
    if name and use_cache:
        return name
    
    # 缓存没有，尝试获取
    try:
        import akshare as ak
        code = symbol.split('.')[0]
        
        # 获取个股信息
        stock_info = ak.stock_info_a_code_name()
        matched = stock_info[stock_info['code'] == code]
        
        if not matched.empty:
            name = matched.iloc[0]['name']
            cache.set_name(symbol, name)
            cache.save_cache()
            return name
    
    except Exception as e:
        print(f"⚠️ 查询 {symbol} 失败：{e}")
    
    return ''


def format_symbol_with_name(symbol):
    """格式化股票代码 + 名称"""
    cache = StockNameCache()
    name = cache.get_name(symbol)
    
    if name:
        return f"{symbol} ({name})"
    else:
        return symbol


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # 查询指定股票
        symbol = sys.argv[1]
        name = get_stock_name(symbol)
        if name:
            print(f"{symbol} = {name}")
        else:
            print(f"未找到 {symbol} 的名称")
    else:
        # 更新缓存
        print("更新股票名称缓存...")
        if update_stock_names():
            print("✅ 更新成功")
        else:
            print("❌ 更新失败")
