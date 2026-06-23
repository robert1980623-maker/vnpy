# P0-3: 数据下载任务修复

## 问题
数据下载 cron 任务失败，需要修复下载脚本和配置。

## 根因
1. 下载脚本缺少环境变量加载逻辑（P0-1 已修复）
2. 下载超时设置过短（P0-2 正在修复）
3. 需要验证完整的下载流程

## 修复方案
1. 创建数据下载 wrapper 脚本 `scripts/run_download_with_env.sh`
2. 更新 cron 配置使用新的 wrapper
3. 验证下载流程端到端工作

## 验收标准
1. 创建 `scripts/run_download_with_env.sh`，包含环境变量加载
2. 更新 `config/cron_config.yaml` 中的数据下载任务配置
3. 手动执行下载脚本验证工作正常
4. 不修改 `~/.openclaw/` 下的任何文件

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `scripts/` 和 `config/` 下的文件
- 预估时间：30 分钟
