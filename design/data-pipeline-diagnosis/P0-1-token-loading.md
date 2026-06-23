# P0-1: Token 加载机制修复

## 问题
Cron 任务执行 `download_data_akshare.py` 时，TUSHARE_TOKEN 环境变量未加载，导致数据下载失败。

## 根因
- Cron 环境不加载 `.zshrc` 或 `.env`
- 下载脚本依赖 `os.environ.get('TUSHARE_TOKEN')`，但环境变量为空
- 导致 USE_TUSHARE=False，降级到 AKShare 后也失败

## 修复方案
修改 `examples/alpha_research/download_data_akshare.py`，在文件开头添加 `.env` 自动加载逻辑：

```python
# 在 import 部分后，配置加载前添加：
def _load_env():
    """从 .env 文件加载环境变量（cron 环境兼容）"""
    from pathlib import Path
    import os
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env()
```

## 验收标准
1. 修改 `examples/alpha_research/download_data_akshare.py`
2. 添加 `_load_env()` 函数并在模块加载时调用
3. 验证：`python3 -c "import sys; sys.path.insert(0, 'examples/alpha_research'); from download_data_akshare import USE_TUSHARE; print(USE_TUSHARE)"` 输出 True
4. 不修改 `~/.openclaw/` 下的任何文件

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `examples/alpha_research/` 下的文件
- 预估时间：15 分钟
