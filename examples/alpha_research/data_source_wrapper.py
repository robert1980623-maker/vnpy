#!/usr/bin/env python3
"""
数据源封装层 - 集成 DataSourceManager 到现有数据获取流程

提供统一的数据获取接口，自动选择最优数据源并处理故障切换

使用示例：
    fetcher = DataSourceFetcher()
    df = fetcher.get_daily_bars('000001.SZ', start_date='20240101', end_date='20241231')
"""

import os
import time
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
from data_source_manager import DataSourceManager


class DataSourceFetcher:
    """
    数据获取器 - 基于 DataSourceManager 的智能数据源选择
    
    支持的数据源：
    - tushare: Tushare Pro API
    - akshare: AKShare 开源数据
    - sina: 新浪财经数据
    """
    
    def __init__(self, config_file: str = './data_source_config.json'):
        self.manager = DataSourceManager(config_file)
        self._init_data_sources()
    
    def _init_data_sources(self):
        """初始化数据源客户端"""
        # Tushare
        tushare_token = os.environ.get('TUSHARE_TOKEN', '')
        if tushare_token:
            import tushare as ts
            ts.set_token(tushare_token)
            self.tushare_pro = ts.pro_api()
            print("✅ Tushare Pro 已初始化")
        else:
            self.tushare_pro = None
            print("⚠️ Tushare Token 未配置")
        
        # AKShare (不需要初始化)
        try:
            import akshare as ak
            self.akshare = ak
            print("✅ AKShare 已初始化")
        except ImportError:
            self.akshare = None
            print("⚠️ AKShare 未安装")
        
        # Sina (使用 requests)
        try:
            import requests
            self.requests = requests
            print("✅ Sina 数据源已准备")
        except ImportError:
            self.requests = None
            print("⚠️ requests 未安装")
    
    def get_daily_bars(self, symbol: str, start_date: str, end_date: str,
                       max_retries: int = 3) -> Optional[pd.DataFrame]:
        """
        获取日线数据（自动选择最优数据源）
        
        Args:
            symbol: 股票代码 (e.g., '000001.SZ')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            max_retries: 最大重试次数
        
        Returns:
            DataFrame with columns: [datetime, open, high, low, close, volume]
        """
        last_error = None
        
        for attempt in range(max_retries):
            # 选择最优数据源
            data_source = self.manager.get_data_source(endpoint='daily')
            
            if not data_source:
                last_error = "无可用数据源"
                break
            
            print(f"\n📡 尝试使用数据源：{data_source} (attempt {attempt + 1}/{max_retries})")
            
            try:
                # 记录请求
                self.manager.record_request(data_source)
                start_time = time.time()
                
                # 获取数据
                df = self._fetch_from_source(data_source, symbol, start_date, end_date)
                
                response_time = (time.time() - start_time) * 1000
                
                if df is not None and len(df) > 0:
                    # 成功
                    self.manager.update_health_metrics(
                        data_source, response_time, success=True,
                        data_completeness=self._check_data_completeness(df, start_date, end_date)
                    )
                    self.manager.update_usage_stats(data_source, response_time, success=True)
                    
                    print(f"✅ 成功获取数据：{len(df)} 条，响应时间：{response_time:.0f}ms")
                    return df
                else:
                    # 数据为空
                    self.manager.update_health_metrics(
                        data_source, response_time, success=False,
                        data_completeness=0.0, error="数据为空"
                    )
                    self.manager.update_usage_stats(data_source, response_time, success=False)
                    last_error = "数据为空"
                    
            except Exception as e:
                response_time = (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
                
                # 检查是否限流
                rate_limit_hit = 'rate limit' in str(e).lower() or '限流' in str(e)
                
                self.manager.update_health_metrics(
                    data_source, response_time, success=False,
                    rate_limit_hit=rate_limit_hit, error=str(e)
                )
                self.manager.update_usage_stats(data_source, response_time, success=False, rate_limit_hit=rate_limit_hit)
                
                last_error = str(e)
                print(f"❌ 数据源 {data_source} 失败：{e}")
                
                # 如果是限流，等待一段时间
                if rate_limit_hit:
                    cooldown = self.manager.config.get('failover', {}).get('cooldown_seconds', 60)
                    print(f"⏳ 触发限流，等待 {cooldown} 秒...")
                    time.sleep(cooldown)
        
        print(f"\n❌ 所有数据源尝试失败：{last_error}")
        return None
    
    def _fetch_from_source(self, source: str, symbol: str, 
                          start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从指定数据源获取数据"""
        
        if source == 'tushare' and self.tushare_pro:
            return self._fetch_tushare(symbol, start_date, end_date)
        elif source == 'akshare' and self.akshare:
            return self._fetch_akshare(symbol, start_date, end_date)
        elif source == 'sina' and self.requests:
            return self._fetch_sina(symbol, start_date, end_date)
        else:
            raise Exception(f"数据源 {source} 不可用")
    
    def _fetch_tushare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从 Tushare 获取数据"""
        code = symbol.split('.')[0]
        ts_code = f"{code}.{symbol.split('.')[1].upper()}"
        
        df = self.tushare_pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or len(df) == 0:
            return None
        
        # 标准化列名
        df = df.rename(columns={
            'trade_date': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume'
        })
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        
        return df
    
    def _fetch_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从 AKShare 获取数据"""
        code = symbol.split('.')[0]
        
        try:
            df = self.akshare.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'datetime',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
            
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime')
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            raise Exception(f"AKShare 获取失败：{e}")
    
    def _fetch_sina(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从 Sina 获取数据（简化版，仅示例）"""
        code = symbol.split('.')[0]
        
        # Sina 数据接口（示例）
        url = f"http://quotes.sina.cn/quotes/api/mobile/v3/getSymbolHistoryList"
        params = {
            'symbol': code,
            'start': start_date,
            'end': end_date,
            'type': 'day'
        }
        
        response = self.requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data or 'data' not in data:
            return None
        
        df = pd.DataFrame(data['data'])
        
        if len(df) == 0:
            return None
        
        # 标准化列名（根据实际 API 调整）
        df = df.rename(columns={
            'd': 'datetime',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume'
        })
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        
        return df
    
    def _check_data_completeness(self, df: pd.DataFrame, 
                                 start_date: str, end_date: str) -> float:
        """检查数据完整性"""
        try:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            expected_days = (end - start).days + 1
            
            # 计算交易日（约 250 天/年）
            trading_days = int(expected_days * 5 / 7)  # 约 5/7 是交易日
            
            actual_days = len(df)
            
            completeness = min(1.0, actual_days / max(1, trading_days))
            return completeness
        except:
            return 1.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        return self.manager.get_statistics()
    
    def print_status(self):
        """打印数据源状态"""
        self.manager.print_status()


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 初始化
    fetcher = DataSourceFetcher('./data_source_config.json')
    
    # 打印状态
    fetcher.print_status()
    
    # 获取数据
    print("\n" + "="*70)
    print("  测试数据获取")
    print("="*70)
    
    df = fetcher.get_daily_bars('000001.SZ', '20241201', '20241231')
    
    if df is not None:
        print(f"\n✅ 成功获取数据:")
        print(f"   数据量：{len(df)} 条")
        print(f"   日期范围：{df['datetime'].min()} - {df['datetime'].max()}")
        print(f"\n前 5 行:")
        print(df.head())
    
    # 查看统计
    print("\n" + "="*70)
    print("  使用统计")
    print("="*70)
    stats = fetcher.get_status()
    for name, data in stats.items():
        print(f"\n{name}:")
        print(f"  状态：{data['status']}")
        print(f"  健康分：{data['health_score']:.1f}")
        print(f"  总请求：{data['usage']['total_requests']}")
        print(f"  成功率：{data['usage']['success_rate']:.2f}")
        print(f"  平均响应：{data['usage']['avg_response_time_ms']:.0f}ms")
