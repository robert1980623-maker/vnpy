# VNPY 深度代码审查摘要 (2026-04-14)

## 快速概览

| 指标 | 数值 |
|------|------|
| 审查模块数 | 9 |
| 总代码行数 | ~3,000+ |
| P0 严重问题 | 6 |
| P1 重要问题 | 13 |
| P2 优化建议 | 10 |

## Top 5 必须修复

1. **MG-01** Manager `active_tasks` 字典内存泄漏 → 长期运行 OOM
2. **MG-02** `track_agent_execution` 同步阻塞轮询 → 严重性能瓶颈
3. **DC-02** `load_tasks`/`save_tasks` 无文件锁 → 多实例并发数据丢失
4. **AL-02** `_database` 初始化无空值检查 → 未配置数据库时崩溃
5. **AL-05** `get_trading_dates` 硬编码假日期 → 回测结果完全不可信

## 架构核心问题

- **Agent 路由死代码**: `agent_mapping` 定义了 5 种 Agent，但 `dispatch_to_delta` 把**所有任务都发给 delta**
- **双写不一致**: SQLite + JSON 双写无事务保护，可能数据分裂
- **轮询泛滥**: 系统大量使用 polling (文件轮询、状态轮询)，应改为事件驱动

## 详细报告

详见: `vnpy_analysis/deep_code_review_2026-04-14.md`
