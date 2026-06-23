# Phase 4B — 失败队列与自动重试

## 任务
实现持久化失败队列和自动重试机制。

## 修复 1: 失败队列原子写入

**当前问题**: `failed_downloads.json` 用 `json.dump` 无 fsync，崩溃会丢队列。

**修复方案**: 使用 `AtomicFailedQueue` 类：
```python
import json
import os
import fcntl
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class AtomicFailedQueue:
    """原子写入的失败队列"""
    
    def __init__(self, path: Path):
        self.path = path
        self.lock_file = path.with_suffix('.lock')
    
    def add(self, symbol: str, error: str):
        """线程安全地添加失败记录"""
        with self._file_lock():
            failed = self._load()
            failed[symbol] = {
                "error": error,
                "timestamp": datetime.now().isoformat(),
                "retries": failed.get(symbol, {}).get("retries", 0) + 1
            }
            self._save_atomic(failed)
    
    def remove(self, symbol: str):
        """标记为已重试"""
        with self._file_lock():
            failed = self._load()
            failed.pop(symbol, None)
            self._save_atomic(failed)
    
    def get_all(self) -> Dict:
        with self._file_lock():
            return self._load()
    
    def _file_lock(self):
        """文件锁，跨进程安全"""
        return open(self.lock_file, 'w')
    
    def _load(self) -> Dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)
    
    def _save_atomic(self, data: Dict):
        """写入 tmp + fsync + rename"""
        tmp_path = str(self.path) + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # 确保写入磁盘
        os.replace(tmp_path, str(self.path))  # 原子替换
```

## 修复 2: 集成到 DataDownloader

**修改 `data_downloader.py`**:
```python
from atomic_failed_queue import AtomicFailedQueue

class DataDownloader:
    def __init__(self, ...):
        # ... 现有初始化
        self.failed_queue = AtomicFailedQueue(Path("data/failed_downloads.json"))
    
    def _download_one(self, symbol: str) -> Dict:
        try:
            # ... 现有下载逻辑
            result = self._do_download(symbol)
            if result.get("success"):
                self.failed_queue.remove(symbol)  # 成功后从队列移除
            return result
        except Exception as e:
            self.failed_queue.add(symbol, str(e))  # 失败后加入队列
            raise
```

## 修复 3: 自动重试脚本

**新增 `retry_failed_downloads.py`**:
```python
#!/usr/bin/env python3
"""失败下载自动重试 cron 任务"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data_downloader import DataDownloader
from atomic_failed_queue import AtomicFailedQueue

def retry_failed(max_retries: int = 3):
    queue = AtomicFailedQueue(Path("data/failed_downloads.json"))
    downloader = DataDownloader()
    
    failed = queue.get_all()
    retry_list = [
        sym for sym, info in failed.items()
        if info.get("retries", 0) < max_retries
    ]
    
    if not retry_list:
        print("No failed downloads to retry")
        return
    
    print(f"Retrying {len(retry_list)} failed symbols...")
    
    for symbol in retry_list:
        try:
            result = downloader.download_one(symbol)
            if result.get("success"):
                queue.remove(symbol)
                print(f"✓ {symbol}")
            else:
                print(f"✗ {symbol}: {result.get('error')}")
        except Exception as e:
            print(f"✗ {symbol}: {e}")

if __name__ == "__main__":
    retry_failed()
```

## 修复 4: Cron 任务配置

**新增 cron 任务** (每天 03:00 执行):
```bash
# 添加到 crontab
0 3 * * * cd /Users/rowang/projects/vnpy && python3 examples/alpha_research/retry_failed_downloads.py >> logs/retry_failed.log 2>&1
```

## 验收标准
- `AtomicFailedQueue` 使用 fsync + rename 原子写入
- `DataDownloader` 集成失败队列
- `retry_failed_downloads.py` 可独立运行
- 新增测试覆盖 3 个修复点
- Cron 任务配置完成

## 输出
- 新增文件: `examples/alpha_research/atomic_failed_queue.py`
- 修改文件: `examples/alpha_research/data_downloader.py`
- 新增文件: `examples/alpha_research/retry_failed_downloads.py`
- 新增测试: `tests/unit/test_atomic_failed_queue.py`
- 报告: `design/data-download-optimization/PHASE-4B-REPORT.md`
