# 数据管道诊断任务

## 背景
系统报告以下问题：
1. **P0 数据管道完全中断**
   - TUSHARE_TOKEN 环境变量未设置
   - 02:30 下载任务：50 只全部失败，成功率 0%
   - 自 06-01 起已连续 23 天下载失败
   - CSV 数据仅到 06-18，且仅 8 只股票有当日数据

2. **P1 持仓数据质量异常**
   - 10 只持仓中代码和名称全部显示 N/A
   - 账户最后更新时间 06-17，市值基于 6 天前数据
   - 两只曾触发止损预警（300039 -15.2%, 605266 -13.2%）

3. **今日无交易执行**
   - 有选股和交易计划，但无实际交易记录
   - 可能原因：数据管道中断导致交易信号无法执行

## 目标
诊断以上问题的根因，输出修复方案

## 范围
- 数据下载脚本：`examples/alpha_research/data_downloader.py`
- Tushare 配置：`examples/alpha_research/.env` 或 `~/.zshrc`
- Cron 任务配置：`config/cron_config.yaml` 或 `~/.openclaw/cron/jobs.json`
- 持仓管理：`accounts/` 目录
- 交易执行：检查交易信号生成和执行链路

## 输出要求

### 1. 诊断报告 → `design/data-pipeline-diagnosis/DIAGNOSIS-REPORT.md`
- 每个问题的根因分析
- 证据链（日志、配置、代码）
- 影响范围评估

### 2. 修复方案 → `design/data-pipeline-diagnosis/FIX-PLAN.md`
- 每个问题的修复步骤
- 优先级排序
- 预估时间

### 3. 验证清单 → `design/data-pipeline-diagnosis/VERIFICATION-CHECKLIST.md`
- 如何验证每个修复
- 回归测试点

## 约束
- 只读诊断，不修改代码
- 输出清晰的证据链
- 预估时间 ≤ 10 分钟
