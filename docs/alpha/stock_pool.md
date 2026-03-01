# 股票池管理模块文档

## 📦 模块位置

```
vnpy/alpha/dataset/pool.py
```

## 🚀 快速开始

```python
from vnpy.alpha.dataset import StockPool, create_pool

# 创建股票池实例
pool = create_pool("./data/pool")
```

## 📊 功能说明

### 1. 预定义指数成分股

支持的指数：

| 代码 | 名称 | 交易所代码 |
|------|------|-----------|
| `csi300` | 沪深 300 | 000300.SSE |
| `csi500` | 中证 500 | 000905.SSE |
| `csi1000` | 中证 1000 | 000852.SSE |
| `csi2000` | 中证 2000 | 932000.SSE |
| `a50` | 富时 A50 | XIN9.SGF |
| `zx300` | 中小 300 | 399008.SZSE |
| `cyb` | 创业板指 | 399006.SZSE |
| `kcb` | 科创 50 | 000688.SSE |

### 2. 成分股数据管理

#### 保存成分股数据

```python
# 成分股数据格式：{日期字符串：[股票代码列表]}
components = {
    "2024-01-01": ["000001.SZSE", "000002.SZSE", "600000.SSE"],
    "2024-06-01": ["000001.SZSE", "000003.SZSE", "600000.SSE"],
}

pool.save_index_components("csi300", components)
```

#### 获取指定日期的成分股

```python
from datetime import datetime

# 获取 2024 年 6 月 1 日的沪深 300 成分股
components = pool.get_index_components(
    "csi300", 
    datetime(2024, 6, 1)
)
```

### 3. 自定义股票池

#### 创建股票池

```python
# 创建自定义股票池
my_stocks = ["000001.SZSE", "600000.SSE", "000002.SZSE"]
pool.create_custom_pool("my_bluechip", my_stocks)
```

#### 添加/移除股票

```python
# 添加股票
pool.add_to_pool("my_bluechip", ["601318.SSE"])

# 移除股票
pool.remove_from_pool("my_bluechip", ["000001.SZSE"])
```

#### 获取股票池

```python
stocks = pool.get_custom_pool("my_bluechip")
```

### 4. 股票过滤

```python
import polars as pl

# 准备行情数据（用于过滤）
df = pl.DataFrame({
    "symbol": ["000001.SZSE", "ST0002.SZSE", "600001.SSE"],
    "date": ["2024-01-01", "2024-01-01", "2024-01-01"],
    "volume": [1000000, 200000, 0],  # 600001 停牌
    "turnover": [10000000, 1000000, 0],
})

# 过滤股票
filtered = pool.filter_stocks(
    symbols=["000001.SZSE", "ST0002.SZSE", "600001.SSE"],
    df=df,
    exclude_st=True,           # 排除 ST 股票
    exclude_suspended=True,    # 排除停牌股票
    exclude_new=True,          # 排除新股
    new_days=60,               # 新股阈值：60 天
    min_turnover=100000,       # 最小成交额：10 万
)
```

### 5. 多股票池操作

#### 并集

```python
# 获取多个股票池的并集
universe = pool.get_universe(["csi300", "csi500", "my_custom"])
```

#### 交集

```python
# 获取多个股票池的交集
intersection = pool.get_intersection(["csi300", "my_bluechip"])
```

## 📥 从 RQData 下载成分股

```python
import rqdatac as rq
from datetime import datetime
from vnpy.alpha.dataset import StockPool

# 初始化
rq.init(user="your_username", pwd="your_password")
pool = StockPool("./data/pool")

# 下载沪深 300 成分股
start_date = "2020-01-01"
end_date = datetime.now().strftime("%Y-%m-%d")

data = rq.index_components("000300.XSHG", start_date=start_date, end_date=end_date)

# 转换格式
components = {}
for dt, symbols in data.items():
    date_str = dt.strftime("%Y-%m-%d")
    vt_symbols = [
        s.replace("XSHG", "SSE").replace("XSHE", "SZSE")
        for s in symbols
    ]
    components[date_str] = vt_symbols

# 保存
pool.save_index_components("csi300", components)
```

## 📁 数据存储结构

```
data/pool/
├── custom_pools.json          # 自定义股票池
├── csi300_components.json     # 沪深 300 成分股历史
├── csi500_components.json     # 中证 500 成分股历史
└── ...
```

## 🔧 API 参考

### StockPool 类

#### 构造函数

```python
StockPool(pool_path: Optional[str] = None)
```

- `pool_path`: 股票池数据存储路径，默认为 `./data/pool`

#### 主要方法

| 方法 | 说明 |
|------|------|
| `get_index_components(index_name, date)` | 获取指数成分股 |
| `save_index_components(index_name, components)` | 保存成分股历史 |
| `create_custom_pool(pool_name, symbols, overwrite)` | 创建自定义股票池 |
| `add_to_pool(pool_name, symbols)` | 添加股票到股票池 |
| `remove_from_pool(pool_name, symbols)` | 从股票池移除股票 |
| `get_custom_pool(pool_name)` | 获取自定义股票池 |
| `list_pools()` | 列出所有自定义股票池 |
| `filter_stocks(symbols, df, ...)` | 过滤股票池 |
| `get_universe(pool_names, date)` | 获取多股票池并集 |
| `get_intersection(pool_names, date)` | 获取多股票池交集 |

## 📝 使用示例

完整示例请查看：`examples/alpha_research/example_stock_pool.py`

运行示例：

```bash
cd ~/projects/vnpy/vnpy
source .venv/bin/activate  # 或激活你的虚拟环境
python examples/alpha_research/example_stock_pool.py
```

## ⚠️ 注意事项

1. **成分股数据需要自行下载**：模块提供了存储和管理功能，但需要从数据源（如 RQData、迅投研等）下载实际的成分股数据

2. **股票代码格式**：统一使用 `vt_symbol` 格式，如 `000001.SZSE`、`600000.SSE`

3. **数据更新**：指数成分股会定期调整，建议定期更新成分股数据

4. **过滤条件**：股票过滤需要提供行情数据 DataFrame，包含 `symbol`、`date`、`volume`、`turnover` 等列

## 🎯 下一步

数据层完成后，继续实现：

- [ ] 策略层：选股策略模板
- [ ] 回测层：选股策略回测框架
- [ ] 工具层：股票筛选器工具
- [ ] 可视化：选股结果展示
