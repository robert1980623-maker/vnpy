# Phase 6: 持仓价格自动更新 - 实现报告

**状态**: ✅ 已完成  
**完成日期**: 2026-06-27  

---

## 📋 需求回顾

### 问题
- `positions.current_price` 仅在 buy/sell 时写入，之后不再更新
- 导致 `market_value`、`unrealized_pnl`、`total_assets` 全部过时

### 解决方案
- 从本地 CSV (`data/akshare/bars/*.csv`) 读取最新收盘价
- 批量更新 positions 表

---

## ✅ 实现内容

### 1. 新增文件: `accounts/price_updater.py`

| 类/函数 | 说明 |
|---------|------|
| `EXCHANGE_MAP` | 交易所代码映射 (SZSE→sz, SHSE→sh, BJSE→bj) |
| `_symbol_to_filename()` | Symbol 格式转换 (000001.SZSE → 000001_sz.csv) |
| `PriceUpdater` | 价格更新器主类 |
| `get_latest_price(symbol)` | 读取单只股票最新收盘价 |
| `get_latest_prices(symbols)` | 批量读取最新收盘价 |
| `refresh_positions(account_id)` | 更新指定账户的所有持仓价格 |
| `refresh_prices(account_id)` | 便捷函数 |

#### Symbol 映射规则

| positions 表格式 | CSV 文件名 |
|-----------------|-----------|
| 000001.SZSE | 000001_sz.csv |
| 600000.SHSE | 600000_sh.csv |
| 430001.BJSE | 430001_bj.csv |

#### 更新的字段

```sql
UPDATE positions 
SET current_price = ?,      -- 最新收盘价
    market_value = ?,       -- quantity * current_price
    unrealized_pnl = ?,    -- quantity * (current_price - avg_cost)
    updated_at = ?
WHERE account_id = ? AND symbol = ?
```

---

### 2. 新增测试: `accounts/tests/test_price_updater.py`

| 测试类 | 测试用例 |
|--------|---------|
| `TestSymbolToFilename` | SZSE/SHSE/BJSE/旧格式/无效格式转换 |
| `TestGetLatestPrice` | 正常读取/文件不存在/空文件/无效价格 |
| `TestGetLatestPrices` | 批量读取/部分文件不存在 |
| `TestRefreshPositions` | 正常更新/无持仓 |
| `TestExchangeMap` | 交易所映射验证 |

**测试结果**: ✅ 15 passed

---

### 3. 集成到 AccountService

#### 修改文件: `accounts/account_service.py`

**新增**:
- 导入 `PriceUpdater`
- 初始化 `_price_updater`
- 方法 `refresh_prices()` - 刷新持仓价格

**修改**:
- `snapshot()` 开头发起 `refresh_prices()`

```python
def snapshot(self, trade_date: str = None) -> Snapshot:
    # Phase 6: 刷新持仓价格
    self.refresh_prices()
    # ... 原有逻辑
```

---

## 🔄 数据流

```
1. 调用方: account.refresh_prices() 或 snapshot()
              ↓
2. PriceUpdater.refresh_positions(account_id)
              ↓
3. 查询 positions 表中该账户的所有持仓
              ↓
4. 批量获取最新价格: get_latest_prices(symbols)
              ↓
5. 读取 data/akshare/bars/{code}_{exchange}.csv
              ↓
6. 取最后一行 close 字段
              ↓
7. 更新 positions 表 (current_price, market_value, unrealized_pnl)
              ↓
8. 失效缓存 _invalidate_cache()
```

---

## 📊 验证结果

### 功能测试
```bash
$ python3 -c "
from accounts.price_updater import PriceUpdater
updater = PriceUpdater()
price = updater.get_latest_price('000001.SZSE')
print(f'000001.SZSE: {price}')
"
# 输出: 000001.SZSE: 11.08
```

### 数据库更新验证
```bash
$ sqlite3 accounts/trading.db "SELECT symbol, current_price, market_value, unrealized_pnl FROM positions WHERE account_id = 'test_db_functionality';"
# 更新前: current_price=16.0, market_value=16000, unrealized_pnl=1000
# 更新后: current_price=11.08, market_value=11080, unrealized_pnl=-3920
```

---

## 🚀 使用方式

### 手动刷新
```python
from accounts.account_service import CachedAccountService

account = CachedAccountService("my_account_id")
updated = account.refresh_prices()
print(f"Updated {updated} positions")
```

### 快照前自动刷新
```python
# snapshot() 方法会自动调用 refresh_prices()
account = CachedAccountService("my_account_id")
snapshot = account.snapshot()
# 此时 market_value / unrealized_pnl 已是最新的
```

### 定时任务
```bash
# 每日收盘后运行
30 16 * * 1-5 python3 -c "
from accounts.account_service import CachedAccountService
for account_id in ['acc1', 'acc2']:
    CachedAccountService(account_id).refresh_prices()
"
```

---

## ⚠️ 已知限制

| 限制 | 说明 |
|------|------|
| 仅支持本地 CSV | 不支持实时行情 API |
| 收盘后更新 | 不支持盘中价格更新 |
| 无 ST/停牌处理 | 暂不处理停牌、ST 等特殊情况 |

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `accounts/price_updater.py` | PriceUpdater 类实现 |
| `accounts/tests/test_price_updater.py` | 单元测试 |
| `accounts/account_service.py` | 集成到 AccountService |
| `data/akshare/bars/*.csv` | 价格数据源 |

---

**实现完成** ✅
