# VNPY 代码审查 — 执行摘要

**日期:** 2026-04-13 | **模块:** delta_consumer, manager, alpha/lab

## 关键发现（11 个严重/高危问题 + 19 个警告）

### 🔴 致命问题（4 个）
1. **Delta Consumer "修复"全是假的** — `invoke_delta_fix` 只返回字符串，不改任何代码，但标记 issue 为 resolved
2. **Industry Rotation 估值数据伪造** — 用 `hash()` 随机生成 PE/PB，回测结果不可信
3. **Industry Rotation 无法运行** — `__init__` 签名与基类不匹配，实例化即崩溃
4. **无文件锁** — 三个模块并发读写 JSON，race condition 必然发生

### 🟡 高危问题（7 个）
- retry_count 双重计数 bug
- 缓存无限增长（内存泄漏）
- 时区 naive/aware 混用（Python 3.12+ 崩溃风险）
- `_get_price` 线性搜索（回测性能瓶颈）
- 回测仓位计算用 initial_capital 而非总资产
- GLM fallback 置信度设为 0.0 误导调用者
- 通知目标硬编码

### 📊 性能瓶颈
- Issue Queue: O(n) 文件扫描 → 改用内存索引
- CrossSectionalEngine._get_price: O(bars) 线性搜索 → 建 dict 索引
- track_agent_execution: busy-wait 轮询 → 事件驱动

### 🏗️ 架构建议
- 当前 JSON 文件方案仅适合原型 → 迁移 SQLite/PostgreSQL
- Delta Consumer 接入真正 LLM 代码修复（Aider/OpenDevin）
- Agent 调度改用消息队列替代 JSON 文件

**详细报告:** `deep_code_review.md`
