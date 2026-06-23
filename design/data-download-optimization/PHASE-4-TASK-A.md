# Phase 4A — 核心下载器修复

## 任务
修复 `examples/alpha_research/data_downloader.py` 中的 3 个 P0 问题。

## 修复 1: is_up_to_date — 替换 subprocess tail 为 Python 原生 seek

**当前问题**: `subprocess.run(['tail', '-2', ...])` 跨平台不可用，且 fork 进程开销比读 CSV 更大。

**修复方案**: 用 Python 原生 `seek` 读文件末尾 4KB：
```python
def is_up_to_date(self, symbol: str, max_age_days: int = 1) -> bool:
    csv_path = self.data_dir / f"{symbol}.csv"
    if not csv_path.exists():
        return False
    try:
        file_size = csv_path.stat().st_size
        read_size = min(4096, file_size)
        with open(csv_path, 'rb') as f:
            f.seek(file_size - read_size)
            tail = f.read(read_size).decode('utf-8', errors='ignore')
        
        last_newline = tail.rfind('\n')
        if last_newline == -1:
            return False
        second_last = tail.rfind('\n', 0, last_newline)
        if second_last == -1:
            second_last = -1
        
        last_line = tail[second_last+1:last_newline].strip()
        if not last_line:
            return False
        
        first_col = last_line.split(',', 1)[0]
        last_date = pd.to_datetime(first_col, errors='coerce')
        if pd.isna(last_date):
            return False
        
        threshold = datetime.now().date() - timedelta(days=max_age_days)
        return last_date.date() >= threshold
    except Exception as e:
        logger.debug(f"增量检测失败 {symbol}: {e}")
        return False
```

## 修复 2: RateLimiter — 替换为滑动窗口

**当前问题**: 简单间隔检查，高并发时仍可能 burst。

**修复方案**: 60s 滑动窗口计数器：
```python
from collections import deque
from threading import Lock

class SlidingWindowRateLimiter:
    """60s 滑动窗口计数器, 避免 burst"""
    def __init__(self, max_per_minute: int = 180):
        self.max_count = max_per_minute
        self._lock = Lock()
        self._timestamps: deque = deque(maxlen=max_count)
    
    def wait(self):
        with self._lock:
            now = time.time()
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()
            
            if len(self._timestamps) >= self.max_count:
                sleep_for = 60 - (now - self._timestamps[0]) + 0.01
                time.sleep(sleep_for)
            
            self._timestamps.append(time.time())
```

保留旧的 `RateLimiter` 类名作为别名，向后兼容。

## 修复 3: CSV 写入原子性

**当前问题**: `to_csv()` 直接覆盖，崩溃后文件可能截断。

**修复方案**: 先写 `.tmp` 再 `os.replace()`：
```python
def _safe_write_csv(self, df, path):
    tmp_path = str(path) + '.tmp'
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, str(path))  # 原子操作
```

## 验收标准
- `is_up_to_date` 不再使用 subprocess
- RateLimiter 使用滑动窗口
- CSV 写入通过 tmp + rename 原子化
- 现有测试通过
- 新增测试覆盖 3 个修复点

## 输出
- 修改文件: `examples/alpha_research/data_downloader.py`
- 新增测试: `tests/unit/test_data_downloader_phase4a.py`
- 报告: `design/data-download-optimization/PHASE-4A-REPORT.md`
