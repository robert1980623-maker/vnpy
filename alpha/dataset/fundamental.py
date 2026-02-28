"""
财务数据模块

提供财务指标的获取和管理功能：
- 估值指标（PE、PB、PS 等）
- 盈利能力（ROE、ROA、毛利率等）
- 成长能力（营收增长率、净利润增长率等）
- 偿债能力（资产负债率、流动比率等）
- 现金流指标
"""

from typing import List, Dict, Optional, Union, Any
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class FinancialCategory(Enum):
    """财务指标类别"""
    VALUATION = "valuation"  # 估值指标
    PROFITABILITY = "profitability"  # 盈利能力
    GROWTH = "growth"  # 成长能力
    SOLVENCY = "solvency"  # 偿债能力
    CASHFLOW = "cashflow"  # 现金流


@dataclass
class FinancialIndicator:
    """
    财务指标数据类
    """
    vt_symbol: str
    report_date: str  # 报告期，如 "2024-03-31"
    
    # 估值指标
    pe_ratio: Optional[float] = None  # 市盈率 (TTM)
    pb_ratio: Optional[float] = None  # 市净率
    ps_ratio: Optional[float] = None  # 市销率
    pcf_ratio: Optional[float] = None  # 市现率
    dividend_yield: Optional[float] = None  # 股息率
    
    # 盈利能力
    roe: Optional[float] = None  # 净资产收益率
    roa: Optional[float] = None  # 总资产收益率
    gross_margin: Optional[float] = None  # 毛利率
    net_margin: Optional[float] = None  # 净利率
    operating_margin: Optional[float] = None  # 营业利润率
    
    # 成长能力
    revenue_growth: Optional[float] = None  # 营收增长率
    net_profit_growth: Optional[float] = None  # 净利润增长率
    eps_growth: Optional[float] = None  # EPS 增长率
    book_value_growth: Optional[float] = None  # 净资产增长率
    
    # 偿债能力
    debt_to_asset: Optional[float] = None  # 资产负债率
    current_ratio: Optional[float] = None  # 流动比率
    quick_ratio: Optional[float] = None  # 速动比率
    interest_coverage: Optional[float] = None  # 利息保障倍数
    
    # 现金流
    operating_cash_flow: Optional[float] = None  # 经营活动现金流
    free_cash_flow: Optional[float] = None  # 自由现金流
    cash_flow_per_share: Optional[float] = None  # 每股现金流
    
    # 每股指标
    eps: Optional[float] = None  # 每股收益
    bps: Optional[float] = None  # 每股净资产
    revenue_per_share: Optional[float] = None  # 每股营收
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "vt_symbol": self.vt_symbol,
            "report_date": self.report_date,
            "valuation": {
                "pe_ratio": self.pe_ratio,
                "pb_ratio": self.pb_ratio,
                "ps_ratio": self.ps_ratio,
                "pcf_ratio": self.pcf_ratio,
                "dividend_yield": self.dividend_yield,
            },
            "profitability": {
                "roe": self.roe,
                "roa": self.roa,
                "gross_margin": self.gross_margin,
                "net_margin": self.net_margin,
                "operating_margin": self.operating_margin,
            },
            "growth": {
                "revenue_growth": self.revenue_growth,
                "net_profit_growth": self.net_profit_growth,
                "eps_growth": self.eps_growth,
                "book_value_growth": self.book_value_growth,
            },
            "solvency": {
                "debt_to_asset": self.debt_to_asset,
                "current_ratio": self.current_ratio,
                "quick_ratio": self.quick_ratio,
                "interest_coverage": self.interest_coverage,
            },
            "cashflow": {
                "operating_cash_flow": self.operating_cash_flow,
                "free_cash_flow": self.free_cash_flow,
                "cash_flow_per_share": self.cash_flow_per_share,
            },
            "per_share": {
                "eps": self.eps,
                "bps": self.bps,
                "revenue_per_share": self.revenue_per_share,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FinancialIndicator":
        """从字典创建"""
        return cls(
            vt_symbol=data["vt_symbol"],
            report_date=data["report_date"],
            pe_ratio=data.get("valuation", {}).get("pe_ratio"),
            pb_ratio=data.get("valuation", {}).get("pb_ratio"),
            ps_ratio=data.get("valuation", {}).get("ps_ratio"),
            pcf_ratio=data.get("valuation", {}).get("pcf_ratio"),
            dividend_yield=data.get("valuation", {}).get("dividend_yield"),
            roe=data.get("profitability", {}).get("roe"),
            roa=data.get("profitability", {}).get("roa"),
            gross_margin=data.get("profitability", {}).get("gross_margin"),
            net_margin=data.get("profitability", {}).get("net_margin"),
            operating_margin=data.get("profitability", {}).get("operating_margin"),
            revenue_growth=data.get("growth", {}).get("revenue_growth"),
            net_profit_growth=data.get("growth", {}).get("net_profit_growth"),
            eps_growth=data.get("growth", {}).get("eps_growth"),
            book_value_growth=data.get("growth", {}).get("book_value_growth"),
            debt_to_asset=data.get("solvency", {}).get("debt_to_asset"),
            current_ratio=data.get("solvency", {}).get("current_ratio"),
            quick_ratio=data.get("solvency", {}).get("quick_ratio"),
            interest_coverage=data.get("solvency", {}).get("interest_coverage"),
            operating_cash_flow=data.get("cashflow", {}).get("operating_cash_flow"),
            free_cash_flow=data.get("cashflow", {}).get("free_cash_flow"),
            cash_flow_per_share=data.get("cashflow", {}).get("cash_flow_per_share"),
            eps=data.get("per_share", {}).get("eps"),
            bps=data.get("per_share", {}).get("bps"),
            revenue_per_share=data.get("per_share", {}).get("revenue_per_share"),
        )
    
    def get_value(self, field: str) -> Optional[float]:
        """
        获取指定字段的值
        
        Args:
            field: 字段名
            
        Returns:
            Optional[float]: 字段值
        """
        return getattr(self, field, None)
    
    def is_valid(self, field: str) -> bool:
        """
        检查字段是否有有效值
        
        Args:
            field: 字段名
            
        Returns:
            bool: 是否有效
        """
        value = self.get_value(field)
        return value is not None and value > 0


class FundamentalData:
    """
    财务数据管理器
    
    提供财务数据的存储、查询和筛选功能
    """
    
    def __init__(self):
        """初始化财务数据管理器"""
        self._data: Dict[str, Dict[str, FinancialIndicator]] = {}
        self._latest_report: Dict[str, str] = {}  # 每只股票最新报告期
    
    def add(self, indicator: FinancialIndicator) -> None:
        """
        添加财务指标数据
        
        Args:
            indicator: 财务指标对象
        """
        vt_symbol = indicator.vt_symbol
        report_date = indicator.report_date
        
        if vt_symbol not in self._data:
            self._data[vt_symbol] = {}
        
        self._data[vt_symbol][report_date] = indicator
        
        # 更新最新报告期
        if vt_symbol not in self._latest_report or report_date > self._latest_report[vt_symbol]:
            self._latest_report[vt_symbol] = report_date
    
    def add_batch(self, indicators: List[FinancialIndicator]) -> None:
        """
        批量添加财务指标数据
        
        Args:
            indicators: 财务指标列表
        """
        for indicator in indicators:
            self.add(indicator)
    
    def get(self, vt_symbol: str, report_date: Optional[str] = None) -> Optional[FinancialIndicator]:
        """
        获取财务指标数据
        
        Args:
            vt_symbol: 股票代码
            report_date: 报告期（可选，默认返回最新）
            
        Returns:
            Optional[FinancialIndicator]: 财务指标
        """
        if vt_symbol not in self._data:
            return None
        
        if report_date is None:
            report_date = self._latest_report.get(vt_symbol)
        
        if report_date is None:
            return None
        
        return self._data[vt_symbol].get(report_date)
    
    def get_latest(self, vt_symbol: str) -> Optional[FinancialIndicator]:
        """
        获取最新财务指标
        
        Args:
            vt_symbol: 股票代码
            
        Returns:
            Optional[FinancialIndicator]: 最新财务指标
        """
        return self.get(vt_symbol)
    
    def get_all_latest(self) -> Dict[str, FinancialIndicator]:
        """
        获取所有股票的最新财务指标
        
        Returns:
            Dict[str, FinancialIndicator]: 股票代码 -> 财务指标映射
        """
        result = {}
        for vt_symbol in self._latest_report:
            indicator = self.get_latest(vt_symbol)
            if indicator:
                result[vt_symbol] = indicator
        return result
    
    def get_history(self, vt_symbol: str) -> List[FinancialIndicator]:
        """
        获取股票的历史财务数据
        
        Args:
            vt_symbol: 股票代码
            
        Returns:
            List[FinancialIndicator]: 按报告期排序的财务指标列表
        """
        if vt_symbol not in self._data:
            return []
        
        reports = self._data[vt_symbol]
        return sorted(reports.values(), key=lambda x: x.report_date)
    
    def filter_by_field(
        self,
        field: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        report_date: Optional[str] = None
    ) -> List[str]:
        """
        根据字段值筛选股票
        
        Args:
            field: 字段名
            min_value: 最小值（包含）
            max_value: 最大值（包含）
            report_date: 报告期（默认最新）
            
        Returns:
            List[str]: 符合条件的股票代码列表
        """
        result = []
        
        for vt_symbol in self._latest_report:
            indicator = self.get(vt_symbol, report_date)
            if indicator is None:
                continue
            
            value = indicator.get_value(field)
            if value is None:
                continue
            
            if min_value is not None and value < min_value:
                continue
            if max_value is not None and value > max_value:
                continue
            
            result.append(vt_symbol)
        
        return sorted(result)
    
    def filter_by_multiple(
        self,
        conditions: Dict[str, Dict[str, float]],
        report_date: Optional[str] = None
    ) -> List[str]:
        """
        根据多个条件筛选股票
        
        Args:
            conditions: 筛选条件，格式 {field: {"min": x, "max": y}}
            report_date: 报告期（默认最新）
            
        Returns:
            List[str]: 符合条件的股票代码列表
            
        Example:
            >>> conditions = {
            ...     "pe_ratio": {"max": 20},
            ...     "pb_ratio": {"max": 3},
            ...     "roe": {"min": 10},
            ...     "dividend_yield": {"min": 2}
            ... }
            >>> fd.filter_by_multiple(conditions)
        """
        result = []
        
        for vt_symbol in self._latest_report:
            indicator = self.get(vt_symbol, report_date)
            if indicator is None:
                continue
            
            match = True
            for field, limits in conditions.items():
                value = indicator.get_value(field)
                if value is None:
                    match = False
                    break
                
                if "min" in limits and value < limits["min"]:
                    match = False
                    break
                if "max" in limits and value > limits["max"]:
                    match = False
                    break
            
            if match:
                result.append(vt_symbol)
        
        return sorted(result)
    
    def get_statistics(self, field: str) -> Dict[str, float]:
        """
        计算字段的统计信息
        
        Args:
            field: 字段名
            
        Returns:
            Dict[str, float]: 统计信息 {min, max, mean, median}
        """
        values = []
        
        for vt_symbol in self._latest_report:
            indicator = self.get_latest(vt_symbol)
            if indicator:
                value = indicator.get_value(field)
                if value is not None:
                    values.append(value)
        
        if not values:
            return {}
        
        values.sort()
        n = len(values)
        
        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / n,
            "median": values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2
        }
    
    def get_stock_count(self) -> int:
        """
        获取股票数量
        
        Returns:
            int: 股票数量
        """
        return len(self._latest_report)
    
    def get_symbols(self) -> List[str]:
        """
        获取所有股票代码
        
        Returns:
            List[str]: 股票代码列表
        """
        return sorted(list(self._latest_report.keys()))
    
    def clear(self) -> None:
        """清空所有数据"""
        self._data.clear()
        self._latest_report.clear()
    
    def save(self, filepath: Union[str, Path]) -> None:
        """
        保存财务数据到文件
        
        Args:
            filepath: 保存路径
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            symbol: {
                date: indicator.to_dict()
                for date, indicator in reports.items()
            }
            for symbol, reports in self._data.items()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "FundamentalData":
        """
        从文件加载财务数据
        
        Args:
            filepath: 文件路径
            
        Returns:
            FundamentalData: 加载的财务数据管理器
        """
        filepath = Path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fd = cls()
        for symbol, reports in data.items():
            for report_date, indicator_dict in reports.items():
                indicator = FinancialIndicator.from_dict(indicator_dict)
                fd.add(indicator)
        
        return fd
    
    def __len__(self) -> int:
        return self.get_stock_count()
    
    def __repr__(self) -> str:
        return f"FundamentalData(stock_count={self.get_stock_count()})"


def create_fundamental_data() -> FundamentalData:
    """
    创建财务数据管理器
    
    Returns:
        FundamentalData: 财务数据管理器
    """
    return FundamentalData()


def create_indicator(
    vt_symbol: str,
    report_date: str,
    **kwargs
) -> FinancialIndicator:
    """
    创建财务指标对象
    
    Args:
        vt_symbol: 股票代码
        report_date: 报告期
        **kwargs: 其他字段值
        
    Returns:
        FinancialIndicator: 财务指标对象
    """
    return FinancialIndicator(
        vt_symbol=vt_symbol,
        report_date=report_date,
        **kwargs
    )
