#!/usr/bin/env python3
"""
vnpy.trader.constant 模块测试

目标：测试所有常量枚举类
"""

import pytest
from vnpy.trader.constant import (
    Direction,
    Offset,
    Status,
    Product,
    OrderType,
    OptionType,
    Exchange,
    Currency,
    Interval
)


class TestDirection:
    """Direction 枚举测试"""
    
    def test_direction_values(self):
        """测试 Direction 枚举值"""
        assert Direction.LONG.value == "多"
        assert Direction.SHORT.value == "空"
        assert Direction.NET.value == "净"
    
    def test_direction_count(self):
        """测试 Direction 枚举数量"""
        assert len(Direction) == 3


class TestOffset:
    """Offset 枚举测试"""
    
    def test_offset_values(self):
        """测试 Offset 枚举值"""
        assert Offset.NONE.value == ""
        assert Offset.OPEN.value == "开"
        assert Offset.CLOSE.value == "平"
        assert Offset.CLOSETODAY.value == "平今"
        assert Offset.CLOSEYESTERDAY.value == "平昨"
    
    def test_offset_count(self):
        """测试 Offset 枚举数量"""
        assert len(Offset) == 5


class TestStatus:
    """Status 枚举测试"""
    
    def test_status_values(self):
        """测试 Status 枚举值"""
        assert Status.SUBMITTING.value == "提交中"
        assert Status.NOTTRADED.value == "未成交"
        assert Status.PARTTRADED.value == "部分成交"
        assert Status.ALLTRADED.value == "全部成交"
        assert Status.CANCELLED.value == "已撤销"
        assert Status.REJECTED.value == "拒单"
    
    def test_status_count(self):
        """测试 Status 枚举数量"""
        assert len(Status) == 6


class TestProduct:
    """Product 枚举测试"""
    
    def test_product_values(self):
        """测试 Product 枚举值"""
        assert Product.EQUITY.value == "股票"
        assert Product.FUTURES.value == "期货"
        assert Product.OPTION.value == "期权"
        assert Product.INDEX.value == "指数"
        assert Product.FOREX.value == "外汇"
        assert Product.SPOT.value == "现货"
        assert Product.ETF.value == "ETF"
        assert Product.BOND.value == "债券"
        assert Product.WARRANT.value == "权证"
        assert Product.SPREAD.value == "价差"
        assert Product.FUND.value == "基金"
        assert Product.CFD.value == "CFD"
        assert Product.SWAP.value == "互换"
    
    def test_product_count(self):
        """测试 Product 枚举数量"""
        assert len(Product) == 13


class TestOrderType:
    """OrderType 枚举测试"""
    
    def test_order_type_values(self):
        """测试 OrderType 枚举值"""
        assert OrderType.LIMIT.value == "限价"
        assert OrderType.MARKET.value == "市价"
        assert OrderType.STOP.value == "STOP"
        assert OrderType.FAK.value == "FAK"
        assert OrderType.FOK.value == "FOK"
        assert OrderType.RFQ.value == "询价"
    
    def test_order_type_count(self):
        """测试 OrderType 枚举数量"""
        assert len(OrderType) == 6


class TestOptionType:
    """OptionType 枚举测试"""
    
    def test_option_type_values(self):
        """测试 OptionType 枚举值"""
        assert OptionType.CALL.value == "看涨期权"
        assert OptionType.PUT.value == "看跌期权"
    
    def test_option_type_count(self):
        """测试 OptionType 枚举数量"""
        assert len(OptionType) == 2


class TestExchange:
    """Exchange 枚举测试"""
    
    def test_chinese_exchanges(self):
        """测试中国交易所"""
        assert Exchange.CFFEX.value == "CFFEX"
        assert Exchange.SHFE.value == "SHFE"
        assert Exchange.CZCE.value == "CZCE"
        assert Exchange.DCE.value == "DCE"
        assert Exchange.INE.value == "INE"
        assert Exchange.GFEX.value == "GFEX"
        assert Exchange.SSE.value == "SSE"
        assert Exchange.SZSE.value == "SZSE"
        assert Exchange.BSE.value == "BSE"
        assert Exchange.SHHK.value == "SHHK"
        assert Exchange.SZHK.value == "SZHK"
        assert Exchange.SGE.value == "SGE"
        assert Exchange.WXE.value == "WXE"
        assert Exchange.CFETS.value == "CFETS"
        assert Exchange.XBOND.value == "XBOND"
    
    def test_global_exchanges(self):
        """测试全球交易所"""
        assert Exchange.SMART.value == "SMART"
        assert Exchange.NYSE.value == "NYSE"
        assert Exchange.NASDAQ.value == "NASDAQ"
        assert Exchange.ARCA.value == "ARCA"
        assert Exchange.EDGEA.value == "EDGEA"
        assert Exchange.ISLAND.value == "ISLAND"
        assert Exchange.BATS.value == "BATS"
        assert Exchange.IEX.value == "IEX"
        assert Exchange.AMEX.value == "AMEX"
        assert Exchange.TSE.value == "TSE"
        assert Exchange.NYMEX.value == "NYMEX"
        assert Exchange.COMEX.value == "COMEX"
        assert Exchange.GLOBEX.value == "GLOBEX"
        assert Exchange.IDEALPRO.value == "IDEALPRO"
        assert Exchange.CME.value == "CME"
        assert Exchange.ICE.value == "ICE"
        assert Exchange.SEHK.value == "SEHK"
        assert Exchange.HKFE.value == "HKFE"
        assert Exchange.SGX.value == "SGX"
        assert Exchange.CBOT.value == "CBOT"
        assert Exchange.CBOE.value == "CBOE"
        assert Exchange.CFE.value == "CFE"
        assert Exchange.DME.value == "DME"
        assert Exchange.EUREX.value == "EUX"
        assert Exchange.APEX.value == "APEX"
        assert Exchange.LME.value == "LME"
        assert Exchange.BMD.value == "BMD"
        assert Exchange.TOCOM.value == "TOCOM"
        assert Exchange.EUNX.value == "EUNX"
        assert Exchange.KRX.value == "KRX"
        assert Exchange.OTC.value == "OTC"
        assert Exchange.IBKRATS.value == "IBKRATS"
    
    def test_special_exchanges(self):
        """测试特殊交易所"""
        assert Exchange.LOCAL.value == "LOCAL"
    
    def test_exchange_count(self):
        """测试 Exchange 枚举数量"""
        assert len(Exchange) == 48


class TestCurrency:
    """Currency 枚举测试"""
    
    def test_currency_values(self):
        """测试 Currency 枚举值"""
        assert Currency.USD.value == "USD"
        assert Currency.HKD.value == "HKD"
        assert Currency.CNY.value == "CNY"
        assert Currency.CAD.value == "CAD"
    
    def test_currency_count(self):
        """测试 Currency 枚举数量"""
        assert len(Currency) == 4


class TestInterval:
    """Interval 枚举测试"""
    
    def test_interval_values(self):
        """测试 Interval 枚举值"""
        assert Interval.MINUTE.value == "1m"
        assert Interval.HOUR.value == "1h"
        assert Interval.DAILY.value == "d"
        assert Interval.WEEKLY.value == "w"
        assert Interval.TICK.value == "tick"
    
    def test_interval_count(self):
        """测试 Interval 枚举数量"""
        assert len(Interval) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
