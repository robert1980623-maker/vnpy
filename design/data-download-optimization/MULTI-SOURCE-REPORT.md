# P0-2: AKShare 多数据源支持实施报告

> **任务编号**: P0-2  
> **实施日期**: 2026-06-22  
> **实施状态**: ✅ 完成  
> **测试结果**: 201 passed, 1 skipped, 0 failed

---

## 1. 背景与目标

### 问题描述
原系统仅依赖 Tushare 单一数据源，存在单点故障风险。Tushare API 不可用时，整个数据下载流程瘫痪。

### 改造目标
1. ✅ 新增 `AKShareDataSource` 类（继承 `DataSource` 基类）
2. ✅ 实现数据源降级策略：Tushare 失败 → 自动切换 AKShare
3. ✅ 配置化数据源优先级（`config.yaml` 中可配置）
4. ✅ 统一数据格式输出（AKShare 数据转换为标准格式）
5. ✅ 添加数据源健康检查（ping/可用性检测）
6. ✅ 日志记录数据源切换事件

---

## 2. 架构设计

### 2.1 核心类层次

```
DataSource (ABC)
├── TushareDataSource (priority=1, 最高优先)
│   └── ts.pro_api().daily() → 标准格式
├── AKShareDataSource (priority=2, 备选)
│   └── ak.stock_zh_a_hist() → 标准格式
└── [可扩展] BaostockDataSource, ...

MultiSourceManager
├── register_source(source)
├── fetch(symbol, start_date, end_date) → (DataFrame, source_name)
├── health_check_all() → Dict[str, bool]
└── get_status() → Dict[str, Dict]

DataDownloader (已集成)
├── _source_manager: Optional[MultiSourceManager]
├── _download_one(symbol) → DownloadResult
│   ├── 优先: MultiSourceManager.fetch()
│   └── 回退: 传统数据源轮转 (get_stock_bars_*)
├── get_source_status() → Dict
└── health_check_sources() → Dict
```

### 2.2 数据流

```
用户请求 download_batch(['000001.SZSE', ...])
    ↓
DataDownloader._download_one('000001.SZSE')
    ↓
[配置了 MultiSourceManager?]
    ├─ Yes → MultiSourceManager.fetch()
    │         ├─ 按 priority 排序: Tushare(1) → AKShare(2)
    │         ├─ Tushare 成功 → 返回 (df, 'tushare')
    │         ├─ Tushare 失败 → WARNING 日志 "数据源降级: tushare → akshare"
    │         ├─ AKShare 成功 → 返回 (df, 'akshare')
    │         └─ 全部失败 → (None, 'none')
    │              ↓
    │         [MultiSourceManager 返回 None?]
    │              ├─ Yes → 回退到传统数据源轮转
    │              └─ No → 保存 CSV, 返回 DownloadResult
    │
    └─ No → 传统数据源轮转 (原有逻辑，100% 向后兼容)
              ├─ attempt 1: Tushare (get_stock_bars_tushare)
              ├─ attempt 2: AKShare (get_stock_bars_akshare)
              └─ attempt 3: Baostock (get_stock_bars_baostock)
```

### 2.3 标准数据格式

所有数据源输出统一为标准列名：

```python
STANDARD_COLUMNS = ['datetime', 'open', 'high', 'low', 'close', 'volume']
```

| 数据源 | 原始列名 | 映射 |
|--------|----------|------|
| AKShare | 日期 → datetime, 开盘 → open, 最高 → high, 最低 → low, 收盘 → close, 成交量 → volume | 中文→英文 |
| Tushare | trade_date → datetime, vol → volume | 缩写→全称 |

---

## 3. 文件清单

### 3.1 新增文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `examples/alpha_research/akshare_source.py` | 561 | DataSource ABC + 实现 + Manager + 配置加载 |
| `examples/alpha_research/config.example.yaml` | 280 | 配置示例（含 data_sources 完整文档） |
| `tests/unit/test_akshare_source.py` | 536 | 34+ 测试用例（全量 mock，不依赖外部服务） |
| `design/data-download-optimization/MULTI-SOURCE-REPORT.md` | 本文件 | 实施报告 |

### 3.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `examples/alpha_research/data_downloader.py` | 集成 MultiSourceManager（新增 ~120 行） |
| `examples/alpha_research/config.yaml` | 新增 `data_sources` 配置段 |
| `tests/unit/test_data_downloader.py` | 新增 TestMultiSourceIntegration 测试类（~180 行） |
| `tests/unit/test_akshare_source.py` | 修复缺失的 `import logging` |

---

## 4. 关键实现细节

### 4.1 DataSource 抽象基类

```python
class DataSource(ABC):
    def __init__(self, name: str, priority: int = 10, enabled: bool = True):
        self.name = name
        self.priority = priority
        self.enabled = enabled
        # EMA 平滑的健康度指标
        self._success_rate: float = 1.0
        self._avg_response_ms: float = 0.0
        self._consecutive_failures: int = 0
        self._healthy: bool = True

    @abstractmethod
    def fetch_daily_bars(self, symbol, start_date, end_date) -> Optional[pd.DataFrame]: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    def record_success(self, response_ms: float) -> None:  # EMA α=0.1
    def record_failure(self, error: str = '') -> None:      # 3 次连续失败 → unhealthy
    def get_status(self) -> Dict: ...
    def reset(self) -> None: ...
```

### 4.2 降级策略

- **优先级排序**: 按 `priority` 升序尝试（数值越小优先级越高）
- **熔断机制**: 连续失败 ≥ `failure_threshold`（默认 3）次后自动跳过该数据源
- **自动恢复**: 熔断后等待 `recovery_timeout`（默认 300 秒）自动恢复
- **日志记录**: 数据源切换时输出 WARNING 日志 `"数据源降级: tushare → akshare (symbol=000001.SZSE)"`

### 4.3 配置化

```yaml
data_sources:
  sources:
    tushare:
      priority: 1          # 数值越小优先级越高
      enabled: true        # 无 TUSHARE_TOKEN 时自动禁用
      token_env: TUSHARE_TOKEN
    akshare:
      priority: 2
      enabled: true
  health_check:
    interval_seconds: 300
    failure_threshold: 3    # 连续失败 N 次后熔断
    recovery_timeout: 300
  failover:
    auto_switch: true
    log_switch_event: true  # 记录降级日志
```

### 4.4 健康检查

```python
# AKShare: 获取 000001 最近 1 天数据
def health_check(self) -> bool:
    df = ak.stock_zh_a_hist(symbol='000001', period='daily',
                            start_date=today, end_date=today, adjust='qfq')
    return True  # API 可达即为健康（非交易日返回空也算正常）

# Tushare: 查询指数日线
def health_check(self) -> bool:
    df = self._pro.index_daily(ts_code='000001.SH',
                               start_date=today, end_date=today)
    return True
```

### 4.5 向后兼容

DataDownloader 的多数据源支持是**可选增强**：

| 场景 | 行为 |
|------|------|
| 配置了 `source_manager` | 优先使用 MultiSourceManager，失败时回退到传统轮转 |
| 配置了 `source_config_path` | 自动创建 MultiSourceManager |
| 未配置任何多源参数 | 传统数据源轮转（100% 原有行为） |

---

## 5. 使用方式

### 5.1 基础使用（无多源管理）

```python
from data_downloader import DataDownloader, DownloaderConfig

config = DownloaderConfig(max_workers=4)
downloader = DataDownloader(config)
results = downloader.download_batch(['000001.SZSE', '000002.SZSE'])
```

### 5.2 使用 MultiSourceManager（推荐）

```python
from data_downloader import DataDownloader, DownloaderConfig
from akshare_source import create_default_manager

# 从 config.yaml 自动加载配置
manager = create_default_manager()
config = DownloaderConfig(max_workers=4, source_manager=manager)
downloader = DataDownloader(config)

# 下载（自动降级）
results = downloader.download_batch(['000001.SZSE'])

# 查看数据源状态
print(downloader.get_source_status())
# {'tushare': {'healthy': True, 'success_rate': 0.95, ...},
#  'akshare': {'healthy': True, 'success_rate': 1.0, ...}}

# 健康检查
print(downloader.health_check_sources())
# {'tushare': True, 'akshare': True}
```

### 5.3 自定义配置

```python
from akshare_source import MultiSourceManager, AKShareDataSource, TushareDataSource

config = {
    'sources': {
        'akshare': {'priority': 1, 'enabled': True},   # AKShare 优先
        'tushare': {'priority': 2, 'enabled': True},
    },
    'health_check': {'failure_threshold': 5},
    'failover': {'auto_switch': True, 'log_switch_event': True},
}

manager = MultiSourceManager(config)
manager.register_source(AKShareDataSource(priority=1))
manager.register_source(TushareDataSource(priority=2))
```

---

## 6. 测试覆盖

### 6.1 测试统计

| 测试文件 | 测试用例数 | 通过 | 覆盖场景 |
|----------|-----------|------|----------|
| `test_akshare_source.py` | 35 | 35 | DataSource 基类、AKShare/Tushare 数据源、MultiSourceManager、配置加载、集成场景 |
| `test_data_downloader.py` | 40 | 40 | 限频、增量检测、下载重试、并行、原子写入、线程安全、graceful shutdown、**MultiSource 集成** |
| **总计** | **201** | **201** | **全部通过** |

### 6.2 关键测试场景

- ✅ DataSource 基类 EMA 平滑、失败计数、熔断
- ✅ AKShare 列名标准化（中文 → 英文）
- ✅ Tushare 无 token 自动禁用
- ✅ MultiSourceManager 优先级选择、降级、熔断跳过
- ✅ 降级事件 WARNING 日志
- ✅ DataDownloader + MultiSourceManager 集成
- ✅ Manager 失败时回退到传统数据源轮转
- ✅ `multi_source` 统计计数
- ✅ `get_source_status()` / `health_check_sources()` API
- ✅ 向后兼容：无 manager 时行为不变

---

## 7. 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| AKShare API 变更 | 低 | `_standardize()` 集中处理列名映射，变更时只需修改一处 |
| MultiSourceManager 异常 | 低 | try/except 包裹，异常时自动回退到传统数据源轮转 |
| 性能影响 | 极低 | Manager 为内存操作，无额外 I/O；降级日志仅在切换时触发 |
| 配置缺失 | 无 | `DEFAULT_CONFIG` 兜底，`load_source_config()` 找不到文件时返回默认值 |

---

## 8. 后续扩展建议

1. **BaostockDataSource**: 在 `akshare_source.py` 中新增 Baostock 数据源类（当前仅通过传统轮转支持）
2. **定时健康检查**: 后台线程定期调用 `health_check_all()`，自动更新数据源健康状态
3. **数据源权重**: 除优先级外，引入权重机制（如 80% Tushare + 20% AKShare 用于交叉验证）
4. **告警通知**: 数据源降级超过阈值时发送飞书/邮件通知
5. **数据源缓存**: 对健康检查结果做 TTL 缓存，避免频繁 ping

---

## 9. 结论

P0-2 AKShare 多数据源支持已完成全部 6 项改造目标：

| # | 目标 | 状态 |
|---|------|------|
| 1 | 新增 AKShareDataSource 类（继承 DataSource 基类） | ✅ |
| 2 | 实现数据源降级策略：Tushare 失败 → 自动切换 AKShare | ✅ |
| 3 | 配置化数据源优先级（config.yaml 中可配置） | ✅ |
| 4 | 统一数据格式输出（AKShare 数据转换为标准格式） | ✅ |
| 5 | 添加数据源健康检查（ping/可用性检测） | ✅ |
| 6 | 日志记录数据源切换事件 | ✅ |

全部 201 个单元测试通过，0 个失败。

---

**实施者**: Claude Code (P0-2)  
**审核**: 待 Chief Architect 审核  
**日期**: 2026-06-22
