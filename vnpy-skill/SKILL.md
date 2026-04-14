---
name: vnpy-quant
description: >
  VNPY A 股量化交易系统操作指南。涵盖：每日选股、数据下载与转换、
  回测验证、持仓管理、生产迁移。当用户提到 vnpy、量化交易、选股、
  回测、持仓、仓位、数据下载、策略配置、生产迁移时使用。
---

# VNPY 量化交易系统

## 系统架构

```
/Users/rowang/projects/vnpy/
│
├── alpha/strategy/
│   ├── cross_sectional_engine.py    # 截面回测引擎（涨跌停/T+1/流动性/滑点）
│   ├── industry_rotation.py         # 行业轮动策略
│   └── stock_screener_strategy.py   # 选股策略基类
├── examples/alpha_research/
│   ├── csv_to_parquet.py            # CSV → Parquet 转换
│   ├── tushare_pro_downloader.py    # Tushare 数据下载
│   ├── build_fina_cache.py          # 财务指标缓存构建
│   ├── check_data_freshness.py      # 数据新鲜度诊断
│   ├── daily_stock_selection.py     # 每日选股
│   ├── vnpy_config.yaml             # 统一配置
│   └── accounts/virtual_2026_account.json
├── lab/data/daily/                  # ⭐ AlphaLab 数据目录
│   └── *.parquet                    # 4579+ 只股票日线
└── data/akshare/bars/*.csv          # 原始日线数据 4627 只
```

## 场景 1：每日选股（最常用）

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
export TUSHARE_TOKEN=xxx

# 一键选股（自动检查数据→修复→执行）
python3 daily_stock_selection.py
```

选股流程：加载股票池 → 批量获取财务数据 (Tushare v2, ~1s) → 多策略筛选 → 生成交易计划 → 同步飞书多维表格

## 场景 2：数据新鲜度检查与修复

### 检查

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 check_data_freshness.py
```

输出示例：
```
📊 VNPY 数据新鲜度报告
状态：OK

📊 检查项:
  parquet_count: 4579 ✅
  parquet_date_range: 2026-04-13 ~ 2026-04-13
  parquet_sample_size: 45 (动态抽样)
  alphalab_load: 9 条 ✅
  fundamental_cache: 9397 ✅
  positions: 8 ✅
  tushare: Token 未设置

🔧 建议:
  → export TUSHARE_TOKEN=xxx
```

### 修复（CSV 有数据但 Parquet 缺失）

```bash
python3 csv_to_parquet.py --lab-dir /Users/rowang/projects/vnpy/lab/data --start 2026-03-06 --end 2026-04-14
```

### 修复（CSV 数据缺失）

```bash
# 下载持仓股
TUSHARE_TOKEN=xxx python3 tushare_pro_downloader.py --all --date 20260414

# 全市场补数据
TUSHARE_TOKEN=xxx python3 tushare_pro_downloader.py --all --start-date 20260306 --end-date 20260414
```

## 场景 3：持仓重建（事故恢复）

positions 数组为空时，从 trades 重建：

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 rebuild_positions.py
```

## 场景 4：回测验证（迁移前必须）

```python
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
from alpha.strategy.industry_rotation import IndustryRotationStrategy
from vnpy.trader.constant import Interval

lab = AlphaLab('/Users/rowang/projects/vnpy/lab/data')
engine = CrossSectionalBacktestingEngine(lab)

# 设置回测参数（initial_capital 在这里传）
engine.set_parameters(
    vt_symbols=['000001.SZSE', '600000.SSE', '600036.SSE'],
    interval=Interval.DAILY,
    start=datetime(2026, 3, 1),
    end=datetime(2026, 4, 14),
    capital=1_000_000,
)

# 加载数据
engine.load_data()

# 添加策略（setting 的 key 必须匹配策略 __init__ 参数名）
engine.add_strategy(IndustryRotationStrategy, setting={
    'name': '行业轮动',
    'max_positions': 10,
    'position_size': 0.1,
    'rebalance_days': 20,
    'max_pe': 20,
    'max_pb': 3,
    'top_industries': 3,
})

# 执行回测
engine.run_backtesting()

# 查看统计结果
stats = engine.calculate_statistics()
print(f'年化收益: {stats.get("annual_return", 0):.2%}')
print(f'最大回撤: {stats.get("max_drawdown", 0):.2%}')
print(f'Sharpe: {stats.get("sharpe_ratio", 0):.2f}')
```

## 场景 5：生产迁移

**⚠️ 必须先通过回测验证，不能直接切生产。**

迁移步骤：
1. 确认 positions 非空 → 场景 3
2. 确认数据最新（Parquet > 4000 只）→ 场景 2
3. 跑基准回测（修复前 commit）→ 场景 4
4. 跑新版回测 → 场景 4
5. 对比信号差异（相关性 < 0.7 需重新调参）
6. 虚拟盘运行至少 1 个调仓周期（5-20 天）
7. 确认无误后切实盘

## 配置与数据

### 关键配置
- `vnpy_config.yaml` — 统一配置（delta_consumer, manager, alert 等）
- `from vnpy_config import get_delta_consumer_config` — 获取配置

### Tushare Token
```bash
export TUSHARE_TOKEN=612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5
```

### 数据格式
Parquet 列名：`[datetime, open, high, low, close, volume, turnover, open_interest]`
由 `AlphaLab.save_bar_data()` 自动处理，无需手动构造。

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| AlphaLab 加载 0 条 | Parquet 目录无文件或路径不对 | 运行 csv_to_parquet.py |
| import 失败 | 不在项目根目录 | `cd /Users/rowang/projects/vnpy` |
| positions 为空 | 4·13 事故后遗症 | 运行 rebuild_positions.py |
| 选股超时 | 旧版逐只获取财务数据 | 已改为批量接口（~1s） |
| CSV 格式混乱 | Tushare 和 AKShare 混写 | csv_to_parquet.py 支持双格式 |
| 'daily' is not valid Interval | 传了字符串而非枚举 | 用 `Interval.DAILY`，不要用 `'daily'` |
