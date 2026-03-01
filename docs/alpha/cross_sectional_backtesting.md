# 截面回测 API 文档

## 概述

截面回测引擎支持多股票同时回测，模拟真实选股策略的执行过程，包括定期调仓、仓位管理、交易成本和绩效统计。

**模块位置**: `vnpy/alpha/strategy/cross_sectional_engine.py`

---

## 快速开始

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from datetime import datetime

# 1. 创建实验室
lab = AlphaLab("./lab/backtest")

# 2. 创建回测引擎
engine = create_cross_sectional_engine(
    lab,
    initial_capital=1_000_000  # 初始资金 100 万
)

# 3. 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH"],
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 4. 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "min_roe": 10,
        "min_dividend_yield": 2.0
    }
)

# 5. 运行回测
engine.load_data()
engine.run_backtesting()

# 6. 查看结果
stats = engine.calculate_statistics()
print(f"总收益：{stats['total_return_pct']:.2f}%")
print(f"年化收益：{stats['annual_return_pct']:.2f}%")
print(f"最大回撤：{stats['max_drawdown_pct']:.2f}%")

# 7. 显示图表
engine.show_chart()
```

---

## 核心类

### CrossSectionalEngine - 截面回测引擎

#### 初始化

```python
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalEngine

engine = CrossSectionalEngine(
    lab=lab,
    initial_capital=1_000_000,
    commission_rate=0.0003,
    slippage_rate=0.001
)
```

**参数**:
- `lab` (AlphaLab): Alpha 实验室实例
- `initial_capital` (float): 初始资金，默认 1,000,000
- `commission_rate` (float): 手续费率，默认 0.0003 (万三)
- `slippage_rate` (float): 滑点率，默认 0.001 (千一)

#### 工厂函数

##### `create_cross_sectional_engine(lab, **kwargs)` - 创建引擎

```python
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine

engine = create_cross_sectional_engine(
    lab,
    initial_capital=1_000_000
)
```

**返回**: `CrossSectionalEngine` - 回测引擎实例

---

### 方法

#### 配置方法

##### `set_parameters()` - 设置回测参数

```python
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH"],
    interval="daily",
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31),
    rebalance_days=20
)
```

**参数**:
- `vt_symbols` (List[str]): 股票代码列表
- `interval` (str): K 线周期，默认 "daily"
- `start` (datetime): 回测开始日期
- `end` (datetime): 回测结束日期
- `rebalance_days` (int): 调仓周期，默认 20

##### `add_strategy(strategy_class, setting=None, name=None)` - 添加策略

```python
from vnpy.alpha.strategy import ValueStockStrategy

# 添加单个策略
engine.add_strategy(
    ValueStockStrategy,
    setting={"max_pe": 20, "min_roe": 10}
)

# 添加带名称的策略
engine.add_strategy(
    ValueStockStrategy,
    setting={"max_pe": 20},
    name="my_value_strategy"
)
```

**参数**:
- `strategy_class` (Type): 策略类
- `setting` (Dict, optional): 策略参数
- `name` (str, optional): 策略名称

---

#### 执行方法

##### `load_data()` - 加载数据

```python
engine.load_data()
```

从实验室加载 K 线数据和财务数据。

##### `run_backtesting()` - 运行回测

```python
engine.run_backtesting()
```

执行回测，模拟策略交易过程。

##### `run_intraday_backtesting()` - 运行日内回测

```python
engine.run_intraday_backtesting()
```

运行更精细的日内回测（如果数据支持）。

---

#### 统计方法

##### `calculate_statistics()` - 计算绩效统计

```python
stats = engine.calculate_statistics()
```

**返回**: `Dict` - 绩效统计字典

```python
{
    # 收益指标
    "total_return_pct": 25.5,        # 总收益率 (%)
    "annual_return_pct": 15.2,       # 年化收益率 (%)
    "excess_return_pct": 8.5,        # 超额收益率 (%)
    
    # 风险指标
    "max_drawdown_pct": -15.3,       # 最大回撤 (%)
    "volatility_pct": 18.5,          # 年化波动率 (%)
    
    # 风险调整收益
    "sharpe_ratio": 1.25,            # 夏普比率
    "sortino_ratio": 1.50,           # 索提诺比率
    "calmar_ratio": 0.99,            # 卡玛比率
    
    # 交易统计
    "total_trades": 150,             # 总交易次数
    "win_rate": 0.65,                # 胜率
    "avg_win_pct": 5.2,              # 平均盈利 (%)
    "avg_loss_pct": -3.1,            # 平均亏损 (%)
    "profit_factor": 1.68,           # 盈亏比
    
    # 时间统计
    "trading_days": 480,             # 交易天数
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    
    # 资金统计
    "initial_capital": 1000000,
    "final_capital": 1255000,
    "total_commission": 3500         # 总手续费
}
```

##### `calculate_all_strategies_statistics()` - 计算所有策略统计

```python
all_stats = engine.calculate_all_strategies_statistics()
for name, stats in all_stats.items():
    print(f"{name}: {stats['total_return_pct']:.2f}%")
```

**返回**: `Dict[str, Dict]` - 各策略的统计字典

##### `get_trade_log()` - 获取交易日志

```python
trades = engine.get_trade_log()
for trade in trades[:10]:
    print(f"{trade.date}: {trade.direction} {trade.vt_symbol} @ {trade.price}")
```

**返回**: `List[Trade]` - 交易记录列表

##### `get_daily_snapshots()` - 获取每日快照

```python
snapshots = engine.get_daily_snapshots()
for snapshot in snapshots[-5:]:
    print(f"{snapshot.date}: 总值={snapshot.total_value:.2f}")
```

**返回**: `List[DailySnapshot]` - 每日快照列表

---

#### 可视化方法

##### `show_chart()` - 显示收益曲线

```python
engine.show_chart(
    title="策略收益曲线",
    save_path="backtest_result.png"
)
```

**参数**:
- `title` (str, optional): 图表标题
- `save_path` (str, optional): 保存路径

##### `show_drawdown_chart()` - 显示回撤曲线

```python
engine.show_drawdown_chart()
```

##### `show_monthly_return_chart()` - 显示月度收益热力图

```python
engine.show_monthly_return_chart()
```

##### `show_strategy_comparison()` - 显示策略比较

```python
engine.show_strategy_comparison()
```

比较多策略的收益曲线。

##### `show_position_distribution()` - 显示持仓分布

```python
engine.show_position_distribution()
```

---

#### 数据导出方法

##### `export_trades()` - 导出交易记录

```python
engine.export_trades("trades.csv")
```

**参数**:
- `path` (str): 导出路径

##### `export_daily_values()` - 导出每日净值

```python
engine.export_daily_values("daily_values.csv")
```

**参数**:
- `path` (str): 导出路径

##### `export_statistics()` - 导出统计结果

```python
engine.export_statistics("statistics.json")
```

**参数**:
- `path` (str): 导出路径

---

## 数据结构

### Position - 持仓信息

```python
@dataclass
class Position:
    vt_symbol: str           # 股票代码
    size: float              # 持仓数量
    price: float             # 持仓成本
    entry_date: datetime     # 建仓日期
    
    def market_value(self, current_price: float) -> float:
        """计算市值"""
    
    def pnl(self, current_price: float) -> float:
        """计算盈亏"""
    
    def pnl_pct(self, current_price: float) -> float:
        """计算盈亏比例"""
```

### Trade - 交易记录

```python
@dataclass
class Trade:
    vt_symbol: str           # 股票代码
    direction: str           # "buy" 或 "sell"
    size: float              # 交易数量
    price: float             # 成交价格
    date: datetime           # 交易日期
    commission: float        # 手续费
    
    def to_dict(self) -> Dict:
        """转换为字典"""
```

### DailySnapshot - 每日快照

```python
@dataclass
class DailySnapshot:
    date: datetime                    # 日期
    total_value: float                # 总资产
    cash: float                       # 现金
    position_count: int               # 持仓数量
    positions: Dict[str, Dict]        # 持仓详情
    
    def to_dict(self) -> Dict:
        """转换为字典"""
```

---

## 完整示例

### 示例 1: 基础回测

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from datetime import datetime

# 创建实验室
lab = AlphaLab("./lab/value_backtest")

# 创建引擎
engine = create_cross_sectional_engine(
    lab,
    initial_capital=1_000_000
)

# 设置参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH", "000002.SZ", "000063.SZ"],
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31),
    rebalance_days=20
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "min_roe": 10,
        "min_dividend_yield": 2.0,
        "max_positions": 10
    }
)

# 运行回测
print("加载数据...")
engine.load_data()

print("运行回测...")
engine.run_backtesting()

# 查看结果
print("\n=== 回测结果 ===")
stats = engine.calculate_statistics()
print(f"总收益：{stats['total_return_pct']:.2f}%")
print(f"年化收益：{stats['annual_return_pct']:.2f}%")
print(f"最大回撤：{stats['max_drawdown_pct']:.2f}%")
print(f"夏普比率：{stats['sharpe_ratio']:.2f}")
print(f"总交易次数：{stats['total_trades']}")
print(f"胜率：{stats['win_rate']:.2%}")

# 显示图表
engine.show_chart(title="价值策略回测")
```

### 示例 2: 多策略比较

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy
)
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from datetime import datetime

# 创建实验室
lab = AlphaLab("./lab/strategy_comparison")

# 创建引擎
engine = create_cross_sectional_engine(
    lab,
    initial_capital=1_000_000
)

# 设置参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH", ...],  # 50 只股票
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 添加多个策略
engine.add_strategy(
    ValueStockStrategy,
    {"max_pe": 20, "min_roe": 10},
    name="value"
)

engine.add_strategy(
    GrowthStockStrategy,
    {"min_revenue_growth": 20, "min_net_profit_growth": 25},
    name="growth"
)

engine.add_strategy(
    QualityStockStrategy,
    {"min_roe": 15, "min_gross_margin": 30},
    name="quality"
)

engine.add_strategy(
    DividendStockStrategy,
    {"min_dividend_yield": 4.0},
    name="dividend"
)

# 运行回测
engine.load_data()
engine.run_backtesting()

# 比较结果
print("\n=== 策略比较 ===")
all_stats = engine.calculate_all_strategies_statistics()

for name, stats in all_stats.items():
    print(f"\n{name.upper()} 策略:")
    print(f"  总收益：{stats['total_return_pct']:.2f}%")
    print(f"  年化收益：{stats['annual_return_pct']:.2f}%")
    print(f"  最大回撤：{stats['max_drawdown_pct']:.2f}%")
    print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")
    print(f"  胜率：{stats['win_rate']:.2%}")

# 显示比较图表
engine.show_strategy_comparison()
```

### 示例 3: 参数优化

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from datetime import datetime
import itertools

# 创建实验室
lab = AlphaLab("./lab/parameter_optimization")

# 参数网格
pe_range = [15, 20, 25, 30]
roe_range = [8, 10, 12, 15]
dividend_range = [1.0, 2.0, 3.0]

best_return = 0
best_params = {}
results = []

# 网格搜索
for max_pe, min_roe, min_dividend in itertools.product(pe_range, roe_range, dividend_range):
    # 创建引擎
    engine = create_cross_sectional_engine(lab, initial_capital=1_000_000)
    engine.set_parameters(
        vt_symbols=["000001.SZ", "600036.SH", "600519.SH", ...],
        start=datetime(2023, 1, 1),
        end=datetime(2024, 12, 31)
    )
    engine.add_strategy(
        ValueStockStrategy,
        {
            "max_pe": max_pe,
            "min_roe": min_roe,
            "min_dividend_yield": min_dividend
        }
    )
    
    # 运行回测
    engine.load_data()
    engine.run_backtesting()
    stats = engine.calculate_statistics()
    
    # 记录结果
    result = {
        "max_pe": max_pe,
        "min_roe": min_roe,
        "min_dividend_yield": min_dividend,
        "total_return": stats["total_return_pct"],
        "sharpe_ratio": stats["sharpe_ratio"],
        "max_drawdown": stats["max_drawdown_pct"]
    }
    results.append(result)
    
    # 更新最优
    if stats["total_return_pct"] > best_return:
        best_return = stats["total_return_pct"]
        best_params = {
            "max_pe": max_pe,
            "min_roe": min_roe,
            "min_dividend_yield": min_dividend
        }

# 输出结果
print("\n=== 参数优化结果 ===")
print(f"最优参数：{best_params}")
print(f"最优收益：{best_return:.2f}%")

# 导出结果
import csv
with open("parameter_scan_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("结果已保存到 parameter_scan_results.csv")
```

### 示例 4: 详细分析

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from datetime import datetime

# 运行回测
lab = AlphaLab("./lab/detailed_analysis")
engine = create_cross_sectional_engine(lab, initial_capital=1_000_000)
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH", ...],
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)
engine.add_strategy(ValueStockStrategy, {"max_pe": 20, "min_roe": 10})
engine.load_data()
engine.run_backtesting()

# 详细分析
stats = engine.calculate_statistics()

print("\n=== 详细回测分析 ===\n")

# 1. 收益分析
print("【收益分析】")
print(f"  初始资金：¥{stats['initial_capital']:,.2f}")
print(f"  最终资金：¥{stats['final_capital']:,.2f}")
print(f"  总收益：{stats['total_return_pct']:.2f}%")
print(f"  年化收益：{stats['annual_return_pct']:.2f}%")
print(f"  超额收益：{stats['excess_return_pct']:.2f}%")

# 2. 风险分析
print("\n【风险分析】")
print(f"  最大回撤：{stats['max_drawdown_pct']:.2f}%")
print(f"  年化波动率：{stats['volatility_pct']:.2f}%")

# 3. 风险调整收益
print("\n【风险调整收益】")
print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")
print(f"  索提诺比率：{stats['sortino_ratio']:.2f}")
print(f"  卡玛比率：{stats['calmar_ratio']:.2f}")

# 4. 交易统计
print("\n【交易统计】")
print(f"  总交易次数：{stats['total_trades']}")
print(f"  交易天数：{stats['trading_days']}")
print(f"  胜率：{stats['win_rate']:.2%}")
print(f"  平均盈利：{stats['avg_win_pct']:.2f}%")
print(f"  平均亏损：{stats['avg_loss_pct']:.2f}%")
print(f"  盈亏比：{stats['profit_factor']:.2f}")

# 5. 成本分析
print("\n【成本分析】")
print(f"  总手续费：¥{stats['total_commission']:,.2f}")
print(f"  手续费占比：{stats['total_commission']/stats['initial_capital']*100:.2f}%")

# 获取交易日志
trades = engine.get_trade_log()
print(f"\n【最近 10 笔交易】")
for trade in trades[-10:]:
    direction = "买入" if trade.direction == "buy" else "卖出"
    print(f"  {trade.date.strftime('%Y-%m-%d')} {direction} {trade.vt_symbol} @ ¥{trade.price:.2f}")

# 导出所有数据
engine.export_trades("all_trades.csv")
engine.export_daily_values("daily_values.csv")
engine.export_statistics("statistics.json")
print("\n数据已导出!")

# 显示图表
engine.show_chart()
engine.show_drawdown_chart()
engine.show_monthly_return_chart()
```

---

## 绩效指标说明

### 收益指标

| 指标 | 公式 | 说明 |
|------|------|------|
| 总收益率 | (最终资金 - 初始资金) / 初始资金 | 回测期间的总收益 |
| 年化收益率 | (1 + 总收益率)^(252/交易天数) - 1 | 年化后的收益率 |
| 超额收益率 | 策略收益 - 基准收益 | 相对基准的超额收益 |

### 风险指标

| 指标 | 公式 | 说明 |
|------|------|------|
| 最大回撤 | max(历史最高值 - 当前值) / 历史最高值 | 最大亏损幅度 |
| 年化波动率 | 日收益率标准差 × √252 | 收益的波动程度 |

### 风险调整收益

| 指标 | 公式 | 说明 |
|------|------|------|
| 夏普比率 | (年化收益 - 无风险利率) / 波动率 | 单位风险的超额收益 |
| 索提诺比率 | (年化收益 - 无风险利率) / 下行波动率 | 只考虑下行风险 |
| 卡玛比率 | 年化收益 / |最大回撤 | | 收益与最大回撤的比值 |

### 交易统计

| 指标 | 说明 |
|------|------|
| 胜率 | 盈利交易次数 / 总交易次数 |
| 平均盈利 | 盈利交易的平均收益率 |
| 平均亏损 | 亏损交易的平均收益率 |
| 盈亏比 | 平均盈利 / |平均亏损 | |

---

## 最佳实践

### 1. 数据质量检查

```python
# 回测前检查数据质量
def check_data_quality(lab, vt_symbols, start, end):
    for symbol in vt_symbols:
        bars = lab.load_bars(symbol, start, end)
        if len(bars) == 0:
            print(f"警告：{symbol} 无数据")
        elif len(bars) < 100:
            print(f"警告：{symbol} 数据不足 ({len(bars)}条)")

check_data_quality(lab, symbols, start, end)
```

### 2. 避免未来函数

```python
# 确保只使用历史数据
def screen_stocks(self, stock_pool, fundamental_data, current_date):
    # ✅ 正确：使用当前日期之前的数据
    data = fundamental_data.get(symbol, report_date=current_date)
    
    # ❌ 错误：不要使用未来数据
    # data = fundamental_data.get(symbol)  # 可能获取到未来数据
```

### 3. 合理的交易成本

```python
# 设置 realistic 的交易成本
engine = create_cross_sectional_engine(
    lab,
    commission_rate=0.0003,  # 万三手续费
    slippage_rate=0.001      # 千一滑点
)
```

### 4. 足够的回测周期

```python
# 建议至少 2-3 年的回测周期
start = datetime(2021, 1, 1)
end = datetime(2024, 12, 31)
# 覆盖牛熊周期
```

---

## 相关文件

- **源码**: `vnpy/alpha/strategy/cross_sectional_engine.py`
- **示例**: `examples/alpha_research/run_backtest.py`
- **策略文档**: `docs/alpha/stock_screener_strategy.md`

---

**最后更新**: 2026-03-01  
**版本**: 1.0.0
