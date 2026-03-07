# 股票池管理模块 API 文档

## 概述

股票池管理模块提供股票池的创建、管理和查询功能，支持指数成分股自动获取、自定义股票池管理以及股票池的交集/并集运算。

**模块位置**: `vnpy/alpha/dataset/pool.py`

---

## 核心类

### StockPool - 股票池基类

所有股票池的基类，提供基本的股票池操作接口。

#### 初始化

```python
from vnpy.alpha.dataset import StockPool

pool = StockPool(name="my_pool")
```

**参数**:
- `name` (str): 股票池名称，默认为 "default"

#### 主要方法

##### add(vt_symbol) - 添加股票

```python
# 添加单只股票
pool.add("000001.SZ")

# 批量添加
pool.add(["000001.SZ", "000002.SZ", "000003.SZ"])
```

**参数**:
- `vt_symbol` (str | List[str]): 股票代码或代码列表

##### remove(vt_symbol) - 移除股票

```python
# 移除单只股票
pool.remove("000001.SZ")

# 批量移除
pool.remove(["000001.SZ", "000002.SZ"])
```

**参数**:
- `vt_symbol` (str | List[str]): 股票代码或代码列表

##### contains(vt_symbol) - 检查股票是否在池中

```python
if pool.contains("000001.SZ"):
    print("股票在池中")
```

**参数**:
- `vt_symbol` (str): 股票代码

**返回**: `bool` - 是否在股票池中

##### get_stocks() - 获取所有股票

```python
stocks = pool.get_stocks()
print(f"股票列表：{stocks}")
```

**返回**: `List[str]` - 排序后的股票代码列表

##### count() - 获取股票数量

```python
count = pool.count()
print(f"股票数量：{count}")
```

**返回**: `int` - 股票数量

##### clear() - 清空股票池

```python
pool.clear()
```

##### save(filepath) - 保存到文件

```python
pool.save("/path/to/pool.json")
```

**参数**:
- `filepath` (str | Path): 保存路径

##### load(filepath) - 从文件加载

```python
pool = StockPool.load("/path/to/pool.json")
```

**参数**:
- `filepath` (str | Path): 文件路径

**返回**: `StockPool` - 加载的股票池对象

##### to_dict() - 转换为字典

```python
data = pool.to_dict()
# {
#     "name": "my_pool",
#     "stocks": ["000001.SZ", "000002.SZ"],
#     "count": 2,
#     "metadata": {...}
# }
```

**返回**: `Dict` - 股票池的字典表示

---

### IndexStockPool - 指数成分股股票池

自动获取和维护指数成分股的股票池。

#### 初始化

```python
from vnpy.alpha.dataset import IndexStockPool

# 沪深 300 成分股
pool = IndexStockPool(index_code="000300.SH")

# 指定名称
pool = IndexStockPool(index_code="000016.SH", name="上证 50 成分股")
```

**参数**:
- `index_code` (str): 指数代码，如 "000300.SH"
- `name` (str, 可选): 股票池名称，默认使用指数名称

**支持的指数代码**:
| 代码 | 名称 |
|------|------|
| 000300.SH | 沪深 300 |
| 000016.SH | 上证 50 |
| 000905.SH | 中证 500 |
| 000852.SH | 中证 1000 |
| 399006.SZ | 创业板指 |
| 000001.SH | 上证指数 |
| 399001.SZ | 深证成指 |

#### 主要方法

##### update_components(components) - 更新成分股

```python
components = ["000001.SZ", "000002.SZ", "000003.SZ"]
pool.update_components(components)
```

**参数**:
- `components` (List[str]): 成分股列表

##### get_index_info() - 获取指数信息

```python
info = pool.get_index_info()
# {
#     "index_code": "000300.SH",
#     "index_name": "沪深 300",
#     "component_count": 300,
#     "last_updated": "2024-03-01T10:00:00"
# }
```

**返回**: `Dict` - 指数信息字典

---

### CustomStockPool - 自定义股票池

支持灵活的股票池组合运算，可管理多个子股票池。

#### 初始化

```python
from vnpy.alpha.dataset import CustomStockPool

pool = CustomStockPool(name="my_custom_pool")
```

**参数**:
- `name` (str): 股票池名称，默认为 "custom"

#### 主要方法

##### add_sub_pool(name, pool) - 添加子股票池

```python
# 创建子池
value_pool = StockPool(name="value_stocks")
value_pool.add(["000001.SZ", "000002.SZ"])

# 添加到主池
pool.add_sub_pool("value", value_pool)
```

**参数**:
- `name` (str): 子池名称
- `pool` (StockPool): 子股票池对象

##### union(*pool_names) - 计算并集

```python
# 获取 value 和 growth 两个子池的并集
stocks = pool.union("value", "growth")
```

**参数**:
- `*pool_names` (str): 子池名称列表

**返回**: `List[str]` - 并集股票列表

##### intersection(*pool_names) - 计算交集

```python
# 获取同时在 value 和 growth 中的股票
stocks = pool.intersection("value", "growth")
```

**参数**:
- `*pool_names` (str): 子池名称列表

**返回**: `List[str]` - 交集股票列表

##### difference(pool_name1, pool_name2) - 计算差集

```python
# 获取在 value 中但不在 growth 中的股票
stocks = pool.difference("value", "growth")
```

**参数**:
- `pool_name1` (str): 第一个子池名称
- `pool_name2` (str): 第二个子池名称

**返回**: `List[str]` - 差集股票列表（在 pool1 但不在 pool2）

##### get_sub_pool_names() - 获取所有子池名称

```python
names = pool.get_sub_pool_names()
# ["value", "growth", "quality"]
```

**返回**: `List[str]` - 子池名称列表

---

## 工厂函数

### create_index_pool()

创建指数成分股股票池的便捷函数。

```python
from vnpy.alpha.dataset import create_index_pool

# 创建沪深 300 成分股池
pool = create_index_pool(
    index_code="000300.SH",
    components=["000001.SZ", "000002.SZ"]  # 可选
)
```

**参数**:
- `index_code` (str): 指数代码
- `components` (List[str], 可选): 成分股列表

**返回**: `IndexStockPool` - 创建的股票池

---

### create_custom_pool()

创建自定义股票池的便捷函数。

```python
from vnpy.alpha.dataset import create_custom_pool

pool = create_custom_pool(name="my_pool")
```

**参数**:
- `name` (str): 股票池名称

**返回**: `CustomStockPool` - 创建的股票池

---

## 完整示例

### 示例 1：管理指数成分股

```python
from vnpy.alpha.dataset import IndexStockPool

# 创建沪深 300 成分股池
pool = IndexStockPool(index_code="000300.SH")

# 更新成分股（实际使用时从数据源获取）
components = ["000001.SZ", "000002.SZ", "600000.SH"]
pool.update_components(components)

# 查询信息
print(f"指数：{pool.get_index_info()['index_name']}")
print(f"成分股数量：{pool.count()}")

# 检查某只股票是否在成分股中
if pool.contains("000001.SZ"):
    print("000001.SZ 是沪深 300 成分股")

# 保存到文件
pool.save("/tmp/hs300_pool.json")
```

### 示例 2：自定义股票池组合运算

```python
from vnpy.alpha.dataset import CustomStockPool, StockPool

# 创建自定义股票池
main_pool = CustomStockPool(name="strategy_pool")

# 创建子池
value_pool = StockPool(name="value")
value_pool.add(["000001.SZ", "000002.SZ", "600000.SH"])

growth_pool = StockPool(name="growth")
growth_pool.add(["000002.SZ", "300001.SZ", "300002.SZ"])

# 添加子池
main_pool.add_sub_pool("value", value_pool)
main_pool.add_sub_pool("growth", growth_pool)

# 计算并集：价值股或成长股
all_stocks = main_pool.union("value", "growth")
print(f"并集：{all_stocks}")
# ['000001.SZ', '000002.SZ', '300001.SZ', '300002.SZ', '600000.SH']

# 计算交集：既是价值股又是成长股
common_stocks = main_pool.intersection("value", "growth")
print(f"交集：{common_stocks}")
# ['000002.SZ']

# 计算差集：是价值股但不是成长股
value_only = main_pool.difference("value", "growth")
print(f"差集：{value_only}")
# ['000001.SZ', '600000.SH']
```

### 示例 3：持久化存储

```python
from vnpy.alpha.dataset import StockPool

# 创建并保存
pool = StockPool(name="my_favorites")
pool.add(["000001.SZ", "000002.SZ", "600000.SH"])
pool.save("/tmp/favorites.json")

# 从文件加载
loaded_pool = StockPool.load("/tmp/favorites.json")
print(f"加载的股票池：{loaded_pool.name}")
print(f"股票数量：{loaded_pool.count()}")
```

---

## 最佳实践

1. **使用有意义的名称**: 为股票池设置描述性名称，便于管理
2. **定期更新指数成分股**: 指数成分股会定期调整，应及时更新
3. **利用集合运算**: 通过交集/并集/差集构建复杂的选股逻辑
4. **持久化存储**: 重要股票池应保存到文件，避免重复构建
5. **批量操作**: 添加/移除多只股票时使用批量操作，提高效率

---

## 相关文件

- 源码：`vnpy/alpha/dataset/pool.py`
- 财务数据模块：`fundamental_data.md`
- 选股策略：`stock_screener_strategy.md`
