# 财务数据模块文档

## 📦 模块位置

```
vnpy/alpha/dataset/fundamental.py
```

## 🚀 快速开始

```python
from vnpy.alpha.dataset import FundamentalData, create_fundamental_data

# 创建财务数据实例
fd = create_fundamental_data("./data/fundamental")
```

## 📊 财务指标分类

### 估值指标 (VALUATION_METRICS)
| 指标 | 说明 |
|------|------|
| `pe_ratio` | 市盈率（TTM） |
| `pb_ratio` | 市净率 |
| `ps_ratio` | 市销率 |
| `pcf_ratio` | 市现率 |
| `ev_ebitda` | 企业价值倍数 |
| `dividend_yield` | 股息率 |

### 盈利能力 (PROFITABILITY_METRICS)
| 指标 | 说明 |
|------|------|
| `roe` | 净资产收益率 |
| `roa` | 总资产收益率 |
| `roic` | 投入资本回报率 |
| `gross_margin` | 毛利率 |
| `net_margin` | 净利率 |
| `operating_margin` | 营业利润率 |

### 成长能力 (GROWTH_METRICS)
| 指标 | 说明 |
|------|------|
| `revenue_growth` | 营收增长率 |
| `net_profit_growth` | 净利润增长率 |
| `roe_growth` | ROE 增长率 |
| `eps_growth` | EPS 增长率 |

### 杠杆水平 (LEVERAGE_METRICS)
| 指标 | 说明 |
|------|------|
| `debt_to_asset` | 资产负债率 |
| `debt_to_equity` | 产权比率 |
| `current_ratio` | 流动比率 |
| `quick_ratio` | 速动比率 |

### 运营效率 (EFFICIENCY_METRICS)
| 指标 | 说明 |
|------|------|
| `asset_turnover` | 总资产周转率 |
| `inventory_turnover` | 存货周转率 |
| `receivables_turnover` | 应收账款周转率 |

## 🔧 核心功能

### 1. 数据管理

#### 保存数据

```python
import polars as pl

# 准备数据
df = pl.DataFrame({
    "symbol": ["000001.SZSE", "000002.SZSE"],
    "date": ["2024-12-31", "2024-12-31"],
    "pe_ratio": [10.5, 15.2],
    "pb_ratio": [1.2, 2.5],
    "roe": [15.5, 18.2],
})

# 保存
fd.save_data(df, data_type="daily")
```

#### 加载数据

```python
# 加载单只股票数据
df = fd.load_data("000001.SZSE", data_type="daily")

# 加载指定日期范围
df = fd.load_data(
    "000001.SZSE",
    data_type="daily",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# 加载全市场数据
df = fd.load_market_data(date="2024-12-31", data_type="daily")
```

### 2. 指标计算

```python
# 计算市盈率
pe = fd.calculate_pe_ratio(price=25.5, eps_ttm=2.1)

# 计算市净率
pb = fd.calculate_pb_ratio(price=25.5, bvps=15.3)

# 计算 ROE
roe = fd.calculate_roe(net_profit=500000000, equity=3000000000)

# 计算增长率
growth = fd.calculate_growth_rate(
    current_value=1200000000,
    previous_value=1000000000,
    periods=1
)
```

### 3. 股票筛选

#### 预设筛选策略

```python
# 价值股（低估值、高股息）
value_stocks = fd.get_value_stocks(
    df,
    max_pe=20,
    max_pb=3,
    min_dividend_yield=2
)

# 成长股（高增长）
growth_stocks = fd.get_growth_stocks(
    df,
    min_revenue_growth=20,
    min_net_profit_growth=25,
    min_roe=10
)

# 优质股（高 ROE、稳定增长、低负债）
quality_stocks = fd.get_quality_stocks(
    df,
    min_roe=15,
    min_revenue_growth=10,
    max_debt_to_asset=60,
    min_net_margin=10
)
```

#### 自定义条件筛选

```python
# 自定义多条件过滤
filtered = fd.filter_by_metrics(
    df=df,
    min_pe=5,           # PE > 5
    max_pe=30,          # PE < 30
    min_roe=15,         # ROE > 15%
    min_revenue_growth=20,  # 营收增长 > 20%
    max_debt_to_asset=60,   # 负债率 < 60%
    min_dividend_yield=2,   # 股息率 > 2%
    date="2024-12-31"
)
```

### 4. 综合得分

```python
# 定义因子权重
factors = {
    "pe_ratio": 0.3,        # 估值 30%
    "roe": 0.3,             # 盈利能力 30%
    "revenue_growth": 0.25, # 成长能力 25%
    "debt_to_asset": 0.15,  # 财务健康 15%
}

# 定义因子方向（1: 越大越好，-1: 越小越好）
direction = {
    "pe_ratio": -1,
    "roe": 1,
    "revenue_growth": 1,
    "debt_to_asset": -1,
}

# 计算综合得分
scored_df = fd.calculate_composite_score(df, factors, direction)

# 按得分排序
ranked = scored_df.sort("composite_score", descending=True)
```

## 📥 从外部数据源下载

### RQData

```python
import rqdatac as rq
from vnpy.alpha.dataset import FundamentalData

# 初始化
rq.init(user="your_username", pwd="your_password")
fd = FundamentalData("./data/fundamental")

# 下载估值数据
valuation = rq.get_valuation(
    order_book_ids=None,  # 全市场
    start_date="2024-12-31",
    end_date="2024-12-31",
    fields=['pe_ratio', 'pb_ratio', 'ps_ratio', 'dividend_yield']
)

# 下载财务指标
financials = rq.financial_indicator(
    order_book_ids=None,
    report_date="2024-12-31",
    fields=['roe', 'roa', 'revenue_growth', 'net_profit_growth']
)

# 合并并保存
# ... 数据合并逻辑 ...
fd.save_data(merged_df, data_type="daily")
```

### Tushare

```python
import tushare as ts
from vnpy.alpha.dataset import FundamentalData

# 初始化
ts.set_token("your_token")
pro = ts.pro_api()
fd = FundamentalData("./data/fundamental")

# 每日估值
daily_basic = pro.daily_basic(
    ts_code='',
    trade_date='20241231',
    fields='ts_code,pe,pb,ps,dv_ratio'
)

# 财务指标
fina_indicator = pro.fina_indicator(
    ts_code='',
    start_date='20240101',
    end_date='20241231'
)

# 转换格式并保存
# ... 数据转换逻辑 ...
fd.save_data(converted_df, data_type="daily")
```

## 📁 数据存储结构

```
data/fundamental/
├── daily/
│   ├── all_20241231_120000.parquet    # 全市场日线指标
│   └── 000001.SZSE.parquet            # 单只股票历史数据
├── quarterly/
│   └── 000001.SZSE.parquet            # 季度财报数据
└── yearly/
    └── 000001.SZSE.parquet            # 年度财报数据
```

## 🔧 API 参考

### FundamentalData 类

#### 构造函数

```python
FundamentalData(data_path: Optional[str] = None)
```

- `data_path`: 数据存储路径，默认为 `./data/fundamental`

#### 主要方法

| 方法 | 说明 |
|------|------|
| `save_data(df, data_type, symbol)` | 保存财务数据 |
| `load_data(symbol, data_type, ...)` | 加载单只股票数据 |
| `load_market_data(date, data_type)` | 加载全市场数据 |
| `calculate_pe_ratio(price, eps_ttm)` | 计算市盈率 |
| `calculate_pb_ratio(price, bvps)` | 计算市净率 |
| `calculate_roe(net_profit, equity)` | 计算 ROE |
| `calculate_growth_rate(...)` | 计算增长率 |
| `filter_by_metrics(...)` | 多条件过滤 |
| `calculate_composite_score(df, factors, direction)` | 计算综合得分 |
| `get_value_stocks(df, ...)` | 筛选价值股 |
| `get_growth_stocks(df, ...)` | 筛选成长股 |
| `get_quality_stocks(df, ...)` | 筛选优质股 |

## 📝 完整示例

### PEG 选股策略

```python
from vnpy.alpha.dataset import FundamentalData

fd = FundamentalData("./data/fundamental")

# 加载数据
df = fd.load_market_data("2024-12-31")

# PEG = PE / 净利润增长率
# 筛选 PEG < 1 的股票
df_with_peg = df.with_columns(
    (pl.col("pe_ratio") / pl.col("net_profit_growth")).alias("peg")
)

# 过滤
peg_stocks = df_with_peg.filter(
    (pl.col("peg") < 1) &
    (pl.col("peg") > 0) &
    (pl.col("roe") > 15)
).sort("peg")

print(peg_stocks.select(["symbol", "pe_ratio", "net_profit_growth", "peg", "roe"]))
```

### 多因子综合评分

```python
# 定义因子体系
factors = {
    "pe_ratio": 0.25,      # 估值
    "pb_ratio": 0.15,
    "roe": 0.25,           # 盈利
    "net_margin": 0.10,
    "revenue_growth": 0.15, # 成长
    "debt_to_asset": 0.10,  # 安全
}

direction = {
    "pe_ratio": -1,
    "pb_ratio": -1,
    "roe": 1,
    "net_margin": 1,
    "revenue_growth": 1,
    "debt_to_asset": -1,
}

# 计算得分并排名
scored = fd.calculate_composite_score(df, factors, direction)
ranked = scored.sort("composite_score", descending=True)

# 选出前 10 名
top10 = ranked.limit(10)
```

## ⚠️ 注意事项

1. **数据质量**：确保财务数据的准确性和及时性
2. **负值处理**：PE 等指标可能为负（亏损），需要特殊处理
3. **异常值**：极端值可能影响标准化和排名
4. **时效性**：财报数据有滞后，注意报告日期
5. **行业差异**：不同行业的估值水平差异较大，建议分行业比较

## 🎯 下一步

财务数据模块完成后，继续实现：

- [ ] 策略层：选股策略模板
- [ ] 回测层：选股策略回测框架
- [ ] 工具层：股票筛选器 CLI
- [ ] 可视化：选股结果展示

## 📖 相关文档

- [股票池管理](stock_pool.md)
- [Alpha158 因子](../community/alpha/alpha158.md)
- [策略回测](../community/app/cta_strategy.md)
