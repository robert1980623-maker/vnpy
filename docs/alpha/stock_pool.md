# 股票池管理 API 文档

## 概述

股票池模块提供股票池的创建、管理和查询功能，支持指数成分股自动获取和自定义股票池管理。

**模块位置**: `vnpy/alpha/dataset/pool.py`

---

## 核心类

### StockPool - 股票池基类

股票池的基础实现，提供基本的股票管理功能。

#### 初始化

```python
from vnpy.alpha.dataset import StockPool

pool = StockPool(name="my_pool")
```

**参数**:
- `name` (str): 股票池名称，默认 "default"

#### 方法

##### `add(vt_symbol)` - 添加股票

```python
# 添加单只股票
pool.add("000001.SZ")

# 添加多只股票
pool.add(["000001.SZ", "600036.SH", "600519.SH"])
```

**参数**:
- `vt_symbol` (str | List[str]): 股票代码或代码列表

##### `remove(vt_symbol)` - 移除股票

```python
# 移除单只股票
pool.remove("000001.SZ")

# 移除多只股票
pool.remove(["000001.SZ", "600036.SH"])
```

**参数**:
- `vt_symbol` (str | List[str]): 股票代码或代码列表

##### `contains(vt_symbol)` - 检查股票

```python
if pool.contains("000001.SZ"):
    print("股票在池中")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `bool` - 是否在股票池中

##### `get_stocks()` - 获取所有股票

```python
stocks = pool.get_stocks()
print(f"股票池包含 {len(stocks)} 只股票")
```

**返回**: `List[str]` - 股票代码列表（已排序）

##### `count()` - 获取股票数量

```python
count = pool.count()
print(f"股票池大小：{count}")
```

**返回**: `int` - 股票数量

##### `clear()` - 清空股票池

```python
pool.clear()
```

##### `update_metadata(**kwargs)` - 更新元数据

```python
pool.update_metadata(
    description="沪深 300 成分股",
    tags=["large-cap", "blue-chip"]
)
```

**参数**: 任意关键字参数，更新元数据字典

##### `to_dict()` - 导出为字典

```python
data = pool.to_dict()
```

**返回**: `Dict` - 包含股票池所有信息的字典

##### `save(path)` - 保存到文件

```python
pool.save("my_pool.json")
```

**参数**:
- `path` (str | Path): 保存路径

##### `load(path)` - 从文件加载 (类方法)

```python
pool = StockPool.load("my_pool.json")
```

**参数**:
- `path` (str | Path): 加载路径

**返回**: `StockPool` - 加载的股票池对象

---

### IndexStockPool - 指数成分股票池

自动获取指数成分股的股票池。

#### 初始化

```python
from vnpy.alpha.dataset import IndexStockPool

# 沪深 300 成分股
pool = IndexStockPool(index="000300.SH")

# 中证 500 成分股
pool = IndexStockPool(index="000905.SH")

# 上证 50 成分股
pool = IndexStockPool(index="000016.SH")
```

**参数**:
- `index` (str): 指数代码（如 "000300.SH"）
- `name` (str, optional): 股票池名称，默认使用指数名称
- `update_on_init` (bool): 初始化时是否自动更新成分股，默认 True

#### 方法

继承 `StockPool` 的所有方法，额外提供：

##### `update_constituents()` - 更新成分股

```python
pool.update_constituents()
print(f"最新成分股数量：{pool.count()}")
```

从数据源获取最新的指数成分股并更新股票池。

##### `get_index()` - 获取指数代码

```python
index_code = pool.get_index()
print(f"跟踪指数：{index_code}")
```

**返回**: `str` - 指数代码

---

### CustomStockPool - 自定义股票池

支持从文件加载或手动定义的自定义股票池。

#### 初始化

```python
from vnpy.alpha.dataset import CustomStockPool

# 方式 1: 从文件加载
pool = CustomStockPool.from_file("my_stocks.txt")

# 方式 2: 手动定义
pool = CustomStockPool(
    name="tech_stocks",
    stocks=["000001.SZ", "600036.SH", "600519.SH"]
)
```

**参数**:
- `name` (str): 股票池名称
- `stocks` (List[str], optional): 初始股票列表
- `source` (str, optional): 数据来源描述

#### 类方法

##### `from_file(path)` - 从文件加载

```python
pool = CustomStockPool.from_file("stocks.txt")
```

**文件格式** (每行一个股票代码):
```
000001.SZ
600036.SH
600519.SH
```

**参数**:
- `path` (str | Path): 文件路径

**返回**: `CustomStockPool` - 加载的股票池对象

---

## 股票池运算

### 交集

```python
from vnpy.alpha.dataset import StockPool

# 创建两个股票池
pool1 = StockPool("pool1")
pool1.add(["000001.SZ", "600036.SH", "600519.SH"])

pool2 = StockPool("pool2")
pool2.add(["600036.SH", "600519.SH", "000002.SZ"])

# 计算交集
intersection = pool1.intersection(pool2)
print(intersection.get_stocks())  # ['600036.SH', '600519.SH']
```

### 并集

```python
# 计算并集
union = pool1.union(pool2)
print(union.get_stocks())  # ['000001.SZ', '000002.SZ', '600036.SH', '600519.SH']
```

### 差集

```python
# 计算差集 (pool1 有但 pool2 没有的)
diff = pool1.difference(pool2)
print(diff.get_stocks())  # ['000001.SZ']
```

---

## 完整示例

### 示例 1: 创建指数股票池

```python
from vnpy.alpha.dataset import IndexStockPool

# 创建沪深 300 股票池
pool = IndexStockPool(index="000300.SH", name="沪深 300")

# 查看成分股数量
print(f"沪深 300 成分股数量：{pool.count()}")

# 查看前 10 只股票
stocks = pool.get_stocks()[:10]
print("前 10 只成分股:", stocks)

# 检查特定股票
if pool.contains("600519.SH"):
    print("贵州茅台是沪深 300 成分股")

# 保存股票池
pool.save("hs300_pool.json")
```

### 示例 2: 自定义股票池运算

```python
from vnpy.alpha.dataset import StockPool, IndexStockPool

# 获取沪深 300 成分股
hs300 = IndexStockPool("000300.SH")

# 创建自定义股票池（科技股）
tech_stocks = StockPool("tech_stocks")
tech_stocks.add([
    "000001.SZ",  # 平安银行
    "600036.SH",  # 招商银行
    "601318.SH",  # 中国平安
])

# 找出沪深 300 中的科技股
tech_in_hs300 = hs300.intersection(tech_stocks)
print(f"沪深 300 中的科技股：{tech_in_hs300.get_stocks()}")

# 导出结果
tech_in_hs300.save("tech_in_hs300.json")
```

### 示例 3: 股票池管理

```python
from vnpy.alpha.dataset import CustomStockPool

# 创建股票池
pool = CustomStockPool(name="my_portfolio")

# 添加股票
pool.add("000001.SZ")
pool.add(["600036.SH", "600519.SH"])

# 更新元数据
pool.update_metadata(
    description="我的核心持仓",
    strategy="价值投资",
    created_by="Robert"
)

# 查看信息
print(f"股票池：{pool.name}")
print(f"股票数量：{pool.count()}")
print(f"描述：{pool._metadata['description']}")

# 导出为字典
data = pool.to_dict()

# 保存到文件
pool.save("portfolio.json")

# 移除股票
pool.remove("000001.SZ")

# 清空股票池
pool.clear()
```

---

## 数据结构

### StockPool 字典格式

```python
{
    "name": "沪深 300",
    "stocks": ["000001.SZ", "600036.SH", ...],
    "metadata": {
        "created_at": "2026-03-01T12:00:00",
        "updated_at": "2026-03-01T15:30:00",
        "description": "沪深 300 指数成分股",
        "index": "000300.SH"  # IndexStockPool 特有
    }
}
```

---

## 最佳实践

### 1. 使用缓存

```python
# 加载已保存的股票池，避免重复获取
try:
    pool = StockPool.load("hs300_pool.json")
except FileNotFoundError:
    pool = IndexStockPool("000300.SH")
    pool.save("hs300_pool.json")
```

### 2. 定期更新成分股

```python
# 每周更新一次成分股
pool = IndexStockPool("000300.SH", update_on_init=False)
pool.update_constituents()
```

### 3. 股票池组合

```python
# 多指数组合
hs300 = IndexStockPool("000300.SH")
zz500 = IndexStockPool("000905.SH")

# 大盘股组合
large_cap = hs300.union(zz500)
```

---

## 错误处理

```python
from vnpy.alpha.dataset import StockPool

pool = StockPool()

try:
    # 检查股票是否存在
    if not pool.contains("INVALID.SZ"):
        print("股票代码无效")
except Exception as e:
    print(f"错误：{e}")
```

---

## 相关文件

- **源码**: `vnpy/alpha/dataset/pool.py`
- **示例**: `examples/alpha_research/example_stock_pool.py`
- **测试**: `examples/alpha_research/test_stock_screener.py`

---

**最后更新**: 2026-03-01  
**版本**: 1.0.0
