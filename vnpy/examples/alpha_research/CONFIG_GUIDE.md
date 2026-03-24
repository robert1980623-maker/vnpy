# 配置文件使用指南

**文件**: `config.yaml`  
**版本**: 1.0  
**最后更新**: 2026-03-01

---

## 📖 概述

`config.yaml` 是量化交易系统的统一配置文件，集中管理所有参数设置。

**优势**:
- ✅ 无需修改代码即可调整参数
- ✅ 所有配置集中管理，易于维护
- ✅ 支持不同环境（开发/生产/测试）
- ✅ 命令行参数可覆盖配置值

---

## 🚀 快速开始

### 1. 使用默认配置

```bash
# 直接使用默认配置运行
python3 main.py
```

系统会自动加载 `config.yaml` 中的默认值。

---

### 2. 指定配置文件

```bash
# 使用自定义配置文件
python3 main.py --config my_config.yaml
```

---

### 3. 命令行覆盖配置

```bash
# 配置文件设置 stocks=10，命令行覆盖为 5
python3 main.py --config config.yaml --stocks 5

# 使用不同的策略
python3 main.py --config config.yaml --strategy momentum
```

**优先级**: 命令行参数 > 配置文件 > 内置默认值

---

## 📋 配置项详解

### 1. 数据配置 (`data`)

```yaml
data:
  source: akshare              # 数据源：akshare | baostock | rqdata
  directory: ./data/akshare/bars  # 数据保存目录
  max_workers: 4               # 并行下载线程数
  max_stocks: 20               # 单次最大下载数量
  force_download: false        # 是否强制重新下载
  
  # 数据质量检查
  quality_check:
    enabled: true
    min_days: 60               # 最少交易日
    max_missing_rate: 0.05     # 最大缺失率 5%
```

**常用场景**:
```yaml
# 快速测试（只下载少量数据）
data:
  max_stocks: 5
  max_workers: 2

# 生产环境（下载更多数据）
data:
  max_stocks: 100
  max_workers: 8
  force_download: false
```

---

### 2. 交易配置 (`trading`)

```yaml
trading:
  initial_capital: 1000000     # 初始资金 100 万
  commission_rate: 0.0003      # 手续费率 万分之三
  slippage: 0.01               # 滑点 1%
  default_volume: 1000         # 默认买入数量
  
  # 仓位控制
  max_position_pct: 0.2        # 单只股票最大仓位 20%
  
  # 交易成本
  cost_calculation:
    include_commission: true   # 包含手续费
    include_slippage: true     # 包含滑点
    include_tax: true          # 包含印花税
    tax_rate: 0.001            # 印花税千分之一
```

**常用场景**:
```yaml
# 保守策略（小仓位）
trading:
  initial_capital: 500000
  max_position_pct: 0.1
  default_volume: 500

# 激进策略（大仓位）
trading:
  initial_capital: 2000000
  max_position_pct: 0.3
  default_volume: 2000
```

---

### 3. 策略配置 (`strategy`)

```yaml
strategy:
  default_strategy: value      # 默认策略
  default_pool: hs300          # 默认股票池
  max_stocks: 10               # 最大选股数量
  
  # 策略参数
  parameters:
    value:
      max_pe: 20               # 最大市盈率
      max_pb: 3                # 最大市净率
      min_roe: 0.10            # 最小 ROE 10%
    
    growth:
      min_revenue_growth: 0.20   # 最小营收增长 20%
      min_profit_growth: 0.25    # 最小净利润增长 25%
    
    momentum:
      lookback_days: 20          # 回看天数
      min_momentum: 0.05         # 最小动量 5%
```

**常用场景**:
```yaml
# 价值投资
strategy:
  default_strategy: value
  parameters:
    value:
      max_pe: 15
      max_pb: 2
      min_roe: 0.15

# 成长股投资
strategy:
  default_strategy: growth
  parameters:
    growth:
      min_revenue_growth: 0.30
      min_profit_growth: 0.40
```

---

### 4. 回测配置 (`backtest`)

```yaml
backtest:
  start_date: "20250101"       # 开始日期
  end_date: "20260301"         # 结束日期
  mode: daily                  # 回测模式
  benchmark: 000300.SH         # 基准指数
  rebalance_days: 5            # 再平衡周期
  
  # 绩效指标
  metrics:
    - total_return
    - annual_return
    - sharpe_ratio
    - max_drawdown
  
  # 可视化
  visualization:
    enabled: true
    save_path: ./backtest_result.html
```

---

### 5. 日志配置 (`logging`)

```yaml
logging:
  level: INFO                  # 日志级别
  directory: ./logs            # 日志目录
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # 输出方式
  output:
    console: true              # 控制台输出
    file: true                 # 文件输出
    rotate: false              # 文件轮转
    max_size_mb: 100           # 单个文件最大 100MB
```

**常用场景**:
```yaml
# 开发调试（详细日志）
logging:
  level: DEBUG
  output:
    console: true
    file: true

# 生产环境（仅警告和错误）
logging:
  level: WARNING
  output:
    console: false
    file: true
```

---

### 6. 股票池配置 (`stock_pool`)

```yaml
stock_pool:
  # 沪深 300
  hs300:
    index_code: 000300.SH
    auto_update: true
    update_frequency: monthly
  
  # 中证 500
  zz500:
    index_code: 000905.SH
    auto_update: true
  
  # 自定义股票池
  custom:
    stocks:
      - 000001.SZ
      - 000002.SZ
      - 600000.SH
      - 600519.SH
```

---

### 7. 缓存配置 (`cache`)

```yaml
cache:
  enabled: true                # 启用缓存
  directory: ./cache           # 缓存目录
  ttl_hours: 24                # 缓存有效期 24 小时
  type: disk                   # 缓存类型：memory | disk
  max_size_mb: 500             # 最大缓存大小
```

---

### 8. 高级配置 (`advanced`)

```yaml
advanced:
  python_path: python3         # Python 路径
  working_directory: ./        # 工作目录
  lab_directory: ./lab/test    # Lab 目录
  max_retries: 3               # 最大重试次数
  retry_interval: 2            # 重试间隔（秒）
  
  # 超时设置
  timeout:
    download: 300              # 下载超时 5 分钟
    backtest: 600              # 回测超时 10 分钟
    trading: 60                # 交易超时 1 分钟
```

---

## 🔧 环境特定配置

### 开发环境

```yaml
# 在 config.yaml 末尾添加
development:
  logging:
    level: DEBUG
  data:
    max_stocks: 5
  trading:
    initial_capital: 100000
```

**使用方式**:
```bash
# 手动指定开发配置
python3 main.py --config config.dev.yaml
```

---

### 生产环境

```yaml
production:
  logging:
    level: WARNING
  trading:
    initial_capital: 10000000
  notification:
    enabled: true
```

---

### 测试环境

```yaml
testing:
  data:
    source: mock             # 使用模拟数据
  trading:
    initial_capital: 100000
```

---

## 📝 配置文件模板

### 最小配置（快速开始）

```yaml
# config.minimal.yaml
strategy:
  default_strategy: value
  max_stocks: 5

trading:
  initial_capital: 100000
  default_volume: 500

logging:
  level: INFO
```

---

### 完整配置（生产环境）

```yaml
# config.production.yaml
data:
  source: akshare
  directory: ./data/akshare/bars
  max_workers: 8
  max_stocks: 100

trading:
  initial_capital: 10000000
  commission_rate: 0.0003
  slippage: 0.01
  default_volume: 5000
  max_position_pct: 0.15

strategy:
  default_strategy: value
  max_stocks: 20
  parameters:
    value:
      max_pe: 20
      max_pb: 3
      min_roe: 0.10

backtest:
  start_date: "20240101"
  end_date: "20260301"
  benchmark: 000300.SH
  rebalance_days: 5

logging:
  level: INFO
  directory: ./logs
  output:
    console: false
    file: true
    rotate: true
    max_size_mb: 100

notification:
  enabled: true
  methods:
    - email
  events:
    - trade_executed
    - daily_summary
    - error_alert
```

---

## 💡 最佳实践

### 1. 版本控制

```bash
# 提交配置文件到 Git
git add config.yaml
git commit -m "feat: 添加配置文件"
```

**注意**: 不要提交包含敏感信息的配置（如密码、API Key）

---

### 2. 配置继承

```bash
# 基础配置
cp config.yaml config.base.yaml

# 开发配置（基于基础配置修改）
cp config.yaml config.dev.yaml
# 编辑 config.dev.yaml，只修改开发环境特定的值

# 生产配置
cp config.yaml config.prod.yaml
# 编辑 config.prod.yaml
```

---

### 3. 配置验证

```bash
# 检查配置文件语法
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 查看当前配置
python3 main.py --config config.yaml --help
```

---

### 4. 配置备份

```bash
# 备份当前配置
cp config.yaml config.backup.$(date +%Y%m%d).yaml

# 恢复配置
cp config.backup.20260301.yaml config.yaml
```

---

## 🐛 常见问题

### Q1: 配置文件不生效？

**检查**:
1. 文件路径是否正确
2. YAML 语法是否正确
3. 配置项名称是否拼写正确

```bash
# 验证 YAML 语法
python3 -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

---

### Q2: 命令行参数和配置冲突？

**规则**: 命令行参数 > 配置文件 > 内置默认值

```bash
# 配置文件中 stocks=10，命令行指定 stocks=5
# 实际使用 5
python3 main.py --config config.yaml --stocks 5
```

---

### Q3: 如何添加自定义配置项？

1. 在 `config.yaml` 中添加新配置项
2. 在 `main.py` 中读取配置
3. 应用到相应功能

```yaml
# config.yaml
my_custom_setting:
  value: 123
```

```python
# main.py
custom_value = config.get('my_custom_setting', {}).get('value', 100)
```

---

### Q4: PyYAML 未安装？

```bash
# 安装 PyYAML
pip3 install pyyaml

# 如果提示权限问题
pip3 install pyyaml --break-system-packages
```

---

## 📊 配置项速查表

| 配置项 | 路径 | 默认值 | 说明 |
|--------|------|--------|------|
| 数据源 | `data.source` | akshare | 数据提供商 |
| 数据目录 | `data.directory` | ./data/akshare/bars | 数据保存位置 |
| 初始资金 | `trading.initial_capital` | 1000000 | 模拟交易资金 |
| 手续费率 | `trading.commission_rate` | 0.0003 | 万分之三 |
| 默认策略 | `strategy.default_strategy` | value | 选股策略 |
| 选股数量 | `strategy.max_stocks` | 10 | 最大选股数 |
| 日志级别 | `logging.level` | INFO | DEBUG/INFO/WARNING/ERROR |
| 回测开始日期 | `backtest.start_date` | 20250101 | 回测区间 |
| 缓存启用 | `cache.enabled` | true | 是否启用缓存 |

---

## 🎯 下一步

1. ✅ 复制 `config.yaml` 为 `config.my.yaml`
2. ✅ 根据自己的需求修改参数
3. ✅ 运行测试：`python3 main.py --config config.my.yaml`
4. ✅ 验证配置是否生效

---

**配置文件版本**: 1.0  
**最后更新**: 2026-03-01  
**维护者**: vnpy 开发团队

[耶]
