# VNPY 数据下载系统 Phase 3 — 审查修复

**作者**: Atlas (Chief Architect)  
**日期**: 2026-06-21  
**状态**: Ready for Implementation  
**基于**: Phase 2 代码审查报告

---

## 1. 问题清单

### 🔴 P0 — 必须修复

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | 增量检测读全量 CSV | `data_downloader.py:244` `pd.read_csv(csv_path)` | 200只股票读24万行只为看日期 |
| 2 | 重试策略浪费 API | `data_downloader.py:268-310` 每次 retry 尝试 3 个数据源 | 3×3×200=1800次调用 |
| 3 | 无限频控制 | `data_downloader.py:340-350` ThreadPoolExecutor 无限制 | 触发 Tushare 200/min 限频 |

### 🟡 P1 — 建议修复

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 4 | Neo4j 连接不复用 | `batch_download_enhanced.py:108-118` 每次创建新连接 | 200次连接/断开开销 |
| 5 | 数据目录路径不一致 | Downloader 存 `akshare/bars`，验证去 `tushare` 找 | 验证永远失败 |
| 6 | 股票格式不一致 | 默认列表 `['000630', ...]` vs `download_index_components` 返回 `'000630.SZSE'` | 文件匹配失败 |

---

## 2. 修复方案

### Fix 1: 增量检测优化

**当前**:
```python
def is_up_to_date(self, symbol: str, max_age_days: int = 1) -> bool:
    df = pd.read_csv(csv_path)  # 读全量
    last_date = pd.to_datetime(df[date_col].iloc[-1]).date()
```

**修复**:
```python
def is_up_to_date(self, symbol: str, max_age_days: int = 1) -> bool:
    csv_path = self.data_dir / f"{symbol}.csv"
    if not csv_path.exists():
        return False
    try:
        # 只读最后 2 行（header + last row）
        import subprocess
        result = subprocess.run(
            ['tail', '-2', str(csv_path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return False
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return False
        # 读 header
        header = lines[0].split(',')
        last_row = dict(zip(header, lines[1].split(',')))
        # 找日期列
        for col in ['date', 'datetime', 'trade_date']:
            if col in last_row:
                last_date = pd.to_datetime(last_row[col]).date()
                threshold = datetime.now().date() - timedelta(days=max_age_days)
                return last_date >= threshold
        return False
    except Exception:
        return False
```

### Fix 2: 重试策略优化

**当前**: 每次 retry 尝试全部 3 个数据源  
**修复**: 每个 retry 只尝试一个数据源，轮换使用

```python
def _download_one(self, symbol: str) -> DownloadResult:
    sources = []
    if USE_TUSHARE:
        sources.append(('tushare', get_stock_bars_tushare))
    sources.append(('akshare', get_stock_bars_akshare))
    sources.append(('baostock', get_stock_bars_baostock))
    
    for attempt in range(self.max_retries):
        source_name, source_fn = sources[attempt % len(sources)]
        try:
            bars = source_fn(symbol, None, None)
            if bars is not None and not bars.empty:
                self._save_bars(symbol, bars)
                remove_from_failed_queue(symbol)
                return DownloadResult(
                    symbol=symbol, status='success',
                    source=source_name, rows=len(bars),
                    duration=time.time() - start_time,
                )
        except Exception as e:
            last_error = f"{source_name} attempt {attempt+1}: {e}"
            logger.debug(last_error)
        
        if attempt < self.max_retries - 1:
            time.sleep(min(delay, self.max_delay))
            delay *= 2
    
    # 全部失败
    add_to_failed_queue(symbol, last_error or "未知错误")
    return DownloadResult(...)
```

### Fix 3: 添加限频控制

```python
from threading import Semaphore
import time

class RateLimiter:
    """简单的令牌桶限流器"""
    def __init__(self, max_per_minute: int = 180):  # 留 10% 余量
        self.interval = 60.0 / max_per_minute
        self._lock = Lock()
        self._last_call = 0.0
    
    def wait(self):
        with self._lock:
            now = time.time()
            wait = self.interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()

# 在 DataDownloader.__init__ 中
self._rate_limiter = RateLimiter(max_per_minute=180)

# 在 _download_one 开头
self._rate_limiter.wait()
```

### Fix 4: Neo4j 连接复用

```python
# batch_download_enhanced.py main()
neo4j_sync = None
if NEO4J_AVAILABLE:
    try:
        neo4j_sync = Neo4jSync()
    except Exception as e:
        logger.warning(f"Neo4j 初始化失败: {e}")

# 修改 sync_to_neo4j 接受连接参数
def sync_to_neo4j(stock_data, neo4j_conn=None):
    if neo4j_conn:
        neo4j_conn.sync_stock_data({...})
    # ...

# main() 结束时关闭
if neo4j_sync:
    neo4j_sync.close()
```

### Fix 5: 统一数据目录

```python
# batch_download_enhanced.py verify_data_consistency
def verify_data_consistency(stock_code, data_dir=None):
    if data_dir is None:
        data_dir = Path(__file__).parent / 'data' / 'akshare' / 'bars'
    # ...
```

### Fix 6: 统一股票格式

```python
# get_stock_list() 返回统一格式
def get_stock_list():
    # ...
    # 确保格式为 code.exchange
    def normalize(code):
        if '.' in code:
            return code
        if code.startswith('6'):
            return f"{code}.SSE"
        return f"{code}.SZSE"
    return [normalize(c) for c in raw_codes]
```

---

## 3. 实施任务

| 任务 | 描述 | 复杂度 |
|------|------|--------|
| T1 | 修复增量检测（tail 方式读最后一行） | Low |
| T2 | 修复重试策略（轮换数据源） | Low |
| T3 | 添加 RateLimiter 类 | Medium |
| T4 | Neo4j 连接复用 | Low |
| T5 | 统一数据目录路径 | Low |
| T6 | 统一股票格式 | Low |

---

## 4. 验收标准

- [ ] 增量检测不再读全量 CSV（用 tail 或类似方式）
- [ ] 每只股票每次 retry 只调用 1 个数据源
- [ ] 4 线程并发不会触发 Tushare 限频（180/min 限制）
- [ ] Neo4j 连接只创建一次
- [ ] 数据目录路径一致
- [ ] 股票格式统一为 `code.exchange`

---

## 5. 预期效果

| 指标 | Phase 2 | Phase 3 修复后 |
|------|---------|----------------|
| 增量检测耗时 | ~2s/只 (读全量) | ~0.01s/只 (tail) |
| API 调用数 | 1800次 (3×3×200) | 600次 (3×200) |
| 限频触发 | 可能 | 不会 |
| Neo4j 连接 | 200次 | 1次 |
