# 测试编写指南

## 目录结构

```
tests/
├── unit/                   # 单元测试
│   ├── __init__.py
│   └── test_*.py
├── integration/           # 集成测试
│   ├── __init__.py
│   └── test_*.py
├── e2e/                  # 端到端测试
│   ├── __init__.py
│   └── test_*.py
├── mocks/                # Mock对象
│   ├── __init__.py
│   └── *.py
├── fixtures/             # Fixtures
│   ├── __init__.py
│   └── *.py
├── templates/            # 测试模板
│   ├── unit_test_template.py
│   ├── integration_test_template.py
│   └── conftest.py
└── TESTING_GUIDE.md      # 本指南
```

## 测试类型

### 1. 单元测试 (Unit Tests)
- 测试单个函数、方法或类
- 隔离被测代码与其他组件
- 快速、可靠、易于调试
- 文件命名: `test_*.py` 或 `*_test.py`

### 2. 集成测试 (Integration Tests)
- 测试多个组件间的交互
- 验证系统整体功能
- 可能涉及外部依赖（使用mock或测试环境）

### 3. 端到端测试 (End-to-End Tests)
- 模拟真实用户场景
- 测试完整的工作流程

## 编写规范

### Pytest 风格
```python
def test_descriptive_name():
    # 使用清晰的测试函数名描述预期行为
    pass

def test_when_condition_then_expected_outcome():
    # 描述性命名：条件 -> 结果
    pass
```

### AAA 模式 (Arrange, Act, Assert)
```python
def test_user_authentication():
    # Arrange - 设置测试条件
    user = User("test@example.com", "password")
    auth_service = AuthService()
    
    # Act - 执行被测代码
    result = auth_service.authenticate(user)
    
    # Assert - 验证结果
    assert result.success is True
```

### Mock 使用
```python
from unittest.mock import Mock, patch

def test_with_external_api():
    # 使用 patch 装饰器mock外部依赖
    with patch('myapp.external_api.call') as mock_api:
        mock_api.return_value = {'status': 'ok'}
        
        result = my_function()
        
        mock_api.assert_called_once()
        assert result == expected_result
```

### Fixtures
```python
@pytest.fixture
def sample_data():
    return {'key': 'value'}

def test_with_fixture(sample_data):
    # 使用fixture提供测试数据
    assert sample_data['key'] == 'value'
```

## 测试覆盖率

### 运行覆盖率检查
```bash
# 运行所有测试并生成覆盖率报告
pytest --cov=src/ --cov-report=html --cov-report=term

# 只运行单元测试
pytest tests/unit/

# 运行特定测试文件
pytest tests/unit/test_specific_module.py
```

### 覆盖率标准
- 新增代码: 100% 覆盖率
- 核心功能: ≥90% 覆盖率
- 整体项目: ≥80% 覆盖率

## 最佳实践

1. **测试独立性**: 每个测试应独立运行，不依赖其他测试
2. **快速执行**: 测试应在合理时间内完成
3. **可读性**: 测试代码应清晰易懂
4. **确定性**: 测试结果应一致，避免随机失败
5. **关注边界条件**: 测试异常和边界情况
6. **文档化**: 为复杂测试添加注释说明

## 常用断言

```python
# 基本断言
assert value == expected
assert value != unexpected

# 类型断言
assert isinstance(obj, MyClass)

# 异常断言
with pytest.raises(ValueError):
    risky_function()

# 容器断言
assert len(items) == 5
assert 'item' in items

# 浮点数比较
from pytest import approx
assert actual == approx(expected, rel=1e-3)
```

## 标记和筛选

```python
# 标记慢测试
@pytest.mark.slow
def test_long_running_process():
    pass

# 标记集成测试
@pytest.mark.integration
def test_database_connection():
    pass

# 运行标记的测试
# pytest -m "integration"
# pytest -m "not slow"
```
