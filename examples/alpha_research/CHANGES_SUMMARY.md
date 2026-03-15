# 无人值守模式更新总结

## 更新日期
2026-03-15 22:27

## 变更概述

为 vnpy 项目的所有主要脚本添加了 `--non-interactive` 参数支持，使其能够在 cron 任务和自动化流程中无人值守运行。

## 新增文件

1. **`non_interactive_helper.py`** - 无人值守模式辅助模块
   - `setup_non_interactive_mode(enabled)` - 启用/禁用模式
   - `is_non_interactive()` - 检查模式状态
   - `safe_input(prompt, default)` - 安全输入函数
   - `confirm_action(prompt, default)` - 安全确认函数

2. **`NON_INTERACTIVE_MODE.md`** - 使用指南文档

## 更新的脚本 (10 个)

所有脚本现已支持 `--non-interactive` 参数：

| 脚本 | 功能 | 状态 |
|------|------|------|
| `data_agent.py` | 统一数据下载 | ✅ |
| `stale_data_updater.py` | 陈旧数据更新 | ✅ |
| `download_data_akshare.py` | 股票数据下载 | ✅ |
| `compliance_checker.py` | 合规检查 | ✅ |
| `chief_risk_officer.py` | 首席风险官 | ✅ |
| `compliance_agent.py` | 合规 Agent | ✅ |
| `realtime_monitor.py` | 实时监控 | ✅ |
| `daily_review.py` | 每日复盘 | ✅ |
| `elite_stock_selector.py` | 精英选股 | ✅ |
| `rebalance_portfolio.py` | 组合调仓 | ✅ |

## 更新的配置文件 (6 个)

所有 cron 配置文件已更新，命令中添加了 `--non-interactive` 参数：

- `config/data_agent_cron.json`
- `config/compliance_cron.json`
- `config/data_freshness_cron.json`
- `config/cron_jobs_to_add.json`
- `config/auto_tasks.json`
- `config/missing_agents_cron.json`

## 使用示例

### 命令行测试

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 检查陈旧数据（无人值守）
python3 stale_data_updater.py --check-only --non-interactive

# 合规检查（无人值守）
python3 compliance_checker.py --non-interactive

# 数据下载（无人值守）
python3 data_agent.py --all --non-interactive
```

### Cron 任务示例

```json
{
  "name": "数据下载 (无人值守)",
  "schedule": "0 1 * * *",
  "command": "cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source venv/bin/activate && python3 data_agent.py --all --non-interactive",
  "timeout": 1800,
  "model": "lmstudio/zai-org/glm-4.7-flash"
}
```

## 行为变化

### 交互模式（默认）
- 可接受用户输入
- 显示详细提示
- 等待用户确认

### 无人值守模式（`--non-interactive`）
- 所有输入使用默认值
- 精简日志输出
- 自动确认操作
- 适合 cron/自动化

## 测试验证

✅ 已测试脚本：
- `stale_data_updater.py --check-only --non-interactive` - 正常运行
- `compliance_checker.py --non-interactive` - 正常运行
- `data_agent.py --help` - 参数显示正确
- `download_data_akshare.py --help` - 参数显示正确

## 后续工作

- [ ] 在下次 cron 执行时验证日志输出
- [ ] 监控无人值守模式下的错误率
- [ ] 根据需要调整默认值和超时设置

## 回滚方法

如需回滚，从 git 恢复以下文件：

```bash
git checkout -- *.py config/*.json
```

或手动移除 `--non-interactive` 参数和相关导入。
