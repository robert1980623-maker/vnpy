# 截面回测引擎 API 文档

## 概述

截面回测引擎支持多股票同时回测，模拟真实选股策略的执行过程，包括定期调仓、仓位管理、交易成本模拟和绩效统计。

**模块位置**: `vnpy/alpha/strategy/cross_sectional_engine.py`

---

## 核心类

### Position - 持仓信息

记录单只股票的持仓信息。

#### 属性

```python
from vnpy.alpha.strategy.cross_sectional_engine import Position

position = Position(
    vt_symbol="000001.SZ",
    size=1000,           # 持仓股数
    price=10.5,          # 买入价格
    entry_date=datetime(2024, 3, 1)
)
```

**属性**:
- `vt_symbol` (str): 股票代码
- `size` (float): 持仓股数
- `price` (float): 买入价格
- `entry_date` (datetime): 买入日期

#### 方法

##### market_value(current_price) - 计算市值

```python
value = position.market_value(current_price=12.0)
print(f"当前市值：{value}")
```

**参数**:
- `current_price` (float): 当前价格

**返回**: `float` - 持仓市值

##### pnl(current_price) - 计算盈亏

```python
profit = position.pnl(current_price=12.0)
print(f"盈亏：{profit}")
```

**参数**:
- `current_price` (float): 当前价格

**返回**: `float` - 盈亏金额

##### pnl_pct(current_price) - 计算盈亏比例

```python
pct = position.pnl_pct(current_price=12.0)
print(f"盈亏比例：{pct*100:.2f}%")
```

**参数**:
- `current_price` (float): 当前价格

**返回**: `float` - 盈亏比例

---

### Trade - 交易记录

记录单次交易信息。

#### 属性

```python
from vnpy.alpha.strategy.cross_sectional_engine import Trade

trade = Trade(
    vt_symbol="000001.SZ",
    direction="buy",     # "buy" 或 "sell"
    size=1000,
    price=10.5,
    date=datetime(2024, 3, 1),
    commission=5.25      # 手续费
)
```

**属性**:
- `vt_symbol` (str): 股票代码
- `direction` (str): 交易方向 ("buy" 或 "sell")
- `size` (float): 交易股数
- `price` (float): 成交价格
- `date` (datetime): 交易日期
- `commission` (float): 手续费

#### 方法

##### to_dict() - 转换为字典

```python
data = trade.to_dict()
# {
#     "vt_symbol": "000001.SZ",
#     "direction": "buy",
#     "size": 1000,
#     "price": 10.5,
#     "date": "2024-03-01T00:00:00",
#     "commission": 5.25
# }
```

**返回**: `Dict` - 交易记录的字典表示

---

### DailySnapshot - 每日快照

记录每日账户状态。

#### 属性

```python
from vnpy.alpha.strategy.cross_sectional_engine import DailySnapshot

snapshot = DailySnapshot(
    date=datetime(2024, 3, 1),
    total_value=1000000,
    cash=100000,
    position_count=10,
    positions={...}
)
```

**属性**:
- `date` (datetime): 日期
- `total_value` (float): 总资产
- `cash` (float): 现金
- `position_count` (int): 持仓数量
- `positions` (Dict): 持仓详情

#### 方法

##### to_dict() - 转换为字典

```python
data = snapshot.to_dict()
```

**返回**: `Dict` - 快照的字典表示

---

### CrossSectionalEngine - 截面回测引擎

核心回测引擎类，模拟选股策略的实际执行过程。

#### 初始化

```python
from vnpy.alpha.strategy import CrossSectionalEngine
from vnpy.alpha.lab import AlphaLab

# 创建 AlphaLab
lab = AlphaLab()

# 创建回测引擎
engine = CrossSectionalEngine(
    lab=lab,
    initial_capital=1_000_000,    # 初始资金 100 万
    commission_rate=0.0003,       # 手续费率 万三
    slippage=0.001,               # 滑点 千一
    max_positions=30,             # 最大持仓 30 只
    position_size=0.03            # 单只股票 3% 仓位
)
```

**参数**:
- `lab` (AlphaLab): AlphaLab 实例
- `initial_capital` (float): 初始资金，默认 1,000,000
- `commission_rate` (float): 手续费率，默认 0.0003 (万三)
- `slippage` (float): 滑点，默认 0.001 (千一)
- `max_positions` (int): 最大持仓数，默认 30
- `position_size` (float): 单只股票仓位比例，默认 0.03 (3%)

#### 主要方法

##### set_parameters() - 设置回测参数

```python
from datetime import datetime
from vnpy.trader.constant import Interval

engine.set_parameters(
    vt_symbols=["000001.SZ", "000002.SZ", "600000.SH"],
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 3, 1),
    capital=1_000_000
)
```

**参数**:
- `vt_symbols` (List[str]): 股票代码列表
- `interval` (Interval): K 线周期
- `start` (datetime): 开始日期
- `end` (datetime): 结束日期
- `capital` (float, 可选): 初始资金

##### add_strategy() - 添加策略

```python
from vnpy.alpha.strategy import ValueStockStrategy

engine.add_strategy(
    strategy_class=ValueStockStrategy,
    setting={
        "max_pe": 20,
        "min_roe": 10,
        "min_dividend_yield": 2,
        "max_positions": 20,
        "rebalance_days": 20
    }
)
```

**参数**:
- `strategy_class` (Type[StockScreenerStrategy]): 策略类
- `setting` (Dict, 可选): 策略参数字典

##### load_data() - 加载数据

```python
engine.load_data()
```

加载股票池的 K 线数据到内存。

**注意**: 调用前必须先调用 `set_parameters()` 设置 `vt_symbols`。

##### run_backtesting() - 运行回测

```python
engine.run_backtesting()
```

执行回测，模拟选股策略的完整执行过程。

**注意**: 调用前必须先调用 `add_strategy()` 和 `load_data()`。

##### calculate_statistics() - 计算统计指标

```python
stats = engine.calculate_statistics()
print(stats)
```

**返回**: `Dict[str, Any]` - 统计结果，包含：

| 字段 | 说明 | 类型 |
|------|------|------|
| `total_return` | 总收益率 | float |
| `total_return_pct` | 总收益率 (%) | float |
| `annual_return` | 年化收益率 | float |
| `annual_return_pct` | 年化收益率 (%) | float |
| `volatility` | 年化波动率 | float |
| `volatility_pct` | 年化波动率 (%) | float |
| `sharpe_ratio` | 夏普比率 | float |
| `max_drawdown` | 最大回撤 | float |
| `max_drawdown_pct` | 最大回撤 (%) | float |
| `total_trades` | 总交易次数 | int |
| `buy_trades` | 买入次数 | int |
| `sell_trades` | 卖出次数 | int |
| `total_commission` | 总手续费 | float |
| `final_value` | 最终资产 | float |
| `initial_value` | 初始资产 | float |
| `start_date` | 开始日期 | str |
| `end_date` | 结束日期 | str |
| `trading_days` | 交易天数 | int |

##### get_trades() - 获取交易记录

```python
trades = engine.get_trades()
for trade in trades[:5]:  # 显示前 5 笔交易
    print(f"{trade['date']}: {trade['direction']} {trade['vt_symbol']} "
          f"@ {trade['price']}, 手续费：{trade['commission']}")
```

**返回**: `List[Dict]` - 交易记录列表

##### get_daily_values() - 获取每日净值

```python
daily_values = engine.get_daily_values()
for snapshot in daily_values[:5]:  # 显示前 5 天
    print(f"{snapshot['date']}: 总资产={snapshot['total_value']}, "
          f"现金={snapshot['cash']}, 持仓数={snapshot['position_count']}")
```

**返回**: `List[Dict]` - 每日快照列表

##### show_chart() - 显示回测图表

```python
engine.show_chart()
```

显示净值曲线和收益分布图。

**依赖**: 需要安装 `matplotlib`

---

## 工厂函数

### create_cross_sectional_engine()

创建截面回测引擎的便捷函数。

```python
from vnpy.alpha.strategy import create_cross_sectional_engine

engine = create_cross_sectional_engine(
    lab=lab,
    initial_capital=1_000_000,
    commission_rate=0.0003,
    max_positions=30
)
```

**参数**:
- `lab` (AlphaLab): AlphaLab 实例
- `**kwargs`: 其他参数

**返回**: `CrossSectionalEngine` - 回测引擎实例

---

## 完整示例

### 示例 1：价值股策略回测

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy import CrossSectionalEngine, ValueStockStrategy
from datetime import datetime
from vnpy.trader.constant import Interval

# 创建 AlphaLab
lab = AlphaLab()

# 创建回测引擎
engine = CrossSectionalEngine(
    lab=lab,
    initial_capital=1_000_000,
    commission_rate=0.0003,
    slippage=0.001,
    max_positions=20,
    position_size=0.05
)

# 设置回测参数
engine.set_parameters(
    vt_symbols=lab.get_stock_list(),  # 获取股票池
    interval=Interval.DAILY,
    start=datetime(2022, 1, 1),
    end=datetime(2024, 3, 1)
)

# 添加价值股策略
engine.add_strategy(
    strategy_class=ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_roe": 10,
        "min_dividend_yield": 2,
        "max_positions": 20,
        "rebalance_days": 20
    }
)

# 加载数据
engine.load_data()

# 运行回测
engine.run_backtesting()

# 查看统计结果
stats = engine.calculate_statistics()
print("=" * 50)
print("回测结果")
print("=" * 50)
print(f"总收益率：{stats['total_return_pct']:.2f}%")
print(f"年化收益率：{stats['annual_return_pct']:.2f}%")
print(f"夏普比率：{stats['sharpe_ratio']:.2f}")
print(f"最大回撤：{stats['max_drawdown_pct']:.2f}%")
print(f"总交易次数：{stats['total_trades']}")
print(f"总手续费：{stats['total_commission']:.2f}元")
```

### 示例 2：成长股策略回测

```python
from vnpy.alpha.strategy import GrowthStockStrategy

# 创建回测引擎
engine = CrossSectionalEngine(
    lab=lab,
    initial_capital=1_000_000,
    max_positions=15,
    position_size=0.06
)

# 设置参数
engine.set_parameters(
    vt_symbols=lab.get_stock_list(),
    interval=Interval.DAILY,
    start=datetime(2022, 1, 1),
    end=datetime(2024, 3, 1)
)

# 添加成长股策略
engine.add_strategy(
    strategy_class=GrowthStockStrategy,
    setting={
        "min_revenue_growth": 25,
        "min_profit_growth": 30,
        "min_roe": 15,
        "max_pe": 50,
        "max_positions": 15,
        "rebalance_days": 25
    }
)

# 运行回测
engine.load_data()
engine.run_backtesting()

# 查看结果
stats = engine.calculate_statistics()
print(f"成长股策略年化收益：{stats['annual_return_pct']:.2f}%")
print(f"夏普比率：{stats['sharpe_ratio']:.2f}")
```

### 示例 3：多策略对比

```python
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy
)

# 策略配置
strategies = {
    "价值股": {
        "class": ValueStockStrategy,
        "setting": {"max_pe": 20, "min_roe": 10, "min_dividend_yield": 2}
    },
    "成长股": {
        "class": GrowthStockStrategy,
        "setting": {"min_revenue_growth": 25, "min_profit_growth": 30}
    },
    "质量股": {
        "class": QualityStockStrategy,
        "setting": {"min_roe": 15, "min_gross_margin": 30}
    },
    "高股息": {
        "class": DividendStockStrategy,
        "setting": {"min_dividend_yield": 4, "min_roe": 8}
    }
}

# 回测对比
results = {}

for name, config in strategies.items():
    print(f"\n回测 {name} 策略...")
    
    engine = CrossSectionalEngine(lab=lab, initial_capital=1_000_000)
    engine.set_parameters(
        vt_symbols=lab.get_stock_list(),
        interval=Interval.DAILY,
        start=datetime(2022, 1, 1),
        end=datetime(2024, 3, 1)
    )
    engine.add_strategy(config["class"], setting=config["setting"])
    engine.load_data()
    engine.run_backtesting()
    
    stats = engine.calculate_statistics()
    results[name] = stats
    
    print(f"  年化收益：{stats['annual_return_pct']:.2f}%")
    print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")
    print(f"  最大回撤：{stats['max_drawdown_pct']:.2f}%")

# 对比表格
print("\n" + "=" * 60)
print(f"{'策略':<10} {'年化收益':>12} {'夏普比率':>12} {'最大回撤':>12}")
print("=" * 60)
for name, stats in results.items():
    print(f"{name:<10} {stats['annual_return_pct']:>11.2f}% "
          f"{stats['sharpe_ratio']:>12.2f} {stats['max_drawdown_pct']:>11.2f}%")
```

### 示例 4：查看交易记录

```python
# 运行回测后
engine.run_backtesting()

# 获取交易记录
trades = engine.get_trades()

print(f"总交易次数：{len(trades)}\n")

# 显示前 10 笔交易
print("前 10 笔交易:")
for i, trade in enumerate(trades[:10], 1):
    direction = "买入" if trade['direction'] == 'buy' else "卖出"
    print(f"{i}. {trade['date'][:10]} {direction} {trade['vt_symbol']} "
          f"@ {trade['price']:.2f} x {trade['size']:.0f}股, "
          f"手续费：¥{trade['commission']:.2f}")

# 统计买入卖出
buy_count = sum(1 for t in trades if t['direction'] == 'buy')
sell_count = sum(1 for t in trades if t['direction'] == 'sell')
print(f"\n买入次数：{buy_count}, 卖出次数：{sell_count}")
```

### 示例 5：分析每日净值

```python
# 获取每日净值
daily_values = engine.get_daily_values()

# 提取数据
dates = [v['date'][:10] for v in daily_values]
values = [v['total_value'] for v in daily_values]

# 计算每日收益
daily_returns = []
for i in range(1, len(values)):
    ret = (values[i] - values[i-1]) / values[i-1]
    daily_returns.append(ret)

# 统计
import statistics
print(f"交易日数：{len(dates)}")
print(f"正收益天数：{sum(1 for r in daily_returns if r > 0)}")
print(f"负收益天数：{sum(1 for r in daily_returns if r < 0)}")
print(f"胜率：{sum(1 for r in daily_returns if r > 0) / len(daily_returns) * 100:.2f}%")
print(f"日均收益：{statistics.mean(daily_returns) * 100:.4f}%")
print(f"日收益波动率：{statistics.stdev(daily_returns) * 100:.4f}%")
```

### 示例 6：显示回测图表

```python
# 需要安装 matplotlib: pip install matplotlib
engine.show_chart()
```

图表包含：
1. **净值曲线**: 显示组合资产随时间的变化
2. **收益分布**: 显示每日收益的直方图

---

## 回测流程

```
1. 创建 AlphaLab
       ↓
2. 创建 CrossSectionalEngine
       ↓
3. set_parameters() - 设置股票池、时间范围
       ↓
4. add_strategy() - 添加选股策略
       ↓
5. load_data() - 加载 K 线数据
       ↓
6. run_backtesting() - 运行回测
       ↓
7. calculate_statistics() - 计算统计指标
       ↓
8. get_trades() / get_daily_values() - 获取详细数据
       ↓
9. show_chart() - 可视化（可选）
```

---

## 交易成本模型

### 手续费

```python
commission = max(amount * commission_rate, 5.0)
```

- 费率：默认 0.0003 (万三)
- 最低：5 元

### 滑点

```python
# 买入
exec_price = price * (1 + slippage)

# 卖出
exec_price = price * (1 - slippage)
```

- 默认：0.001 (千一)
- 买入价格上浮，卖出价格下浮

---

## 最佳实践

1. **合理的股票池**: 选择流动性好的股票，排除 ST、*ST 等风险股
2. **足够的回测周期**: 至少 2-3 年，覆盖不同市场环境
3. **真实的成本假设**: 设置合理的手续费和滑点
4. **关注最大回撤**: 不仅看收益，也要看风险
5. **多策略对比**: 对比不同策略的表现，选择适合的
6. **样本外验证**: 用部分数据做验证，避免过拟合
7. **定期复盘**: 分析交易记录，优化策略参数

---

## 性能指标解读

### 年化收益率 (Annual Return)

```
年化收益 = (1 + 总收益)^(365/天数) - 1
```

- 反映策略的盈利能力
- 一般 >15% 为优秀

### 夏普比率 (Sharpe Ratio)

```
夏普比率 = (年化收益 - 无风险利率) / 波动率
```

- 反映风险调整后的收益
- >1 为良好，>2 为优秀
- 无风险利率默认 3%

### 最大回撤 (Max Drawdown)

```
最大回撤 = (峰值 - 谷值) / 峰值
```

- 反映策略的最大亏损幅度
- 一般 <20% 为可接受
- 越小越好

### 波动率 (Volatility)

```
波动率 = 日收益标准差 × √252
```

- 反映策略的风险程度
- 一般 <30% 为稳健

---

## 相关文件

- 源码：`vnpy/alpha/strategy/cross_sectional_engine.py`
- 选股策略：`stock_screener_strategy.md`
- AlphaLab: `alpha_lab.md` (待创建)
