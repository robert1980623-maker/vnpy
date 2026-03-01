# 实盘交易配置说明

本文档说明如何使用选股策略系统进行实盘交易。

## 📁 配置文件

系统提供 3 个配置文件：

| 文件 | 用途 | 适用阶段 |
|------|------|---------|
| `config/paper_config.yaml` | 模拟交易配置 | 阶段一：模拟交易 |
| `config/live_config.yaml` | 实盘交易配置 (小资金) | 阶段二：小资金测试 |
| `config/auto_config.yaml` | 自动化交易配置 | 阶段三：正式运行 |

## 🚀 快速开始

### 1. 模拟交易 (推荐先做这个)

```bash
# 启动模拟交易
python3 start_trading.py --mode paper
```

**说明**:
- 使用虚拟资金 (默认 100 万)
- 验证策略逻辑
- 熟悉操作流程
- 建议运行 1-2 周

### 2. 实盘交易 (小资金测试)

**前置准备**:
1. 开通证券账户
2. 申请 API 交易权限
3. 获取 API 密钥

**配置券商信息**:
```bash
# 编辑配置文件
vim config/live_config.yaml

# 修改以下内容:
broker:
  account: "your_account"     # 你的证券账号
  password: "your_password"   # 你的密码
  api_key: "your_api_key"     # 你的 API 密钥
```

**启动实盘**:
```bash
python3 start_trading.py --mode live
```

**⚠️ 重要**:
- 首次实盘建议开启 `manual_confirm: true`
- 每笔交易都会要求手动确认
- 建议投入 1-5 万元测试

### 3. 自动化交易

**前置条件**:
- ✅ 模拟交易 2 周以上
- ✅ 小资金实盘 2 周以上
- ✅ 确认策略稳定有效

**启动自动化**:
```bash
python3 start_trading.py --mode auto
```

**⚠️ 警告**:
- 自动化交易无需手动确认
- 请确保风险控制参数设置合理
- 建议设置告警通知

## 📊 配置参数说明

### 账户配置 (account)

```yaml
account:
  initial_capital: 1000000    # 初始资金
  mode: paper                 # 交易模式：paper/live
```

### 策略配置 (strategy)

```yaml
strategy:
  name: value                 # 策略名称：value/growth/quality/dividend
  max_pe: 20                  # 最大市盈率
  min_roe: 10                 # 最小 ROE(%)
  min_dividend_yield: 2.0     # 最小股息率 (%)
  max_positions: 30           # 最大持仓数量
```

### 交易配置 (trading)

```yaml
trading:
  position_size: 0.03         # 单只股票仓位 (3%)
  rebalance_days: 20          # 调仓周期 (20 天)
  commission_rate: 0.0003     # 手续费率 (万分之三)
  slippage: 0.01              # 滑点 (1%)
  manual_confirm: true        # 手动确认交易
```

### 风险控制 (risk_control)

```yaml
risk_control:
  max_daily_loss: 0.02        # 日最大亏损 (2%)
  max_position_ratio: 0.95    # 最大仓位 (95%)
  stop_loss: 0.10             # 单只止损 (10%)
  max_sector_ratio: 0.40      # 单一行业最大仓位 (40%)
```

## 📋 每日操作流程

### 开盘前 (9:00-9:15)

```bash
# 1. 查看系统状态
python3 start_trading.py --mode paper --check

# 2. 运行选股
python3 start_trading.py --mode paper --select-only
```

### 交易中 (14:50-15:00)

```bash
# 执行调仓
python3 start_trading.py --mode paper --trade-only
```

### 收盘后 (15:30 以后)

```bash
# 生成日报
python3 generate_report.py --daily

# 查看报告
open reports/daily_report_*.html
```

## ⚠️ 注意事项

### 模拟交易阶段

- ✅ 至少运行 1-2 周
- ✅ 熟悉所有操作流程
- ✅ 验证策略有效性
- ✅ 记录问题和异常

### 小资金实盘阶段

- ✅ 开启手动确认
- ✅ 每笔交易仔细核对
- ✅ 记录滑点和手续费
- ✅ 对比模拟和实盘差异

### 自动化交易阶段

- ✅ 设置告警通知
- ✅ 每日检查运行状态
- ✅ 定期复盘和优化
- ✅ 备份配置文件

## 🔧 故障排查

### 问题 1: 无法连接券商 API

**解决**:
1. 检查网络连接
2. 确认账号密码正确
3. 确认 API 权限已开通
4. 查看日志：`tail -f logs/trading.log`

### 问题 2: 数据更新失败

**解决**:
1. 手动更新数据：`python3 download_optimized.py --max 50 --cache`
2. 检查数据源状态
3. 使用备用数据源

### 问题 3: 交易执行失败

**解决**:
1. 检查账户资金是否充足
2. 检查持仓是否足够 (卖出时)
3. 检查是否停牌
4. 查看错误日志

## 📞 获取帮助

### 文档
- 实盘计划：`docs/alpha/LIVE_TRADING_PLAN.md`
- 快速指南：`docs/alpha/QUICK_START.md`
- API 文档：`docs/alpha/`

### 日志
```bash
# 查看实时日志
tail -f logs/trading.log

# 查看错误日志
tail -f logs/error.log
```

### 报告
```bash
# 查看最新报告
ls -lt reports/

# 打开日报
open reports/daily_report_*.html
```

---

**祝投资顺利！** [耶]
