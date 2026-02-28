"""
AlphaLab - Alpha 研究实验室

提供统一的数据访问接口和研究工具
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json

# 可选导入 pandas
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# 可选导入 vnpy
try:
    from vnpy.trader.object import BarData, TickData
    from vnpy.trader.constant import Interval
    from vnpy.trader.database import get_database
    HAS_VNPY = True
except ImportError:
    HAS_VNPY = False
    BarData = Any
    TickData = Any
    Interval = Any
    def get_database():
        return None


class AlphaLab:
    """
    Alpha 研究实验室
    
    提供便捷的数据访问和研究功能
    """
    
    def __init__(self, workspace: str = "./lab"):
        """
        初始化 AlphaLab
        
        Args:
            workspace: 工作目录路径
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # 数据库
        self._database = get_database()
        
        # 缓存
        self._bars_cache: Dict[str, List[BarData]] = {}
        self._fundamental_cache: Dict[str, Any] = {}
        
        # 数据路径
        self._data_path = self.workspace / "data"
        self._data_path.mkdir(exist_ok=True)
    
    def get_bars(
        self,
        vt_symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """
        获取 K 线数据
        
        Args:
            vt_symbol: 股票代码
            interval: K 线周期
            start: 开始日期
            end: 结束日期
            
        Returns:
            List[BarData]: K 线数据列表
        """
        cache_key = f"{vt_symbol}_{interval}_{start}_{end}"
        
        if cache_key in self._bars_cache:
            return self._bars_cache[cache_key]
        
        # 从数据库加载
        bars = self._database.load_bar_data(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end
        )
        
        # 缓存
        self._bars_cache[cache_key] = bars
        
        return bars
    
    def get_fundamental(
        self,
        vt_symbol: str,
        date: datetime
    ) -> Optional[Any]:
        """
        获取财务数据
        
        Args:
            vt_symbol: 股票代码
            date: 日期
            
        Returns:
            Optional[Any]: 财务指标对象
        """
        # 尝试从缓存加载
        cache_key = f"{vt_symbol}_{date.strftime('%Y-%m-%d')}"
        
        if cache_key in self._fundamental_cache:
            return self._fundamental_cache[cache_key]
        
        # 从文件加载（如果存在）
        fundamental_file = self._data_path / f"{vt_symbol.replace('.', '_')}_fundamental.json"
        
        if fundamental_file.exists():
            with open(fundamental_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 找到最接近的报告期
            from vnpy.alpha.dataset.fundamental import FinancialIndicator
            
            target_date = date.strftime('%Y-%m-%d')
            closest_report = None
            closest_diff = float('inf')
            
            for report_date, indicators in data.items():
                diff = abs((datetime.strptime(report_date, '%Y-%m-%d') - date).days)
                if diff < closest_diff:
                    closest_diff = diff
                    closest_report = indicators
            
            if closest_report:
                indicator = FinancialIndicator.from_dict(closest_report)
                self._fundamental_cache[cache_key] = indicator
                return indicator
        
        return None
    
    def load_fundamental_from_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        从文件加载财务数据
        
        Args:
            filepath: 文件路径
            
        Returns:
            Dict[str, Any]: 财务数据字典 {vt_symbol: FinancialIndicator}
        """
        from vnpy.alpha.dataset.fundamental import FundamentalData, FinancialIndicator
        
        filepath = Path(filepath)
        
        if not filepath.exists():
            return {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = {}
        
        for vt_symbol, reports in data.items():
            # 获取最新报告期
            latest_report = None
            latest_date = None
            
            for report_date, indicator_dict in reports.items():
                if latest_date is None or report_date > latest_date:
                    latest_date = report_date
                    latest_report = indicator_dict
            
            if latest_report:
                indicator = FinancialIndicator.from_dict(latest_report)
                result[vt_symbol] = indicator
        
        return result
    
    def save_fundamental_to_file(
        self,
        fundamental_data: Dict[str, Any],
        filename: str = "fundamental.json"
    ) -> None:
        """
        保存财务数据到文件
        
        Args:
            fundamental_data: 财务数据字典
            filename: 文件名
        """
        filepath = self._data_path / filename
        
        # 转换为可序列化格式
        data = {}
        for vt_symbol, indicator in fundamental_data.items():
            if hasattr(indicator, 'to_dict'):
                data[vt_symbol] = {
                    indicator.report_date: indicator.to_dict()
                }
            else:
                data[vt_symbol] = indicator
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_stock_pool(self, name: str = "stock_pool") -> List[str]:
        """
        获取股票池
        
        Args:
            name: 股票池名称
            
        Returns:
            List[str]: 股票代码列表
        """
        pool_file = self._data_path / f"{name}.json"
        
        if pool_file.exists():
            with open(pool_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("stocks", [])
        
        return []
    
    def save_stock_pool(
        self,
        stocks: List[str],
        name: str = "stock_pool"
    ) -> None:
        """
        保存股票池
        
        Args:
            stocks: 股票代码列表
            name: 股票池名称
        """
        pool_file = self._data_path / f"{name}.json"
        
        data = {
            "name": name,
            "stocks": stocks,
            "count": len(stocks),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(pool_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_trading_dates(
        self,
        start: datetime,
        end: datetime,
        exchange: str = "SSE"
    ) -> List[datetime]:
        """
        获取交易日期列表
        
        Args:
            start: 开始日期
            end: 结束日期
            exchange: 交易所
            
        Returns:
            List[datetime]: 交易日期列表
        """
        # 通过加载 K 线数据推断交易日期
        # 简化实现：假设每天都有交易
        dates = []
        current = start
        
        while current <= end:
            # 排除周末
            if current.weekday() < 5:
                dates.append(current)
            current += timedelta(days=1)
        
        return dates
    
    def calculate_returns(
        self,
        bars: List[BarData],
        periods: List[int] = [5, 10, 20, 60]
    ) -> pd.DataFrame:
        """
        计算收益率
        
        Args:
            bars: K 线数据
            periods: 计算周期列表
            
        Returns:
            pd.DataFrame: 收益率数据框
        """
        # 转换为 DataFrame
        data = {
            'datetime': [bar.datetime for bar in bars],
            'open': [bar.open_price for bar in bars],
            'high': [bar.high_price for bar in bars],
            'low': [bar.low_price for bar in bars],
            'close': [bar.close_price for bar in bars],
            'volume': [bar.volume for bar in bars]
        }
        
        df = pd.DataFrame(data)
        df.set_index('datetime', inplace=True)
        
        # 计算收益率
        for period in periods:
            df[f'return_{period}d'] = df['close'].pct_change(period)
        
        return df
    
    def export_bars_to_csv(
        self,
        vt_symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
        filename: Optional[str] = None
    ) -> Path:
        """
        导出 K 线数据到 CSV
        
        Args:
            vt_symbol: 股票代码
            interval: K 线周期
            start: 开始日期
            end: 结束日期
            filename: 文件名（可选）
            
        Returns:
            Path: 文件路径
        """
        bars = self.get_bars(vt_symbol, interval, start, end)
        
        if filename is None:
            filename = f"{vt_symbol.replace('.', '_')}_{interval.value}.csv"
        
        filepath = self._data_path / filename
        
        # 转换为 DataFrame
        data = {
            'datetime': [bar.datetime for bar in bars],
            'open': [bar.open_price for bar in bars],
            'high': [bar.high_price for bar in bars],
            'low': [bar.low_price for bar in bars],
            'close': [bar.close_price for bar in bars],
            'volume': [bar.volume for bar in bars],
            'turnover': [bar.turnover for bar in bars] if bars and hasattr(bars[0], 'turnover') else []
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._bars_cache.clear()
        self._fundamental_cache.clear()
    
    def __repr__(self) -> str:
        return f"AlphaLab(workspace='{self.workspace}')"


def create_lab(workspace: str = "./lab") -> AlphaLab:
    """
    创建 AlphaLab 实例
    
    Args:
        workspace: 工作目录
        
    Returns:
        AlphaLab: 实验室实例
    """
    return AlphaLab(workspace)
