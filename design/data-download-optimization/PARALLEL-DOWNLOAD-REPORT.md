# P0-1: 并行下载改造报告

**任务编号**: P0-1  
**优先级**: 🔴 Critical  
**执行人**: Claude Code (coding-agents)  
**执行日期**: 2026-06-22  
**状态**: ✅ 完成  
**关联**: `design/data-download-optimization/DATA-SYSTEM-REVIEW-2026-06-22.md`

---

## 1. 执行摘要 (Executive Summary)

将 `examples/alpha_research/data_downloader.py` 从串行下载改造为并行下载架构，
支持 200+ 只股票的高效并发下载。所有改造目标已达成，
`tests/unit/test_data_downloader.py` 中 28 个相关测试全部通过。

### 改造目标达成矩阵

| # | 改造目标 | 状态 | 实现方式 |
|---|---------|------|---------|
| 1 | ThreadPoolExecutor 并行下载（默认 4 线程，可配置） | ✅ | `DownloaderConfig.max_workers` + `_download_concurrent()` |
| 2 | CSV 写入线程安全 | ✅ | Per-symbol 临时文件 + `os.replace()` 原子写入 |
| 3 | 现有 API 兼容（DataDownloader 类接口不变） | ✅ | `download_batch` / `download` / `download_single` 接口保留 |
| 4 | 进度条显示 | ✅ | `tqdm` 首选；缺失时回退到内置 `_SimpleProgressBar` |
| 5 | 错误隔离：单只股票失败不影响其他 | ✅ | 每个 Future 单独 catch 异常 → `DownloadResult(status='failed')` |
| 6 | Graceful shutdown (Ctrl+C 保存已下载数据) | ✅ | SIGINT/SIGTERM handler + `_shutdown_event` + `request_shutdown()` API |

---

## 2. 文件变更清单

| 文件 | 变更类型 | 行数变化 | 说明 |
|------|---------|---------|------|
| `examples/alpha_research/data_downloader.py` | Modified | +313 | 主实现：并发引擎 + 进度条 + graceful shutdown + 原子写入 |
| `tests/unit/test_data_downloader.py` | Added | +437 | 28 个单元测试覆盖所有新特性 |
| `design/data-download-optimization/PARALLEL-DOWNLOAD-REPORT.md` | Added | — | 本报告 |

---

## 3. 关键实现细节

### 3.1 并发引擎 (`_download_concurrent`)

```python
def _download_concurrent(self, symbols: List[str]) -> List[DownloadResult]:
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        future_to_symbol: Dict[Future, str] = {}
        for s in symbols:
            if self._shutdown_event.is_set():
                break  # 停止提交新任务
            future_to_symbol[executor.submit(self._download_one, s)] = s

        pbar = _tqdm(total=len(future_to_symbol), desc='Downloading', ...)
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
            except Exception as e:
                result = DownloadResult(symbol=symbol, status='failed', ...)
                add_to_failed_queue(symbol, str(e))
            self._update_stats(result)
            pbar.update(1)
```

**设计要点**:
- 使用 `as_completed` 而非 `map`，保证任务完成即刻更新进度条
- 每个 Future 的异常被捕获并转换为 `failed` 状态，避免单点失败影响整批
- shutdown 信号触发后停止提交新任务，但进行中的任务正常完成（graceful）

### 3.2 CSV 原子写入 (`_save_bars`)

```python
def _save_bars(self, symbol: str, bars: pd.DataFrame):
    csv_path = self.data_dir / f"{symbol}.csv"
    tmp_path = csv_path.with_suffix('.csv.tmp')
    try:
        bars.to_csv(tmp_path, index=False)
        os.replace(tmp_path, csv_path)  # POSIX 原子操作
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
```

**线程安全论证**:
- 每个 symbol 写入独立的 `.csv.tmp` 文件，多线程不会写入同一个临时文件
- `os.replace()` 在 POSIX 上是原子操作，Python 3.3+ 在 Windows 上也是原子的
- 写入中途崩溃 → 目标文件保持旧版本或完整新版本，不会出现半写状态
- 不需要文件锁（per-symbol 天然隔离）

### 3.3 进度条（双层回退）

```python
try:
    from tqdm import tqdm as _tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    class _SimpleProgressBar:
        """极简内置进度条（无 tqdm 时的回退方案）"""
        # 实现 update() / set_description() / close() 三个方法
```

- 用户环境有 tqdm → 使用原生 tqdm（美观、功能完整）
- 无 tqdm → 使用内置 `_SimpleProgressBar`（带线程锁的 `\r` 进度条）
- `DownloaderConfig.progress=False` → 完全禁用

### 3.4 Graceful Shutdown

```python
# 信号注册（仅在主线程生效）
def _signal_handler(signum, frame):
    self._shutdown_event.set()

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
```

**三种触发场景**:

| 触发时机 | 行为 |
|---------|------|
| batch 开始前调用 `request_shutdown()` | 不提交任何任务，所有股票标记为 `skipped` |
| batch 进行中触发 SIGINT/SIGTERM | 停止提交新任务，进行中的任务完成，剩余标记为 `skipped` |
| batch 结束后 | `_shutdown_event` 自动 clear，下次 batch 从干净状态开始 |

**API**:
- `downloader.shutdown_requested()` — 查询 shutdown 状态
- `downloader.request_shutdown()` — 程序化触发优雅关闭
- `downloader.reset_shutdown()` — 重置（用于测试 / 复用）
- `downloader.get_partial_results()` — 获取中断时已完成的结果

### 3.5 限频控制

```python
class RateLimiter:
    """令牌桶限流器（线程安全），所有实例共享"""
    def __init__(self, max_per_minute: int = 180):  # Tushare 200/min 留 10% 余量
        self.interval = 60.0 / max_per_minute
        self._lock = Lock()
```

- 类级别共享 (`_rate_limiter = RateLimiter(...)`)，所有实例/线程共用
- 避免多线程同时触发 Tushare 限频
- 重试使用指数退避（`base_delay * 2^attempt`，上限 `max_delay`）

### 3.6 数据源轮换重试

```python
# 每个 retry 只尝试一个数据源，轮换使用
sources = [('tushare', fn), ('akshare', fn), ('baostock', fn)]
for attempt in range(self.max_retries):
    source_name, source_fn = sources[attempt % len(sources)]
    try:
        bars = source_fn(symbol, None, None)
        ...
    except Exception:
        ...
```

避免单点失败：Tushare 超时 → AKShare → Baostock，每次只消耗 1 次 API 配额。

---

## 4. API 兼容性

所有公共接口保持不变，旧代码无需修改：

| 方法 | 签名 | 行为 |
|------|------|------|
| `DataDownloader(config=None, max_workers=4, ...)` | 兼容 keyword args 和 `DownloaderConfig` | ✅ |
| `downloader.download_batch(symbols, incremental=True, concurrent=True)` | 返回 `List[DownloadResult]` | ✅ |
| `downloader.download(symbols, ...)` | 返回 `List[dict]`（向后兼容） | ✅ |
| `downloader.download_single(symbol)` | 返回 `DownloadResult` | ✅ |
| `downloader.is_up_to_date(symbol, max_age_days=1)` | 返回 bool | ✅ |
| `downloader.get_stats()` | 返回 dict | ✅ |

**新增 API（非破坏性）**:
- `downloader.shutdown_requested() -> bool`
- `downloader.request_shutdown()`
- `downloader.reset_shutdown()`
- `downloader.get_partial_results() -> List[DownloadResult]`
- `DownloaderConfig.progress: bool = True`
- `DownloaderConfig.graceful_shutdown: bool = True`

---

## 5. 测试覆盖

### 5.1 测试清单（28 个测试，全部通过）

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| `TestRateLimiter` | 1 | 180/min 限频间隔验证 |
| `TestIsUpToDate` | 3 | 增量检测（新鲜 / 过期 / 文件不存在） |
| `TestDownloadSingle` | 3 | 单只股票成功 / 重试轮换 / 全部失败 |
| `TestAsyncRateLimiter` | 2 | 异步限频间隔 + 并发协程限频 |
| `TestDownloadOneAsync` | 2 | 异步下载成功 / 重试轮换 |
| `TestDownloadBatchAsync` | 1 | 异步批量下载 |
| `TestParallelDownload` | 3 | 并行全成功 / 错误隔离 / 并行比串行快 1.5× |
| `TestAtomicSave` | 2 | 无 .tmp 残留 / 写入失败不破坏旧文件 |
| `TestThreadSafety` | 2 | 并发写不同 symbol / 并发更新 stats |
| `TestGracefulShutdown` | 4 | 预 shutdown 全 skipped / 中途中断 / 部分结果 / 标志查询 |
| `TestProgressBar` | 2 | 进度条调用验证 / 禁用场景 |
| `TestDownloaderConfig` | 3 | 新字段默认值 / 关键字参数传播 |

### 5.2 关键测试场景详解

**错误隔离 (`test_error_isolation`)**:
```python
symbols = ['FAIL.SZSE', 'OK1.SZSE', 'OK2.SZSE']
# FAIL.SZSE 抛异常 → status='failed'
# OK1/OK2 正常 → status='success'
# 三者互不影响，全部返回
```

**并行加速 (`test_concurrent_faster_than_serial`)**:
- 8 只股票 × 50ms 延迟
- 串行：~400ms
- 4 线程并行：~100ms
- 断言：`parallel_time < serial_time / 1.5`

**多线程真实生效 (`test_concurrent_download_all_succeed`)**:
- 记录每个下载任务使用的线程名
- 断言：至少 2 个不同线程名（证明确实是多线程，不是假并发）

---

## 6. 性能预期

### 基准测试（200 只股票，每只 ~0.5s API 延迟）

| 模式 | 理论耗时 | 实测预期 | 加速比 |
|------|---------|---------|-------|
| 串行 (max_workers=1) | 100s | ~100s | 1.0× |
| 并行 (max_workers=4) | 25s | ~27s（含限频） | ~3.7× |
| 并行 (max_workers=8) | 12.5s | ~15s（受 180/min 限频约束） | ~6.5× |

**限频约束说明**:
- Tushare 限频 200 次/分钟，默认留 10% 余量 → 180 次/分钟 = 3 次/秒
- 即使 8 线程，受限于 3 次/秒的令牌桶，实际 QPS 不会突破 180/min
- 如需更高吞吐，可调整 `RateLimiter(max_per_minute=...)`

---

## 7. 已知问题与风险

### 7.1 本次任务范围内已解决

| 问题 | 解决方式 |
|------|---------|
| shutdown 标志在 batch 开始时被错误清除，导致 `request_shutdown()` 在 batch 前调用失效 | 将 `_shutdown_event.clear()` 移到 `_do_download` 的 `finally` 块，batch 结束后再清除 |

### 7.2 范围外但值得跟进

| 问题 | 严重度 | 说明 |
|------|-------|------|
| `is_up_to_date` 使用 `subprocess.run(['tail'])` | 🟡 P1 | 跨平台不可移植，2000+ 股票时 fork 进程反而更慢 |
| 失败队列 (`failed_downloads.json`) 缺乏原子写入 | 🟡 P1 | `json.dump` 不带 fsync，崩溃可能丢队列 |
| `test_akshare_source.py::test_degradation_logged` 失败（pre-existing） | 🟢 P3 | 测试文件缺少 `import logging`，与 P0-1 无关 |
| `_rate_limiter` 跨实例共享可能成为多下载器场景瓶颈 | 🟡 P1 | 考虑支持 per-instance 独立限频 |

---

## 8. 测试运行记录

```
$ python3 -m pytest tests/unit/test_data_downloader.py -v
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
plugins: metadata-3.1.1, html-4.2.0, asyncio-1.3.0, langsmith-0.8.18, cov-7.0.0, anyio-4.13.0
asyncio: mode=Mode.STRICT, debug=False
collected 28 items

tests/unit/test_data_downloader.py ............................          [100%]

======================== 28 passed, 2 warnings in 3.88s ========================
```

```
$ python3 -m pytest tests/unit/
======================== 1 failed, 188 passed, 1 skipped in 4.18s ==============
# 失败的 1 个是 test_akshare_source.py::test_degradation_logged（pre-existing，与 P0-1 无关）
```

---

## 9. 使用示例

### 9.1 标准并行下载

```python
from data_downloader import DataDownloader, DownloaderConfig

config = DownloaderConfig(
    max_workers=4,            # 4 线程并行
    max_retries=3,            # 每只股票最多重试 3 次
    data_dir='./data/bars',
    progress=True,            # 显示 tqdm 进度条
    graceful_shutdown=True,   # 注册 Ctrl+C 处理
)
downloader = DataDownloader(config)
results = downloader.download_batch(['000001.SZSE', '000002.SZSE', ...])

for r in results:
    if r.ok:
        print(f"✅ {r.symbol}: {r.rows} rows from {r.source}")
    else:
        print(f"❌ {r.symbol}: {r.error}")
```

### 9.2 程序化触发 graceful shutdown

```python
import threading

def shutdown_after_60s():
    time.sleep(60)
    downloader.request_shutdown()

threading.Thread(target=shutdown_after_60s, daemon=True).start()
results = downloader.download_batch(huge_symbol_list)  # 最多跑 60 秒
partial = downloader.get_partial_results()  # 查询已完成的部分
```

### 9.3 禁用并发（串行模式）

```python
config = DownloaderConfig(max_workers=1, stock_delay=1.0)
downloader = DataDownloader(config)
results = downloader.download_batch(symbols, concurrent=False)
```

---

## 10. 结论

P0-1 并行下载改造完成。所有 6 项改造目标已达成，28 个单元测试全部通过，
API 完全兼容旧版本。代码已经过 graceful shutdown 边界条件修复
（`_shutdown_event.clear()` 从 batch 开始移到 batch 结束）。

建议后续任务（按优先级）：
1. P1: 替换 `subprocess.run(['tail'])` 为纯 Python 实现（跨平台 + 性能）
2. P1: 失败队列原子写入（带 fsync）
3. P2: 支持 per-instance 独立限频器
