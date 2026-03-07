# 财务数据模块 API 文档

## 概述

财务数据模块提供财务指标的获取和管理功能，支持 5 大类财务指标：估值指标、盈利能力、成长能力、偿债能力和现金流指标。

**模块位置**: `vnpy/alpha/dataset/fundamental.py`

---

## 核心类

### FinancialCategory - 财务指标类别枚举

定义财务指标的 5 大类别。

```python
from vnpy.alpha.dataset.fundamental import FinancialCategory

# 类别列表
FinancialCategory.VALUATION      # 估值指标
FinancialCategory.PROFITABILITY  # 盈利能力
FinancialCategory.GROWTH         # 成长能力
FinancialCategory.SOLVENCY       # 偿债能力
FinancialCategory.CASHFLOW       # 现金流
```

---

### FinancialIndicator - 财务指标数据类

存储单只股票在特定报告期的财务指标数据。

#### 初始化

```python
from vnpy.alpha.dataset.fundamental import FinancialIndicator

indicator = FinancialIndicator(
    vt_symbol="000001.SZ",
    report_date="2024-03-31",
    pe_ratio=10.5,
    pb_ratio=1.2,
    roe=15.3,
    revenue_growth=20.5,
    dividend_yield=3.2
)
```

**必填参数**:
- `vt_symbol` (str): 股票代码
- `report_date` (str): 报告期，格式 "YYYY-MM-DD"

**可选参数** (按类别):

**估值指标**:
- `pe_ratio` (float): 市盈率 (TTM)
- `pb_ratio` (float): 市净率
- `ps_ratio` (float): 市销率
- `pcf_ratio` (float): 市现率
- `dividend_yield` (float): 股息率 (%)

**盈利能力**:
- `roe` (float): 净资产收益率 (%)
- `roa` (float): 总资产收益率 (%)
- `gross_margin` (float): 毛利率 (%)
- `net_margin` (float): 净利率 (%)
- `operating_margin` (float): 营业利润率 (%)

**成长能力**:
- `revenue_growth` (float): 营收增长率 (%)
- `net_profit_growth` (float): 净利润增长率 (%)
- `eps_growth` (float): EPS 增长率 (%)
- `book_value_growth` (float): 净资产增长率 (%)

**偿债能力**:
- `debt_to_asset` (float): 资产负债率 (%)
- `current_ratio` (float): 流动比率
- `quick_ratio` (float): 速动比率
- `interest_coverage` (float): 利息保障倍数

**现金流**:
- `operating_cash_flow` (float): 经营活动现金流
- `free_cash_flow` (float): 自由现金流
- `cash_flow_per_share` (float): 每股现金流

**每股指标**:
- `eps` (float): 每股收益
- `bps` (float): 每股净资产
- `revenue_per_share` (float): 每股营收

#### 主要方法

##### to_dict() - 转换为字典

```python
data = indicator.to_dict()
# {
#     "vt_symbol": "000001.SZ",
#     "report_date": "2024-03-31",
#     "valuation": {"pe_ratio": 10.5, "pb_ratio": 1.2, ...},
#     "profitability": {"roe": 15.3, "roa": 8.2, ...},
#     "growth": {"revenue_growth": 20.5, ...},
#     "solvency": {...},
#     "cashflow": {...},
#     "per_share": {...}
# }
```

**返回**: `Dict` - 分类组织的字典表示

##### from_dict(data) - 从字典创建

```python
data = {...}  # to_dict() 的输出
indicator = FinancialIndicator.from_dict(data)
```

**参数**:
- `data` (Dict): 字典数据

**返回**: `FinancialIndicator` - 财务指标对象

##### get_value(field) - 获取字段值

```python
pe = indicator.get_value("pe_ratio")
roe = indicator.get_value("roe")
```

**参数**:
- `field` (str): 字段名

**返回**: `Optional[float]` - 字段值

##### is_valid(field) - 检查字段是否有效

```python
if indicator.is_valid("pe_ratio"):
    print("PE 数据有效")
```

**参数**:
- `field` (str): 字段名

**返回**: `bool` - 是否有有效值 (非 None 且 > 0)

---

### FundamentalData - 财务数据管理器

管理多只股票、多报告期的财务数据，提供存储、查询和筛选功能。

#### 初始化

```python
from vnpy.alpha.dataset import FundamentalData

fd = FundamentalData()
```

#### 主要方法

##### add(indicator) - 添加单条数据

```python
indicator = FinancialIndicator(
    vt_symbol="000001.SZ",
    report_date="2024-03-31",
    pe_ratio=10.5,
    roe=15.3
)
fd.add(indicator)
```

**参数**:
- `indicator` (FinancialIndicator): 财务指标对象

##### add_batch(indicators) - 批量添加

```python
indicators = [
    FinancialIndicator("000001.SZ", "2024-03-31", pe_ratio=10.5),
    FinancialIndicator("000002.SZ", "2024-03-31", pe_ratio=12.3),
    FinancialIndicator("000003.SZ", "2024-03-31", pe_ratio=8.7),
]
fd.add_batch(indicators)
```

**参数**:
- `indicators` (List[FinancialIndicator]): 财务指标列表

##### get(vt_symbol, report_date) - 获取指定数据

```python
# 获取最新数据
indicator = fd.get("000001.SZ")

# 获取指定报告期数据
indicator = fd.get("000001.SZ", "2024-03-31")
```

**参数**:
- `vt_symbol` (str): 股票代码
- `report_date` (str, 可选): 报告期，默认返回最新

**返回**: `Optional[FinancialIndicator]` - 财务指标

##### get_latest(vt_symbol) - 获取最新数据

```python
indicator = fd.get_latest("000001.SZ")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `Optional[FinancialIndicator]` - 最新财务指标

##### get_all_latest() - 获取所有股票的最新数据

```python
all_data = fd.get_all_latest()
# {"000001.SZ": FinancialIndicator, "000002.SZ": FinancialIndicator, ...}
```

**返回**: `Dict[str, FinancialIndicator]` - 股票代码到指标的映射

##### get_history(vt_symbol) - 获取历史数据

```python
history = fd.get_history("000001.SZ")
for indicator in history:
    print(f"{indicator.report_date}: PE={indicator.pe_ratio}")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `List[FinancialIndicator]` - 按报告期排序的历史数据

##### filter_by_field() - 单字段筛选

```python
# 筛选 PE < 20 的股票
low_pe_stocks = fd.filter_by_field("pe_ratio", max_value=20)

# 筛选 ROE > 15% 的股票
high_roe_stocks = fd.filter_by_field("roe", min_value=15)

# 筛选 PE 在 10-20 之间的股票
mid_pe_stocks = fd.filter_by_field("pe_ratio", min_value=10, max_value=20)
```

**参数**:
- `field` (str): 字段名
- `min_value` (float, 可选): 最小值（包含）
- `max_value` (float, 可选): 最大值（包含）
- `report_date` (str, 可选): 报告期，默认最新

**返回**: `List[str]` - 符合条件的股票代码列表

##### filter_by_multiple() - 多条件筛选

```python
# 价值股筛选条件
conditions = {
    "pe_ratio": {"max": 20},
    "pb_ratio": {"max": 3},
    "roe": {"min": 10},
    "dividend_yield": {"min": 2}
}

value_stocks = fd.filter_by_multiple(conditions)
print(f"价值股：{value_stocks}")
```

**参数**:
- `conditions` (Dict[str, Dict[str, float]]): 筛选条件，格式 `{field: {"min": x, "max": y}}`
- `report_date` (str, 可选): 报告期，默认最新

**返回**: `List[str]` - 符合条件的股票代码列表

##### get_statistics(field) - 计算统计信息

```python
stats = fd.get_statistics("pe_ratio")
# {
#     "count": 300,
#     "min": 5.2,
#     "max": 50.3,
#     "mean": 18.5,
#     "median": 15.2
# }
```

**参数**:
- `field` (str): 字段名

**返回**: `Dict[str, float]` - 统计信息 {count, min, max, mean, median}

##### get_stock_count() - 获取股票数量

```python
count = fd.get_stock_count()
print(f"共有 {count} 只股票")
```

**返回**: `int` - 股票数量

##### get_symbols() - 获取所有股票代码

```python
symbols = fd.get_symbols()
print(f"股票列表：{symbols}")
```

**返回**: `List[str]` - 排序后的股票代码列表

##### save(filepath) - 保存到文件

```python
fd.save("/tmp/fundamental_data.json")
```

**参数**:
- `filepath` (str | Path): 保存路径

##### load(filepath) - 从文件加载

```python
fd = FundamentalData.load("/tmp/fundamental_data.json")
```

**参数**:
- `filepath` (str | Path): 文件路径

**返回**: `FundamentalData` - 加载的数据管理器

##### clear() - 清空数据

```python
fd.clear()
```

---

## 工厂函数

### create_fundamental_data()

创建财务数据管理器的便捷函数。

```python
from vnpy.alpha.dataset import create_fundamental_data

fd = create_fundamental_data()
```

**返回**: `FundamentalData` - 财务数据管理器

---

### create_indicator()

创建财务指标对象的便捷函数。

```python
from vnpy.alpha.dataset import create_indicator

indicator = create_indicator(
    vt_symbol="000001.SZ",
    report_date="2024-03-31",
    pe_ratio=10.5,
    roe=15.3,
    dividend_yield=3.2
)
```

**参数**:
- `vt_symbol` (str): 股票代码
- `report_date` (str): 报告期
- `**kwargs`: 其他字段值

**返回**: `FinancialIndicator` - 财务指标对象

---

## 完整示例

### 示例 1：构建财务数据库

```python
from vnpy.alpha.dataset import FundamentalData, create_indicator

# 创建数据管理器
fd = FundamentalData()

# 添加多只股票的财务数据
indicators = [
    create_indicator("000001.SZ", "2024-03-31", 
                     pe_ratio=10.5, pb_ratio=1.2, roe=15.3, 
                     revenue_growth=20.5, dividend_yield=3.2),
    create_indicator("000002.SZ", "2024-03-31", 
                     pe_ratio=12.3, pb_ratio=1.5, roe=18.2,
                     revenue_growth=25.1, dividend_yield=2.8),
    create_indicator("600000.SH", "2024-03-31", 
                     pe_ratio=8.7, pb_ratio=0.9, roe=12.1,
                     revenue_growth=15.3, dividend_yield=4.5),
]

fd.add_batch(indicators)
print(f"已添加 {fd.get_stock_count()} 只股票")
```

### 示例 2：价值股筛选

```python
from vnpy.alpha.dataset import FundamentalData

fd = FundamentalData.load("/tmp/fundamental_data.json")

# 定义价值股筛选条件
conditions = {
    "pe_ratio": {"max": 20},      # PE < 20
    "pb_ratio": {"max": 3},       # PB < 3
    "roe": {"min": 10},           # ROE > 10%
    "dividend_yield": {"min": 2}  # 股息率 > 2%
}

# 筛选价值股
value_stocks = fd.filter_by_multiple(conditions)
print(f"找到 {len(value_stocks)} 只价值股")

# 查看每只股票的详细数据
for symbol in value_stocks[:5]:  # 显示前 5 只
    indicator = fd.get_latest(symbol)
    print(f"{symbol}: PE={indicator.pe_ratio}, ROE={indicator.roe}%, "
          f"股息率={indicator.dividend_yield}%")
```

### 示例 3：成长股筛选

```python
# 定义成长股筛选条件
conditions = {
    "revenue_growth": {"min": 25},    # 营收增长 > 25%
    "net_profit_growth": {"min": 30}, # 净利润增长 > 30%
    "roe": {"min": 15},               # ROE > 15%
    "pe_ratio": {"max": 50}           # PE < 50 (排除过高估值)
}

growth_stocks = fd.filter_by_multiple(conditions)
print(f"成长股：{growth_stocks}")
```

### 示例 4：统计分析

```python
# 分析 PE 分布
pe_stats = fd.get_statistics("pe_ratio")
print(f"PE 统计:")
print(f"  最小值：{pe_stats['min']}")
print(f"  最大值：{pe_stats['max']}")
print(f"  平均值：{pe_stats['mean']:.2f}")
print(f"  中位数：{pe_stats['median']:.2f}")

# 分析 ROE 分布
roe_stats = fd.get_statistics("roe")
print(f"\nROE 统计:")
print(f"  最小值：{roe_stats['min']}%")
print(f"  最大值：{roe_stats['max']}%")
print(f"  平均值：{roe_stats['mean']:.2f}%")
```

### 示例 5：历史数据追踪

```python
# 查看某只股票的历史财务数据
history = fd.get_history("000001.SZ")

print("000001.SZ 历史 ROE 变化:")
for indicator in history:
    print(f"  {indicator.report_date}: ROE={indicator.roe}%")

# 计算 ROE 趋势
if len(history) >= 2:
    recent_roe = history[-1].roe
    previous_roe = history[-2].roe
    change = recent_roe - previous_roe
    print(f"\nROE 变化：{change:+.2f}%")
```

### 示例 6：持久化存储

```python
# 保存数据
fd.save("/tmp/fundamental_2024Q1.json")

# 加载数据
fd = FundamentalData.load("/tmp/fundamental_2024Q1.json")
print(f"加载了 {fd.get_stock_count()} 只股票的数据")
```

---

## 最佳实践

1. **批量操作**: 添加多只股票数据时使用 `add_batch()` 提高效率
2. **多条件筛选**: 使用 `filter_by_multiple()` 一次性应用多个筛选条件
3. **定期更新**: 财报发布后及时更新财务数据
4. **数据验证**: 使用 `is_valid()` 检查关键字段是否有有效值
5. **统计分析**: 使用 `get_statistics()` 了解指标分布，设定合理阈值
6. **持久化**: 定期保存数据到文件，避免重复获取

---

## 相关文件

- 源码：`vnpy/alpha/dataset/fundamental.py`
- 股票池管理：`stock_pool.md`
- 选股策略：`stock_screener_strategy.md`
