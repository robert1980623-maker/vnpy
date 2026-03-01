# 财务数据 API 文档

## 概述

财务数据模块提供财务指标的获取和管理功能，支持 5 大类财务指标：估值、盈利能力、成长能力、偿债能力和现金流。

**模块位置**: `vnpy/alpha/dataset/fundamental.py`

---

## 核心类

### FinancialCategory - 财务指标类别枚举

定义财务指标的 5 大类别。

```python
from vnpy.alpha.dataset import FinancialCategory

# 5 大类别
FinancialCategory.VALUATION      # 估值指标
FinancialCategory.PROFITABILITY  # 盈利能力
FinancialCategory.GROWTH         # 成长能力
FinancialCategory.SOLVENCY       # 偿债能力
FinancialCategory.CASHFLOW       # 现金流
```

---

### FinancialIndicator - 财务指标数据类

存储单只股票在特定报告期的完整财务数据。

#### 初始化

```python
from vnpy.alpha.dataset import FinancialIndicator

indicator = FinancialIndicator(
    vt_symbol="600519.SH",
    report_date="2024-03-31",
    pe_ratio=25.5,
    roe=15.2,
    revenue_growth=10.5
)
```

#### 属性

##### 估值指标 (Valuation)

| 属性 | 类型 | 说明 |
|------|------|------|
| `pe_ratio` | float | 市盈率 (TTM) |
| `pb_ratio` | float | 市净率 |
| `ps_ratio` | float | 市销率 |
| `pcf_ratio` | float | 市现率 |
| `dividend_yield` | float | 股息率 (%) |

##### 盈利能力 (Profitability)

| 属性 | 类型 | 说明 |
|------|------|------|
| `roe` | float | 净资产收益率 (%) |
| `roa` | float | 总资产收益率 (%) |
| `gross_margin` | float | 毛利率 (%) |
| `net_margin` | float | 净利率 (%) |
| `operating_margin` | float | 营业利润率 (%) |

##### 成长能力 (Growth)

| 属性 | 类型 | 说明 |
|------|------|------|
| `revenue_growth` | float | 营收增长率 (%) |
| `net_profit_growth` | float | 净利润增长率 (%) |
| `eps_growth` | float | EPS 增长率 (%) |
| `book_value_growth` | float | 净资产增长率 (%) |

##### 偿债能力 (Solvency)

| 属性 | 类型 | 说明 |
|------|------|------|
| `debt_to_asset` | float | 资产负债率 (%) |
| `current_ratio` | float | 流动比率 |
| `quick_ratio` | float | 速动比率 |
| `interest_coverage` | float | 利息保障倍数 |

##### 现金流 (Cashflow)

| 属性 | 类型 | 说明 |
|------|------|------|
| `operating_cash_flow` | float | 经营活动现金流 (元) |
| `free_cash_flow` | float | 自由现金流 (元) |
| `cash_flow_per_share` | float | 每股现金流 (元) |

##### 每股指标

| 属性 | 类型 | 说明 |
|------|------|------|
| `eps` | float | 每股收益 (元) |
| `bps` | float | 每股净资产 (元) |
| `revenue_per_share` | float | 每股营收 (元) |

#### 方法

##### `to_dict()` - 转换为字典

```python
data = indicator.to_dict()
```

**返回**: `Dict` - 结构化的财务数据字典

```python
{
    "vt_symbol": "600519.SH",
    "report_date": "2024-03-31",
    "valuation": {
        "pe_ratio": 25.5,
        "pb_ratio": 5.2,
        ...
    },
    "profitability": {
        "roe": 15.2,
        ...
    },
    ...
}
```

##### `get_category(category)` - 获取某类别指标

```python
valuation_data = indicator.get_category(FinancialCategory.VALUATION)
print(f"PE: {valuation_data['pe_ratio']}")
```

**参数**:
- `category` (FinancialCategory): 指标类别

**返回**: `Dict` - 该类别的所有指标

---

### FundamentalData - 财务数据管理器

管理多只股票的财务数据集合。

#### 初始化

```python
from vnpy.alpha.dataset import FundamentalData

fundamental = FundamentalData()
```

#### 方法

##### `add(indicator)` - 添加财务数据

```python
from vnpy.alpha.dataset import FinancialIndicator

indicator = FinancialIndicator(
    vt_symbol="600519.SH",
    report_date="2024-03-31",
    pe_ratio=25.5,
    roe=15.2
)

fundamental.add(indicator)
```

**参数**:
- `indicator` (FinancialIndicator): 财务指标对象

##### `get(vt_symbol, report_date=None)` - 获取财务数据

```python
# 获取最新数据
indicator = fundamental.get("600519.SH")

# 获取指定报告期数据
indicator = fundamental.get("600519.SH", report_date="2024-03-31")
```

**参数**:
- `vt_symbol` (str): 股票代码
- `report_date` (str, optional): 报告期，默认返回最新数据

**返回**: `FinancialIndicator | None` - 财务指标对象

##### `get_latest(vt_symbol)` - 获取最新数据

```python
indicator = fundamental.get_latest("600519.SH")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `FinancialIndicator | None` - 最新财务指标

##### `get_history(vt_symbol)` - 获取历史数据

```python
history = fundamental.get_history("600519.SH")
for indicator in history:
    print(f"{indicator.report_date}: PE={indicator.pe_ratio}")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `List[FinancialIndicator]` - 历史数据列表（按时间排序）

##### `get_all()` - 获取所有数据

```python
all_data = fundamental.get_all()
print(f"共 {len(all_data)} 条财务数据")
```

**返回**: `List[FinancialIndicator]` - 所有财务数据

##### `get_symbols()` - 获取所有股票代码

```python
symbols = fundamental.get_symbols()
print(f"覆盖 {len(symbols)} 只股票")
```

**返回**: `List[str]` - 股票代码列表

##### `filter_by_pe(max_pe)` - 按 PE 筛选

```python
low_pe_stocks = fundamental.filter_by_pe(max_pe=20)
print(f"低 PE 股票：{low_pe_stocks}")
```

**参数**:
- `max_pe` (float): 最大市盈率

**返回**: `List[str]` - 符合条件的股票代码列表

##### `filter_by_roe(min_roe)` - 按 ROE 筛选

```python
high_roe_stocks = fundamental.filter_by_roe(min_roe=15)
print(f"高 ROE 股票：{high_roe_stocks}")
```

**参数**:
- `min_roe` (float): 最小净资产收益率

**返回**: `List[str]` - 符合条件的股票代码列表

##### `filter_by_dividend(min_yield)` - 按股息率筛选

```python
dividend_stocks = fundamental.filter_by_dividend(min_yield=3.0)
print(f"高股息股票：{dividend_stocks}")
```

**参数**:
- `min_yield` (float): 最小股息率 (%)

**返回**: `List[str]` - 符合条件的股票代码列表

##### `filter_multi(**criteria)` - 多条件筛选

```python
# 价值股筛选：低 PE + 高 ROE + 高股息
value_stocks = fundamental.filter_multi(
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2.0
)
print(f"价值股：{value_stocks}")
```

**参数**:
- `max_pe` (float, optional): 最大市盈率
- `min_pe` (float, optional): 最小市盈率
- `max_pb` (float, optional): 最大市净率
- `min_roe` (float, optional): 最小 ROE
- `min_dividend_yield` (float, optional): 最小股息率
- `min_revenue_growth` (float, optional): 最小营收增长率
- 其他指标类似...

**返回**: `List[str]` - 符合条件的股票代码列表

##### `count()` - 获取数据量

```python
count = fundamental.count()
print(f"财务数据总量：{count}")
```

**返回**: `int` - 数据条数

##### `to_dict()` - 导出为字典

```python
data = fundamental.to_dict()
```

**返回**: `Dict` - 所有财务数据的字典表示

##### `save(path)` - 保存到文件

```python
fundamental.save("fundamental_data.json")
```

**参数**:
- `path` (str | Path): 保存路径

##### `load(path)` - 从文件加载 (类方法)

```python
fundamental = FundamentalData.load("fundamental_data.json")
```

**参数**:
- `path` (str | Path): 加载路径

**返回**: `FundamentalData` - 加载的财务数据管理器

---

## 完整示例

### 示例 1: 创建财务数据

```python
from vnpy.alpha.dataset import FinancialIndicator, FundamentalData

# 创建财务数据管理器
fundamental = FundamentalData()

# 添加贵州茅台数据
moutai = FinancialIndicator(
    vt_symbol="600519.SH",
    report_date="2024-03-31",
    pe_ratio=25.5,
    pb_ratio=5.2,
    roe=15.2,
    revenue_growth=10.5,
    net_profit_growth=12.3,
    dividend_yield=2.5,
    debt_to_asset=30.5,
    gross_margin=90.2
)
fundamental.add(moutai)

# 添加招商银行数据
cmb = FinancialIndicator(
    vt_symbol="600036.SH",
    report_date="2024-03-31",
    pe_ratio=5.8,
    pb_ratio=0.7,
    roe=12.5,
    revenue_growth=8.2,
    dividend_yield=5.2,
    debt_to_asset=90.5
)
fundamental.add(cmb)

# 获取数据
moutai_data = fundamental.get("600519.SH")
print(f"贵州茅台 PE: {moutai_data.pe_ratio}")
print(f"贵州茅台 ROE: {moutai_data.roe}%")
```

### 示例 2: 财务筛选

```python
from vnpy.alpha.dataset import FundamentalData

# 加载财务数据
fundamental = FundamentalData.load("fundamental_data.json")

# 单条件筛选
print("=== 低 PE 股票 (PE < 10) ===")
low_pe = fundamental.filter_by_pe(max_pe=10)
for symbol in low_pe:
    data = fundamental.get(symbol)
    print(f"{symbol}: PE={data.pe_ratio}")

print("\n=== 高 ROE 股票 (ROE > 15%) ===")
high_roe = fundamental.filter_by_roe(min_roe=15)
for symbol in high_roe:
    data = fundamental.get(symbol)
    print(f"{symbol}: ROE={data.roe}%")

print("\n=== 高股息股票 (股息率 > 4%) ===")
high_dividend = fundamental.filter_by_dividend(min_yield=4.0)
for symbol in high_dividend:
    data = fundamental.get(symbol)
    print(f"{symbol}: 股息率={data.dividend_yield}%")

# 多条件筛选（价值股）
print("\n=== 价值股 (PE<20, ROE>10%, 股息率>2%) ===")
value_stocks = fundamental.filter_multi(
    max_pe=20,
    min_roe=10,
    min_dividend_yield=2.0
)
for symbol in value_stocks:
    data = fundamental.get(symbol)
    print(f"{symbol}: PE={data.pe_ratio}, ROE={data.roe}%, 股息率={data.dividend_yield}%")
```

### 示例 3: 财务分析

```python
from vnpy.alpha.dataset import FundamentalData, FinancialCategory

fundamental = FundamentalData.load("fundamental_data.json")

# 分析单只股票
symbol = "600519.SH"
data = fundamental.get(symbol)

print(f"=== {symbol} 财务分析 ===")

# 估值分析
valuation = data.get_category(FinancialCategory.VALUATION)
print("\n估值指标:")
for key, value in valuation.items():
    if value is not None:
        print(f"  {key}: {value}")

# 盈利能力
profitability = data.get_category(FinancialCategory.PROFITABILITY)
print("\n盈利能力:")
for key, value in profitability.items():
    if value is not None:
        print(f"  {key}: {value}%")

# 成长能力
growth = data.get_category(FinancialCategory.GROWTH)
print("\n成长能力:")
for key, value in growth.items():
    if value is not None:
        print(f"  {key}: {value}%")

# 历史数据
print("\n历史 ROE 变化:")
history = fundamental.get_history(symbol)
for record in history[-5:]:  # 最近 5 期
    print(f"  {record.report_date}: ROE={record.roe}%")
```

### 示例 4: 数据导出

```python
from vnpy.alpha.dataset import FundamentalData

fundamental = FundamentalData.load("fundamental_data.json")

# 导出为字典
data = fundamental.to_dict()

# 导出为 JSON 文件
import json
with open("financial_report.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# 导出为 CSV
import csv
all_data = fundamental.get_all()

with open("financial_data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # 表头
    writer.writerow([
        "股票代码", "报告期", "PE", "PB", "ROE", 
        "营收增长率", "净利润增长率", "股息率"
    ])
    # 数据
    for record in all_data:
        writer.writerow([
            record.vt_symbol,
            record.report_date,
            record.pe_ratio,
            record.pb_ratio,
            record.roe,
            record.revenue_growth,
            record.net_profit_growth,
            record.dividend_yield
        ])

print("数据导出完成!")
```

---

## 数据结构

### FinancialIndicator 字典格式

```python
{
    "vt_symbol": "600519.SH",
    "report_date": "2024-03-31",
    "valuation": {
        "pe_ratio": 25.5,
        "pb_ratio": 5.2,
        "ps_ratio": 8.3,
        "pcf_ratio": 20.1,
        "dividend_yield": 2.5
    },
    "profitability": {
        "roe": 15.2,
        "roa": 12.5,
        "gross_margin": 90.2,
        "net_margin": 25.3,
        "operating_margin": 30.1
    },
    "growth": {
        "revenue_growth": 10.5,
        "net_profit_growth": 12.3,
        "eps_growth": 11.8,
        "book_value_growth": 8.5
    },
    "solvency": {
        "debt_to_asset": 30.5,
        "current_ratio": 2.5,
        "quick_ratio": 2.0,
        "interest_coverage": 15.2
    },
    "cashflow": {
        "operating_cash_flow": 50000000000,
        "free_cash_flow": 40000000000,
        "cash_flow_per_share": 40.5
    },
    "per_share": {
        "eps": 50.5,
        "bps": 350.2,
        "revenue_per_share": 200.5
    }
}
```

---

## 筛选器速查

### 价值股筛选

```python
value_stocks = fundamental.filter_multi(
    max_pe=20,           # PE < 20
    max_pb=3,            # PB < 3
    min_roe=10,          # ROE > 10%
    min_dividend_yield=2 # 股息率 > 2%
)
```

### 成长股筛选

```python
growth_stocks = fundamental.filter_multi(
    min_revenue_growth=20,    # 营收增长 > 20%
    min_net_profit_growth=25, # 净利润增长 > 25%
    min_eps_growth=20         # EPS 增长 > 20%
)
```

### 质量股筛选

```python
quality_stocks = fundamental.filter_multi(
    min_roe=15,           # ROE > 15%
    min_gross_margin=30,  # 毛利率 > 30%
    max_debt_to_asset=50  # 资产负债率 < 50%
)
```

### 高股息筛选

```python
dividend_stocks = fundamental.filter_multi(
    min_dividend_yield=4,  # 股息率 > 4%
    min_roe=10,            # ROE > 10%
    max_debt_to_asset=60   # 资产负债率 < 60%
)
```

---

## 最佳实践

### 1. 数据验证

```python
def validate_indicator(indicator: FinancialIndicator) -> bool:
    """验证财务数据有效性"""
    if indicator.pe_ratio is not None and indicator.pe_ratio < 0:
        return False
    if indicator.roe is not None and indicator.roe < -100:
        return False
    if indicator.debt_to_asset is not None and indicator.debt_to_asset > 100:
        return False
    return True

# 使用
for symbol in fundamental.get_symbols():
    data = fundamental.get(symbol)
    if not validate_indicator(data):
        print(f"警告：{symbol} 数据异常")
```

### 2. 数据更新

```python
# 只更新特定股票的数据
symbols_to_update = ["600519.SH", "600036.SH"]
for symbol in symbols_to_update:
    new_data = fetch_latest_data(symbol)  # 从数据源获取
    fundamental.add(new_data)

# 保存更新
fundamental.save("fundamental_data.json")
```

### 3. 缓存管理

```python
from pathlib import Path

CACHE_FILE = Path("cache/fundamental_data.json")

def load_fundamental_data():
    """加载财务数据（优先使用缓存）"""
    if CACHE_FILE.exists():
        return FundamentalData.load(CACHE_FILE)
    else:
        # 从数据源加载
        fundamental = FundamentalData()
        # ... 加载数据 ...
        fundamental.save(CACHE_FILE)
        return fundamental
```

---

## 错误处理

```python
from vnpy.alpha.dataset import FundamentalData

try:
    fundamental = FundamentalData.load("data.json")
    data = fundamental.get("INVALID.SZ")
    if data is None:
        print("未找到该股票的财务数据")
except FileNotFoundError:
    print("数据文件不存在")
except Exception as e:
    print(f"错误：{e}")
```

---

## 相关文件

- **源码**: `vnpy/alpha/dataset/fundamental.py`
- **示例**: `examples/alpha_research/example_fundamental_data.py`
- **测试**: `examples/alpha_research/test_stock_screener.py`

---

**最后更新**: 2026-03-01  
**版本**: 1.0.0
