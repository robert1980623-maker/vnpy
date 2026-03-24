# 涨停龙头策略文档

## 📊 策略概述

涨停龙头策略是一种基于市场强势股的动量策略，核心逻辑是：
- **识别涨停股票**：筛选每日涨停的强势股
- **评估龙头特征**：通过多维度评分识别真正的龙头
- **及时介入**：在龙头确立后介入，享受溢价
- **严格风控**：设置止损止盈，控制风险

## 🎯 核心逻辑

### 1. 涨停识别
- 识别 A 股市场所有涨停股票（10% 或 20% 涨幅）
- 数据来源：AKShare 涨停池数据

### 2. 龙头评分体系

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| **连续涨停天数** | 40% | 连板数越高，分数越高（上限 40 分） |
| **板块效应** | 25% | 同板块涨停数量越多，分数越高（上限 25 分） |
| **成交量放大** | 20% | 量比 1.5-3 倍最佳（上限 20 分） |
| **市值偏好** | 15% | 50-200 亿最佳（上限 15 分） |

### 3. 筛选条件
- 最小连续涨停天数：≥ 2 天
- 成交量放大倍数：≥ 1.5 倍
- 市值范围：50 亿 - 500 亿
- 最大持仓数量：5 只

### 4. 交易信号
- **买入信号**：新入选的龙头候选
- **卖出信号**：
  - 止损：亏损 ≥ 8%
  - 止盈：盈利 ≥ 20%
  - 龙头地位丧失：不再在候选列表中

## 📁 文件结构

```
alpha_research/
├── strategies/
│   ├── __init__.py              # 策略包初始化
│   └── limit_up_leader.py       # 核心策略逻辑
├── limit_up_strategy_runner.py  # 策略运行器
├── config/
│   └── limit_up_strategy.json   # 策略配置
├── tests/
│   └── test_limit_up_strategy.py # 单元测试
├── setup_limit_up_cron.py       # Cron 任务设置脚本
└── docs/
    └── LIMIT_UP_STRATEGY.md     # 策略文档
```

## 🚀 快速开始

### 1. 手动运行策略

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 运行当日选股（自动检测日期）
python3 limit_up_strategy_runner.py --auto --notify

# 指定日期运行
python3 limit_up_strategy_runner.py --date 20260318

# 自动执行交易信号（模拟盘）
python3 limit_up_strategy_runner.py --auto --execute
```

### 2. 查看 cron 任务

```bash
# 列出所有任务
openclaw cron list

# 查看策略任务
openclaw cron list | grep "涨停龙头"

# 立即运行任务
openclaw cron run limit_up_leader_strategy
```

### 3. 查看选股结果

```bash
# 查看最新报告
cat reports/limit_up_strategy/report_$(date +%Y%m%d).json | python3 -m json.tool

# 查看龙头候选
cat reports/limit_up_strategy/report_*.json | tail -1
```

## ⚙️ 配置参数

### 策略配置 (`config/limit_up_strategy.json`)

```json
{
  "strategy_config": {
    "min_limit_up_days": 2,        // 最小连续涨停天数
    "max_position_count": 5,       // 最大持仓数量
    "stop_loss_pct": -8.0,         // 止损百分比
    "take_profit_pct": 20.0,       // 止盈百分比
    "volume_ratio_threshold": 1.5, // 成交量放大阈值
    "min_market_cap": 5000000000,  // 最小市值 (50 亿)
    "max_market_cap": 50000000000, // 最大市值 (500 亿)
    "leader_score_weights": {
      "limit_up_days": 0.4,        // 连续涨停权重
      "industry_effect": 0.25,     // 板块效应权重
      "volume_ratio": 0.2,         // 成交量权重
      "market_cap": 0.15           // 市值权重
    }
  },
  "execution": {
    "auto_execute": false,         // 是否自动执行交易
    "send_notification": true,     // 是否发送通知
    "slack_channel": "trading-alerts"
  },
  "risk_control": {
    "max_single_position": 0.2,    // 单只股票最大仓位
    "max_total_exposure": 0.8,     // 最大总仓位
    "daily_loss_limit": -50000     // 单日亏损限制
  }
}
```

## 📊 策略报告

每日策略报告包含以下信息：

```json
{
  "date": "20260318",
  "total_limit_up": 45,           // 涨停总数
  "leader_candidates": 5,         // 龙头候选数量
  "current_positions": 3,         // 当前持仓数量
  "leaders": [                    // 龙头候选列表
    {
      "symbol": "000001",
      "name": "平安银行",
      "score": 85.5,              // 龙头评分
      "limit_up_days": 3,         // 连续涨停天数
      "volume_ratio": 2.5,        // 成交量放大倍数
      "industry": "银行",
      "market_cap": 20000000000
    }
  ],
  "signals": [                    // 交易信号
    {
      "symbol": "000001",
      "action": "buy",
      "price": 10.5,
      "quantity": 1000,
      "reason": "龙头候选：评分=85.5, 连板=3",
      "confidence": 0.85
    }
  ]
}
```

## 🧪 测试

### 运行单元测试

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 运行所有测试
pytest tests/test_limit_up_strategy.py -v

# 运行特定测试
pytest tests/test_limit_up_strategy.py::TestLimitUpLeaderStrategy::test_initialization -v

# 运行集成测试（需要真实数据）
pytest tests/test_limit_up_strategy.py::TestLimitUpLeaderStrategyIntegration -v
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest tests/test_limit_up_strategy.py --cov=strategies/limit_up_leader --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

## 📈 策略优化方向

### 1. 评分体系优化
- [ ] 增加资金流向维度（主力资金净流入）
- [ ] 增加市场情绪维度（涨停家数/跌停家数）
- [ ] 增加技术形态维度（突破平台、新高）

### 2. 风控优化
- [ ] 动态止损（根据波动率调整）
- [ ] 仓位管理（根据评分分配仓位）
- [ ] 黑名单机制（问题股排除）

### 3. 执行优化
- [ ] 集合竞价策略（9:15-9:25 观察）
- [ ] 分批建仓（避免一次性买入）
- [ ] 滑点控制（价格偏离监控）

### 4. 数据优化
- [ ] 增加龙虎榜数据
- [ ] 增加融资融券数据
- [ ] 增加机构调研数据

## ⚠️ 风险提示

1. **涨停股风险**：涨停股票波动大，可能出现连续跌停
2. **流动性风险**：涨停股可能无法及时卖出
3. **政策风险**：监管政策变化可能影响策略效果
4. **模型风险**：历史表现不代表未来

**建议**：
- 先用模拟盘测试至少 1 个月
- 实盘从小资金开始（≤ 总资金 10%）
- 严格执行止损纪律
- 定期复盘优化策略

## 📝 更新日志

### v1.0.0 (2026-03-18)
- ✅ 核心策略实现
- ✅ 龙头评分体系
- ✅ 交易信号生成
- ✅ Cron 任务集成
- ✅ 单元测试
- ✅ 文档完善

## 🔗 相关资源

- [AKShare 涨停数据文档](https://akshare.akfamily.xyz/data/stock/stock.html#stock-zt-pool-em)
- [龙头战法实战指南](https://xueqiu.com/topic/longtou)
- [涨停板敢死队研究](https://www.jisilu.cn/question/longtou)

---

**作者**: OpenClaw Alpha Research  
**创建日期**: 2026-03-18  
**最后更新**: 2026-03-18
