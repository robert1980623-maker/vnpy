# Agent Neo4j 同步指南

## 问题

**用户问**: 每次新增加的 agent 会自动同步到 neo4j 吗？

**答案**: ❌ **不会自动同步**

---

## 现状分析

### 已有资源

1. ✅ **agent_registry.py** - Agent 注册模块
   - 位置：`world_model/agent_registry.py`
   - 功能：扫描 Agent 并注册到 Neo4j
   - 状态：模块存在，但**没有定时任务**

2. ❌ **自动同步任务** - 缺失
   - 没有 cron 任务定期执行同步
   - 新增 Agent 不会自动同步到 Neo4j

---

## 解决方案

### 方案 1: 定时同步（推荐）

创建 cron 任务，每天凌晨 2 点自动同步：

```bash
./setup_agent_sync_cron.sh
```

**配置**:
- 频率：每天 02:00
- 模型：glm-4.7-flash (本地)
- 超时：300 秒
- 功能：扫描 + 注册 + 报告

### 方案 2: 手动同步

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 sync_agents_to_neo4j.py --auto
```

### 方案 3: 新增 Agent 时手动触发

每创建一个新的 Agent 文件后：

```bash
python3 sync_agents_to_neo4j.py --scan  # 查看
python3 sync_agents_to_neo4j.py --auto  # 同步
```

---

## 使用指南

### 部署自动同步

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 1. 创建 cron 任务
./setup_agent_sync_cron.sh

# 2. 验证
openclaw cron list | grep Neo4j

# 3. 手动测试
python3 sync_agents_to_neo4j.py --auto
```

### 查看同步报告

```bash
# 报告位置
ls -lt reports/agent_sync/

# 查看最新报告
cat reports/agent_sync/sync_*.md | head -50
```

---

## 工作流程

```
每天 02:00 触发
    ↓
扫描项目中的 Agent 文件
    ↓
解析 Agent 信息（名称、类型、描述）
    ↓
注册/更新到 Neo4j
    ↓
生成同步报告
    ↓
完成
```

---

## 同步内容

### Agent 信息

| 字段 | 说明 |
|------|------|
| agent_id | Agent 文件 ID |
| agent_name | Agent 类名 |
| file_name | 文件名 |
| file_path | 完整路径 |
| type | 类型（monitoring/trading/risk 等） |
| description | 描述 |
| status | 状态（active/inactive） |
| updated_at | 更新时间 |

### Agent 类型映射

| 关键词 | 类型 |
|--------|------|
| health_check, log_analyzer | monitoring |
| risk_officer, compliance | risk |
| trading, quant | trading |
| data | data |
| dispatcher | coordinator |
| report, review | reporting |
| decision_maker | decision |

---

## 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `world_model/agent_registry.py` | Agent 注册模块 | ✅ 已存在 |
| `sync_agents_to_neo4j.py` | 同步脚本 | ✅ 已创建 |
| `setup_agent_sync_cron.sh` | cron 配置 | ✅ 已创建 |
| `AGENT_NEO4J_SYNC_GUIDE.md` | 使用指南 | ✅ 已创建 |

---

## Neo4j 数据结构

```cypher
// Agent 节点
MATCH (a:Agent) RETURN a

// 属性
- id: agent_id
- name: agent_name
- type: agent_type
- description: description
- status: active/inactive
- file_name: file_name
- file_path: file_path
- updated_at: datetime
```

---

## 故障排查

### 问题 1: Neo4j 连接失败

```bash
# 检查 Neo4j 状态
docker ps | grep neo4j

# 检查连接
python3 -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'admin_robert')).verify_connectivity()"
```

### 问题 2: 同步失败

```bash
# 查看详细错误
python3 sync_agents_to_neo4j.py --auto 2>&1 | tail -50

# 检查报告
cat reports/agent_sync/sync_*.md
```

### 问题 3: Agent 未识别

```bash
# 手动扫描
python3 sync_agents_to_neo4j.py --scan

# 检查文件命名
# 确保文件名包含 'agent', 'officer', 或 'decision'
```

---

## 最佳实践

### ✅ 推荐

1. **启用自动同步** - 每天凌晨 2 点
2. **新增 Agent 后手动同步** - 确保及时更新
3. **定期检查报告** - 确认同步成功
4. **保持 Neo4j 运行** - 确保可以连接

### ❌ 避免

1. ~~频繁手动同步~~ - 每小时不超过 1 次
2. ~~忽略错误报告~~ - 及时处理同步失败
3. ~~修改 Agent 命名规范~~ - 保持可识别性

---

## 总结

**问题**: 新增 Agent 不会自动同步到 Neo4j

**原因**: 缺少定时同步任务

**解决**: 
- ✅ 创建 `sync_agents_to_neo4j.py`
- ✅ 配置每天凌晨 2 点自动同步
- ✅ 支持手动触发

**状态**: ✅ 准备就绪，等待部署
