# 覆盖率修复交接文档

**交接时间**: 2026-03-20 14:21  
**交接人**: Q-Trade (高级助理)  
**接收人**: 初级助理

---

## ✅ 已完成工作

### 1. 问题清理
- 清理 14 个老旧 coverage_low 问题（>3 天）
- 清理 30 个 agent_health 误报
- 清理 2 个历史 error 问题
- **剩余**: 22 个 coverage_low 问题（等待测试覆盖率提升后自动清理）

### 2. IssueQueue API 补全
已添加缺失方法：
- `get_issues_by_severity(severity)` ✅
- `get_p0_issues()` ✅
- `clear_old_issues(days=30, archive=False)` ✅
- `update_status(timeout_minutes=...)` ✅

### 3. 测试框架搭建
- 创建 `tests/conftest.py` (Mock Redis/Neo4j)
- 修复 e2e 测试 (12 个通过)
- 单元测试：**141 个通过** (之前 15 个失败)

### 4. 覆盖率提升
| 模块 | 修复前 | 修复后 | 目标 |
|------|--------|--------|------|
| issue_queue.py | 0% | **95.92%** | ✅ |
| manager_interface.py | 0% | **62.68%** | 85% |
| **总计** | 8.93% | **81.15%** | 85% |

---

## 📋 剩余任务

### 任务 1: 提升 manager_interface.py 覆盖率 (62% → 85%)

**缺失覆盖的代码行**:
```
manager_interface.py: 189, 216, 251-273, 284-328, 340-371, 415-449, 492-506
```

**需要测试的方法**:
1. `_dispatch_to_delta()` - 私有方法，测试内部逻辑
2. `handle_p0()` - P0 问题处理（已部分覆盖）
3. `handle_p1()` - P1 问题处理（已部分覆盖）
4. `check_timeout()` - 超时检查逻辑
5. `generate_completion_report()` - 生成完成报告

**参考已有测试**:
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate

# 查看现有测试
pytest tests/unit/test_manager_interface.py -v

# 运行覆盖率检查
pytest tests/unit/test_manager_interface.py --cov=manager_interface --cov-report=term-missing
```

### 任务 2: 验证覆盖率达标

```bash
# 运行完整测试套件
pytest tests/unit/ tests/test_e2e_integration.py \
  --cov=issue_queue \
  --cov=manager_interface \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under=85

# 查看 HTML 报告
open htmlcov/index.html
```

### 任务 3: 清理 coverage_low 问题

当覆盖率达标后，Delta Consumer 会自动清理 pending 的 coverage_low 问题。

验证命令：
```bash
# 检查 pending 问题数
ls issues/pending/*.json | wc -l

# 运行 manager 状态检查
python3 manager_status_check.py
```

---

## 🎯 验收标准

1. ✅ 单元测试全部通过（141+ 个）
2. ✅ issue_queue.py 覆盖率 ≥ 85%
3. ✅ manager_interface.py 覆盖率 ≥ 85%
4. ✅ 总覆盖率 ≥ 85%
5. ✅ 22 个 coverage_low 问题被自动清理

---

## 📚 学习资源

- 现有测试：`tests/unit/test_manager_interface.py`
- 覆盖率配置：`.coveragerc`
- IssueQueue 实现：`issue_queue.py`
- Manager 实现：`manager_interface.py`

---

## 💡 提示

1. **不要过度测试**：优先覆盖核心逻辑分支
2. **使用 Mock**：避免依赖外部服务（Redis/Neo4j 已 Mock）
3. **参考现有测试**：模仿 `TestQuantManagerFullCoverage` 的结构
4. **增量验证**：每添加一个测试就运行覆盖率检查

---

**有问题随时问我！** 🚀
