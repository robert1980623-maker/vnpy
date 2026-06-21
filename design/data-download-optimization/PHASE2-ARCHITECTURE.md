# VNPY 数据下载系统 Phase 2 架构设计

**作者**: Atlas (Chief Architect)  
**日期**: 2026-06-21  
**状态**: Draft  
**版本**: 1.0

---

## 1. 问题陈述

### 1.1 当前架构痛点

| 问题 | 影响 | 严重度 |
|------|------|--------|
| 每只股票启动 subprocess | 200只 = 200次 Python 启动 (~100-200s 纯开销) | 🔴 Critical |
| 5个下载脚本职责重叠 | 维护成本高，逻辑不一致 | 🟡 High |
| Token 加载重复 5+ 处 | 改一处漏四处 | 🟡 High |
| 串行下载 + 过度延迟 | 30分钟完成 200只，API 利用率 10% | 🔴 Critical |
| 无增量检测 | 每天重复下载已有数据 | 🟡 High |
| 失败队列不持久化 | 进程退出丢失失败记录 | 🟡 High |

### 1.2 性能基准

**当前状态** (Phase 1 后):
- 200 只股票下载耗时: ~30 分钟
- API 调用利用率: ~10% (Tushare 限频 200/min，实际 20/min)
- 进程启动开销: ~0.5-1s/只

**目标状态** (Phase 2 后):
- 200 只股票下载耗时: **3-5 分钟** (6-10x 提升)
- API 调用利用率: **60-80%**
- 进程启动开销: **0ms** (进程内调用)

---

## 2. 目标架构

### 2.1 架构原则

1. **单一职责**: 一个统一的 DataDownloader 类
2. **进程内调用**: 消除 subprocess 开销
3. **并发优先**: ThreadPoolExecutor 4 线程
4. **增量感知**: 自动跳过已有最新数据
5. **失败持久化**: 失败队列跨进程保留

### 2.2 模块结构

```
examples/alpha_research/
├── data_downloader.py          # [新增] 统一下载器
├── config_loader.py            # [已有] 统一配置加载
├── batch_download_enhanced.py  # [重构] 调用 DataDownloader
├── data_source_wrapper.py      # [保留] 兼容旧接口
├── tushare_pro_downloader.py   # [保留] 兼容旧接口
└── download_data_akshare.py    # [不变] 底层数据源
```

### 2.3 核心类设计

#### DataDownloader

```python
class DataDownloader:
    """统一数据下载器"""
    
    def __init__(self, config: DownloaderConfig):
        self.config = config
        self._tushare_pro: Optional[pro_api]
        self._akshare: Optional[ak]
        self._failed_queue: FailedQueue
    
    # 核心方法
    def download_single(self, symbol: str) -> DownloadResult
    def download_batch(self, symbols: List[str]) -> List[DownloadResult]
    
    # 辅助方法
    def _is_up_to_date(self, symbol: str) -> bool
    def _save_to_csv(self, symbol: str, df: pd.DataFrame)
    def _fallback_to_akshare(self, symbol: str) -> DownloadResult
```

#### DownloaderConfig

```python
@dataclass
class DownloaderConfig:
    max_workers: int = 4          # 并发线程数
    stock_delay: float = 0.5      # 单只间隔 (秒)
    batch_delay: float = 5.0      # 批次间隔 (秒)
    batch_size: int = 50          # 批次大小
    max_retries: int = 3          # 单只最大重试
    data_dir: str = './data/akshare/bars'
    failed_queue_file: str = './failed_downloads.json'
```

#### DownloadResult

```python
@dataclass
class DownloadResult:
    symbol: str
    status: str  # 'success' | 'failed' | 'skipped'
    source: str  # 'tushare' | 'akshare' | 'cache'
    rows: int = 0
    duration: float = 0.0
    error: str = ''
```

### 2.4 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    batch_download_enhanced.py               │
│  (CLI 入口，参数解析，通知)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    DataDownloader                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 增量检测     │  │ 失败队列     │  │ 并发控制     │     │
│  │ is_up_to_date│  │ FailedQueue  │  │ ThreadPool   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  Tushare Pro     │      │  AKShare         │
│  (主数据源)       │      │  (备用数据源)     │
└──────────────────┘      └──────────────────┘
```

### 2.5 并发策略

```python
# 伪代码
def download_batch(symbols):
    # 1. 过滤已最新的
    to_download = [s for s in symbols if not self._is_up_to_date(s)]
    
    # 2. 分批并发
    for batch in chunk(to_download, self.config.batch_size):
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
            futures = [pool.submit(self.download_single, s) for s in batch]
            results = [f.result() for f in as_completed(futures)]
        
        # 3. 批次间隔 (避免限频)
        time.sleep(self.config.batch_delay)
    
    return results
```

---

## 3. 实施计划

### 3.1 任务分解

| 任务 | 描述 | 复杂度 | 预估时间 |
|------|------|--------|----------|
| T1 | 创建 `data_downloader.py` | Medium | 2h |
| T2 | 重构 `batch_download_enhanced.py` 使用 DataDownloader | Medium | 1h |
| T3 | 添加单元测试 | Low | 1h |
| T4 | 性能基准测试 | Low | 0.5h |

### 3.2 依赖关系

```
T1 (DataDownloader)
  ↓
T2 (重构 batch_download)
  ↓
T3 (单元测试) + T4 (性能测试)
```

### 3.3 验收标准

- [ ] `DataDownloader.download_batch(200只)` 耗时 < 5 分钟
- [ ] API 利用率 > 60%
- [ ] 失败股票自动加入 `failed_downloads.json`
- [ ] 下次运行优先重试失败队列
- [ ] 已有最新数据的股票自动跳过
- [ ] 现有 CLI 接口不变

---

## 4. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Tushare 限频触发 | 中 | 高 | 动态调整 batch_delay |
| 多线程数据冲突 | 低 | 中 | 每只股票独立文件，无共享状态 |
| 内存占用过高 | 低 | 低 | 流式处理，不缓存 DataFrame |
| 旧脚本兼容性问题 | 中 | 低 | 保留旧接口，内部委托 DataDownloader |

---

## 5. 未来演进

### Phase 3 (可选)

- [ ] 支持 Parquet 格式 (替代 CSV)
- [ ] 支持增量下载 (只下载新数据)
- [ ] 支持断点续传
- [ ] 支持多机器分布式下载

---

## 6. 附录

### 6.1 相关文件

- `examples/alpha_research/batch_download_enhanced.py` (当前实现)
- `examples/alpha_research/download_data_akshare.py` (底层数据源)
- `examples/alpha_research/config_loader.py` (配置加载)

### 6.2 参考资料

- [Tushare Pro API 文档](https://tushare.pro/document/2)
- [AKShare 文档](https://akshare.akfamily.xyz/)
- [Python ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html)

---

**下一步**: Coding Agent 根据此设计实现 T1-T4 任务。
