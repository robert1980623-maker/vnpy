# 选股策略文档

## 📦 模块位置

```
vnpy/alpha/strategy/strategies/
├── stock_screener_strategy.py    # 选股策略基类
└── preset_strategies.py          # 预设策略
```

## 🚀 快速开始

### 使用预设策略

```python
from vnpy.alpha.strategy import ValueStockStrategy, GrowthStockStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.lab import AlphaLab

# 创建实验室
lab = AlphaLab("./lab/my_strategy")

# 创建回测引擎
engine = BacktestingEngine(lab)

# 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZSE", "000002.SZSE", ...],  # 股票池
    interval=Interval.DAILY,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000,
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_dividend_yield": 2,
        "top_k": 30
    }
)

# 运行回测
engine.run_backtesting()
```

## 📊 策略基类

### StockScreenerStrategy

选股策略的基类，提供完整的调仓和仓位管理逻辑。

#### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `rebalance_frequency` | str | "weekly" | 调仓频率（daily/weekly/monthly） |
| `rebalance_day` | int | 1 | 调仓日（周频：1-5，月频：1-31） |
| `max_holdings` | int | 50 | 最大持仓数量 |
| `min_holdings` | int | 10 | 最小持仓数量 |
| `cash_ratio` | float | 0.95 | 目标仓位比例 |
| `max_weight` | float | 0.10 | 个股权重上限 |
| `min_weight` | float | 0.01 | 个股权重下限 |
| `min_holding_days` | int | 1 | 最小持有天数 |
| `max_turnover_rate` | float | 0.5 | 最大换手率 |

#### 需要实现的方法

```python
class MyStrategy(StockScreenerStrategy):
    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        """
        获取候选股票池
        
        Returns:
            DataFrame 包含：
            - vt_symbol: 股票代码
            - signal: 选股信号值（用于排序）
        """
        # 你的选股逻辑
        signal_df = self.get_signal()
        
        # 过滤和排序
        filtered = signal_df.filter(...)
        
        return filtered
```

## 🎯 预设策略

### 1. 价值选股策略 (ValueStockStrategy)

筛选低估值、高股息的股票。

**筛选条件**：
- PE ≤ 20
- PB ≤ 3
- 股息率 ≥ 2%
- ROE ≥ 10%

**调仓频率**：月度

```python
setting = {
    "max_pe": 20,
    "max_pb": 3,
    "min_dividend_yield": 2.0,
    "min_roe": 10.0,
    "top_k": 30
}
```

### 2. 成长选股策略 (GrowthStockStrategy)

筛选高增长、高 ROE 的股票。

**筛选条件**：
- 营收增长率 ≥ 20%
- 净利润增长率 ≥ 25%
- ROE ≥ 15%
- PE ≤ 50（容忍高估值）

**调仓频率**：月度

```python
setting = {
    "min_revenue_growth": 20,
    "min_net_profit_growth": 25,
    "min_roe": 15,
    "max_pe": 50,
    "top_k": 30
}
```

### 3. 动量选股策略 (MomentumStockStrategy)

筛选价格动量强的股票。

**参数**：
- 回看周期：20 天
- 最小动量：0（正收益）

**调仓频率**：周度

```python
setting = {
    "lookback_period": 20,
    "min_momentum": 0.0,
    "top_k": 30
}
```

### 4. 多因子选股策略 (MultiFactorStrategy)

综合估值、质量、成长、动量四个维度。

**因子权重**：
- 估值因子：25%（PE、PB，逆向）
- 质量因子：25%（ROE、净利率，正向）
- 成长因子：25%（营收增长、净利润增长，正向）
- 动量因子：25%（20 日动量，正向）

**调仓频率**：月度

```python
setting = {
    "value_weight": 0.25,
    "quality_weight": 0.25,
    "growth_weight": 0.25,
    "momentum_weight": 0.25,
    "top_k": 50
}
```

## 📝 自定义策略示例

### 示例 1：简单动量策略

```python
from vnpy.alpha.strategy import StockScreenerStrategy
from vnpy.trader.object import BarData
import polars as pl

class SimpleMomentumStrategy(StockScreenerStrategy):
    """简单动量策略"""
    
    top_k = 20
    rebalance_frequency = "weekly"
    
    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        signal_df = self.get_signal()
        
        # 假设有 20 日收益率列
        if "return_20d" in signal_df.columns:
            # 选择前 20 名
            filtered = signal_df.sort("return_20d", descending=True).limit(self.top_k)
            filtered = filtered.with_columns(pl.col("return_20d").alias("signal"))
            return filtered
        
        return signal_df
```

### 示例 2：低波动策略

```python
class LowVolatilityStrategy(StockScreenerStrategy):
    """低波动策略 - 选择波动率最低的股票"""
    
    top_k = 30
    rebalance_frequency = "monthly"
    
    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        signal_df = self.get_signal()
        
        # 使用波动率倒数作为信号（波动率越低越好）
        if "volatility_20d" in signal_df.columns:
            filtered = signal_df.filter(pl.col("volatility_20d") > 0)
            filtered = filtered.with_columns(
                (1.0 / pl.col("volatility_20d")).alias("signal")
            )
            return filtered
        
        return signal_df
```

### 示例 3：结合股票池和财务数据

```python
from vnpy.alpha.dataset import StockPool, FundamentalData

class FundamentalScreenerStrategy(StockScreenerStrategy):
    """基本面选股策略"""
    
    top_k = 50
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化股票池和财务数据
        self.stock_pool = StockPool("./data/pool")
        self.fundamental = FundamentalData("./data/fundamental")
    
    def _get_stock_pool(self, bars: dict[str, BarData]) -> pl.DataFrame:
        # 1. 获取沪深 300 成分股
        csi300 = self.stock_pool.get_index_components(
            "csi300",
            self.datetime
        )
        
        # 2. 获取信号
        signal_df = self.get_signal()
        
        # 3. 过滤到成分股
        signal_df = signal_df.filter(
            pl.col("vt_symbol").is_in(csi300)
        )
        
        # 4. 加载财务数据
        fundamental_df = self.fundamental.load_market_data(
            self.datetime.strftime("%Y-%m-%d")
        )
        
        # 5. 合并并筛选
        if not fundamental_df.is_empty():
            merged = signal_df.join(
                fundamental_df,
                on="vt_symbol",
                how="inner"
            )
            
            # 筛选优质股
            filtered = merged.filter(
                (pl.col("roe") >= 15) &
                (pl.col("revenue_growth") >= 10) &
                (pl.col("pe_ratio") <= 40)
            )
            
            # 综合得分
            filtered = filtered.with_columns(
                (
                    pl.col("roe") * 0.4 +
                    pl.col("revenue_growth") * 0.4 -
                    pl.col("pe_ratio") * 0.01
                ).alias("signal")
            )
            
            return filtered
        
        return signal_df
```

## 🔧 调仓逻辑

### 调仓流程

```
1. 判断是否到达调仓日
   ↓
2. 获取候选股票池 (_get_stock_pool)
   ↓
3. 计算目标持仓 (_calculate_target_positions)
   ↓
4. 生成交易列表 (_generate_trades)
   ↓
5. 执行卖出 (_execute_sells)
   ↓
6. 执行买入 (_execute_buys)
   ↓
7. 更新调仓日期
```

### 调仓频率设置

```python
# 日频调仓
rebalance_frequency = "daily"

# 周频调仓（每周一）
rebalance_frequency = "weekly"
rebalance_day = 1  # 1=周一，5=周五

# 月频调仓（每月 1 号）
rebalance_frequency = "monthly"
rebalance_day = 1  # 1-31
```

### 仓位控制

```python
# 等权重配置
# 默认行为：每只股票分配相同资金

# 自定义权重
def _calculate_target_positions(self, stock_pool, bars):
    target_positions = {}
    
    for row in stock_pool.iter_rows(named=True):
        vt_symbol = row["vt_symbol"]
        signal = row["signal"]
        
        # 根据信号强度分配权重
        weight = signal / total_signal
        
        # 计算目标市值
        portfolio_value = self.get_portfolio_value()
        target_value = portfolio_value * self.cash_ratio * weight
        
        # 计算目标股数
        price = bars[vt_symbol].close_price
        target_volume = round_to(target_value / price, 100)
        
        target_positions[vt_symbol] = target_volume
    
    return target_positions
```

## 📊 回测配置

### 完整回测示例

```python
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.trader.constant import Interval

# 创建实验室
lab = AlphaLab("./lab/value_strategy")

# 创建回测引擎
engine = BacktestingEngine(lab)

# 设置回测参数
engine.set_parameters(
    vt_symbols=[],  # 空列表表示使用信号中的所有股票
    interval=Interval.DAILY,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000,
    risk_free=0.03,  # 无风险利率 3%
    annual_days=240
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_dividend_yield": 2,
        "min_roe": 10,
        "top_k": 30,
        "cash_ratio": 0.95
    }
)

# 加载数据
engine.load_data()

# 运行回测
engine.run_backtesting()

# 计算绩效
engine.calculate_result()
engine.calculate_statistics()

# 显示结果
engine.show_chart()
```

## ⚠️ 注意事项

1. **信号数据**：确保 `get_signal()` 返回的 DataFrame 包含所需列
2. **股票池更新**：成分股会定期调整，需要定期更新
3. **财务数据滞后**：财报数据有披露滞后，注意使用点
4. **交易成本**：合理设置费率参数
5. **流动性**：考虑最小成交量限制

## 🎯 下一步

策略层完成后，继续实现：

- [ ] 回测层升级 - 支持截面回测模式
- [ ] 数据下载脚本
- [ ] CLI 工具

## 📖 相关文档

- [股票池管理](stock_pool.md)
- [财务数据](fundamental_data.md)
- [策略回测](cta_strategy.md)
