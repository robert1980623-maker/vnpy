# 选股策略模块 API 文档

## 概述

选股策略模块提供选股策略的统一接口和基础功能，支持定期调仓、仓位管理、股票筛选和绩效跟踪。

**模块位置**: `vnpy/alpha/strategy/stock_screener_strategy.py`

---

## 核心类

### StockScreenerStrategy - 选股策略基类

所有选股策略的基类，提供通用的调仓和仓位管理功能。

#### 初始化

```python
from vnpy.alpha.strategy import StockScreenerStrategy

strategy = StockScreenerStrategy(
    name="my_strategy",
    max_positions=30,        # 最大持仓 30 只
    position_size=0.03,      # 单只股票 3% 仓位
    rebalance_days=20        # 每 20 个交易日调仓
)
```

**参数**:
- `name` (str): 策略名称，默认为 "stock_screener"
- `max_positions` (int): 最大持仓数量，默认 30
- `position_size` (float): 单只股票仓位比例，默认 0.03 (3%)
- `rebalance_days` (int): 调仓周期（交易日），默认 20

#### 抽象方法（子类必须实现）

##### screen_stocks() - 筛选股票

```python
def screen_stocks(
    self,
    stock_pool: List[str],
    fundamental_data: Dict[str, Any],
    current_date: datetime
) -> List[str]:
    """筛选股票，返回选中的股票代码列表"""
    pass
```

**参数**:
- `stock_pool` (List[str]): 可选股票池
- `fundamental_data` (Dict[str, Any]): 财务数据字典 `{vt_symbol: FinancialIndicator}`
- `current_date` (datetime): 当前日期

**返回**: `List[str]` - 筛选出的股票代码列表

#### 主要方法

##### should_rebalance(date) - 判断是否需要调仓

```python
if strategy.should_rebalance(current_date):
    print("需要调仓")
```

**参数**:
- `current_date` (datetime): 当前日期

**返回**: `bool` - 是否需要调仓

##### update_positions() - 更新持仓

```python
to_buy, to_sell, to_keep = strategy.update_positions(
    new_positions=["000001.SZ", "000002.SZ"],
    current_date=datetime.now()
)

print(f"买入：{to_buy}")
print(f"卖出：{to_sell}")
print(f"保持：{to_keep}")
```

**参数**:
- `new_positions` (List[str]): 新的目标持仓列表
- `current_date` (datetime): 当前日期

**返回**: `Tuple[List[str], List[str], List[str]]` - (买入列表，卖出列表，保持列表)

##### increment_days() - 增加交易日计数

```python
strategy.increment_days(1)  # 增加 1 个交易日
```

**参数**:
- `days` (int): 增加的交易日数，默认 1

##### get_position_info() - 获取持仓信息

```python
info = strategy.get_position_info()
# {
#     "current_positions": ["000001.SZ", "000002.SZ"],
#     "target_positions": ["000001.SZ", "000002.SZ"],
#     "position_count": 2,
#     "max_positions": 30,
#     "last_rebalance": "2024-03-01T10:00:00",
#     "days_since_rebalance": 5
# }
```

**返回**: `Dict` - 持仓信息字典

##### set_parameters() - 设置策略参数

```python
strategy.set_parameters(
    max_pe=20,
    min_roe=10
)
```

**参数**:
- `**kwargs`: 参数键值对

##### get_parameters() - 获取策略参数

```python
params = strategy.get_parameters()
print(params)
```

**返回**: `Dict[str, Any]` - 参数字典

##### to_dict() - 转换为字典

```python
data = strategy.to_dict()
```

**返回**: `Dict` - 策略的字典表示

---

## 预设策略类

### ValueStockStrategy - 价值股策略

基于估值指标筛选低估值、高分红的股票。

#### 初始化

```python
from vnpy.alpha.strategy import ValueStockStrategy

strategy = ValueStockStrategy(
    max_pe=20,              # 最大 PE 20
    max_pb=3,               # 最大 PB 3
    min_dividend_yield=2,   # 最小股息率 2%
    min_roe=10,             # 最小 ROE 10%
    max_positions=30,
    rebalance_days=20
)
```

**参数**:
- `max_pe` (float): 最大市盈率，默认 20
- `max_pb` (float): 最大市净率，默认 3
- `min_dividend_yield` (float): 最小股息率 (%)，默认 2
- `min_roe` (float): 最小 ROE (%)，默认 10
- `name` (str): 策略名称，默认 "value_stock"
- `**kwargs`: 其他基类参数

#### 筛选条件

- PE ≤ max_pe
- PB ≤ max_pb
- 股息率 ≥ min_dividend_yield
- ROE ≥ min_roe

按 PE 从低到高排序，选择最低的一批股票。

---

### GrowthStockStrategy - 成长股策略

基于成长指标筛选高增长的股票。

#### 初始化

```python
from vnpy.alpha.strategy import GrowthStockStrategy

strategy = GrowthStockStrategy(
    min_revenue_growth=20,   # 最小营收增长 20%
    min_profit_growth=25,    # 最小净利润增长 25%
    min_roe=15,              # 最小 ROE 15%
    max_pe=50,               # 最大 PE 50
    max_positions=30,
    rebalance_days=20
)
```

**参数**:
- `min_revenue_growth` (float): 最小营收增长率 (%)，默认 20
- `min_profit_growth` (float): 最小净利润增长率 (%)，默认 25
- `min_roe` (float): 最小 ROE (%)，默认 15
- `max_pe` (float): 最大市盈率，默认 50
- `name` (str): 策略名称，默认 "growth_stock"
- `**kwargs`: 其他基类参数

#### 筛选条件

- 营收增长率 ≥ min_revenue_growth
- 净利润增长率 ≥ min_profit_growth
- ROE ≥ min_roe
- PE ≤ max_pe

按净利润增长率从高到低排序，选择最高的一批股票。

---

### QualityStockStrategy - 质量股策略

基于盈利能力筛选高质量股票。

#### 初始化

```python
from vnpy.alpha.strategy import QualityStockStrategy

strategy = QualityStockStrategy(
    min_roe=15,              # 最小 ROE 15%
    min_gross_margin=30,     # 最小毛利率 30%
    min_net_margin=10,       # 最小净利率 10%
    max_debt_ratio=50,       # 最大资产负债率 50%
    max_positions=30,
    rebalance_days=20
)
```

**参数**:
- `min_roe` (float): 最小 ROE (%)，默认 15
- `min_gross_margin` (float): 最小毛利率 (%)，默认 30
- `min_net_margin` (float): 最小净利率 (%)，默认 10
- `max_debt_ratio` (float): 最大资产负债率 (%)，默认 50
- `name` (str): 策略名称，默认 "quality_stock"
- `**kwargs`: 其他基类参数

#### 筛选条件

- ROE ≥ min_roe
- 毛利率 ≥ min_gross_margin
- 净利率 ≥ min_net_margin
- 资产负债率 ≤ max_debt_ratio

按 ROE 从高到低排序，选择最高的一批股票。

---

### DividendStockStrategy - 高股息策略

基于股息率筛选高分红股票。

#### 初始化

```python
from vnpy.alpha.strategy import DividendStockStrategy

strategy = DividendStockStrategy(
    min_dividend_yield=4,    # 最小股息率 4%
    min_payout_years=3,      # 最小连续分红年数 3 年
    max_payout_ratio=80,     # 最大分红比例 80%
    min_roe=8,               # 最小 ROE 8%
    max_positions=30,
    rebalance_days=20
)
```

**参数**:
- `min_dividend_yield` (float): 最小股息率 (%)，默认 4
- `min_payout_years` (int): 最小连续分红年数，默认 3
- `max_payout_ratio` (float): 最大分红比例 (%)，默认 80
- `min_roe` (float): 最小 ROE (%)，默认 8
- `name` (str): 策略名称，默认 "dividend_stock"
- `**kwargs`: 其他基类参数

#### 筛选条件

- 股息率 ≥ min_dividend_yield
- ROE ≥ min_roe
- PE > 0 (排除亏损股)

按股息率从高到低排序，选择最高的一批股票。

---

## 工厂函数

### create_strategy()

创建选股策略的工厂函数。

```python
from vnpy.alpha.strategy import create_strategy

# 创建价值股策略
value_strategy = create_strategy(
    "value",
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2
)

# 创建成长股策略
growth_strategy = create_strategy(
    "growth",
    min_revenue_growth=25,
    min_profit_growth=30
)

# 创建质量股策略
quality_strategy = create_strategy(
    "quality",
    min_roe=15,
    min_gross_margin=30
)

# 创建高股息策略
dividend_strategy = create_strategy(
    "dividend",
    min_dividend_yield=4
)
```

**参数**:
- `strategy_type` (str): 策略类型 ("value", "growth", "quality", "dividend")
- `**kwargs`: 策略参数

**返回**: `StockScreenerStrategy` - 策略实例

**异常**: `ValueError` - 未知的策略类型

---

## 完整示例

### 示例 1：使用预设策略

```python
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.dataset import FundamentalData

# 加载财务数据
fd = FundamentalData.load("/tmp/fundamental_data.json")

# 创建价值股策略
strategy = ValueStockStrategy(
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2,
    max_positions=20,
    rebalance_days=20
)

# 获取股票池
stock_pool = fd.get_symbols()

# 获取最新财务数据
fundamental_data = fd.get_all_latest()

# 筛选股票
selected = strategy.screen_stocks(
    stock_pool=stock_pool,
    fundamental_data=fundamental_data,
    current_date=datetime(2024, 3, 1)
)

print(f"选中的股票：{selected}")
print(f"数量：{len(selected)}")
```

### 示例 2：调仓逻辑

```python
from datetime import datetime, timedelta
from vnpy.alpha.strategy import GrowthStockStrategy

# 创建成长股策略
strategy = GrowthStockStrategy(
    min_revenue_growth=25,
    min_profit_growth=30,
    max_positions=15
)

# 模拟调仓周期
current_date = datetime(2024, 3, 1)
stock_pool = ["000001.SZ", "000002.SZ", "000003.SZ"]
fundamental_data = {...}  # 财务数据

# 第一次调仓
if strategy.should_rebalance(current_date):
    selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
    to_buy, to_sell, to_keep = strategy.update_positions(selected, current_date)
    
    print(f"买入：{to_buy}")
    print(f"卖出：{to_sell}")
    print(f"保持：{to_keep}")

# 过了 10 天
strategy.increment_days(10)
current_date = datetime(2024, 3, 11)

# 检查是否需要调仓
if strategy.should_rebalance(current_date):
    print("需要调仓")
else:
    print(f"距离下次调仓还有 {strategy.rebalance_days - strategy._days_since_rebalance} 天")
```

### 示例 3：自定义策略

```python
from vnpy.alpha.strategy import StockScreenerStrategy
from typing import List, Dict, Any
from datetime import datetime

class MyCustomStrategy(StockScreenerStrategy):
    """自定义策略：低估值 + 高成长"""
    
    def __init__(
        self,
        max_pe=25,
        min_growth=20,
        min_roe=12,
        **kwargs
    ):
        super().__init__(name="custom_value_growth", **kwargs)
        self.max_pe = max_pe
        self.min_growth = min_growth
        self.min_roe = min_roe
    
    def screen_stocks(
        self,
        stock_pool: List[str],
        fundamental_data: Dict[str, Any],
        current_date: datetime
    ) -> List[str]:
        selected = []
        
        for vt_symbol in stock_pool:
            if vt_symbol not in fundamental_data:
                continue
            
            indicator = fundamental_data[vt_symbol]
            
            # 获取指标
            pe = getattr(indicator, 'pe_ratio', None)
            growth = getattr(indicator, 'revenue_growth', None)
            roe = getattr(indicator, 'roe', None)
            
            # 检查数据有效性
            if pe is None or growth is None or roe is None:
                continue
            
            # 应用筛选条件
            if pe > self.max_pe:
                continue
            if growth < self.min_growth:
                continue
            if roe < self.min_roe:
                continue
            
            selected.append(vt_symbol)
        
        # 按 ROE 排序
        selected_with_roe = [
            (sym, fundamental_data[sym].roe)
            for sym in selected
        ]
        selected_with_roe.sort(key=lambda x: x[1], reverse=True)
        
        return [sym for sym, _ in selected_with_roe[:self.max_positions]]

# 使用自定义策略
strategy = MyCustomStrategy(
    max_pe=25,
    min_growth=20,
    min_roe=12,
    max_positions=20
)

# 筛选股票
selected = strategy.screen_stocks(stock_pool, fundamental_data, datetime.now())
```

### 示例 4：多策略对比

```python
from vnpy.alpha.strategy import (
    ValueStockStrategy,
    GrowthStockStrategy,
    QualityStockStrategy,
    DividendStockStrategy
)

# 创建多个策略
strategies = {
    "价值股": ValueStockStrategy(max_pe=20, min_roe=10),
    "成长股": GrowthStockStrategy(min_revenue_growth=25, min_profit_growth=30),
    "质量股": QualityStockStrategy(min_roe=15, min_gross_margin=30),
    "高股息": DividendStockStrategy(min_dividend_yield=4)
}

# 获取数据
stock_pool = fd.get_symbols()
fundamental_data = fd.get_all_latest()
current_date = datetime(2024, 3, 1)

# 各策略选股结果
for name, strategy in strategies.items():
    selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
    print(f"{name}: {len(selected)} 只")
    print(f"  前 5 只：{selected[:5]}")
```

### 示例 5：策略参数调整

```python
from vnpy.alpha.strategy import ValueStockStrategy

# 创建策略
strategy = ValueStockStrategy()

# 查看默认参数
print("默认参数:", strategy.get_parameters())

# 调整参数
strategy.set_parameters(
    max_pe=15,      # 更严格的 PE 要求
    min_roe=15,     # 更高的 ROE 要求
    min_dividend_yield=3  # 更高的股息率要求
)

# 查看新参数
print("新参数:", strategy.get_parameters())

# 使用新参数筛选
selected = strategy.screen_stocks(stock_pool, fundamental_data, current_date)
print(f"更严格条件下的选股数量：{len(selected)}")
```

---

## 最佳实践

1. **选择合适的策略**: 根据投资目标选择策略类型
   - 稳健收益 → 价值股/高股息
   - 资本增值 → 成长股
   - 平衡配置 → 质量股

2. **参数调优**: 根据市场环境调整策略参数
   - 牛市：适当放宽估值要求
   - 熊市：提高安全边际

3. **定期调仓**: 设置合理的调仓周期
   - 太频繁：增加交易成本
   - 太稀疏：可能错过机会
   - 建议：15-30 个交易日

4. **分散投资**: 设置合理的最大持仓数
   - 太少：集中风险
   - 太多：管理困难
   - 建议：15-30 只

5. **组合策略**: 可以结合多个策略
   - 核心 - 卫星配置
   - 不同策略分配不同权重

---

## 相关文件

- 源码：`vnpy/alpha/strategy/stock_screener_strategy.py`
- 股票池管理：`stock_pool.md`
- 财务数据：`fundamental_data.md`
- 截面回测：`cross_sectional_backtesting.md`
