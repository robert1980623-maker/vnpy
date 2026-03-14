# 代码覆盖率强制要求

## 📋 核心原则

**所有代码变更必须保证覆盖率≥90%**

这是强制要求，不可绕过。

---

## 🎯 覆盖率标准

| 指标 | 要求 | 检查方式 |
|------|------|----------|
| **总体覆盖率** | ≥90% | 强制 |
| **核心模块覆盖率** | ≥90% | 强制 |
| **新增代码覆盖率** | ≥90% | 强制 |
| **测试用例通过率** | 100% | 强制 |

---

## 📊 检查流程

### QA 门禁流程

```
代码变更 → 检测变更 → 覆盖率检查 (≥90%) → QA 闭环 → 质量报告 → 允许/禁止提交
              ↓            ↓                    ↓          ↓           ↓
           5 分钟      运行测试            qa_loop    生成报告    ✅/❌
```

### 覆盖率检查步骤

1. **清除历史覆盖率数据**
   ```bash
   python3 -m coverage erase
   ```

2. **运行测试并收集覆盖率**
   ```bash
   python3 -m coverage run --source=. -m pytest tests/ -v
   ```

3. **生成覆盖率报告**
   ```bash
   python3 -m coverage report --fail-under=90
   ```

4. **生成 HTML 详细报告**
   ```bash
   python3 -m coverage html
   # 查看：open htmlcov/index.html
   ```

---

## 📁 覆盖率配置文件

### .coveragerc

```ini
[run]
source = .
omit = 
    venv/*
    tests/*
    test_*.py
    data/*
    reports/*

[report]
fail_under = 90.0
show_missing = True
precision = 2

[html]
directory = htmlcov
```

---

## 🧪 测试类型

### 1. 单元测试 (tests/unit/)

测试核心功能，确保代码逻辑正确。

**示例**:
```python
def test_create_issue():
    from issue_queue import IssueQueue
    iq = IssueQueue()
    issue = iq.create_issue('agent', 'P1', 'Error', 'Message')
    assert issue.severity == 'P1'
```

### 2. 集成测试 (tests/integration/)

测试系统整体功能，确保各模块协作正常。

**示例**:
```python
def test_data_pipeline():
    from manager_interface import QuantManager
    manager = QuantManager()
    status = manager.get_status()
    assert 'pending_issues' in status
```

---

## 📈 覆盖率报告示例

```
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
issue_queue.py               50      5  90.00%   43-47
manager_interface.py         66      6  90.91%   113-118
virtual_account.py           80      7  91.25%   25-31
-------------------------------------------------------
TOTAL                       196     18  90.82%

✅ 代码覆盖率 ≥ 90%
```

---

## ⚠️ 未达标处理

### 如果覆盖率<90%

1. **查看详细报告**
   ```bash
   python3 -m coverage report -m
   # -m 显示缺失覆盖率的行号
   ```

2. **查看 HTML 报告**
   ```bash
   python3 -m coverage html
   open htmlcov/index.html
   ```

3. **补充测试用例**
   - 针对未覆盖的代码行编写测试
   - 确保边界条件都被测试

4. **重新运行检查**
   ```bash
   python3 qa_change_gate.py
   ```

---

## 🚫 禁止行为

❌ **降低覆盖率阈值**
```ini
# 禁止修改 .coveragerc 中的 fail_under
fail_under = 90.0  # ✅ 正确
fail_under = 80.0  # ❌ 禁止
```

❌ **绕过覆盖率检查**
```bash
# 禁止跳过覆盖率检查
python3 qa_change_gate.py --skip-coverage  # ❌ 禁止
```

❌ **排除核心代码**
```ini
# 禁止排除核心模块
omit = 
    core_module.py  # ❌ 禁止
```

---

## 🎯 最佳实践

### 1. 测试驱动开发 (TDD)

```python
# 先写测试
def test_new_feature():
    assert new_feature() == expected

# 再实现功能
def new_feature():
    return expected
```

### 2. 边界条件测试

```python
def test_edge_cases():
    # 空值
    assert process(None) == default
    
    # 极值
    assert process(0) == expected_zero
    assert process(MAX_VALUE) == expected_max
    
    # 异常
    with pytest.raises(ValueError):
        process(invalid_input)
```

### 3. 参数化测试

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

## 📞 故障排查

### 常见问题

**Q: 覆盖率一直不达标？**
```bash
# 查看哪些文件覆盖率最低
python3 -m coverage report --sort=cover

# 查看具体缺失的行
python3 -m coverage report -m
```

**Q: 某些代码无法测试？**
```python
# 使用 pragma: no cover 标记
def debug_only():  # pragma: no cover
    print("Debug info")
```

**Q: 想查看历史覆盖率趋势？**
```bash
# 查看质量报告历史
ls -lt change_logs/quality_report_*.json
cat change_logs/quality_report_YYYYMMDD_HHMMSS.json
```

---

## 📚 相关工具

| 工具 | 用途 | 命令 |
|------|------|------|
| coverage.py | 覆盖率收集 | `python3 -m coverage run` |
| pytest-cov | pytest 集成 | `pytest --cov=. tests/` |
| coverage report | 文本报告 | `coverage report` |
| coverage html | HTML 报告 | `coverage html` |

---

## 📊 质量报告内容

每个质量报告包含：

```json
{
  "report_id": "QA-20260315_023400",
  "qa_results": {
    "qa_loop_passed": true,
    "coverage_passed": true,
    "coverage_value": 92.5,
    "coverage_threshold": 90.0,
    "overall_passed": true
  },
  "verdict": "✅ APPROVED"
}
```

---

**最后更新**: 2026-03-15  
**维护者**: QA Team  
**状态**: ✅ 已启用 (≥90%)
