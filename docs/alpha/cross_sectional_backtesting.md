# 截面回测引擎文档

## 📦 模块位置

```
vnpy/alpha/strategy/cross_sectional_engine.py
```

## 🚀 快速开始

### 基础回测

```python
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.trader.constant import Interval

# 创建实验室
lab = AlphaLab("./lab/value_strategy")

# 创建截面回测引擎
engine = CrossSectionalBacktestingEngine(lab)

# 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZSE", "000002.SZSE", ...],  # 全市场股票池
    interval=Interval.DAILY,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000,
    risk_free=0.03,
    annual_days=240
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_dividend_yield": 2,
        "top_k": 30,
        "rebalance_frequency": "monthly"
    }
)

# 加载数据
engine.load_data()

# 运行回测
engine.run_backtesting()

# 计算结果
engine.calculate_result()
stats = engine.calculate_statistics()

# 显示图表
engine.show_chart()
```

## 📊 核心功能

### 1. 截面回测支持

截面回测引擎专为选股策略设计，支持：

- ✅ **多股票同时回测** - 支持全市场股票池
- ✅ **动态股票池** - 股票池可以随时间变化
- ✅ **截面调仓** - 基于信号的截面排序和筛选
- ✅ **资金管理** - 等权重配置、仓位控制

### 2. 与传统回测的区别

| 特性 | 传统回测 | 截面回测 |
|------|----------|----------|
| 标的数量 | 单标的或少量 | 多标的（几十到几百） |
| 调仓逻辑 | 基于时间序列信号 | 基于截面排序 |
| 股票池 | 固定 | 动态变化 |
| 仓位管理 | 手动 | 自动等权重 |
| 适用策略 | 时序策略 | 选股策略 |

## 🔧 参数说明

### set_parameters

```python
engine.set_parameters(
    vt_symbols: list[str],        # 股票池
    interval: Interval,           # K 线周期
    start: datetime,              # 开始日期
    end: datetime,                # 结束日期
    capital: int = 1_000_000,     # 初始资金
    risk_free: float = 0,         # 无风险利率
    annual_days: int = 240        # 年交易日数
)
```

### add_strategy

```python
engine.add_strategy(
    strategy_class: type,         # 策略类
    setting: dict                 # 策略参数
)
```

## 📝 完整示例

### 示例 1：价值股回测

```python
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.trader.constant import Interval

# 创建回测引擎
lab = AlphaLab("./lab/value_backtest")
engine = create_cross_sectional_engine(lab)

# 设置参数
engine.set_parameters(
    vt_symbols=[],  # 从信号数据中获取
    interval=Interval.DAILY,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000,
    risk_free=0.03
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_dividend_yield": 2.0,
        "min_roe": 10.0,
        "top_k": 30,
        "rebalance_frequency": "monthly",
        "cash_ratio": 0.95
    }
)

# 加载数据
engine.load_data()

# 运行回测
engine.run_backtesting()

# 计算绩效
engine.calculate_result()
stats = engine.calculate_statistics()

# 输出结果
print("\n回测结果:")
for key, value in stats.items():
    print(f"  {key}: {value}")

# 显示图表
engine.show_chart()
```

### 示例 2：多因子策略回测

```python
from vnpy.alpha.strategy import MultiFactorStrategy

engine.add_strategy(
    MultiFactorStrategy,
    setting={
        "value_weight": 0.25,
        "quality_weight": 0.25,
        "growth_weight": 0.25,
        "momentum_weight": 0.25,
        "top_k": 50,
        "rebalance_frequency": "monthly"
    }
)
```

### 示例 3：成长股回测

```python
from vnpy.alpha.strategy import GrowthStockStrategy

engine.add_strategy(
    GrowthStockStrategy,
    setting={
        "min_revenue_growth": 20,
        "min_net_profit_growth": 25,
        "min_roe": 15,
        "max_pe": 50,
        "top_k": 30,
        "rebalance_frequency": "monthly"
    }
)
```

## 📊 统计指标

回测完成后，`calculate_statistics()` 返回以下指标：

| 指标 | 说明 |
|------|------|
| 总交易日 | 回测总天数 |
| 盈利交易日 | 盈利的交易日数量 |
| 亏损交易日 | 亏损的交易日数量 |
| 胜率 | 盈利交易日占比 |
| 初始资金 | 回测初始资金 |
| 结束资金 | 回测结束资金 |
| 总收益率 | 总收益百分比 |
| 年化收益 | 年化收益率 |
| 最大回撤 | 最大资金回撤 |
| 夏普比率 | 风险调整后收益 |
| 总交易次数 | 总成交次数 |
| 总成交额 | 总成交金额 |
| 总手续费 | 总交易成本 |

## 📈 图表展示

`show_chart()` 显示三个子图：

1. **资金曲线** - 组合资金变化
2. **每日盈亏** - 每日收益柱状图
3. **回撤** - 资金回撤曲线

## 🔧 高级用法

### 自定义选股策略

```python
from vnpy.alpha.strategy import StockScreenerStrategy
import polars as pl

class MyCustomStrategy(StockScreenerStrategy):
    """自定义选股策略"""
    
    top_k = 30
    rebalance_frequency = "weekly"
    
    def _get_stock_pool(self, bars):
        signal_df = self.get_signal()
        
        # 自定义选股逻辑
        filtered = signal_df.filter(
            (pl.col("roe") >= 15) &
            (pl.col("revenue_growth") >= 20)
        )
        
        # 计算综合得分
        filtered = filtered.with_columns(
            (pl.col("roe") * 0.6 + pl.col("revenue_growth") * 0.4).alias("signal")
        )
        
        return filtered

# 使用自定义策略
engine.add_strategy(
    MyCustomStrategy,
    setting={"top_k": 30}
)
```

### 准备信号数据

```python
from vnpy.alpha.lab import AlphaLab
import polars as pl

# 创建实验室
lab = AlphaLab("./lab/my_strategy")

# 准备信号数据
# 假设有全市场的因子数据
signals = pl.DataFrame({
    "datetime": ["2024-01-01", "2024-01-01", ...],
    "vt_symbol": ["000001.SZSE", "000002.SZSE", ...],
    "pe_ratio": [10.5, 15.2, ...],
    "pb_ratio": [1.2, 2.5, ...],
    "roe": [15.5, 18.2, ...],
    # ... 其他因子
})

# 保存信号
lab.save_signals(signals)
```

### 结合股票池和财务数据

```python
from vnpy.alpha.dataset import StockPool, FundamentalData

# 创建数据实例
pool = StockPool("./data/pool")
fd = FundamentalData("./data/fundamental")

# 获取股票池
csi300 = pool.get_index_components("csi300")

# 加载财务数据
fundamental_df = fd.load_market_data("2024-12-31")
fundamental_df = fundamental_df.filter(pl.col("symbol").is_in(csi300))

# 生成信号
signals = fundamental_df.with_columns(
    (pl.col("roe") * 0.5 - pl.col("pe_ratio") * 0.01).alias("signal")
)

# 保存到实验室
lab.save_signals(signals)
```

## ⚠️ 注意事项

1. **信号数据** - 确保信号数据包含 `datetime` 和 `vt_symbol` 列
2. **数据对齐** - 信号日期、K 线日期需要对齐
3. **股票池更新** - 成分股变化需要及时更新
4. **财务数据滞后** - 财报数据有披露滞后，注意使用时点
5. **交易成本** - 合理设置手续费和滑点
6. **流动性** - 考虑最小成交量限制

## 🔍 调试技巧

### 查看日志

```python
# 回测过程中会输出详细日志
# 包括：
# - 每日调仓信息
# - 买卖交易记录
# - 持仓变化
# - 资金变化
```

### 检查中间结果

```python
# 查看每日结果
for d, result in engine.daily_results.items():
    print(f"{d}: balance={result.balance:.2f}, pnl={result.net_pnl:.2f}")

# 查看成交记录
for trade_id, trade in engine.trades.items():
    print(f"{trade.datetime}: {trade.vt_symbol} {trade.direction} {trade.volume}@{trade.price}")
```

## 🎯 下一步

截面回测引擎完成后，继续实现：

- [ ] 数据下载脚本 - 从 RQData 下载真实数据
- [ ] CLI 工具 - 命令行选股工具
- [ ] 可视化增强 - 更多分析图表

## 📖 相关文档

- [选股策略](stock_screener_strategy.md)
- [股票池管理](stock_pool.md)
- [财务数据](fundamental_data.md)
- [策略回测](cta_strategy.md)
