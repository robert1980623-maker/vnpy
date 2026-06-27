# Phase 6: 持仓价格自动更新

**状态**: 设计中
**创建**: 2026-06-27
**优先级**: P0

---

## 问题

`positions.current_price` 仅在 buy/sell 时写入，之后不再更新。导致：
- `market_value`、`unrealized_pnl`、`total_assets` 全部过时
- 快照、报表、风控指标基于过期价格

## 数据源

本地已有 `data/akshare/bars/*.csv`，格式：
```
datetime,open,high,low,close,volume
20260602,10.98,11.1,10.94,11.08,885428.42
```

文件名格式：`{code}_{exchange}.csv`，如 `000001_sz.csv`。

## 设计方案

### 新增模块：`accounts/price_updater.py`

```python
class PriceUpdater:
    """从本地 CSV 读取最新收盘价，批量更新 positions 表"""

    def __init__(self, bars_dir: Path = None):
        self.bars_dir = bars_dir or Path(__file__).parent.parent / "data" / "akshare" / "bars"

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """读取单只股票最新收盘价"""
        # 1. symbol -> 文件名映射 (000001 -> 000001_sz.csv)
        # 2. 读 CSV 最后一行 close 列
        # 3. 返回 float 或 None

    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """批量读取最新收盘价"""

    def refresh_positions(self, account_id: str) -> int:
        """更新指定账户的所有持仓价格
        Returns: 更新的持仓数量
        """
        # 1. 查询该账户所有持仓 symbol
        # 2. 批量获取最新价格
        # 3. 在事务内更新 positions 表:
        #    - current_price = latest_close
        #    - market_value = quantity * current_price
        #    - unrealized_pnl = quantity * (current_price - avg_cost)
        # 4. 失效 AccountService 缓存
```

### AccountService 集成

```python
# account_service.py 新增方法
def refresh_prices(self) -> int:
    """刷新持仓价格（从本地 CSV）"""
    updater = PriceUpdater()
    count = updater.refresh_positions(self.account_id)
    self._invalidate_cache()
    return count
```

### Symbol 映射

positions 表存的是 tushare 格式（如 `000001.SZ`），CSV 文件名是 akshare 格式（`000001_sz`）。

映射逻辑：
```python
def _symbol_to_filename(symbol: str) -> str:
    """000001.SZ -> 000001_sz"""
    code, exchange = symbol.split(".")
    return f"{code}_{exchange.lower()}.csv"
```

实际格式确认：
- positions 表: `000001.SZSE` (tushare 格式，大写)
- CSV 文件名: `000001_sz.csv` (akshare 格式，小写)

映射逻辑：
```python
def _symbol_to_filename(symbol: str) -> str:
    """000001.SZSE -> 000001_sz.csv"""
    code, exchange = symbol.split(".")
    exchange_map = {"SZSE": "sz", "SHSE": "sh", "BJSE": "bj"}
    ext = exchange_map.get(exchange, exchange.lower())
    return f"{code}_{ext}.csv"
```

### 调用时机

1. **手动调用**: `account.refresh_prices()` — 报表生成前、快照前
2. **快照前自动调用**: `snapshot()` 方法开头先 `refresh_prices()`
3. **定时任务（可选）**: 收盘后 cron 调用

## 任务拆分

### Task 1: 创建 `accounts/price_updater.py`（🟢 简单）
- 文件：`accounts/price_updater.py`（新建）
- 功能：`get_latest_price()` + `get_latest_prices()` + `refresh_positions()`
- symbol 映射逻辑
- 测试：`accounts/tests/test_price_updater.py`
- 预估：5 分钟

### Task 2: AccountService 集成 + snapshot 自动刷新（🟢 简单）
- 文件：`accounts/account_service.py`（修改）
- 新增 `refresh_prices()` 方法
- `snapshot()` 开头调用 `refresh_prices()`
- 测试：更新 `accounts/tests/test_account_service.py`
- 预估：5 分钟

### Task 3: 调用方集成（🟡 常规）
- 文件：`examples/alpha_research/` 下的报表/快照模块
- 在 `generate_reports.py`、`daily_portfolio_update.py` 等生成报表前调用 `refresh_prices()`
- 预估：5 分钟

## 不做的事

- ❌ 不做实时行情推送（不需要 websocket）
- ❌ 不做盘中价格更新（只做收盘后更新）
- ❌ 不接入新的行情 API（用现有本地 CSV）
- ❌ 不处理停牌/ST 等特殊情况（后续迭代）
