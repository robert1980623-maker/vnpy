# VNPY 核心模块修复计划

> **编制人:** Atlas (Chief Architect)
> **日期:** 2026-04-13
> **来源:** 深度代码审查报告（11 模块 / 3,670 行 / 4 致命 + 7 高危 + 19 警告）
> **目标:** 4 周内将系统评分从 78 → 90+

---

## 📋 总览

| 阶段 | 时间 | 任务数 | 目标 |
|------|------|--------|------|
| P0 | 第 1 周 | 4 | 消除所有致命问题，恢复系统可信度 |
| P1 | 第 1-2 周 | 6 | 修复高危问题，提升稳定性和性能 |
| P2 | 第 3-4 周 | 5 | 架构优化，中长期改进 |

---

## 🔴 P0 — 立即修复（第 1 周）

### P0-1: Delta Consumer 假修复问题

**严重度:** 🔴 致命 | **影响:** 100% | **文件:** `delta_consumer.py`

**问题:** `invoke_delta_fix()` 对 14 种错误类型全部返回 `True` + 描述文本，但从不修改任何代码。
系统标记问题为 resolved，实际 bug 原封不动。

**修复方案:**

**方案 A — 重命名为诊断器（推荐，快速）**
```python
# 修改前
def invoke_delta_fix(self, task) -> tuple[bool, str]:
    return True, "已添加 None 值检查"  # 假的

# 修改后
def diagnose_error(self, task) -> tuple[str, str, float]:
    """诊断错误类型，返回修复建议（不执行修复）"""
    return fix_type, suggestion, confidence
```
- 返回值改为 `(diagnosis, suggestion, confidence)`
- Issue 状态标记为 `diagnosed` 而非 `resolved`
- 需要人工确认或接入真正的修复工具后才标记 `resolved`

**方案 B — 接入真实修复工具（中期）**
- 集成 Aider 或 OpenDevin 作为后端
- `invoke_delta_fix()` 实际执行 AST diff + patch apply
- 工作量更大，需要 2-3 天

**验收标准:**
- [ ] `invoke_delta_fix` 不再返回假的 "已修复"
- [ ] Issue 状态机增加 `diagnosed` 状态
- [ ] 所有 delta 任务必须有对应的真实修复动作才能标记 resolved

**预估工时:** 方案 A: 2h | 方案 B: 3d
**建议团队:** 后端工程组（1 人）

---

### P0-2: 文件锁 — 消除并发数据丢失

**严重度:** 🔴 致命 | **影响:** 高 | **文件:** `delta_consumer.py`, `manager_interface.py`, `issue_queue.py`

**问题:** 三个模块通过 JSON 文件通信，无锁。读→改→写是 race condition，高并发下任务丢失。

**修复方案:**

```python
import fcntl

class FileLock:
    """跨平台文件锁（Windows fallback 到 Lock 对象）"""
    @staticmethod
    def locked_write(filepath, data):
        with open(filepath, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(data, f, ensure_ascii=False, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def locked_read(filepath):
        if not filepath.exists():
            return None
        with open(filepath, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return data
```

**修改范围:**
| 文件 | 修改点 |
|------|--------|
| `delta_consumer.py` | `load_tasks()` / `save_tasks()` |
| `manager_interface.py` | `dispatch_to_delta()` 的读→改→写 |
| `issue_queue.py` | `update_status()` 的文件移动 |

**验收标准:**
- [ ] 所有 JSON 文件读写使用 `FileLock`
- [ ] 并发测试（2 个实例同时写入）无数据丢失
- [ ] 超时锁释放机制（避免死锁）

**预估工时:** 4h
**建议团队:** 后端工程组（1 人）
**依赖:** 无

---

### P0-3: Industry Rotation 策略无法运行

**严重度:** 🔴 致命 | **影响:** 100% | **文件:** `alpha/strategy/industry_rotation.py`

**问题:** `__init__` 签名与基类 `StockScreenerStrategy` 完全不匹配，实例化即崩溃。

**修复方案:**

```python
class IndustryRotationStrategy(StockScreenerStrategy):
    def __init__(
        self,
        name: str = "Industry Rotation",
        max_positions: int = 10,
        position_size: float = 0.1,
        rebalance_days: int = 20,
        industry_data: Dict[str, List[str]] = None,
    ):
        # ✅ 修复：正确调用基类 __init__
        super().__init__(name, max_positions, position_size, rebalance_days)
        self._industry_data = industry_data or INDUSTRY_STOCKS
```

**验收标准:**
- [ ] `IndustryRotationStrategy()` 可正常实例化
- [ ] 可接入 Cross-Sectional Engine 执行回测
- [ ] 单元测试覆盖实例化和基础筛选

**预估工时:** 1h
**建议团队:** 策略研究组（1 人）
**依赖:** 无

---

### P0-4: Industry Rotation 估值数据伪造

**严重度:** 🔴 致命 | **影响:** 100% | **文件:** `alpha/strategy/industry_rotation.py`

**问题:** PE/PB 用 `hash()` 随机生成，回测结果完全不可信。

**修复方案:**

**短期方案（第 1 周）:**
```python
def _get_stock_valuation(self, vt_symbol: str):
    """从 Tushare/AKShare 获取真实估值数据"""
    # 优先使用 alpha/lab 缓存
    if vt_symbol in self._lab._fundamental_cache:
        report = self._lab._fundamental_cache[vt_symbol]
        return report.pe, report.pb
    
    # fallback: 从数据源拉取
    return self._fetch_valuation_from_source(vt_symbol)
```

**验收标准:**
- [ ] 不再使用 `hash()` 生成估值
- [ ] 估值数据可追溯到真实来源
- [ ] 回测结果与手动计算偏差 < 1%

**预估工时:** 4h
**建议团队:** 策略研究组（1 人）
**依赖:** 数据下载模块正常

---

## 🟡 P1 — 短期修复（第 1-2 周）

### P1-1: 统一配置管理

**严重度:** 🟡 高 | **文件:** 全项目

**问题:** 所有配置散落各处（`max_retries=3` 硬编码在两个位置等）。

**修复方案:**

```yaml
# vnpy_config.yaml
delta_consumer:
  max_retries: 3
  max_history: 100
  poll_interval: 30

manager:
  default_timeout_minutes: 30
  poll_interval: 5

alert:
  notify_threshold: 3
  channels:
    - type: feishu
      target: "user:ou_xxx"
    - type: slack
      target: "U0AHSM009ML"

glm_analyzer:
  timeout: 30
  fallback_confidence: 0.5
  model_url: "http://localhost:1234/v1/chat/completions"
```

```python
# config.py
from pathlib import Path
import yaml

_config_cache = None

def get_config():
    global _config_cache
    if _config_cache is None:
        config_path = Path(__file__).parent / "vnpy_config.yaml"
        with open(config_path) as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache
```

**验收标准:**
- [ ] 所有硬编码常量迁移到 `vnpy_config.yaml`
- [ ] 新增 `get_config()` 统一读取入口
- [ ] 配置变更无需修改代码

**预估工时:** 3h
**建议团队:** 后端工程组（1 人）
**依赖:** P0-2（文件锁）

---

### P1-2: 修复 retry_count 双重计数

**严重度:** 🟡 高 | **文件:** `delta_consumer.py`

**问题:** 每次失败重试，retry_count 被加了 2 次。

**修复方案:**
```python
def process_task(self, task):
    # ❌ 修改前：在 status=failed 分支里又 +1
    if task['status'] == 'failed':
        task['retry_count'] += 1
    
    success, message = self.invoke_delta_fix(task)
    if not success:
        task['retry_count'] += 1  # ← 重复加
        task['status'] = 'pending'
    
    # ✅ 修改后：只在一处 +1
    task['retry_count'] += 1
    success, message = self.invoke_delta_fix(task)
    if not success:
        task['status'] = 'pending'
```

**验收标准:**
- [ ] 失败 3 次后 retry_count = 3（不是 6）
- [ ] `max_retries` 检查使用统一的配置值

**预估工时:** 30min
**建议团队:** 后端工程组（1 人）
**依赖:** P0-1

---

### P1-3: 统一时区处理

**严重度:** 🟡 高 | **文件:** `manager_interface.py`, `delta_consumer.py`

**问题:** `datetime.now()` (naive) 与 `datetime.fromisoformat()` (可能 aware) 混用，Python 3.12+ 会抛 TypeError。

**修复方案:**
```python
from datetime import datetime, timezone

# 全局统一
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_local() -> datetime:
    return datetime.now().astimezone()
```

**修改范围:**
- `manager_interface.py` — `check_timeout()` 中的 `datetime.now()`
- `delta_consumer.py` — 所有时间戳生成
- `alpha/lab.py` — `get_trading_dates()` 中的日期计算

**验收标准:**
- [ ] 全项目搜索 `datetime.now()` 全部替换
- [ ] Python 3.12+ 环境测试无 TypeError

**预估工时:** 2h
**建议团队:** 后端工程组（1 人）

---

### P1-4: Cross-Sectional Engine _get_price 索引优化

**严重度:** 🟡 高 | **文件:** `alpha/strategy/cross_sectional_engine.py`

**问题:** 每天 × 每只股票线性搜索 bars → O(days × stocks × avg_bars)。

**修复方案:**
```python
class CrossSectionalEngine:
    def _build_price_index(self):
        """回测开始时构建 {date: {symbol: price}} 索引"""
        self._price_index: Dict[date, Dict[str, float]] = {}
        for symbol, bars in self._all_bars.items():
            for bar in bars:
                d = bar.datetime.date()
                if d not in self._price_index:
                    self._price_index[d] = {}
                self._price_index[d][symbol] = bar.close_price
    
    def _get_price(self, symbol: str, date: date) -> float:
        return self._price_index.get(date, {}).get(symbol)
```

**验收标准:**
- [ ] 回测速度提升 > 10x
- [ ] 回测结果与优化前一致

**预估工时:** 2h
**建议团队:** 量化工程组（1 人）

---

### P1-5: 缓存 TTL/LRU 限制

**严重度:** 🟡 高 | **文件:** `alpha/lab.py`, `alert_notifier.py`

**问题:** `_bars_cache` / `_fundamental_cache` / `pending_alerts` 无限增长。

**修复方案:**
```python
from functools import lru_cache
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size: int = 1000):
        self._cache = OrderedDict()
        self._max_size = max_size
    
    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
```

**验收标准:**
- [ ] 缓存大小不超过配置上限
- [ ] 长时间运行内存稳定

**预估工时:** 2h
**建议团队:** 后端工程组（1 人）

---

### P1-6: 回测仓位计算修复

**严重度:** 🟡 高 | **文件:** `alpha/strategy/cross_sectional_engine.py`

**问题:** 始终用 `initial_capital` 计算目标仓位，盈利后仓位比例越来越小。

**修复方案:**
```python
def _rebalance(self, date):
    # ❌ 修改前
    target_amount = self.initial_capital * target_position_size
    
    # ✅ 修改后
    total_assets = self._cash + self._get_total_market_value()
    target_amount = total_assets * target_position_size
```

**验收标准:**
- [ ] 盈利后仓位比例保持稳定
- [ ] 回测收益曲线与修复前有明显差异（应更合理）

**预估工时:** 1h
**建议团队:** 量化工程组（1 人）

---

## 🟢 P2 — 中期优化（第 3-4 周）

### P2-1: Issue Queue 迁移 SQLite

**严重度:** 🟢 中 | **文件:** `issue_queue.py`

**问题:** `read_issue()` 遍历 4 个目录 × glob 所有 JSON，100+ issue 时性能退化。

**修复方案:**
```sql
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT,
    status TEXT,
    created_at TEXT,
    assigned_at TEXT,
    metadata TEXT
);
CREATE INDEX idx_status ON issues(status);
CREATE INDEX idx_severity ON issues(severity);
```

**验收标准:**
- [ ] `read_issue()` 从 O(n) 降为 O(1)
- [ ] 迁移脚本自动从 JSON 导入现有数据
- [ ] 向后兼容（JSON 模式可切换回）

**预估工时:** 1d
**建议团队:** 后端工程组（1 人）

---

### P2-2: 回测执行细节完善

**严重度:** 🟢 中 | **文件:** `alpha/strategy/cross_sectional_engine.py`

**缺失:**
- [ ] 涨跌停限制（A 股 ±10% / ST ±5% / 创业板 ±20%）
- [ ] 最小交易单位（100 股整数倍）
- [ ] 流动性限制（成交量不足时部分成交）
- [ ] T+1 交易规则
- [ ] 滑点模拟

**预估工时:** 2d
**建议团队:** 量化工程组（1 人）

---

### P2-3: 端到端集成测试

**严重度:** 🟢 中

**测试覆盖:**
- [ ] Delta Consumer 完整流程（发现 → 诊断 → 修复 → 验证）
- [ ] Manager 调度 + 执行 + 结果回收
- [ ] 回测引擎完整运行（选股 → 回测 → 统计）
- [ ] Industry Rotation 可实例化 + 可运行

**预估工时:** 1d
**建议团队:** QA 组（1 人）

---

### P2-4: 告警系统多渠道支持

**严重度:** 🟢 中 | **文件:** `alert_notifier.py`

**问题:** 通知目标硬编码，只有 Slack。

**修复方案:** 从配置读取，支持飞书 / 邮件 / Telegram / 企业微信。

**预估工时:** 2h
**建议团队:** 后端工程组（1 人）

---

### P2-5: 行业轮动股票池扩充

**严重度:** 🟢 中 | **文件:** `alpha/strategy/industry_rotation.py`

**问题:** `INDUSTRY_STOCKS` 只有 ~50 只股票，每行业 3-7 只，无法有效分散风险。

**修复方案:** 从申万行业分类 API 动态获取成分股列表。

**预估工时:** 1d
**建议团队:** 策略研究组（1 人）

---

## 📊 资源分配建议

| 团队 | 人员 | P0 任务 | P1 任务 | P2 任务 | 总工时 |
|------|------|---------|---------|---------|--------|
| **后端工程组** | 1-2 人 | P0-1, P0-2 | P1-1, P1-2, P1-3, P1-5 | P2-1, P2-4 | ~3d |
| **策略研究组** | 1 人 | P0-3, P0-4 | — | P2-5 | ~1.5d |
| **量化工程组** | 1 人 | — | P1-4, P1-6 | P2-2 | ~1.5d |
| **QA 组** | 1 人 | — | — | P2-3 | ~1d |

**总计:** ~7 人日（4 周完成）

---

## 🔍 验收里程碑

| 节点 | 时间 | 检查项 |
|------|------|--------|
| M1: P0 完成 | 第 1 周末 | 4 个致命问题全部修复，系统评分 78→85 |
| M2: P1 完成 | 第 2 周末 | 6 个高危问题修复，系统评分 85→88 |
| M3: P2 完成 | 第 4 周末 | 5 个中期优化完成，系统评分 88→90+ |
| M4: 回归测试 | 第 4 周末 | 全部端到端测试通过，无 regression |

---

## ⚠️ 风险提示

1. **P0-1 方案选择影响后续:** 如果选方案 B（接入真实修复工具），P0 工期延长 2 天，建议先用方案 A 止血
2. **P2-1 SQLite 迁移有数据丢失风险:** 必须保留 JSON 备份，迁移后验证数据完整性
3. **P2-2 回测细节可能改变现有策略结果:** 需要重新回测所有策略，可能发现策略本身需要调整

---

*本修复计划由 Atlas 编制，建议 Manager 审阅后按优先级派遣团队执行。*
