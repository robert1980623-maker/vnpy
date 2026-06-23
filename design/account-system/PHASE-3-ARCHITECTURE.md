# Phase 3 架构设计 — 调用方迁移

> **设计日期**: 2026-06-23
> **依赖**: Phase 2 已完成 (AccountService, FeishuSyncService)
> **目标**: 将所有调用方从 VirtualAccount 迁移到 AccountService

---

## 1. 迁移策略

### 1.1 分批迁移

| 批次 | 优先级 | 模块 | 文件数 |
|------|--------|------|--------|
| Batch 1 | P0 | 核心交易模块 | 4 |
| Batch 2 | P1 | 风控/报表模块 | 6 |
| Batch 3 | P2 | 策略/模拟模块 | 10 |

### 1.2 向后兼容

每个批次迁移后：
1. 保留 VirtualAccount 类（标记 @deprecated）
2. VirtualAccount 内部转发到 AccountService
3. 旧代码可继续运行，逐步切换

---

## 2. Batch 1 — 核心交易模块 (P0)

### 2.1 daily_trading.py

**当前实现**:
```python
from virtual_account import VirtualAccount

account = VirtualAccount("virtual_2026")
result = account.buy(symbol, name, price, quantity)
```

**迁移后**:
```python
from accounts.account_service import AccountService

account = AccountService("virtual_2026")
result = account.buy(symbol, name, price, quantity, source_module="daily_trading.py")
```

**变更点**:
- import 路径: `virtual_account` → `accounts.account_service`
- 类名: `VirtualAccount` → `AccountService`
- 新增参数: `source_module="daily_trading.py"` (审计用)

### 2.2 daily_trading_fixed.py

同 daily_trading.py，仅改 import 和类名。

### 2.3 manual_trade_today.py

同上。

### 2.4 execute_trading.py

**当前实现**:
```python
# 内联类 FeishuVirtualAccount
class FeishuVirtualAccount:
    def __init__(self):
        self.cache = self._load_feishu_cache()
    
    def buy(self, ...):
        # 直接写飞书缓存
```

**迁移后**:
```python
from accounts.account_service import AccountService
from accounts.feishu_sync import FeishuSyncService

account = AccountService("virtual_2026")
sync = FeishuSyncService(account, account.event_bus)

# buy 后自动同步飞书
result = account.buy(..., source_module="execute_trading.py")
```

---

## 3. Batch 2 — 风控/报表模块 (P1)

### 3.1 risk_check.py

**当前实现**:
```python
account = VirtualAccount("virtual_2026")
balance = account.get_balance()
```

**迁移后**:
```python
from accounts.account_service import AccountService

account = AccountService("virtual_2026")
balance = account.get_balance()
```

### 3.2 generate_reports.py

同上。

### 3.3 comprehensive_attribution.py

同上。

### 3.4 performance_attribution.py

同上。

### 3.5 realtime_monitor.py

**当前实现**:
```python
# 自行计算 balance
cash = account_data.get("current_cash", 0)
positions = account_data.get("positions", [])
total = cash + sum(p.get("market_value", 0) for p in positions)
```

**迁移后**:
```python
from accounts.account_service import AccountService

account = AccountService("virtual_2026")
balance = account.get_balance()
total = balance.total_assets
```

### 3.6 rebalance_portfolio.py

同 realtime_monitor.py。

---

## 4. Batch 3 — 策略/模拟模块 (P2)

### 4.1 limit_up_strategy_runner.py

同 Batch 1 模式。

### 4.2 limit_up_leaders_20260415.py / 20260416.py

只读操作，改 import 即可。

### 4.3 daily_portfolio_update.py

**当前实现**:
```python
from paper_trading import PaperTradingAccount

account = PaperTradingAccount("demo")
```

**迁移后**:
```python
from accounts.account_service import AccountService

account = AccountService("demo")
```

### 4.4 paper_trading_demo.py / main.py

同上。

### 4.5 advanced_trading_features.py

**当前实现**:
```python
from paper_trading_system import PaperTradingAccount
```

**迁移后**:
```python
from accounts.account_service import AccountService
```

### 4.6 simulated_trading.py

**当前实现**:
```python
# 自实现账户逻辑
class SimulatedAccount:
    def __init__(self):
        self.cash = 1000000
        self.positions = {}
```

**迁移后**:
```python
from accounts.account_service import AccountService

account = AccountService("simulated")
```

### 4.7 execute_stock_selection.py

同 realtime_monitor.py（自行计算 → AccountService.get_balance）。

### 4.8 debug_virtual_account.py

只读操作，改 import 即可。

---

## 5. VirtualAccount 兼容层

迁移完成后，保留 VirtualAccount 作为兼容层：

```python
# accounts/virtual_account_compat.py

import warnings
from accounts.account_service import AccountService


class VirtualAccount:
    """向后兼容层 — 内部转发到 AccountService
    
    @deprecated 使用 AccountService 代替
    """
    
    def __init__(self, account_id: str = "virtual_2026"):
        warnings.warn(
            "VirtualAccount is deprecated, use AccountService instead",
            DeprecationWarning,
            stacklevel=2
        )
        self._service = AccountService(account_id)
    
    def buy(self, symbol: str, name: str, price: float, quantity: int, **kwargs):
        return self._service.buy(symbol, name, price, quantity, **kwargs)
    
    def sell(self, symbol: str, price: float, quantity: int, **kwargs):
        return self._service.sell(symbol, price, quantity, **kwargs)
    
    def get_balance(self):
        return self._service.get_balance()
    
    def get_positions(self):
        return self._service.get_positions()
    
    # ... 其他方法转发
```

---

## 6. 迁移检查清单

### Batch 1 (P0)
- [ ] daily_trading.py — import + 类名 + source_module
- [ ] daily_trading_fixed.py — import + 类名 + source_module
- [ ] manual_trade_today.py — import + 类名 + source_module
- [ ] execute_trading.py — 删除 FeishuVirtualAccount，改用 AccountService + FeishuSyncService
- [ ] 测试: `pytest examples/alpha_research/tests/ -k "daily_trading or manual_trade"`

### Batch 2 (P1)
- [ ] risk_check.py — import + 类名
- [ ] generate_reports.py — import + 类名
- [ ] comprehensive_attribution.py — import + 类名
- [ ] performance_attribution.py — import + 类名
- [ ] realtime_monitor.py — 删除自行计算，改用 get_balance()
- [ ] rebalance_portfolio.py — 删除自行计算，改用 get_balance()
- [ ] 测试: `pytest examples/alpha_research/tests/ -k "risk or report or attribution"`

### Batch 3 (P2)
- [ ] limit_up_strategy_runner.py — import + 类名
- [ ] limit_up_leaders_20260415.py — import + 类名
- [ ] limit_up_leaders_20260416.py — import + 类名
- [ ] daily_portfolio_update.py — import + 类名
- [ ] paper_trading_demo.py — import + 类名
- [ ] main.py — import + 类名
- [ ] advanced_trading_features.py — import + 类名
- [ ] simulated_trading.py — 删除自实现，改用 AccountService
- [ ] execute_stock_selection.py — 删除自行计算，改用 get_balance()
- [ ] debug_virtual_account.py — import + 类名
- [ ] 测试: `pytest examples/alpha_research/tests/`

### 兼容层
- [ ] 创建 accounts/virtual_account_compat.py
- [ ] 更新 examples/alpha_research/virtual_account.py — 转发到兼容层
- [ ] 测试: 旧代码仍可运行

---

## 7. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 迁移后功能异常 | 每批次迁移后运行完整测试 |
| 飞书同步失败 | FeishuSyncService 失败仅记录日志，不影响交易 |
| 性能下降 | AccountService 使用 SQLite WAL，性能与 VirtualAccount 相当 |
| 遗漏调用方 | grep 扫描所有 import，建立完整清单 |

---

## 8. 验收标准

Phase 3 完成条件：

- [ ] 所有 20 个调用方迁移到 AccountService
- [ ] VirtualAccount 保留为兼容层（@deprecated）
- [ ] 所有测试通过
- [ ] 无功能回归
- [ ] 飞书同步正常
