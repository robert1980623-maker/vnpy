# API Reference

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-21  
> **适用对象**: 开发者 + AI Agent

---

## 📦 核心模块

### alpha.strategy.industry_rotation

行业轮动策略核心模块。

#### `IndustryRotationStrategy`

主策略类，实现行业轮动选股逻辑。

```python
from alpha.strategy.industry_rotation import IndustryRotationStrategy

strategy = IndustryRotationStrategy(
    name='行业轮动',
    max_positions=10,
    position_size=0.1,
    rebalance_days=20,
    max_pe=20,
    max_pb=3,
    top_industries=3,
)
```

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | `'行业轮动'` | 策略名称 |
| `max_positions` | int | `10` | 最大持仓数量 |
| `position_size` | float | `0.1` | 单只股票仓位比例 |
| `rebalance_days` | int | `20` | 调仓周期（天） |
| `max_pe` | float | `20` | 最大市盈率 |
| `max_pb` | float | `3` | 最大市净率 |
| `top_industries` | int | `3` | 选择前 N 个行业 |

**核心方法**:

```python
# 计算行业综合得分
scores = strategy._calculate_industry_scores(industry='bank')
# 返回: {'momentum': 0.8, 'valuation': 0.6, 'capital_flow': 0.7, 'volatility': 0.5, 'total': 0.68}

# 行业内选股
stocks = strategy._select_stocks_in_industries(industry='bank', count=5)
# 返回: ['600000.SSE', '600016.SSE', ...]

# 获取行业估值
valuation = strategy._get_industry_valuation(industry='bank')
# 返回: (PE=8.5, PB=0.9, dividend_yield=3.2, source='cache')

# 计算行业换手率
turnover = strategy._calculate_industry_turnover(stocks=['600000.SSE'], bars=bars_data)
# 返回: 0.05
```

#### `ValuationFetcher`

估值数据获取类，支持 Tushare/AKShare 双数据源。

```python
from alpha.strategy.industry_rotation import ValuationFetcher

fetcher = ValuationFetcher()
```

**核心方法**:

```python
# 获取单个股票估值
result = fetcher._fetch_symbol_valuation(symbol='000001.SZSE')
# 返回: (PE=12.5, PB=1.2, dividend_yield=2.5, source='tushare')

# 缓存策略: 内存 → Parquet → Tushare → AKShare → Fallback
# Fallback 值: PE=15.0, PB=2.0, dividend_yield=1.5
```

#### `safe_float()`

安全数值转换函数，防护 NaN/Inf。

```python
from alpha.strategy.industry_rotation import safe_float

safe_float('12.5')        # 返回: 12.5
safe_float('nan')         # 返回: None
safe_float(float('inf'))  # 返回: None
safe_float(None)          # 返回: None
safe_float('', default=0) # 返回: 0
```

#### `_normalize_symbol()`

股票代码标准化函数，支持北交所。

```python
from alpha.strategy.industry_rotation import _normalize_symbol

_normalize_symbol('600000')  # 返回: '600000.SSE' (上海)
_normalize_symbol('000001')  # 返回: '000001.SZSE' (深圳)
_normalize_symbol('830001')  # 返回: '830001.BSE' (北交所)
_normalize_symbol('688001')  # 返回: '688001.SSE' (科创板)
```

---

### alpha.strategy.stock_screener_strategy

选股策略基类模块。

#### `StockScreenerStrategy`

选股策略抽象基类。

```python
from alpha.strategy.stock_screener_strategy import StockScreenerStrategy

class MyStrategy(StockScreenerStrategy):
    def screen_stocks(self, universe: List[str]) -> List[str]:
        # 实现选股逻辑
        return selected_stocks
    
    def calculate_score(self, stock: str) -> float:
        # 实现评分逻辑
        return score
    
    def should_rebalance(self) -> bool:
        # 判断是否需要调仓
        return True
```

**派生策略**:

```python
from alpha.strategy.stock_screener_strategy import (
    ValueStockStrategy,      # 价值股策略
    GrowthStockStrategy,     # 成长股策略
    QualityStockStrategy,    # 质量股策略
    DividendStockStrategy,   # 高股息策略
)

# 创建策略
strategy = ValueStockStrategy(max_pe=15, max_pb=2)
strategy = GrowthStockStrategy(min_revenue_growth=0.2)
strategy = QualityStockStrategy(min_roe=0.15)
strategy = DividendStockStrategy(min_dividend_yield=0.03)
```

#### `create_strategy()`

策略工厂函数。

```python
from alpha.strategy.stock_screener_strategy import create_strategy

strategy = create_strategy(
    strategy_type='value',
    params={'max_pe': 15, 'max_pb': 2}
)
```

---

### alpha.strategy.cross_sectional_engine

截面分析引擎模块。

#### `CrossSectionalBacktestingEngine`

截面回测引擎，支持涨跌停/T+1/流动性/滑点。

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import CrossSectionalBacktestingEngine
from alpha.strategy.industry_rotation import IndustryRotationStrategy
from vnpy.trader.constant import Interval
from datetime import datetime

lab = AlphaLab('/Users/rowang/projects/vnpy/lab/data')
engine = CrossSectionalBacktestingEngine(lab)

# 设置回测参数
engine.set_parameters(
    vt_symbols=['000001.SZSE', '600000.SSE', '600036.SSE'],
    interval=Interval.DAILY,
    start=datetime(2026, 3, 1),
    end=datetime(2026, 4, 14),
    capital=1_000_000,
)

# 加载数据
engine.load_data()

# 添加策略
engine.add_strategy(IndustryRotationStrategy, setting={
    'name': '行业轮动',
    'max_positions': 10,
    'position_size': 0.1,
    'rebalance_days': 20,
})

# 执行回测
engine.run_backtesting()

# 获取统计结果
stats = engine.calculate_statistics()
print(f"年化收益: {stats['annual_return']:.2%}")
print(f"最大回撤: {stats['max_drawdown']:.2%}")
print(f"Sharpe: {stats['sharpe_ratio']:.2f}")
```

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `vt_symbols` | List[str] | 股票代码列表 |
| `interval` | Interval | K线周期（DAILY/MINUTE） |
| `start` | datetime | 回测开始日期 |
| `end` | datetime | 回测结束日期 |
| `capital` | float | 初始资金 |

**配置选项**:

```python
engine = CrossSectionalBacktestingEngine(
    lab,
    limit_up_down=True,      # 涨跌停限制
    t_plus_1=True,           # T+1 限制
    liquidity_filter=True,   # 流动性过滤
    slippage=0.001,          # 滑点（0.1%）
)
```

---

### core.data_source_router

数据源路由模块。

#### `DataSourceRouter`

多数据源自动路由和故障转移。

```python
from core.data_source_router import DataSourceRouter

router = DataSourceRouter()

# 获取数据（自动故障转移）
data = router.fetch(symbol='000001.SZSE', data_type='daily')
```

**数据源优先级**:

1. Tushare Pro（主）
2. AKShare（备）
3. 本地缓存（最终 fallback）

**熔断机制**:

```python
# 连续失败 3 次 → 触发熔断
# 熔断后 5 分钟自动恢复
# 支持手动重置
router.reset_circuit_breaker('tushare')
```

---

### core.circuit_breaker

熔断器模块。

#### `CircuitBreaker`

防止级联故障。

```python
from core.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=3,      # 失败阈值
    recovery_timeout=300,     # 恢复超时（秒）
)

# 记录失败
breaker.record_failure('tushare')

# 检查是否可以执行
if breaker.can_execute('tushare'):
    # 执行操作
    pass
```

**状态**:

- `CLOSED` - 正常状态
- `OPEN` - 熔断状态
- `HALF_OPEN` - 半开状态（尝试恢复）

---

### core.proxy_pool

代理池模块。

#### `ProxyPool`

管理代理 IP 池。

```python
from core.proxy_pool import ProxyPool

pool = ProxyPool()

# 获取可用代理
proxy = pool.get_proxy()
if proxy:
    print(f"使用代理: {proxy}")

# 报告代理失败
pool.report_failure(proxy)
```

---

## 📊 数据类型

### BarData

K线数据结构。

```python
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from datetime import datetime

bar = BarData(
    symbol='000001',
    exchange=Exchange.SZSE,
    datetime=datetime(2026, 6, 20),
    interval=Interval.DAILY,
    open_price=10.5,
    high_price=10.8,
    low_price=10.3,
    close_price=10.6,
    volume=1000000,
    turnover=10500000,
    open_interest=0,
)
```

### Interval

K线周期枚举。

```python
from vnpy.trader.constant import Interval

Interval.DAILY    # 日线
Interval.MINUTE   # 分钟线
Interval.HOUR     # 小时线
Interval.WEEKLY   # 周线
```

---

## 🔧 工具函数

### 数据转换

```python
from alpha.strategy.industry_rotation import safe_float

# 安全转换为 float
safe_float('12.5')        # 12.5
safe_float('nan')         # None
safe_float(float('inf'))  # None
```

### 代码标准化

```python
from alpha.strategy.industry_rotation import _normalize_symbol

# 标准化股票代码
_normalize_symbol('600000')  # '600000.SSE'
_normalize_symbol('000001')  # '000001.SZSE'
_normalize_symbol('830001')  # '830001.BSE'
```

---

## 📝 常量

### 行业股票池

```python
from alpha.strategy.industry_rotation import INDUSTRY_STOCKS

# 行业股票定义
INDUSTRY_STOCKS = {
    'bank': ['600000.SSE', '600016.SSE', ...],
    'securities': ['600030.SSE', ...],
    'insurance': ['601318.SSE', ...],
    'liquor': ['600519.SSE', ...],
    # ... 更多行业
}
```

### 估值 Fallback 值

```python
# 当所有数据源失败时使用的默认值
FALLBACK_PE = 15.0
FALLBACK_PB = 2.0
FALLBACK_DIVIDEND_YIELD = 1.5
```

---

## 🆘 错误处理

### 常见异常

```python
from alpha.strategy.industry_rotation import ValuationFetcher

fetcher = ValuationFetcher()

try:
    result = fetcher._fetch_symbol_valuation('000001.SZSE')
except ValueError as e:
    print(f"数据格式错误: {e}")
except ConnectionError as e:
    print(f"网络连接失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 日志级别

```python
import logging

logging.debug()    # 调试信息（开发环境）
logging.info()     # 正常运行信息
logging.warning()  # 潜在问题（如 fallback）
logging.error()    # 错误但可恢复
logging.critical() # 严重错误，程序可能崩溃
```

---

## 📚 相关文档

- [AGENTS.md](../AGENTS.md) - 通用 AI agent 指南
- [CLAUDE.md](../CLAUDE.md) - Claude Code 操作指南
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构详解

---

**最后更新**: 2026-06-21 by Atlas
