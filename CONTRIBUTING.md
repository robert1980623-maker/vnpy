# Contributing Guide

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-21  
> **适用对象**: 人类开发者 + AI Agent

---

## 📋 贡献流程

### 1. 开发环境准备

```bash
# 克隆项目
git clone https://github.com/robert1980623-maker/vnpy.git
cd vnpy

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .

# 配置环境变量
export TUSHARE_TOKEN=***
```

### 2. 开发工作流

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 开发 + 测试
python3 -m pytest tests/ -v

# 提交变更
git add .
git commit -m "feat: 添加 xxx 功能"

# 推送并创建 PR
git push origin feature/your-feature-name
```

### 3. 代码审查清单

提交 PR 前，请确认：

- [ ] 所有测试通过 (`python3 -m pytest tests/ -v`)
- [ ] 新增代码有单元测试
- [ ] 边界条件已处理（NaN/Inf/除零/空值）
- [ ] 日志记录完整（使用 `logging` 模块）
- [ ] 文档已更新（如需要）
- [ ] 代码符合 PEP 8 规范

---

## 🎯 代码规范

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `IndustryRotationStrategy` |
| 函数/方法 | snake_case | `_calculate_industry_scores` |
| 常量 | UPPER_SNAKE_CASE | `INDUSTRY_STOCKS` |
| 私有方法 | 前缀 `_` | `_normalize_symbol` |
| 模块名 | snake_case | `industry_rotation.py` |

### 导入顺序

```python
# 1. 标准库
import math
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# 2. 第三方库
import numpy as np
import pandas as pd

# 3. 本地模块
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from alpha.strategy.stock_screener_strategy import StockScreenerStrategy
```

### 日志规范

```python
import logging
logger = logging.getLogger(__name__)

# ✅ 正确：使用 logging 模块
logger.info("策略初始化完成")
logger.warning("估值数据获取失败，使用 fallback")
logger.error("数据源不可用: %s", error_msg)

# ❌ 避免：print 语句
print("策略初始化完成")  # 不要这样做
```

### 错误处理

```python
# ✅ 推荐：明确的 fallback + 日志
try:
    result = fetch_data()
except Exception as e:
    logger.warning(f"Data fetch failed: {e}, using fallback")
    result = DEFAULT_VALUE

# ❌ 避免：静默吞掉异常
try:
    result = fetch_data()
except:
    pass  # 不要这样做
```

---

## 🧪 测试规范

### 测试结构

```
tests/
├── integration/          # 集成测试
│   ├── test_industry_rotation.py
│   └── test_manager_flow.py
└── unit/                 # 单元测试（待补充）
    ├── test_safe_float.py
    └── test_normalize_symbol.py
```

### 测试命名

```python
# ✅ 正确：描述性命名
def test_safe_float_handles_nan():
    assert safe_float('nan') is None

def test_normalize_symbol_bse_codes():
    assert _normalize_symbol('830001') == '830001.BSE'

# ❌ 避免：模糊命名
def test_1():
    pass
```

### 测试覆盖范围

每个新功能/修复必须包含：

1. **正常路径测试** - 验证功能正确性
2. **边界条件测试** - NaN/Inf/0/None/空字符串
3. **错误处理测试** - API 失败、数据缺失
4. **代码标准化测试** - 各交易所代码格式

### 运行测试

```bash
# 所有测试
python3 -m pytest tests/ -v

# 特定模块
python3 -m pytest tests/integration/test_industry_rotation.py -v

# 生成覆盖率报告
python3 -m pytest --cov=alpha.strategy --cov-report=html
```

---

## 📝 Commit Message 规范

### 格式

```
<type>: <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加行业轮动策略` |
| `fix` | Bug 修复 | `fix: 修复北交所代码识别错误` |
| `docs` | 文档更新 | `docs: 更新 AGENTS.md` |
| `style` | 代码格式 | `style: 统一日志格式` |
| `refactor` | 重构 | `refactor: 提取估值获取逻辑` |
| `test` | 测试相关 | `test: 添加边界条件测试` |
| `chore` | 构建/工具 | `chore: 更新依赖版本` |

### 示例

```bash
# ✅ 好的 commit message
git commit -m "fix: 修复 industry_rotation.py 的 4 个 P0 边界条件问题

1. safe_float(): 添加 math.isinf() 防护
2. _normalize_symbol(): 北交所代码标准化（83/87/88/43 → .BSE）
3. _calculate_industry_turnover(): 除零保护
4. 估值缓存穿透: 添加 warning 日志

修复由 coding-agents CLI (Claude Code) 完成，22 个测试全部通过。"

# ❌ 避免：模糊的 commit message
git commit -m "fix bug"
git commit -m "update code"
```

---

## 🔒 安全规范

### API Token 管理

```python
# ✅ 从环境变量读取
import os
TUSHARE_TOKEN = ***'TUSHARE_TOKEN')
if not TUSHARE_TOKEN:
    *** ValueError("TUSHARE_TOKEN not set")

# ❌ 不要硬编码
TUSHARE_TOKEN = '***'  # 危险！
```

### 数据验证

```python
# ✅ 验证输入数据
def process_data(data: Dict) -> Dict:
    if not isinstance(data, dict):
        raise ValueError("Expected dict")
    if 'price' not in data:
        raise KeyError("Missing 'price' field")
    if data['price'] <= 0:
        raise ValueError("Price must be positive")
    return data
```

---

## 📚 文档规范

### 新增功能

必须更新：

1. **AGENTS.md** - 如果影响架构
2. **CLAUDE.md** - 如果影响代码修改流程
3. **docs/ARCHITECTURE.md** - 如果影响系统架构
4. **README.md** - 如果影响用户使用
5. **CHANGELOG.md** - 所有变更

### 文档格式

- 使用 Markdown 格式
- 中文撰写，技术术语保留英文
- 代码示例必须可运行
- 架构图用 Mermaid 或 ASCII

---

## 🤖 AI Agent 贡献指南

### 使用 Coding Agent CLI

```bash
# 1. Atlas 设计 + 拆解任务
# 2. 委托给 Claude Code
coding-agents dispatch claude "修复 xxx 问题" \
  --workdir /Users/rowang/projects/vnpy \
  --budget 2.0

# 3. 监控进度
coding-agents status <session_id>

# 4. 审查结果
git diff
python3 -m pytest tests/ -v

# 5. 提交
git commit -m "fix: xxx"
```

### Budget 指导

| 任务类型 | Budget | 示例 |
|---------|--------|------|
| Trivial | 0.3-0.5 | 简单修复、文档更新 |
| Small | 1-2 | 单文件修改、添加测试 |
| Medium | 2-5 | 多文件重构、新功能 |
| Large | 5-10 | 架构改造、性能优化 |

---

## 🆘 获取帮助

### 内部资源

- 查看 [AGENTS.md](AGENTS.md) 了解项目架构
- 查看 [CLAUDE.md](CLAUDE.md) 了解代码修改流程
- 查看 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 了解系统架构
- 搜索历史 issue

### 外部资源

- [VNPY 官方文档](https://www.vnpy.com/docs/)
- [Tushare API 文档](https://tushare.pro/document/2)
- [AKShare 文档](https://akshare.akfamily.xyz/)

---

## 📝 审查流程

### 代码审查

1. **功能正确性** - 代码是否实现了预期功能？
2. **边界条件** - 是否处理了 NaN/Inf/除零/空值？
3. **错误处理** - 是否有明确的 fallback + 日志？
4. **测试覆盖** - 是否有足够的测试？
5. **文档更新** - 是否更新了相关文档？
6. **性能影响** - 是否引入了性能问题？

### 合并标准

- ✅ 所有 CI 检查通过
- ✅ 至少 1 个审查者批准
- ✅ 无未解决的评论
- ✅ 与主分支无冲突

---

**最后更新**: 2026-06-21 by Atlas
