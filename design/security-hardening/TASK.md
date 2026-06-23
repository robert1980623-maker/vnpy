# 安全加固调研任务

## 目标
调研 VNPY 当前安全风险，输出设计方案和任务拆分。

## 背景
当前存在以下已知安全问题：
1. Control UI device auth 已禁用 — 未授权访问风险
2. groupPolicy="open" + 运行时工具暴露 — 工具滥用风险
3. 35B 小模型无沙箱 + 网页工具 — 代码执行风险
4. architect-agent heartbeat 未启用 — 健康监控缺失

## 范围
- OpenClaw 配置文件（gateway config）
- 沙箱机制（Docker/容器隔离）
- 工具权限控制（allowlist/denylist）
- 认证机制（device auth、OAuth）
- 网络隔离策略

## 输出要求

### 1. 调研报告 → design/security-hardening/RESEARCH-REPORT.md
- 当前安全配置现状
- 风险清单（按严重度排序）
- 每个风险的攻击场景和影响范围
- 修复方案对比

### 2. 任务拆分 → design/security-hardening/TASK-BREAKDOWN.md
- 每个子任务：目标、涉及文件、预估时间、复杂度级别（🟢/🟡/🔴）
- 依赖关系
- 可并发的任务组
- 每个子任务 ≤ 10 分钟执行时间
- 每个子任务修改 ≤ 2 个文件

## 约束
- 修复方案不能影响现有功能
- 需要向后兼容
- 优先考虑最小改动方案
