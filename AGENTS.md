# VNPY Alpha 交易系统 - AI Agent 指南

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-21  
> **维护者**: Atlas (Chief Architect AI)

---

## 📋 项目概述

VNPY Alpha 是一个基于 Python 的量化交易系统，专注于 A 股市场的行业轮动策略和多因子选股。

### 核心能力
- **行业轮动策略**: 基于动量、估值、资金流的行业评分系统
- **多因子选股**: 价值、成长、质量、股息等多维度筛选
- **数据管道**: Tushare/AKShare 双数据源，自动故障转移
- **回测引擎**: 支持日级/分钟级回测，完整的归因分析

### 技术栈
- **语言**: Python 3.11+
- **核心框架**: VNPY (vnpy 核心)
- **数据源**: Tushare Pro, AKShare
- **测试**: pytest (集成测试 + 单元测试)
- **部署**: 单机运行，支持 cron 调度

---

## 🏗️ 项目架构

```
vnpy/
├── alpha/                    # Alpha 策略模块
│   ├── strategy/            # 策略实现
│   │   ├── industry_rotation.py      # 行业轮动策略（核心）
│   │   ├── stock_screener_strategy.py # 选股策略基类
│   │   ├── cross_sectional_engine.py  # 截面分析引擎
│   │   └── preset_strategies.py       # 预设策略配置
│   └── dataset/             # 数据集处理
├── core/                    # 核心基础设施
│   ├── proxy_pool.py        # 代理池管理
│   ├── circuit_breaker.py   # 熔断器
│   └── data_source_router.py # 数据源路由
├── data/                    # 数据存储
│   ├── fundamental/         # 基本面数据
│   ├── capital_flow/        # 资金流数据
│   └── akshare/            # AKShare 缓存
├── tests/                   # 测试目录
│   ├── integration/         # 集成测试
│   └── fixtures/           # 测试数据
├── vnpy/                    # VNPY 核心框架（子模块）
├── docs/                    # 文档
└── scripts/                 # 工具脚本
```

---

## 🎯 核心模块详解

### 1. 行业轮动策略 (`alpha/strategy/industry_rotation.py`)

**职责**: 基于多维度评分的行业轮动选股

**关键类**:
- `IndustryRotationStrategy`: 主策略类
- `ValuationFetcher`: 估值数据获取（支持 Tushare/AKShare 双源）
- `safe_float()`: 安全数值转换（防护 NaN/Inf）
- `_normalize_symbol()`: 股票代码标准化（支持北交所）

**数据流**:
```
原始行情 → 行业评分计算 → 选股 → 组合构建 → 归因分析
         ↓
    [动量, 估值, 资金流, 波动率]
```

**关键方法**:
- `_calculate_industry_scores()`: 计算行业综合得分
- `_select_stocks_in_industries()`: 行业内选股
- `_get_industry_valuation()`: 获取行业估值（含 fallback 逻辑）
- `_calculate_industry_turnover()`: 计算行业换手率

**边界条件处理** (已修复):
- ✅ `safe_float()` 防护 `math.isinf()`
- ✅ `_normalize_symbol()` 支持北交所 (83/87/88/43 → .BSE)
- ✅ `_calculate_industry_turnover()` 除零保护
- ✅ 估值缓存穿透时记录 warning 日志

### 2. 数据源路由 (`core/data_source_router.py`)

**职责**: 多数据源自动故障转移

**支持的数据源**:
- Tushare Pro (主)
- AKShare (备)
- 本地缓存 (最终 fallback)

**熔断机制**:
- 连续失败 3 次 → 触发熔断
- 熔断后 5 分钟自动恢复
- 支持手动重置

### 3. 估值数据获取 (`ValuationFetcher`)

**缓存策略**:
```
内存缓存 → 本地 Parquet → Tushare API → AKShare API → 硬编码 fallback
```

**Fallback 值** (不可信):
- PE: 15.0
- PB: 2.0
- 股息率: 1.5

**日志**: 使用 fallback 时会记录 `logger.warning()`

---

## 🧪 测试策略

### 测试结构
```
tests/
├── integration/
│   └── test_industry_rotation.py  # 22 个测试用例
└── fixtures/
    └── mock_data.py               # Mock 数据
```

### 运行测试
```bash
# 运行所有集成测试
python3 -m pytest tests/integration/ -v

# 运行特定测试
python3 -m pytest tests/integration/test_industry_rotation.py::TestIndustryRotationValuation -v

# 生成覆盖率报告
python3 -m pytest --cov=alpha.strategy --cov-report=html
```

### 测试覆盖范围
- ✅ 策略实例化
- ✅ 行业评分计算
- ✅ 估值数据获取（含 fallback）
- ✅ 代码标准化（含北交所）
- ✅ 边界条件（除零、NaN、Inf）

---

## 📝 代码约定

### 命名规范
- **类名**: PascalCase (如 `IndustryRotationStrategy`)
- **方法/变量**: snake_case (如 `_calculate_industry_scores`)
- **常量**: UPPER_SNAKE_CASE (如 `INDUSTRY_STOCKS`)
- **私有方法**: 前缀 `_` (如 `_normalize_symbol`)

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

# 级别使用
logger.debug()    # 调试信息（开发环境）
logger.info()     # 正常运行信息
logger.warning()  # 潜在问题（如 fallback）
logger.error()    # 错误但可恢复
logger.critical() # 严重错误，程序可能崩溃
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

## 🔧 常见问题与解决方案

### 1. 估值数据获取失败
**症状**: 日志中出现 "Valuation cache penetration"
**原因**: Tushare/AKShare 数据源均不可用
**解决**: 
- 检查网络连接
- 验证 API token 有效性
- 系统会自动使用 fallback 值（PE=15, PB=2）

### 2. 北交所代码识别错误
**症状**: 83/87/88/43 开头的代码被错误映射到 .SZSE
**解决**: 已修复，`_normalize_symbol()` 现在正确识别北交所代码

### 3. 行业换手率计算异常
**症状**: 返回 NaN 或 Inf
**原因**: `total_volume == 0` 导致除零
**解决**: 已修复，现在返回 0.0

### 4. 测试失败
**排查步骤**:
1. 确认 Python 版本 >= 3.11
2. 安装依赖: `pip install -r requirements.txt`
3. 检查 mock 数据是否完整
4. 运行单个测试定位问题

---

## 🚀 运行与部署

### 本地运行
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行策略
python3 scripts/run_industry_rotation.py

# 查看日志
tail -f logs/strategy.log
```

### Cron 调度（示例）
```bash
# 每个交易日 14:30 运行
30 14 * * 1-5 cd /path/to/vnpy && python3 scripts/run_industry_rotation.py >> logs/cron.log 2>&1
```

---

## 📊 性能指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 策略初始化 | < 2s | ~1.5s |
| 行业评分计算 | < 500ms | ~300ms |
| 估值数据获取 | < 1s (缓存) | ~200ms |
| 测试套件 | < 5s | ~2s |

---

## 🔒 安全注意事项

### API Token 管理
- **不要**在代码中硬编码 token
- 使用环境变量: `export TUSHARE_TOKEN=xxx`
- `.env` 文件已加入 `.gitignore`

### 数据访问
- 所有外部 API 调用通过 `data_source_router.py`
- 支持代理池（`proxy_pool.py`）
- 熔断器保护（`circuit_breaker.py`）

---

## 🤝 贡献指南

### 代码审查清单
- [ ] 所有测试通过
- [ ] 新增边界条件处理
- [ ] 添加适当的日志
- [ ] 更新文档（如需要）
- [ ] 代码符合 PEP 8

### 提交流程
1. 创建功能分支: `git checkout -b feature/xxx`
2. 提交变更: `git commit -m "feat: xxx"`
3. 推送并创建 PR
4. 等待 Atlas 审查

---

## 📚 相关文档

- [架构设计文档](docs/ARCHITECTURE.md) - 系统架构详解
- [数据流图](docs/DATA_FLOW.md) - 数据处理流程
- [API 参考](docs/API_REFERENCE.md) - 核心类/方法说明
- [变更日志](CHANGELOG.md) - 版本历史

---

## 🆘 获取帮助

### 内部资源
- 查看 `docs/` 目录
- 搜索历史 issue
- 联系 Atlas (Chief Architect)

### 外部资源
- [VNPY 官方文档](https://www.vnpy.com/docs/)
- [Tushare API 文档](https://tushare.pro/document/2)
- [AKShare 文档](https://akshare.akfamily.xyz/)

---

**最后更新**: 2026-06-21 by Atlas
