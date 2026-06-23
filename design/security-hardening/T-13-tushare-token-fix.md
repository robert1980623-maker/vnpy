# T-13: Tushare Token 加载问题修复

## 问题
Cron 任务运行时 `TUSHARE_TOKEN` 环境变量为空，导致：
- 02:30 下载任务：50 只全部失败
- 自 06-01 起已连续 23 天下载失败
- 所有交易信号无法执行

## 根因
- Token 在 `~/.zshrc` 中 export
- 但 Cron 任务使用 `bin/zsh` 而非 `zsh -i`，**不会加载 .zshrc**
- Python 进程拿不到环境变量
- `config_loader.py` 退回到 .env 文件，但如果 .env 不在正确路径就会失败

## 涉及文件
- `cli/main.py` — CLI 入口
- `cli/utils/config.py` — 配置加载器
- `examples/alpha_research/config_loader.py` — 数据源配置

## 修复方案
1. **CLI 启动时显式 source ~/.zshrc**（仅当 TUSHARE_TOKEN 未设置时）
2. **增加详细日志**：打印 TUSHARE_TOKEN 来源（env/.zshrc/.env）
3. **添加 sanity check 命令**：`vnpy health --check env`

## 变更内容
```python
# cli/main.py 启动时
import os, subprocess
if not os.environ.get('TUSHARE_TOKEN'):
    zshrc = os.path.expanduser('~/.zshrc')
    if os.path.exists(zshrc):
        result = subprocess.run(
            ['zsh', '-c', f'source {zshrc} && env | grep TUSHARE_TOKEN'],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if line.startswith('TUSHARE_TOKEN='):
                token = line.split('=', 1)[1]
                os.environ['TUSHARE_TOKEN'] = token
                break
```

## 验收标准
1. `vnpy download tushare --dry-run` 显示 Token 已加载
2. cron 环境下 `os.environ.get('TUSHARE_TOKEN')` 不为空
3. 添加日志显示 Token 来源

## 预估时间
5 分钟
