# VNPY 架构参考

## 核心模块

### AlphaLab (`vnpy/alpha/lab.py`)
数据管理中心，负责 parquet 格式日线/分钟线的读写。
- `save_bar_data(bars)` — 写入 parquet
- `load_bar_data(vt_symbol, interval, start, end)` — 读取历史数据
- `load_bar_df(vt_symbol, interval, start, end)` — 返回 polars DataFrame

### 截面回测引擎 (`vnpy/alpha/strategy/cross_sectional_engine.py`)
- 支持涨跌停限制、T+1、流动性约束、最小交易单位、滑点
- `send_order()` — 下单入口，自动应用执行细节

### 行业轮动策略 (`alpha/strategy/industry_rotation.py`)
- 继承自 `StockScreenerStrategy`
- 行业动量 + 估值筛选 + 行业内选股
- `_get_industry_valuation()` 从成分股动态计算平均 PE/PB

## 数据路径

| 类型 | 路径 |
|------|------|
| 原始 CSV | `examples/alpha_research/data/akshare/bars/*.csv` |
| Parquet | `examples/alpha_research/lab/*/daily/*.parquet` |
| 财务缓存 | `examples/alpha_research/cache/fundamental/*.json` |
| 账户 | `examples/alpha_research/accounts/virtual_2026_account.json` |
| 配置 | `examples/alpha_research/vnpy_config.yaml` |

## 策略继承链

```
AlphaStrategy (template.py)
  └── StockScreenerStrategy (strategies/)
        └── IndustryRotationStrategy (industry_rotation.py)
```
