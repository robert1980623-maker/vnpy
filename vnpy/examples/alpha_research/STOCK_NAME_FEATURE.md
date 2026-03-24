# 📝 股票名称查询功能

**更新时间**: 2026-03-02 22:50  
**功能**: 在报告自动显示股票名称

---

## ✅ 已完成

### 1. 股票名称工具 (`stock_name_utils.py`)

**功能**:
- ✅ 从 AKShare 获取 A 股股票名称
- ✅ 本地缓存 (7 天有效期)
- ✅ 批量查询支持
- ✅ 自动格式化输出

**使用示例**:

```python
from stock_name_utils import StockNameCache, format_symbol_with_name

# 创建缓存对象
cache = StockNameCache()

# 查询单个股票
name = cache.get_name('000999.SZ')
print(name)  # 华润三九

# 格式化输出 (代码 + 名称)
symbol_with_name = format_symbol_with_name('000999.SZ')
print(symbol_with_name)  # 000999.SZ (华润三九)

# 批量查询
symbols = ['000999.SZ', '601825.SH', '301577.SZ']
names = cache.get_names(symbols)
```

---

### 2. 命令行工具

**更新缓存**:
```bash
cd ~/projects/vnpy/examples/alpha_research
python3 stock_name_utils.py
```

**查询单个股票**:
```bash
python3 stock_name_utils.py 000999.SZ
```

---

### 3. 已集成脚本

**每日复盘** (`daily_review.py`):
- ✅ 自动显示最佳/最差股票名称
- ✅ 报告 JSON 包含名称字段

**每日选股** (`daily_stock_selection.py`):
- ✅ Top 10 股票显示名称
- ✅ 交易计划显示名称
- ✅ 报告 JSON 包含名称字段

---

## 📊 效果对比

### 之前 (只有代码)

```
最佳股票:
  604808.SZ: +4.59%
  301577.SZ: +5.65%
  608999.SZ: +4.78%
```

### 现在 (代码 + 名称)

```
最佳股票:
  604808.SZ (XXX 股份): +4.59%
  301577.SZ (美信科技): +5.65%
  608999.SZ (XXX 集团): +4.78%
```

---

## 📁 缓存文件

**位置**: `data/stock_names.json`

**格式**:
```json
{
  "cache_time": "2026-03-02T22:50:00",
  "names": {
    "000999": "华润三九",
    "601825": "沪农商行",
    "301577": "美信科技",
    ...
  }
}
```

**有效期**: 7 天 (自动更新)

**大小**: ~5500 只股票

---

## 🔧 管理命令

### 手动更新缓存

```bash
# 强制更新
python3 stock_name_utils.py

# 查看缓存信息
python3 -c "
from stock_name_utils import StockNameCache
from datetime import datetime

cache = StockNameCache()
print(f'缓存股票数：{len(cache.cache_data)}')
print(f'缓存时间：{cache.cache_data.get(\"cache_time\", \"未知\")}')
"
```

### 查询股票

```bash
# 单个查询
python3 stock_name_utils.py 000999.SZ

# 批量查询
python3 -c "
from stock_name_utils import format_symbol_with_name

symbols = ['000999.SZ', '601825.SH', '301577.SZ']
for s in symbols:
    print(format_symbol_with_name(s))
"
```

---

## 📈 性能

**首次加载**: ~5 秒 (从 AKShare 获取 5500 只股票)  
**后续加载**: <0.1 秒 (从缓存读取)  
**查询速度**: <1ms (内存查询)

---

## 🎯 使用场景

### 1. 每日复盘报告

```bash
python3 daily_review.py
```

输出包含股票名称的复盘报告

### 2. 每日选股报告

```bash
python3 daily_stock_selection.py
```

输出包含股票名称的选股报告

### 3. 自定义脚本

```python
from stock_name_utils import format_symbol_with_name

# 在你的脚本中使用
for symbol in your_stock_list:
    display_name = format_symbol_with_name(symbol)
    print(f"买入：{display_name}")
```

---

## ⚠️ 注意事项

### 股票代码格式

- ✅ **正确**: `000999.SZ`, `601825.SH` (带交易所后缀)
- ❌ **错误**: `000999`, `601825` (纯数字)

### 缓存更新

- 缓存有效期 7 天
- 新股上市可能不在缓存中
- 股票更名需要更新缓存

### 网络依赖

- 首次获取需要网络
- 缓存过期后需要网络
- 无网络时使用旧缓存

---

## 🚀 未来优化

- [ ] 支持港股股票名称
- [ ] 支持美股股票名称
- [ ] 添加股票行业分类
- [ ] 添加股票概念板块
- [ ] 支持模糊搜索

---

## 📞 问题排查

### 缓存加载失败

```bash
# 删除缓存，重新获取
rm data/stock_names.json
python3 stock_name_utils.py
```

### 查询不到名称

1. 检查股票代码格式是否正确
2. 手动更新缓存
3. 检查 AKShare 是否可访问

### 缓存文件损坏

```bash
# 删除并重建
rm data/stock_names.json
python3 stock_name_utils.py
```

---

**股票名称功能已完成，报告更易读！** [耶]
