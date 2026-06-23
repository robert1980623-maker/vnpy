# P2-1: 交易执行链路恢复

## 问题
- 执行脚本以 dry_run 模式运行，无实际交易
- Cron 任务链断裂：31 个任务定义但大部分未安装
- 缺失关键任务：trade-rebalance, trade-stop-loss-executor, trade-stop-loss-check, monitor-virtual-account

## 根因
- `logs/execution_2026-06-12.json` 显示 `dry_run: true`
- `config/cron_config.yaml` 定义了 31 个任务，但 crontab 只有 3 个
- 数据管道中断导致交易信号无法执行

## 修复方案
1. 创建交易执行 wrapper 脚本 `scripts/run_trade_with_env.sh`
2. 更新 `config/cron_config.yaml` 中的交易任务配置
3. 生成 crontab 安装命令清单（不直接修改 crontab，输出命令供雅轩执行）

## 验收标准
1. 创建 `scripts/run_trade_with_env.sh`
2. 更新 `config/cron_config.yaml` 交易任务配置
3. 输出 crontab 安装命令清单
4. 不修改 `~/.openclaw/` 下的任何文件
5. 不直接修改系统 crontab（只输出命令）

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `scripts/` 和 `config/` 下的文件
- 预估时间：30 分钟
