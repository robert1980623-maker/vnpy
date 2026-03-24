# 实盘快速启动指南

**版本**: v1.0  
**更新日期**: 2026-03-02  
**预计时间**: 30 分钟完成配置

---

## 🚀 5 分钟快速了解

### 这是什么？

这是一个**自动化选股交易系统**，可以：
- ✅ 自动筛选优质股票 (价值股/成长股)
- ✅ 自动生成交易信号
- ✅ 模拟交易或实盘交易
- ✅ 自动调仓和再平衡

### 核心优势

| 特性 | 说明 |
|------|------|
| 🎯 策略驱动 | 基于财务指标的量化选股 |
| ⚡ 自动化 | 定时选股、自动调仓 |
| 🛡️ 风控完善 | 仓位控制、止损机制 |
| 📊 透明可追溯 | 完整日志、绩效报告 |

---

## 📋 实盘前的 3 个阶段

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  阶段一：模拟    │ →  │  阶段二：小资金  │ →  │  阶段三：正式    │
│  (1-2 周)         │    │  (2 周)           │    │  (持续)          │
└──────────────────┘    └──────────────────┘    └──────────────────┘
   ✅ 验证策略              ✅ 验证执行              ✅ 稳定运行
   ✅ 熟悉流程              ✅ 测试接口              ✅ 持续优化
```

---

## 🎯 阶段一：模拟交易 (推荐先做这个！)

### 第一步：准备环境 (5 分钟)

```bash
# 1. 进入项目目录
cd ~/projects/vnpy/examples/alpha_research

# 2. 检查依赖
python3 check_dependencies.py

# 3. 确认数据已下载
ls data/akshare/bars/*.csv | wc -l
# 应该显示：48
```

### 第二步：配置模拟账户 (2 分钟)

创建配置文件：
```bash
# 创建配置目录
mkdir -p config

# 创建模拟交易配置
cat > config/paper_config.yaml << 'EOF'
# 模拟交易配置

account:
  initial_capital: 1000000  # 初始资金 100 万
  mode: paper               # 模拟模式
  
strategy:
  name: value               # 价值股策略
  max_pe: 20                # 最大 PE
  min_roe: 10               # 最小 ROE(%)
  min_dividend_yield: 2.0   # 最小股息率 (%)
  max_positions: 30         # 最大持仓数
  
trading:
  position_size: 0.03       # 单只股票 3% 仓位
  rebalance_days: 20        # 20 天调仓一次
  commission_rate: 0.0003   # 手续费万分之三
  slippage: 0.01            # 1% 滑点
  
schedule:
  select_time: "09:15"      # 选股时间
  trade_time: "14:50"       # 交易时间
EOF
```

### 第三步：运行模拟交易 (1 分钟)

```bash
# 启动模拟交易
python3 paper_trading.py --config config/paper_config.yaml --mode paper
```

### 第四步：查看结果 (2 分钟)

模拟交易会输出：
```
============================================================
模拟交易账户
============================================================
初始资金：¥1,000,000
当前资金：¥1,025,000
收益率：+2.5%

持仓：
  600036.SH    招商银行    1000 股    均价：35.2    盈亏：+5.2%
  600519.SH    贵州茅台    200 股     均价：1680    盈亏：+3.1%

今日信号：
  买入：['000858.SZ', '600036.SH']
  卖出：['300750.SZ']
============================================================
```

---

## 💰 阶段二：小资金实盘

### 前置条件

- ✅ 模拟交易运行 1-2 周
- ✅ 熟悉所有操作流程
- ✅ 确认策略有效

### 第一步：选择券商

推荐券商 (支持 API):
| 券商 | API 类型 | 佣金 | 推荐度 |
|------|---------|------|--------|
| 华泰证券 | hts | 万 2.5 | ⭐⭐⭐⭐⭐ |
| 东方财富 | eastmoney | 万 2.5 | ⭐⭐⭐⭐ |
| 国泰君安 | gtja | 万 2.5 | ⭐⭐⭐⭐ |

### 第二步：开通账户

1. 开设证券账户 (线上/线下)
2. 申请 API 交易权限
3. 获取 API 密钥 (账号、密码、token)

### 第三步：配置实盘

```bash
# 创建实盘配置
cat > config/live_config.yaml << 'EOF'
# 实盘交易配置

account:
  initial_capital: 50000    # 初始资金 5 万 (测试用)
  mode: live                # 实盘模式
  
broker:
  name: hts                 # 华泰证券
  account: "your_account"   # 你的账号
  password: "your_password" # 你的密码
  
strategy:
  name: value
  max_pe: 20
  min_roe: 10
  min_dividend_yield: 2.0
  max_positions: 10         # 实盘减少持仓
  
trading:
  position_size: 0.1        # 单只 10% 仓位
  rebalance_days: 20
  commission_rate: 0.00025  # 实际佣金
  slippage: 0.01
  manual_confirm: true      # 手动确认交易 (初期建议开启)
EOF
```

### 第四步：小资金测试

```bash
# 启动实盘交易 (手动确认模式)
python3 paper_trading.py --config config/live_config.yaml --mode live
```

**⚠️ 重要提示**:
- 初期开启 `manual_confirm: true`
- 每笔交易都会要求确认
- 确认无误后再执行

---

## 🚀 阶段三：正式运行

### 自动化配置

```bash
# 创建自动化配置
cat > config/auto_config.yaml << 'EOF'
account:
  initial_capital: 200000   # 根据自己情况设定
  mode: live
  
broker:
  name: hts
  account: "your_account"
  password: "your_password"
  
strategy:
  name: value
  max_pe: 20
  min_roe: 10
  max_positions: 20
  
trading:
  position_size: 0.05       # 单只 5% 仓位
  manual_confirm: false     # 自动执行 (充分测试后开启)
  
risk_control:
  max_daily_loss: 0.02      # 日最大亏损 2%
  max_position_ratio: 0.95  # 最大仓位 95%
  stop_loss: 0.10           # 单只止损 10%
EOF
```

### 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下任务 (交易日运行)
# 周一至周五 9:15 选股
15 9 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 paper_trading.py --config config/auto_config.yaml --select-only

# 周一至周五 14:50 调仓
50 14 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 paper_trading.py --config config/auto_config.yaml --trade-only

# 周一至周五 15:30 生成日报
30 15 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 generate_report.py --daily
```

---

## 📊 每日操作流程

### 开盘前 (9:00-9:15)

```bash
# 1. 检查系统状态
python3 check_system.py

# 2. 查看今日选股
python3 paper_trading.py --config config/auto_config.yaml --select-only
```

**检查清单**:
- [ ] 数据更新正常
- [ ] 系统无异常告警
- [ ] 选股结果合理

### 交易中 (14:50-15:00)

```bash
# 执行调仓
python3 paper_trading.py --config config/auto_config.yaml --trade-only
```

**检查清单**:
- [ ] 买入列表确认
- [ ] 卖出列表确认
- [ ] 仓位计算正确

### 收盘后 (15:30 以后)

```bash
# 生成日报
python3 generate_report.py --daily

# 查看报告
open reports/daily_report_2026-03-02.html
```

**检查清单**:
- [ ] 查看今日收益
- [ ] 检查持仓变化
- [ ] 记录异常情况

---

## 📈 监控指标

### 每日必看

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| 日收益率 | -2% ~ +2% | <-3% 或 >+5% |
| 仓位利用率 | 80% ~ 95% | <70% 或 >98% |
| 持仓数量 | 15 ~ 25 只 | <10 或 >30 |

### 每周必看

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| 周收益率 | -5% ~ +5% | <-8% |
| 行业集中度 | <40% | >50% |
| 最大回撤 | <10% | >15% |

### 每月必看

| 指标 | 目标 | 警戒线 |
|------|------|--------|
| 月收益率 | +2% ~ +5% | <-5% |
| 月胜率 | >50% | <40% |
| 夏普比率 | >1.5 | <1.0 |

---

## ⚠️ 风险控制

### 仓位控制

```yaml
# 单只股票最大仓位
max_position_ratio: 0.10    # 10%

# 单一行业最大仓位
max_sector_ratio: 0.30      # 30%

# 总体最大仓位
max_total_ratio: 0.95       # 95%
```

### 止损设置

```yaml
# 单只股票止损
stop_loss: 0.10             # 亏损 10% 止损

# 日最大亏损
max_daily_loss: 0.02        # 2%

# 周最大亏损
max_weekly_loss: 0.05       # 5%
```

### 应急处理

**情况 1: 系统故障**
```bash
# 1. 立即停止自动交易
python3 paper_trading.py --stop

# 2. 检查日志
tail -f logs/trading.log

# 3. 手动平仓 (如需要)
python3 manual_close.py --all
```

**情况 2: 极端行情**
```bash
# 1. 暂停交易
python3 paper_trading.py --pause

# 2. 降低仓位
python3 manual_close.py --ratio 0.5

# 3. 等待市场稳定
```

---

## 📚 常见问题

### Q1: 需要多少资金起步？

**A**: 
- 模拟交易：0 元 (虚拟资金)
- 小资金测试：1-5 万元
- 正式运行：建议 20 万元以上

### Q2: 年化收益大概多少？

**A**: 
- 回测数据：15-25%
- 实盘预期：10-20% (考虑滑点和手续费)
- 市场波动会影响实际收益

### Q3: 最大回撤会是多少？

**A**: 
- 历史回测：<20%
- 实盘预期：<25%
- 通过仓位控制可以降低

### Q4: 需要每天盯着吗？

**A**: 
- 自动化后不需要
- 每日检查 1-2 次即可
- 收盘后查看报告

### Q5: 策略会失效吗？

**A**: 
- 任何策略都可能阶段性失效
- 建议：
  - 多策略分散 (2-3 个)
  - 定期评估和优化
  - 根据市场调整参数

---

## 🛠️ 工具命令速查

### 模拟交易
```bash
# 启动模拟
python3 paper_trading.py --config config/paper_config.yaml --mode paper

# 查看持仓
python3 paper_trading.py --show-positions

# 查看信号
python3 paper_trading.py --show-signals
```

### 实盘交易
```bash
# 启动实盘 (手动确认)
python3 paper_trading.py --config config/live_config.yaml --mode live

# 选股 (不交易)
python3 paper_trading.py --config config/auto_config.yaml --select-only

# 调仓 (不选股)
python3 paper_trading.py --config config/auto_config.yaml --trade-only
```

### 报告生成
```bash
# 日报
python3 generate_report.py --daily

# 周报
python3 generate_report.py --weekly

# 月报
python3 generate_report.py --monthly
```

### 系统管理
```bash
# 检查状态
python3 check_system.py

# 更新数据
python3 download_optimized.py --max 50 --cache

# 查看日志
tail -f logs/trading.log
```

---

## 📞 获取帮助

### 文档
- 实盘计划：`docs/alpha/LIVE_TRADING_PLAN.md`
- API 文档：`docs/alpha/`
- 测试报告：`docs/alpha/TEST_REPORT.md`

### 日志位置
```
logs/
├── trading.log      # 交易日志
├── error.log        # 错误日志
└── system.log       # 系统日志
```

### 报告位置
```
reports/
├── daily/           # 日报
├── weekly/          # 周报
└── monthly/         # 月报
```

---

## ✅ 开始行动

### 今天就可以开始：

```bash
# 1. 进入目录
cd ~/projects/vnpy/examples/alpha_research

# 2. 创建配置
mkdir -p config
cp config/paper_config.yaml.example config/paper_config.yaml

# 3. 运行模拟
python3 paper_trading.py --config config/paper_config.yaml --mode paper

# 4. 查看结果
ls -lh reports/
```

### 一周后：

- ✅ 熟悉所有操作
- ✅ 验证策略有效性
- ✅ 准备实盘资金

### 两周后：

- ✅ 开通券商账户
- ✅ 配置实盘环境
- ✅ 小资金测试

### 一个月后：

- ✅ 正式运行
- ✅ 持续优化
- ✅ 稳定收益

---

## 🎯 成功的关键

1. **从模拟开始** - 不要跳过模拟阶段
2. **小资金测试** - 验证后再加大资金
3. **严格风控** - 永远把风险放在第一位
4. **持续学习** - 市场在变，策略也要优化
5. **保持耐心** - 量化投资是长跑

---

**祝你投资顺利！** [耶]

---

**文档版本**: v1.0  
**最后更新**: 2026-03-02  
**维护者**: OpenClaw Agent
