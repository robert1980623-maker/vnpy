# VNPY Alpha 量化交易系统

> **A 股行业轮动 + 多因子选股量化交易系统**  
> **版本**: 1.0.0  
> **最后更新**: 2026-06-21

---

## 📋 项目简介

VNPY Alpha 是一个基于 Python 的量化交易系统，专注于 A 股市场的**行业轮动策略**和**多因子选股**。

### 核心能力
- 🎯 **行业轮动策略**: 基于动量、估值、资金流的行业评分系统
- 📊 **多因子选股**: 价值、成长、质量、股息等多维度筛选
- 🔄 **数据管道**: Tushare/AKShare 双数据源，自动故障转移
- 🧪 **回测引擎**: 支持日级/分钟级回测，完整的归因分析
- 🤖 **AI 友好**: 完整的 AI agent 维护文档（见 [AGENTS.md](AGENTS.md)）

---

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/robert1980623-maker/vnpy.git
cd vnpy

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 2. 配置 API Token
```bash
export TUSHARE_TOKEN=***
```

### 3. 运行每日选股
```bash
cd examples/alpha_research
python3 daily_stock_selection.py
```

### 4. 运行测试
```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行特定测试
python3 -m pytest tests/integration/test_industry_rotation.py -v
```

---

## 📁 项目结构

```
vnpy/
├── alpha/strategy/              # 策略模块
│   ├── industry_rotation.py     # 行业轮动策略（核心）
│   ├── stock_screener_strategy.py # 选股策略基类
│   ├── cross_sectional_engine.py  # 截面分析引擎
│   └── preset_strategies.py       # 预设策略配置
├── core/                        # 核心基础设施
│   ├── proxy_pool.py            # 代理池管理
│   ├── circuit_breaker.py       # 熔断器
│   └── data_source_router.py    # 数据源路由
├── data/                        # 数据存储
│   ├── fundamental/             # 基本面数据
│   ├── capital_flow/            # 资金流数据
│   └── akshare/                 # AKShare 缓存
├── tests/                       # 测试目录
│   ├── integration/             # 集成测试
│   └── fixtures/                # 测试数据
├── examples/alpha_research/     # 示例脚本
│   ├── daily_stock_selection.py # 每日选股
│   ├── tushare_pro_downloader.py # 数据下载
│   └── vnpy_config.yaml         # 统一配置
├── docs/                        # 文档
└── vnpy-skill/                  # OpenClaw Skill 定义
```

---

## 📚 文档导航

### 面向 AI Agent
- **[AGENTS.md](AGENTS.md)** - 通用 AI agent 指南（项目架构、核心模块、测试）
- **[CLAUDE.md](CLAUDE.md)** - Claude Code 特定操作指南
- **[vnpy-skill/SKILL.md](vnpy-skill/SKILL.md)** - 操作场景（选股、回测、持仓）

### 面向开发者
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构详解
- **[docs/alpha/](docs/alpha/)** - Alpha 模块文档
  - [QUICK_START.md](docs/alpha/QUICK_START.md) - 快速入门
  - [TEST_REPORT.md](docs/alpha/TEST_REPORT.md) - 测试报告
  - [LIVE_TRADING_PLAN.md](docs/alpha/LIVE_TRADING_PLAN.md) - 实盘计划

### 面向研究者
- **[docs/study/](docs/study/)** - 量化投资学习资料
  - [01-量化投资基础.md](docs/study/01-量化投资基础.md)
  - [02-股票策略汇总.md](docs/study/02-股票策略汇总.md)
  - [03-风险管理指南.md](docs/study/03-风险管理指南.md)

---

## 🧪 测试

### 运行测试
```bash
# 所有测试
python3 -m pytest tests/ -v

# 特定模块
python3 -m pytest tests/integration/test_industry_rotation.py -v

# 生成覆盖率报告
python3 -m pytest --cov=alpha.strategy --cov-report=html
```

### 测试覆盖
- ✅ 策略实例化与配置
- ✅ 行业评分计算
- ✅ 估值数据获取（含 fallback）
- ✅ 代码标准化（含北交所）
- ✅ 边界条件（除零、NaN、Inf）

---

## 🔧 常用命令

### 数据管理
```bash
# 检查数据新鲜度
cd examples/alpha_research && python3 check_data_freshness.py

# 下载数据
TUSHARE_TOKEN=***

# CSV → Parquet
python3 csv_to_parquet.py --lab-dir /Users/rowang/projects/vnpy/lab/data
```

### 回测
```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
from alpha.strategy.industry_rotation import IndustryRotationStrategy
from vnpy.trader.constant import Interval
from datetime import datetime

lab = AlphaLab('/Users/rowang/projects/vnpy/lab/data')
engine = CrossSectionalBacktestingEngine(lab)
engine.set_parameters(
    vt_symbols=['000001.SZSE', '600000.SSE'],
    interval=Interval.DAILY,
    start=datetime(2026, 3, 1),
    end=datetime(2026, 4, 14),
    capital=1_000_000,
)
engine.load_data()
engine.add_strategy(IndustryRotationStrategy, setting={...})
engine.run_backtesting()
stats = engine.calculate_statistics()
```

---

## 📊 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 核心框架 | VNPY |
| 数据源 | Tushare Pro, AKShare |
| 测试 | pytest |
| 数据存储 | Parquet, SQLite |
| 部署 | 单机 + Cron |

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
4. 等待审查

---

## 📈 性能指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 策略初始化 | < 2s | ~1.5s |
| 行业评分计算 | < 500ms | ~300ms |
| 估值数据获取 | < 1s (缓存) | ~200ms |
| 测试套件 | < 5s | ~2s |

---

## 🔒 安全注意事项

- **不要**在代码中硬编码 API token
- 使用环境变量: `export TUSHARE_TOKEN=***
- `.env` 文件已加入 `.gitignore`
- 所有外部 API 调用通过 `data_source_router.py`

---

## 🆘 获取帮助

### 内部资源
- 查看 [AGENTS.md](AGENTS.md) 了解项目架构
- 查看 [CLAUDE.md](CLAUDE.md) 了解代码修改流程
- 搜索历史 issue

### 外部资源
- [VNPY 官方文档](https://www.vnpy.com/docs/)
- [Tushare API 文档](https://tushare.pro/document/2)
- [AKShare 文档](https://akshare.akfamily.xyz/)

---

## 📝 版本历史

见 [CHANGELOG.md](CHANGELOG.md)

---

## 📄 许可证

MIT License

---

**最后更新**: 2026-06-21 by Atlas
