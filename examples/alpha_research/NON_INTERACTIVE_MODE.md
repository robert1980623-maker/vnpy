# 无人值守模式使用指南

## 概述

所有主要脚本现已支持 `--non-interactive` 参数，用于在 cron 任务或自动化流程中运行，无需人工交互。

## 支持的脚本

- ✅ `data_agent.py` - 统一数据下载
- ✅ `stale_data_updater.py` - 陈旧数据更新
- ✅ `download_data_akshare.py` - 股票数据下载
- ✅ `compliance_checker.py` - 合规检查
- ✅ `chief_risk_officer.py` - 首席风险官
- ✅ `compliance_agent.py` - 合规 Agent
- ✅ `realtime_monitor.py` - 实时监控
- ✅ `daily_review.py` - 每日复盘
- ✅ `elite_stock_selector.py` - 精英选股
- ✅ `rebalance_portfolio.py` - 组合调仓

## 用法

### 命令行使用

```bash
# 启用无人值守模式
python3 data_agent.py --all --non-interactive

# 检查陈旧数据（无人值守）
python3 stale_data_updater.py --check-only --non-interactive

# 自动更新陈旧数据（无人值守）
python3 stale_data_updater.py --auto --threshold 2 --non-interactive

# 下载股票数据（无人值守）
python3 download_data_akshare.py --max 10 --non-interactive
```

### Cron 任务配置

```json
{
  "name": "数据下载 (无人值守)",
  "schedule": "0 1 * * *",
  "command": "python3 data_agent.py --all --non-interactive",
  "model": "lmstudio/zai-org/glm-4.7-flash"
}
```

## 行为差异

| 行为 | 交互模式 | 无人值守模式 |
|------|---------|-------------|
| 确认提示 | 等待用户输入 | 使用默认值 |
| 错误处理 | 可手动选择重试 | 自动重试或跳过 |
| 日志输出 | 详细 | 精简（仅关键信息） |
| input() 调用 | 阻塞等待 | 使用默认值或抛出异常 |

## 环境变量

启用 `--non-interactive` 时会自动设置：

```bash
export NON_INTERACTIVE=1
```

可在代码中通过以下方式检查：

```python
from non_interactive_helper import is_non_interactive

if is_non_interactive():
    # 无人值守模式逻辑
    use_default_config()
else:
    # 交互模式逻辑
    ask_user_for_config()
```

## 辅助函数

`non_interactive_helper.py` 提供以下函数：

- `setup_non_interactive_mode(enabled)` - 启用/禁用无人值守模式
- `is_non_interactive()` - 检查是否处于无人值守模式
- `safe_input(prompt, default)` - 安全的输入函数（无人值守时返回默认值）
- `confirm_action(prompt, default)` - 安全的确认函数（无人值守时返回默认值）

## 示例代码

```python
from non_interactive_helper import setup_non_interactive_mode, safe_input, confirm_action

# 在 main 函数中
setup_non_interactive_mode(args.non_interactive)

# 需要用户输入时
config_file = safe_input("配置文件路径", default="config.yaml")

# 需要确认时
if confirm_action("确认执行？", default=True):
    execute_task()
```

## 注意事项

1. **默认值很重要**: 在无人值守模式下，所有输入都使用默认值
2. **错误处理**: 确保有完善的错误处理，避免任务卡住
3. **日志记录**: 使用日志文件记录执行过程，便于排查问题
4. **超时设置**: cron 任务应设置合理的超时时间

## 测试

```bash
# 测试无人值守模式
python3 data_agent.py --all --non-interactive

# 检查是否真正无人值守（应该立即返回或使用默认值）
time python3 stale_data_updater.py --check-only --non-interactive
```
