# 选股策略 API 文档

## 概述

选股策略模块提供选股策略的统一接口和基础功能，支持定期调仓、仓位管理、股票筛选和绩效跟踪。

**模块位置**: `vnpy/alpha/strategy/stock_screener_strategy.py`

---

## 核心类

### StockScreenerStrategy - 选股策略基类

所有选股策略应继承此类并实现筛选逻辑。

#### 初始化

```python
from vnpy.alpha.strategy import StockScreenerStrategy

strategy = StockScreenerStrategy(
    name="my_strategy",
    max_positions=30,
    position_size=0.03,
    rebalance_days=20
)
```

**参数**:
- `name` (str): 策略名称，默认 "stock_screener"
- `max_positions` (int): 最大持仓数量，默认 30
- `position_size` (float): 单只股票仓位比例，默认 0.03 (3%)
- `rebalance_days` (int): 调仓周期（交易日），默认 20

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | 策略名称 |
| `max_positions` | int | 最大持仓数量 |
| `position_size` | float | 单只股票仓位比例 |
| `rebalance_days` | int | 调仓周期 |
| `_current_positions` | List[str] | 当前持仓列表 |
| `_target_positions` | List[str] | 目标持仓列表 |
| `_last_rebalance_date` | datetime | 上次调仓日期 |
| `_days_since_rebalance` | int | 距上次调仓的天数 |
| `parameters` | Dict | 策略参数（子类可覆盖） |

#### 抽象方法

##### `screen_stocks(stock_pool, fundamental_data, current_date)` - 筛选股票

**子类必须实现此方法！**

```python
from vnpy.alpha.strategy import StockScreenerStrategy
from vnpy.alpha.dataset import FundamentalData

class MyStrategy(StockScreenerStrategy):
    def screen_stocks(self, stock_pool, fundamental_data, current_date):
        """
        筛选股票
        
        Args:
            stock_pool: 可选股票池 List[str]
            fundamental_data: 财务数据 Dict[str, FinancialIndicator]
            current_date: 当前日期 datetime
            
        Returns:
            List[str]: 筛选出的股票代码列表
        """
        selected = []
        for symbol in stock_pool:
            data = fundamental_data.get(symbol)
            if data and data.pe_ratio < 20:
                selected.append(symbol)
        return selected[:self.max_positions]
```

#### 方法

##### `should_rebalance(current_date)` - 判断是否需要调仓

```python
if strategy.should_rebalance(current_date):
    print("需要调仓")
```

**参数**:
- `current_date` (datetime): 当前日期

**返回**: `bool` - 是否需要调仓

##### `update_positions(new_positions, current_date)` - 更新持仓

```python
# 获取新的目标持仓
new_positions = strategy.screen_stocks(stock_pool, fundamental_data, current_date)

# 更新持仓
to_buy, to_sell, to_hold = strategy.update_positions(new_positions, current_date)

print(f"买入：{to_buy}")
print(f"卖出：{to_sell}")
print(f"持有：{to_hold}")
```

**参数**:
- `new_positions` (List[str]): 新的目标持仓列表
- `current_date` (datetime): 当前日期

**返回**: `Tuple[List[str], List[str], List[str]]` - (买入列表，卖出列表，持有列表)

##### `get_current_positions()` - 获取当前持仓

```python
positions = strategy.get_current_positions()
print(f"当前持仓：{positions}")
```

**返回**: `List[str]` - 当前持仓股票代码列表

##### `get_target_positions()` - 获取目标持仓

```python
targets = strategy.get_target_positions()
print(f"目标持仓：{targets}")
```

**返回**: `List[str]` - 目标持仓股票代码列表

##### `get_position_size(vt_symbol)` - 获取单只股票仓位

```python
size = strategy.get_position_size("600519.SH")
print(f"贵州茅台仓位：{size:.2%}")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `float` - 仓位比例

##### `get_total_position()` - 获取总仓位

```python
total = strategy.get_total_position()
print(f"总仓位：{total:.2%}")
```

**返回**: `float` - 总仓位比例

##### `get_parameters()` - 获取策略参数

```python
params = strategy.get_parameters()
print(f"策略参数：{params}")
```

**返回**: `Dict` - 策略参数字典

##### `set_parameters(**kwargs)` - 设置策略参数

```python
strategy.set_parameters(
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2.0
)
```

**参数**: 任意关键字参数

##### `reset()` - 重置策略状态

```python
strategy.reset()
print("策略已重置")
```

清空当前持仓和目标持仓，重置调仓状态。

##### `to_dict()` - 导出为字典

```python
data = strategy.to_dict()
```

**返回**: `Dict` - 策略状态字典

---

## 预设策略

### ValueStockStrategy - 价值股策略

筛选低估值、高 ROE、高分红的价值股。

#### 初始化

```python
from vnpy.alpha.strategy import ValueStockStrategy

strategy = ValueStockStrategy(
    max_positions=20,
    position_size=0.05,
    rebalance_days=20,
    max_pe=20,
    max_pb=3,
    min_roe=10,
    min_dividend_yield=2.0
)
```

**参数** (除基类参数外):
- `max_pe` (float): 最大市盈率，默认 20
- `max_pb` (float): 最大市净率，默认 3
- `min_roe` (float): 最小 ROE，默认 10
- `min_dividend_yield` (float): 最小股息率，默认 2.0

#### 筛选逻辑

```python
# 价值股筛选条件:
# 1. PE < max_pe
# 2. PB < max_pb
# 3. ROE > min_roe
# 4. 股息率 > min_dividend_yield
# 5. 按 ROE 降序排序，取前 max_positions 只
```

---

### GrowthStockStrategy - 成长股策略

筛选高成长的成长股。

#### 初始化

```python
from vnpy.alpha.strategy import GrowthStockStrategy

strategy = GrowthStockStrategy(
    max_positions=20,
    position_size=0.05,
    rebalance_days=20,
    min_revenue_growth=20,
    min_net_profit_growth=25,
    min_eps_growth=20,
    max_pe=50
)
```

**参数** (除基类参数外):
- `min_revenue_growth` (float): 最小营收增长率，默认 20
- `min_net_profit_growth` (float): 最小净利润增长率，默认 25
- `min_eps_growth` (float): 最小 EPS 增长率，默认 20
- `max_pe` (float): 最大市盈率，默认 50

#### 筛选逻辑

```python
# 成长股筛选条件:
# 1. 营收增长率 > min_revenue_growth
# 2. 净利润增长率 > min_net_profit_growth
# 3. EPS 增长率 > min_eps_growth
# 4. PE < max_pe (避免过高估值)
# 5. 按净利润增长率降序排序，取前 max_positions 只
```

---

### QualityStockStrategy - 质量股策略

筛选高质量的质量股。

#### 初始化

```python
from vnpy.alpha.strategy import QualityStockStrategy

strategy = QualityStockStrategy(
    max_positions=20,
    position_size=0.05,
    rebalance_days=20,
    min_roe=15,
    min_gross_margin=30,
    max_debt_to_asset=50,
    min_net_margin=15
)
```

**参数** (除基类参数外):
- `min_roe` (float): 最小 ROE，默认 15
- `min_gross_margin` (float): 最小毛利率，默认 30
- `max_debt_to_asset` (float): 最大资产负债率，默认 50
- `min_net_margin` (float): 最小净利率，默认 15

#### 筛选逻辑

```python
# 质量股筛选条件:
# 1. ROE > min_roe
# 2. 毛利率 > min_gross_margin
# 3. 资产负债率 < max_debt_to_asset
# 4. 净利率 > min_net_margin
# 5. 按 ROE 降序排序，取前 max_positions 只
```

---

### DividendStockStrategy - 高股息策略

筛选高股息的高股息股。

#### 初始化

```python
from vnpy.alpha.strategy import DividendStockStrategy

strategy = DividendStockStrategy(
    max_positions=20,
    position_size=0.05,
    rebalance_days=20,
    min_dividend_yield=4.0,
    min_roe=10,
    max_debt_to_asset=60,
    min_payout_ratio=30
)
```

**参数** (除基类参数外):
- `min_dividend_yield` (float): 最小股息率，默认 4.0
- `min_roe` (float): 最小 ROE，默认 10
- `max_debt_to_asset` (float): 最大资产负债率，默认 60
- `min_payout_ratio` (float): 最小分红率，默认 30

#### 筛选逻辑

```python
# 高股息股筛选条件:
# 1. 股息率 > min_dividend_yield
# 2. ROE > min_roe (确保盈利能力)
# 3. 资产负债率 < max_debt_to_asset (财务安全)
# 4. 分红率 > min_payout_ratio (分红意愿)
# 5. 按股息率降序排序，取前 max_positions 只
```

---

### PresetStrategies - 预设策略配置

提供开箱即用的策略配置。

```python
from vnpy.alpha.strategy import PresetStrategies

# 获取所有预设策略
presets = PresetStrategies.get_all()

# 获取特定策略
value_strategy = PresetStrategies.get("value")
growth_strategy = PresetStrategies.get("growth")
quality_strategy = PresetStrategies.get("quality")
dividend_strategy = PresetStrategies.get("dividend")
balanced_strategy = PresetStrategies.get("balanced")

# 创建策略实例
strategy = PresetStrategies.create("value", max_positions=30)
```

**可用策略**:
- `"value"` - 价值股策略
- `"growth"` - 成长股策略
- `"quality"` - 质量股策略
- `"dividend"` - 高股息策略
- `"balanced"` - 平衡策略

---

## 完整示例

### 示例 1: 创建自定义策略

```python
from vnpy.alpha.strategy import StockScreenerStrategy
from vnpy.alpha.dataset import FundamentalData
from datetime import datetime

class MyValueStrategy(StockScreenerStrategy):
    """自定义价值投资策略"""
    
    def __init__(self):
        super().__init__(
            name="my_value",
            max_positions=20,
            position_size=0.05,
            rebalance_days=20
        )
        # 设置策略参数
        self.parameters = {
            "max_pe": 15,
            "min_roe": 12,
            "min_dividend_yield": 3.0
        }
    
    def screen_stocks(self, stock_pool, fundamental_data, current_date):
        """筛选价值股"""
        selected = []
        
        for symbol in stock_pool:
            data = fundamental_data.get(symbol)
            if data is None:
                continue
            
            # 筛选条件
            if (data.pe_ratio is not None and data.pe_ratio < self.parameters["max_pe"] and
                data.roe is not None and data.roe > self.parameters["min_roe"] and
                data.dividend_yield is not None and data.dividend_yield > self.parameters["min_dividend_yield"]):
                selected.append((symbol, data.roe))
        
        # 按 ROE 排序，取前 max_positions 只
        selected.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in selected[:self.max_positions]]

# 使用策略
strategy = MyValueStrategy()

# 准备数据
stock_pool = ["600519.SH", "600036.SH", "000001.SZ", ...]
fundamental_data = FundamentalData.load("fundamental_data.json")
current_date = datetime(2024, 3, 1)

# 筛选股票
selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
print(f"筛选结果：{selected}")

# 更新持仓
to_buy, to_sell, to_hold = strategy.update_positions(selected, current_date)
print(f"买入：{to_buy}")
print(f"卖出：{to_sell}")
```

### 示例 2: 使用预设策略

```python
from vnpy.alpha.strategy import ValueStockStrategy, PresetStrategies
from vnpy.alpha.dataset import FundamentalData
from datetime import datetime

# 方式 1: 直接创建
value_strategy = ValueStockStrategy(
    max_positions=20,
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2.0
)

# 方式 2: 使用预设
value_strategy = PresetStrategies.create("value", max_positions=20)

# 准备数据
stock_pool = ["600519.SH", "600036.SH", "000001.SZ"]
fundamental_data = FundamentalData.load("fundamental_data.json")
current_date = datetime(2024, 3, 1)

# 运行策略
selected = value_strategy.screen_stocks(stock_pool, fundamental_data, current_date)
print(f"价值股：{selected}")

# 查看持仓
print(f"当前持仓：{value_strategy.get_current_positions()}")
print(f"总仓位：{value_strategy.get_total_position():.2%}")
```

### 示例 3: 策略回测

```python
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.lab import AlphaLab
from datetime import datetime

# 创建实验室
lab = AlphaLab("./lab/backtest")

# 创建回测引擎
engine = create_cross_sectional_engine(
    lab,
    initial_capital=1_000_000
)

# 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH", ...],
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "min_roe": 10,
        "min_dividend_yield": 2.0
    }
)

# 运行回测
engine.load_data()
engine.run_backtesting()

# 查看结果
stats = engine.calculate_statistics()
print(f"总收益：{stats['total_return_pct']:.2f}%")
print(f"年化收益：{stats['annual_return_pct']:.2f}%")
print(f"最大回撤：{stats['max_drawdown_pct']:.2f}%")
print(f"夏普比率：{stats['sharpe_ratio']:.2f}")

# 显示图表
engine.show_chart()
```

### 示例 4: 多策略比较

```python
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy
)
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.lab import AlphaLab
from datetime import datetime

# 创建实验室和引擎
lab = AlphaLab("./lab/strategy_comparison")
engine = create_cross_sectional_engine(lab, initial_capital=1_000_000)

# 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600036.SH", "600519.SH", ...],
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 添加多个策略
engine.add_strategy(ValueStockStrategy, {"max_pe": 20, "min_roe": 10}, name="value")
engine.add_strategy(GrowthStockStrategy, {"min_growth": 20}, name="growth")
engine.add_strategy(QualityStockStrategy, {"min_roe": 15}, name="quality")
engine.add_strategy(DividendStockStrategy, {"min_yield": 4}, name="dividend")

# 运行回测
engine.load_data()
engine.run_backtesting()

# 比较结果
all_stats = engine.calculate_all_strategies_statistics()
for name, stats in all_stats.items():
    print(f"\n{name} 策略:")
    print(f"  总收益：{stats['total_return_pct']:.2f}%")
    print(f"  年化收益：{stats['annual_return_pct']:.2f}%")
    print(f"  最大回撤：{stats['max_drawdown_pct']:.2f}%")
    print(f"  夏普比率：{stats['sharpe_ratio']:.2f}")

# 显示比较图表
engine.show_strategy_comparison()
```

---

## 策略参数调优

### 参数扫描

```python
from vnpy.alpha.strategy import ValueStockStrategy

# 扫描不同的 PE 阈值
for max_pe in [10, 15, 20, 25, 30]:
    strategy = ValueStockStrategy(max_pe=max_pe, min_roe=10)
    selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
    print(f"PE<{max_pe}: 筛选出 {len(selected)} 只股票")
```

### 参数优化

```python
# 寻找最优参数组合
best_return = 0
best_params = {}

for max_pe in [15, 20, 25]:
    for min_roe in [8, 10, 12]:
        for min_dividend in [1, 2, 3]:
            strategy = ValueStockStrategy(
                max_pe=max_pe,
                min_roe=min_roe,
                min_dividend_yield=min_dividend
            )
            # 运行回测...
            # return = run_backtest(strategy)
            if return > best_return:
                best_return = return
                best_params = {
                    "max_pe": max_pe,
                    "min_roe": min_roe,
                    "min_dividend_yield": min_dividend
                }

print(f"最优参数：{best_params}")
print(f"最优收益：{best_return:.2f}%")
```

---

## 最佳实践

### 1. 策略组合

```python
# 同时运行多个策略，分散风险
strategies = [
    ValueStockStrategy(max_positions=10),
    GrowthStockStrategy(max_positions=10),
    DividendStockStrategy(max_positions=10)
]

all_selected = []
for strategy in strategies:
    selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
    all_selected.extend(selected)

# 去重
all_selected = list(set(all_selected))
print(f"组合选股：{len(all_selected)} 只")
```

### 2. 动态调仓

```python
# 根据市场状态调整调仓频率
def get_rebalance_days(market_condition):
    if market_condition == "bull":
        return 15  # 牛市快速调仓
    elif market_condition == "bear":
        return 30  # 熊市慢速调仓
    else:
        return 20  # 正常调仓

strategy = ValueStockStrategy(rebalance_days=get_rebalance_days("normal"))
```

### 3. 仓位控制

```python
# 根据市场估值调整仓位
def get_position_size(pe_percentile):
    if pe_percentile < 30:  # 低估值
        return 0.05  # 5% 仓位
    elif pe_percentile < 70:  # 中等估值
        return 0.03  # 3% 仓位
    else:  # 高估值
        return 0.01  # 1% 仓位

strategy = ValueStockStrategy(position_size=get_position_size(40))
```

---

## 相关文件

- **源码**: `vnpy/alpha/strategy/stock_screener_strategy.py`
- **预设策略**: `vnpy/alpha/strategy/preset_strategies.py`
- **示例**: `examples/alpha_research/test_stock_screener.py`
- **回测引擎**: `docs/alpha/cross_sectional_backtesting.md`

---

**最后更新**: 2026-03-01  
**版本**: 1.0.0
