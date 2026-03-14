# 代码覆盖率 90% 强制要求

## ✅ 已实施

### 1. 覆盖率检查工具
- ✅ `.coveragerc` - 覆盖率配置文件
- ✅ `tests/test_coverage.py` - 覆盖率测试
- ✅ `qa_change_gate.py` - QA 门禁（包含覆盖率检查）
- ✅ Git pre-commit hook - 提交前强制检查

### 2. 单元测试
- ✅ `tests/unit/test_core_modules.py` - 核心模块测试 (9 个测试)
- ✅ `tests/unit/test_virtual_account.py` - 虚拟账户测试
- ✅ `tests/integration/` - 集成测试 (31 个测试)

### 3. 覆盖率阈值
- **要求**: ≥90%
- **检查点**: Git 提交前、Cron 定时检查 (每 5 分钟)

---

## 📊 当前状态

### 核心模块覆盖率

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| `issue_queue.py` | 82% | ⚠️ 需改进 |
| `manager_interface.py` | 29% | ⚠️ 需改进 |
| **总体** | 27% | ❌ 未达标 |

### 测试用例

| 类型 | 数量 | 状态 |
|------|------|------|
| 单元测试 | 11 个 | ✅ |
| 集成测试 | 31 个 | ✅ |
| **总计** | **42 个** | ✅ |

---

## 🎯 下一步计划

### 需要补充的测试

1. **IssueQueue 完整测试** (目标：90%)
   - ✅ `test_create_issue`
   - ✅ `test_write_issue`
   - ✅ `test_read_issue`
   - ✅ `test_get_pending_issues`
   - ❌ `test_update_status` (需要适配 API)
   - ❌ `test_resolve_issue` (需要实现方法)
   - ❌ `test_archive_issue` (需要实现方法)

2. **QuantManager 完整测试** (目标：90%)
   - ✅ `test_get_status`
   - ✅ `test_issue_queue_access`
   - ❌ `test_handle_error_report` (需要适配)
   - ❌ `test_resolve_issue` (需要实现方法)

3. **VirtualAccount 测试** (目标：90%)
   - ✅ `test_account_file_structure`
   - ✅ `test_account_balance`
   - ❌ `test_buy_stock` (需要适配实际 API)
   - ❌ `test_sell_stock` (需要适配实际 API)

---

## 📋 执行流程

### 提交前检查

```bash
# 自动触发 (Git hook)
git commit -m "feat: 新功能"

# 手动触发
python3 qa_change_gate.py
```

### 检查步骤

1. **检测代码变更**
2. **运行覆盖率检查** (必须≥90%)
3. **运行 QA 闭环测试**
4. **生成质量报告**
5. **允许/禁止提交**

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `.coveragerc` | 覆盖率配置 |
| `qa_change_gate.py` | QA 门禁系统 |
| `tests/unit/` | 单元测试目录 |
| `tests/integration/` | 集成测试目录 |
| `COVERAGE_REQUIREMENT.md` | 覆盖率要求文档 |
| `htmlcov/` | HTML 覆盖率报告 |

---

## 🚀 提高覆盖率指南

### 1. 为核心方法添加测试

```python
# 示例：为 issue_queue 添加测试
def test_update_status():
    from issue_queue import IssueQueue
    iq = IssueQueue()
    issue = iq.create_issue('agent', 'P1', 'Error', 'Message')
    issue_id = iq.write_issue(issue)
    
    iq.update_status(issue_id, 'processing', 'reviewer')
    updated = iq.read_issue(issue_id)
    
    assert updated.status == 'processing'
    assert updated.assigned_to == 'reviewer'
```

### 2. 测试边界条件

```python
def test_edge_cases():
    # 空值
    assert process(None) == default
    
    # 极值
    assert process(0) == expected_zero
    
    # 异常
    with pytest.raises(ValueError):
        process(invalid_input)
```

### 3. 使用参数化测试

```python
@pytest.mark.parametrize('input,expected', [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected
```

---

## ⚠️ 强制规则

**必须遵守:**

1. ✅ 新增代码必须有测试
2. ✅ 修改代码必须更新测试
3. ✅ 覆盖率必须≥90%
4. ✅ 所有测试必须通过

**禁止行为:**

❌ 绕过覆盖率检查  
❌ 降低覆盖率阈值  
❌ 排除核心代码  
❌ 使用 `--no-verify` 跳过检查

---

**状态**: 🔄 实施中 (当前 27%, 目标 90%)  
**最后更新**: 2026-03-15  
**维护者**: QA Team
