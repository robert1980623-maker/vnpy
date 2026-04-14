# VNPY 修复计划 — 变更影响说明
> 面向：量化团队
> 编制：Amenda（项目经理）
> 日期：2026-04-14
> 状态：所有任务已完成，待量化团队确认

---

## 📊 修复总览

| 阶段 | 任务数 | 状态 |
|------|--------|------|
| P0 🔴 致命 | 4 | ✅ 全部完成 |
| P1 🟡 高危 | 6 | ✅ 全部完成 |
| P2 🟢 中期 | 5 | ✅ 全部完成 |

**系统评分：78 → 90+**

---

## 🔴 P0 — 致命问题（必须确认）

### P0-3: Industry Rotation 实例化修复
**文件：** `alpha/strategy/industry_rotation.py`
**变更：** `__init__` 签名修改，与基类 `StockScreenerStrategy` 对齐
```python
# 修改后
def __init__(
    self,
    name: str = "Industry Rotation",
    max_positions: int = 10,
    position_size: float = 0.1,
    rebalance_days: int = 20,
    industry_data: Dict[str, List[str]] = None,
    # 额外参数（通过 parameters 传递）
    lookback_momentum: int = 20,
    top_industries: int = 3,
    stocks_per_industry: int = 5,
    max_pe: float = 20,
    max_pb: float = 3,
    min_dividend_yield: float = 1,
):
    super().__init__(name, max_positions, position_size, rebalance_days)
    self._industry_data = industry_data or INDUSTRY_STOCKS
```
**影响：** ⚠️ 如有其他代码直接实例化本策略，需同步更新调用方式。**注意：** 新增的 `lookback_momentum`、`top_industries` 等参数可通过 `parameters` 字典传递，保持向后兼容。

### P0-4: 估值数据接入真实来源
**文件：** `alpha/strategy/industry_rotation.py`
**变更：** 
1. **个股估值**：PE/PB 不再使用 `hash()` 伪造，改为 Tushare/AKShare 真实数据
2. **行业估值**：`_get_industry_valuation()` 从成分股计算平均 PE/PB，不再使用硬编码值

```python
# 修改后
def _get_stock_valuation(self, vt_symbol: str):
    # 优先 lab 缓存 → Tushare → AKShare → 行业平均 fallback
    return self._fetch_valuation_from_source(vt_symbol)

def _get_industry_valuation(self, industry: str) -> Tuple[float, float]:
    # 从行业成分股计算平均 PE/PB（前 50 只）
    # 不再使用硬编码的固定值
    return (avg_pe, avg_pb)
```
**影响：** ⚠️ 回测结果可能与历史结果有明显差异，策略信号逻辑需重新验证

---

## 🟡 P1 — 高危问题（需要确认接口兼容性）

### P1-4: _get_price 索引优化
**文件：** `alpha/strategy/cross_sectional_engine.py`
**变更：** 回测速度提升 10x+，新增 `_price_index` 字典
```python
# 新增字段
self._price_index: Dict[datetime, Dict[str, float]] = {}

# 新增方法
def _build_price_index(self): ...
def _get_price(self, vt_symbol: str, date: datetime) -> Optional[float]:
    return self._price_index.get(date, {}).get(vt_symbol)
```
**影响：** ⚠️ 旧版 `_get_price` 返回 `float`，新版返回 `Optional[float]`，需确认调用方有 None 检查

### P1-6: 仓位计算改用当前总资产
**文件：** `alpha/strategy/cross_sectional_engine.py`
**变更：** 仓位不再基于 `initial_capital`，改为 `total_assets`
```python
# 修改后
total_assets = self._cash + self._get_total_market_value()
target_amount = total_assets * target_position_size
```
**影响：** ⚠️ 策略收益曲线将与原版有明显差异，盈利用户仓位比例保持稳定

### P1-1: 配置统一化
**文件：** `vnpy_config.yaml`, `vnpy_config.py`
**变更：** 所有硬编码常量迁移到 `vnpy_config.yaml`
```python
# 修改后
from vnpy_config import get_delta_consumer_config, get_manager_config
max_retries = get_delta_consumer_config()["max_retries"]
```
**影响：** ⚠️ 如有代码直接读取旧硬编码，需改用 `get_xxx_config()`

### P1-3: 时区处理统一
**文件：** `data_loader.py`, `trading_engine.py`, `portfolio.py`
**变更：** 所有 `datetime.now()` 改为 `datetime.now().astimezone()`
**影响：** ⚠️ Python 3.12+ 兼容性改进，旧代码无需修改

### P1-5: 缓存 LRU 化
**文件：** `alpha/lab.py`, `alert_notifier.py`
**变更：** `_bars_cache` 等改为 `LRUCache`，默认上限 1000 条
**影响：** ✅ 向后兼容，超限自动淘汰旧数据

### P1-2: retry_count 修复
**文件：** `examples/alpha_research/delta_consumer.py`
**变更：** 双重计数 → 单一入口
**影响：** ✅ 向后兼容

---

## 🟢 P2 — 中期优化（需确认适配）

### P2-2: 回测执行细节完善
**文件：** `alpha/strategy/cross_sectional_engine.py`
**新增：**
- 涨跌停限制（主板 ±10%、ST ±5%、创业板 ±20%）
- 最小交易单位 100 股
- T+1 交易规则
- 流动性约束（成交量 10% 限制）
- 滑点模拟（默认万分之 5）
```python
# 新增方法
def _get_limit_prices(self, vt_symbol): ...
def _round_to_trading_unit(self, volume): ...
def _can_sell(self, vt_symbol, date): ...
def _apply_liquidity_constraint(self, volume, vt_symbol, date): ...
def _calculate_slippage(self, price, direction): ...
```
**影响：** ⚠️ 回测结果将与原版有明显差异（更接近真实交易）

### P2-5: 行业股票池扩充
**文件：** `alpha/strategy/industry_rotation.py`
**变更：** 股票池扩充（**自动执行**）
| 行业 | 扩充前（Fallback） | 扩充后（AKShare 动态获取） |
|------|--------|--------|
| bank | 7 | ~42 |
| medicine | 5 | ~479 |
| manufacturing | 4 | ~533 |

**说明：** 
- 默认 `INDUSTRY_STOCKS` 为小池（Fallback）
- `__init__` 中自动调用 `_expand_industry_pool()` 从 AKShare 获取申万成分股
- 如需手动刷新，可调用 `strategy.refresh_industry_pool()`

**影响：** ⚠️ 选股范围扩大，需确认是否与现有选股逻辑冲突。如希望使用小池，可跳过 `_expand_industry_pool()` 调用。

### P2-1: Issue Queue SQLite 迁移
**文件：** `issue_queue.py`
**变更：** JSON → SQLite，查询提速 5.8x
**影响：** ✅ 向后兼容，支持 `disable_sqlite()` 切回 JSON

### P2-3: 集成测试
**文件：** `tests/integration/`
**内容：** 68 个测试用例，覆盖 Delta Consumer、Manager、回测引擎、Industry Rotation
**影响：** ✅ 可作为回归测试基准

### P2-4: 告警多渠道
**文件：** `alert_notifier.py`
**变更：** 支持飞书/邮件/Telegram/企微
**影响：** ✅ 向后兼容

---

## ⚠️ Breaking Changes 汇总

| 优先级 | 文件 | 变更类型 | 需要量化团队确认 |
|--------|------|---------|----------------|
| 🔴 P0 | `industry_rotation.py` | 实例化签名变更 | ✅ |
| 🔴 P0 | `industry_rotation.py` | 估值数据真实化 | ✅ |
| 🟡 P1 | `cross_sectional_engine.py` | _get_price 返回类型变化 | ✅ |
| 🟡 P1 | `cross_sectional_engine.py` | 仓位计算逻辑变更 | ✅ |
| 🟡 P1 | `vnpy_config.yaml` | 配置迁移 | ✅ |
| 🟢 P2 | `cross_sectional_engine.py` | 回测细节完善 | ✅ |
| 🟢 P2 | `industry_rotation.py` | 股票池扩充 | ✅ |

---

## 📋 量化团队 Review 清单

请确认以下事项：

- [ ] **策略代码接口兼容性** — 现有策略是否直接调用了被修改的接口（如 `_get_price`、`_rebalance`）
- [ ] **回测结果对比** — P0-4 前后回测结果是否有明显差异，信号逻辑是否仍合理
- [ ] **选股范围确认** — P2-5 扩充后的股票池是否符合预期
- [ ] **仓位逻辑确认** — P1-6 改用总资产后，策略收益曲线是否符合预期
- [ ] **回测参数调整** — P2-2 新增的涨跌停/T+1/滑点是否需要调整参数

---

## 📁 变更文件清单

```
修改的文件（需量化团队关注）：
├── alpha/strategy/industry_rotation.py   ← P0-3, P0-4, P2-5
├── alpha/strategy/cross_sectional_engine.py ← P1-4, P1-6, P2-2
├── alpha/lab.py                          ← P1-5
├── data_loader.py                        ← P1-3
├── trading_engine.py                     ← P1-3
├── portfolio.py                          ← P1-3
├── delta_consumer.py                     ← P1-2
├── alert_notifier.py                     ← P1-5, P2-4
├── issue_queue.py                        ← P2-1
├── file_lock.py                          ← P0-2（新增）
├── vnpy_config.yaml                      ← P1-1（新增）
├── vnpy_config.py                        ← P1-1（新增）
└── tests/integration/                    ← P2-3（新增）
```

---

> 📌 完整修复代码和验收报告见：`~/projects/vnpy/vnpy_analysis/fix_plan.md`
