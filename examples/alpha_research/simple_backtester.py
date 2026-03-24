#!/usr/bin/env python3
"""
简易策略回测系统

功能：
- 基于历史数据回测策略
- 计算收益指标
- 生成回测报告
"""

import tushare as ts
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional

# 初始化 Tushare
ts.set_token('612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5')
pro = ts.pro_api()


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    daily_returns: List[float]


class SimpleBacktester:
    """简易回测器"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.results: List[BacktestResult] = []
    
    def get_price_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取历史价格数据"""
        try:
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                return pd.DataFrame()
            
            # 按日期排序
            df = df.sort_values('trade_date').reset_index(drop=True)
            return df
        except Exception as e:
            print(f"❌ 获取数据失败：{e}")
            return pd.DataFrame()
    
    def backtest_buy_and_hold(self, ts_code: str, stock_name: str,
                               start_date: str, end_date: str) -> BacktestResult:
        """回测买入持有策略"""
        print(f"\n【回测】买入持有策略 - {stock_name} ({ts_code})")
        print("-" * 60)
        
        # 获取数据
        df = self.get_price_data(ts_code, start_date, end_date)
        
        if df.empty:
            print("  ❌ 无数据")
            return None
        
        print(f"  数据范围：{df['trade_date'].iloc[0]} - {df['trade_date'].iloc[-1]}")
        print(f"  交易日数：{len(df)}")
        
        # 计算收益
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        
        # 考虑分红（简化处理，暂不考虑）
        total_return = (end_price - start_price) / start_price * 100
        
        # 计算年化收益
        days = (datetime.strptime(end_date, '%Y%m%d') - 
                datetime.strptime(start_date, '%Y%m%d')).days
        years = days / 365.25
        annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # 计算日收益率
        daily_returns = df['close'].pct_change().dropna().tolist()
        
        # 计算夏普比率（假设无风险利率 3%）
        if len(daily_returns) > 1:
            excess_returns = [r - 0.03/252 for r in daily_returns]
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
        else:
            sharpe = 0
        
        # 计算最大回撤
        cumulative = (1 + pd.Series(daily_returns)).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min()) * 100 if len(drawdowns) > 0 else 0
        
        # 计算胜率
        positive_days = sum(1 for r in daily_returns if r > 0)
        win_rate = positive_days / len(daily_returns) * 100 if daily_returns else 0
        
        # 最终价值
        final_value = self.initial_capital * (1 + total_return/100)
        
        result = BacktestResult(
            strategy_name="买入持有",
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=1,
            daily_returns=daily_returns
        )
        
        self.results.append(result)
        
        # 打印结果
        print()
        print("【回测结果】")
        print(f"  初始资金：  ¥{self.initial_capital:>14,.2f}")
        print(f"  最终价值：  ¥{final_value:>14,.2f}")
        print(f"  总收益：    {total_return:>13.2f}%")
        print(f"  年化收益：  {annual_return:>13.2f}%")
        print(f"  夏普比率：  {sharpe:>13.2f}")
        print(f"  最大回撤：  {max_drawdown:>13.2f}%")
        print(f"  胜率：      {win_rate:>13.2f}%")
        print(f"  交易次数：  {result.trade_count:>13}")
        
        return result
    
    def backtest_ma_strategy(self, ts_code: str, stock_name: str,
                              start_date: str, end_date: str,
                              short_window: int = 5, long_window: int = 20) -> BacktestResult:
        """回测均线策略（金叉买入，死叉卖出）"""
        print(f"\n【回测】均线策略 ({short_window}/{long_window}) - {stock_name} ({ts_code})")
        print("-" * 60)
        
        # 获取数据
        df = self.get_price_data(ts_code, start_date, end_date)
        
        if len(df) < long_window:
            print("  ❌ 数据不足")
            return None
        
        print(f"  数据范围：{df['trade_date'].iloc[0]} - {df['trade_date'].iloc[-1]}")
        print(f"  交易日数：{len(df)}")
        
        # 计算均线
        df['ma_short'] = df['close'].rolling(window=short_window).mean()
        df['ma_long'] = df['close'].rolling(window=long_window).mean()
        
        # 生成交易信号
        df['signal'] = 0
        df.loc[df['ma_short'] > df['ma_long'], 'signal'] = 1  # 持有
        
        # 计算策略收益
        df['strategy_return'] = df['signal'].shift(1) * df['close'].pct_change()
        
        # 计算累计收益
        cumulative_returns = (1 + df['strategy_return'].fillna(0)).cumprod()
        total_return = (cumulative_returns.iloc[-1] - 1) * 100
        
        # 计算年化收益
        days = (datetime.strptime(end_date, '%Y%m%d') - 
                datetime.strptime(start_date, '%Y%m%d')).days
        years = days / 365.25
        annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # 日收益率
        daily_returns = df['strategy_return'].fillna(0).tolist()
        
        # 夏普比率
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            excess_returns = [r - 0.03/252 for r in daily_returns]
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        # 最大回撤
        cumulative = pd.Series(daily_returns).cumsum()
        cumulative = cumulative + 1  # 从 1 开始
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min()) * 100 if len(drawdowns) > 0 else 0
        
        # 胜率
        positive_days = sum(1 for r in daily_returns if r > 0)
        win_rate = positive_days / len(daily_returns) * 100 if daily_returns else 0
        
        # 交易次数（信号变化次数）
        signal_changes = (df['signal'].diff() != 0).sum()
        trade_count = signal_changes // 2  # 一次买卖算一笔交易
        
        # 最终价值
        final_value = self.initial_capital * (1 + total_return/100)
        
        result = BacktestResult(
            strategy_name=f"均线策略 ({short_window}/{long_window})",
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            daily_returns=daily_returns
        )
        
        self.results.append(result)
        
        # 打印结果
        print()
        print("【回测结果】")
        print(f"  初始资金：  ¥{self.initial_capital:>14,.2f}")
        print(f"  最终价值：  ¥{final_value:>14,.2f}")
        print(f"  总收益：    {total_return:>13.2f}%")
        print(f"  年化收益：  {annual_return:>13.2f}%")
        print(f"  夏普比率：  {sharpe:>13.2f}")
        print(f"  最大回撤：  {max_drawdown:>13.2f}%")
        print(f"  胜率：      {win_rate:>13.2f}%")
        print(f"  交易次数：  {trade_count:>13}")
        
        return result
    
    def compare_strategies(self):
        """对比策略表现"""
        if not self.results:
            print("❌ 无回测结果")
            return
        
        print("\n" + "=" * 80)
        print(" " * 25 + "📊 策略对比")
        print("=" * 80)
        
        print(f"\n{'策略':<25} {'总收益':>12} {'年化':>12} {'夏普':>10} {'回撤':>10} {'胜率':>10} {'交易':>8}")
        print("-" * 95)
        
        for result in self.results:
            print(f"{result.strategy_name:<25} "
                  f"{result.total_return:>11.2f}% "
                  f"{result.annual_return:>11.2f}% "
                  f"{result.sharpe_ratio:>10.2f} "
                  f"{result.max_drawdown:>9.2f}% "
                  f"{result.win_rate:>9.2f}% "
                  f"{result.trade_count:>8}")
        
        print()
        
        # 最佳策略
        best_return = max(self.results, key=lambda x: x.total_return)
        best_sharpe = max(self.results, key=lambda x: x.sharpe_ratio)
        lowest_drawdown = min(self.results, key=lambda x: x.max_drawdown)
        
        print("【最佳表现】")
        print(f"  最高收益：  {best_return.strategy_name} ({best_return.total_return:.2f}%)")
        print(f"  最佳夏普：  {best_sharpe.strategy_name} ({best_sharpe.sharpe_ratio:.2f})")
        print(f"  最小回撤：  {lowest_drawdown.strategy_name} ({lowest_drawdown.max_drawdown:.2f}%)")
        print()


def main():
    """主函数 - 演示回测"""
    print("=" * 80)
    print(" " * 25 + "📊 策略回测系统")
    print("=" * 80)
    
    # 创建回测器
    backtester = SimpleBacktester(initial_capital=1000000.0)
    
    # 回测时间段（1 年）
    end_date = '20260320'
    start_date = '20250320'
    
    # 回测股票
    stocks = [
        ('600519.SH', '贵州茅台'),
        ('600036.SH', '招商银行'),
        ('000001.SZ', '平安银行'),
    ]
    
    # 对每只股票回测
    for ts_code, stock_name in stocks:
        print(f"\n{'='*80}")
        print(f"  {stock_name} ({ts_code})")
        print(f"{'='*80}")
        
        # 买入持有策略
        backtester.backtest_buy_and_hold(ts_code, stock_name, start_date, end_date)
        
        # 均线策略
        backtester.backtest_ma_strategy(ts_code, stock_name, start_date, end_date, 
                                         short_window=5, long_window=20)
    
    # 对比策略
    backtester.compare_strategies()
    
    # 保存回测报告
    print("=" * 80)
    print("✅ 回测完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
