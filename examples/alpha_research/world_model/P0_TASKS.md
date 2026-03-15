# P0 任务清单 - vnpy 世界模型集成

**开始日期**: 2026-03-15  
**预计完成**: 2026-03-29 (2 周)

---

## P0-1: 数据同步管道 (3-4 天)

### 任务分解
- [x] ✅ 创建 StockPrice WorldState Schema
- [x] ✅ 创建 Neo4j 同步模块 (neo4j_sync.py)
- [ ] 集成到 batch_download.py
- [ ] 实现增量同步逻辑
- [ ] 添加错误处理和重试
- [ ] 数据一致性验证测试

### 验收标准
- [ ] 股票下载后自动同步到 Neo4j
- [ ] 增量同步正常工作
- [ ] 错误处理完善
- [ ] 测试覆盖率 > 80%

### 预计完成时间
2026-03-18

---

## P0-2: 交易事件总线 (3-4 天)

### 任务分解
- [ ] 定义 TradeExecutedEvent Schema
- [ ] 定义 OrderPlacedEvent Schema
- [ ] 创建事件发布模块
- [ ] 集成到 daily_trading.py
- [ ] 实现事件监听器
- [ ] 事件溯源验证

### 验收标准
- [ ] 交易事件实时发布
- [ ] Redis Streams 持久化
- [ ] 事件查询正常
- [ ] 测试覆盖率 > 80%

### 预计完成时间
2026-03-22

---

## P0-3: Agent 注册同步 (2-3 天)

### 任务分解
- [ ] 创建 vnpy Agent 注册脚本
- [ ] 映射现有 Agent (10+ 个)
- [ ] 实现 Agent 状态同步
- [ ] Agent 能力图谱构建
- [ ] 健康检查集成

### 验收标准
- [ ] 所有 Agent 在 Neo4j 中可查询
- [ ] Agent 状态实时更新
- [ ] 健康检查正常
- [ ] 测试覆盖率 > 80%

### 预计完成时间
2026-03-25

---

## 开发环境

**虚拟环境**: `venv-world-model`  
**激活命令**: `source venv-world-model/bin/activate`

**依赖包**:
- neo4j>=5.0.0
- redis>=4.5.0
- flask>=2.3.0

**测试命令**:
```bash
source venv-world-model/bin/activate
python3 world_model/neo4j_sync.py
```

---

## 进度追踪

| 日期 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 2026-03-15 | 环境准备 | ✅ 完成 | 虚拟环境 + 依赖 |
| 2026-03-15 | Neo4j 同步模块 | ✅ 完成 | 基础功能 |
| 2026-03-16 | batch_download 集成 | ⏳ 待开始 | - |
| 2026-03-17 | 增量同步 | ⏳ 待开始 | - |
| 2026-03-18 | P0-1 验证 | ⏳ 待开始 | - |

---

**文档位置**: `/Users/rowang/projects/vnpy/examples/alpha_research/world_model/P0_TASKS.md`
