# VirtualAccount 迁移计划

**目标**: 将剩余 4 个模块从 VirtualAccount 迁移到 AccountService，消除技术债

**状态**: 设计中
**创建**: 2026-06-28

---

## 一、现状分析

### 1.1 待迁移模块

| 文件 | 使用方式 | 复杂度 |
|------|----------|--------|
| `vnpy/examples/alpha_research/daily_trading.py` | `VirtualAccount(initial_capital=50000)` | 🟢 简单 |
| `vnpy/examples/alpha_research/daily_trading_fixed.py` | `VirtualAccount(initial_capital=50000)` | 🟢 简单 |
| `vnpy/examples/alpha_research/generate_reports.py` | `VirtualAccount(...)` + 属性访问 | 🟡 中等 |
| `vnpy/examples/alpha_research/manual_trade_today.py` | `VirtualAccount(initial_capital=1000000)` | 🟢 简单 |

### 1.2 已迁移模块（参考）

- `examples/alpha_research/daily_trading.py` ✅
- `examples/alpha_research/generate_reports.py` ✅
- `examples/alpha_research/manual_trade_today.py` ✅
- `examples/alpha_research/virtual_account.py` → 兼容层

**注意**: `vnpy/` 目录是旧代码副本，需要同步更新。

---

## 二、迁移指南

### 2.1 API 对照表

| VirtualAccount | AccountService |
|----------------|----------------|
| `VirtualAccount(initial_capital, account_id)` | `AccountService(account_id)` + 初始化 |
| `account.buy(symbol, name, price, volume, date, reason)` | `account.buy(symbol, name, price, quantity, reason)` |
| `account.sell(symbol, price, volume, date, reason)` | `account.sell(symbol, price, quantity, reason)` |
| `account.positions` | `account.get_positions()` |
| `account.balance` | `account.get_balance()` |
| `account.cash` | `account.get_balance().cash` |
| `account.get_total_value()` | `account.get_balance().total_assets` |
| `account.get_position_value()` | `account.get_balance().market_value` |
| `account.create_snapshot()` | `account.snapshot()` |

### 2.2 迁移模板

```python
# 旧代码
from virtual_account import VirtualAccount

account = VirtualAccount(initial_capital=50000, account_id='virtual_2026')
account.buy("000001.SZSE", "平安银行", 10.5, 1000, "2026-06-28", "测试")

# 新代码
from accounts.account_service import AccountService
from accounts.account_db import AccountDB, Account

# 账户初始化（确保存在）
db = AccountDB()
if not db.get_account("virtual_2026"):
    db.create_account(Account(
        account_id="virtual_2026",
        account_name="虚拟账户",
        account_type="virtual",
        initial_capital=50000,
        cash=50000,
        currency="CNY",
        status="active",
        risk_level="moderate",
    ))

account = AccountService("virtual_2026")
account.buy(symbol="000001.SZSE", name="平安银行", price=10.5, quantity=1000, reason="测试")
```

---

## 三、任务拆分

### Task 1: 迁移 daily_trading.py（🟢 简单）

**文件**: `vnpy/examples/alpha_research/daily_trading.py`

**改动**:
1. 替换 `from virtual_account import VirtualAccount` → `from accounts.account_service import AccountService`
2. 添加 `from accounts.account_db import AccountDB, Account`
3. 添加账户初始化逻辑
4. 替换 `VirtualAccount(...)` → `AccountService(...)`
5. 替换 `account.buy(...)` 参数格式

**预估**: 5 分钟

### Task 2: 迁移 daily_trading_fixed.py（🟢 简单）

**文件**: `vnpy/examples/alpha_research/daily_trading_fixed.py`

**改动**: 同 Task 1

**预估**: 5 分钟

### Task 3: 迁移 generate_reports.py（🟡 中等）

**文件**: `vnpy/examples/alpha_research/generate_reports.py`

**改动**:
1. 替换导入
2. 替换账户初始化
3. 替换 `account.positions` → `account.get_positions()`
4. 替换 `account.balance` → `account.get_balance()`
5. 适配返回格式（Position/Balance 对象）

**预估**: 10 分钟

### Task 4: 迁移 manual_trade_today.py（🟢 简单）

**文件**: `vnpy/examples/alpha_research/manual_trade_today.py`

**改动**: 同 Task 1

**预估**: 5 分钟

### Task 5: 删除 virtual_account.py（🟢 简单）

**文件**: `vnpy/examples/alpha_research/virtual_account.py`

**改动**: 删除文件

**预估**: 1 分钟

### Task 6: 更新测试（🟡 中等）

**文件**: `vnpy/examples/alpha_research/tests/unit/test_core_zero_coverage.py`

**改动**:
1. 替换 `from virtual_account import VirtualAccount` → `from accounts.account_service import AccountService`
2. 更新测试用例（适配新 API）

**预估**: 10 分钟

---

## 四、执行计划

**顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

**验证**:
1. 每个 Task 完成后运行 `python3 -c "from accounts.account_service import AccountService; print('OK')"`
2. 所有 Task 完成后运行 `python3 -m pytest accounts/tests/ -v`
3. 运行端到端测试 `python3 examples/alpha_research/test_phase6_e2e.py`

---

## 五、风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 参数格式不兼容 | 逐个文件测试，发现问题立即修复 |
| 返回格式变化 | 检查所有使用 positions/balance 的地方 |
| 测试失败 | 保留旧测试作为参考，逐步迁移 |
| 运行时错误 | 迁移后先手动运行一次，确认无问题 |

---

## 六、预期收益

1. **消除技术债**: 移除 VirtualAccount 兼容层
2. **统一数据源**: 所有模块使用 SQLite
3. **提升可靠性**: 事务保证 + 审计日志
4. **性能优化**: TTL 缓存 + 连接池
5. **价格准确**: Phase 6 自动刷新

---

**下一步**: 开始执行 Task 1（迁移 daily_trading.py）
