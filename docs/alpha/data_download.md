# 数据下载文档

## 📦 脚本位置

```
examples/alpha_research/
├── download_data_rq.py         # RQData 下载脚本（付费数据源）
├── download_data_simple.py     # 简化版下载脚本（免费数据源）
└── check_data_quality.py       # 数据质量检查工具
```

## 🚀 快速开始

### 方法 1：使用 AKShare 免费数据（推荐新手）

```bash
# 安装依赖
pip install akshare

# 运行下载脚本
cd examples/alpha_research
python download_data_simple.py
```

**特点**：
- ✅ 免费数据源
- ✅ 无需账号
- ✅ 包含 300 只主流股票
- ✅ 自动配置测试环境

### 方法 2：使用 RQData 专业数据（推荐实盘）

```bash
# 安装依赖
pip install rqdatac

# 编辑脚本配置（填写账号）
# 修改 download_data_rq.py 中的 RQ_USER 和 RQ_PASSWORD

# 运行下载脚本
python download_data_rq.py
```

**特点**：
- ✅ 全市场数据
- ✅ 完整的财务数据
- ✅ 指数成分股历史数据
- ✅ 高质量数据源

## 📝 详细使用说明

### 1. AKShare 下载脚本

**文件**: `download_data_simple.py`

**功能**：
- 下载 300 只主流股票日频数据
- 创建测试股票池
- 生成模拟信号数据

**配置**：
```python
# 时间范围（默认最近 1 年）
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)

# 股票池（可自定义）
TEST_SYMBOLS = [
    "000001.SZSE",  # 平安银行
    "000002.SZSE",  # 万科 A
    # ... 更多股票
]
```

**运行**：
```bash
python download_data_simple.py
```

**输出**：
```
数据保存路径：/path/to/data
实验室路径：/path/to/lab/test_strategy

创建示例股票池
✅ 创建测试股票池：300 只股票
✅ 创建沪深 300 样本池：300 只股票

下载测试数据（使用 AKShare 免费数据源）
股票数量：300
时间范围：2024-01-01 - 2024-12-31

[1/300] 000001.SZSE ✅ 245 条记录
[2/300] 000002.SZSE ✅ 245 条记录
...

下载完成
成功：300/300
总记录数：73,500
```

### 2. RQData 下载脚本

**文件**: `download_data_rq.py`

**功能**：
- 下载 8 大指数成分股历史数据
- 下载全市场财务数据
- 下载股票日频数据
- 自动生成选股信号

**配置**：
```python
# RQData 登录信息
RQ_USER = "your_username"
RQ_PASSWORD = "your_password"

# 时间范围
START_DATE = "2020-01-01"
END_DATE = "2024-12-31"

# 指数列表
INDICES = {
    "csi300": "000300.XSHG",    # 沪深 300
    "csi500": "000905.XSHG",    # 中证 500
    "csi1000": "000852.XSHG",   # 中证 1000
    # ...
}
```

**运行**：
```bash
python download_data_rq.py
```

**输出**：
```
开始下载指数成分股数据

📊 下载 csi300 (000300.XSHG) 成分股...
  ✅ 已保存 1,200 个交易日的成分股数据
  📈 最新成分股数量 (2024-12-31): 300 只

📊 下载财务数据...
  ✅ 已保存 50,000 条季度财务数据

📈 生成选股信号...
  ✅ 生成 360,000 条信号记录
```

### 3. 数据质量检查

**文件**: `check_data_quality.py`

**功能**：
- 检查数据完整性
- 检查交易日连续性
- 检查信号数据质量
- 生成摘要报告

**运行**：
```bash
python check_data_quality.py
```

**输出**：
```
数据完整性检查
📊 找到 300 只股票的数据

000001.SZSE:
  记录数：245
  时间范围：2024-01-01 - 2024-12-31
  零成交天数：0
  极端涨跌幅天数：2

交易日连续性检查
📊 总交易日数：245
✅ 数据连续性良好

信号数据检查
📊 找到 245 个交易日的信号

2024-01-01:
  股票数：300
  信号统计：均值=0.001, 标准差=0.577

数据摘要报告
股票数据:
  - 股票数量：300
  - 总记录数：73,500

信号数据:
  - 交易日数：245
  - 总记录数：73,500
```

## 📊 数据格式

### 股票数据（Parquet）

**位置**: `lab/daily/*.parquet`

**字段**：
```
- datetime: 日期时间
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- volume: 成交量
- turnover: 成交额
- open_interest: 持仓量（股票为 0）
```

### 信号数据（Parquet）

**位置**: `lab/signal/signals_YYYY-MM-DD.parquet`

**字段**：
```
- datetime: 日期时间
- vt_symbol: 股票代码
- signal: 信号值（用于排序）
- pe_ratio: 市盈率（可选）
- roe: 净资产收益率（可选）
```

### 股票池数据（Shelve）

**位置**: `lab/component/*.db`

**格式**：
```python
{
    "2024-01-01": ["000001.SZSE", "000002.SZSE", ...],
    "2024-01-02": ["000001.SZSE", "000002.SZSE", ...],
    ...
}
```

## 🔧 自定义配置

### 修改股票池

编辑 `download_data_simple.py`：

```python
# 自定义股票池
TEST_SYMBOLS = [
    "000001.SZSE",  # 平安银行
    "000002.SZSE",  # 万科 A
    "000063.SZSE",  # 中兴通讯
    # 添加更多股票...
]
```

### 修改时间范围

```python
# 下载最近 3 年数据
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365*3)
```

### 自定义信号生成

```python
# 在 download_data_simple.py 中修改 generate_test_signals()
def generate_test_signals() -> None:
    # 使用基本面数据生成信号
    for dt in trading_dates:
        signal_data = []
        for vt_symbol in TEST_SYMBOLS:
            # 计算真实信号
            signal = calculate_signal(vt_symbol, dt)
            signal_data.append({
                "datetime": dt,
                "vt_symbol": vt_symbol,
                "signal": signal,
            })
```

## ⚠️ 注意事项

### AKShare 数据

1. **数据量** - 单次下载不宜过大，建议分批
2. **频率限制** - 避免过快请求，可能被限流
3. **复权处理** - 默认不复权，回测时注意
4. **停牌股票** - 部分股票可能数据不全

### RQData 数据

1. **账号权限** - 确保账号有足够权限
2. **数据范围** - 根据订阅级别可能有限制
3. **财务数据滞后** - 财报数据有披露滞后
4. **成分股调整** - 指数成分股定期调整

### 通用

1. **磁盘空间** - 全市场数据约需 1-2GB
2. **内存占用** - 大数据集需要足够内存
3. **网络稳定** - 下载过程保持网络稳定
4. **数据校验** - 下载完成后建议运行质量检查

## 🎯 使用示例

### 回测测试

```python
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.trader.constant import Interval

# 创建实验室
lab = AlphaLab("./lab/test_strategy")

# 创建回测引擎
engine = create_cross_sectional_engine(lab)

# 设置参数
engine.set_parameters(
    vt_symbols=[],  # 从信号中获取
    interval=Interval.DAILY,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000
)

# 添加策略
engine.add_strategy(
    ValueStockStrategy,
    setting={
        "max_pe": 20,
        "max_pb": 3,
        "min_dividend_yield": 2,
        "top_k": 30
    }
)

# 运行回测
engine.load_data()
engine.run_backtesting()
engine.calculate_statistics()
engine.show_chart()
```

### 查看数据

```python
from vnpy.alpha.lab import AlphaLab

lab = AlphaLab("./lab/test_strategy")

# 查看股票数据
df = lab.load_bar_df(
    vt_symbols=["000001.SZSE"],
    interval=Interval.DAILY,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    extended_days=0
)

print(df.head())

# 查看信号数据
signals = lab.load_signals(
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

print(signals.head())
```

## 📖 相关文档

- [股票池管理](stock_pool.md)
- [财务数据](fundamental_data.md)
- [截面回测](cross_sectional_backtesting.md)
- [选股策略](stock_screener_strategy.md)

## 🆘 常见问题

### Q1: 下载失败怎么办？

**A**: 检查网络连接，确认股票代码格式正确，稍后重试。

### Q2: 数据量太大怎么办？

**A**: 减少股票数量或缩短时间范围，分批下载。

### Q3: 信号数据为空？

**A**: 检查财务数据是否正确下载，确认信号生成逻辑。

### Q4: 回测报错？

**A**: 运行 `check_data_quality.py` 检查数据完整性。

---

[耶]
