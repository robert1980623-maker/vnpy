# 完整交易流程说明

**制定人**: 王雅轩 (Robert)  
**版本**: v1.0  
**日期**: 2026-03-02

---

## 📋 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        交易日流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  09:00  多策略选股 ──→ 100 只股票 + 选择原因                     │
│           ↓                                                     │
│  09:15  交易计划通知 ──→ 钉钉消息 (买入/卖出清单)                │
│           ↓                                                     │
│  09:30  开盘监控 ──→ 市场状态检查                               │
│           ↓                                                     │
│  14:50  执行交易 ──→ 模拟交易执行                               │
│           ↓                                                     │
│  15:30  收盘统计 ──→ 当日收益计算                               │
│           ↓                                                     │
│  20:00  每日复盘 ──→ 复盘报告 + 心得分享                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        周流程                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  周六 10:00  周总结 ──→ 周报 + 策略分析 + 经验总结               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🕐 详细时间表

### 交易日 (周一至周五)

| 时间 | 任务 | 脚本 | 输出 | 通知 |
|------|------|------|------|------|
| **09:00** | 多策略选股 | `daily_stock_selection.py` | 100 只股票清单 | ✅ |
| **09:15** | 交易计划通知 | `send_notification.py` | 买入/卖出清单 | ✅ |
| **09:30** | 开盘监控 | `market_monitor.py` | 市场状态 | ❌ |
| **14:50** | 执行交易 | `execute_trading.py` | 成交记录 | ❌ |
| **15:30** | 收盘统计 | `daily_stats.py` | 当日收益 | ❌ |
| **20:00** | 每日复盘 | `daily_review.py` | 复盘报告 | ✅ |

### 周末

| 时间 | 任务 | 脚本 | 输出 | 通知 |
|------|------|------|------|------|
| **周六 10:00** | 周总结 | `weekly_summary.py` | 周报 | ✅ |

---

## 📊 每个环节详解

### 1️⃣ 多策略选股 (09:00)

**目标**: 选出 100 只优质股票，说明选择原因

**策略组合**:
- **价值策略**: PE<20, ROE>10%, 股息率>2%
- **成长策略**: 营收增长>25%, 利润增长>30%
- **质量策略**: ROE>15%
- **高息策略**: 股息率>3%

**输出内容**:
```json
{
  "date": "2026-03-02",
  "total_selected": 100,
  "stocks": [
    {
      "symbol": "002625.SZ",
      "strategies": ["价值", "成长", "质量", "高息"],
      "score": 10,
      "reasons": [
        "PE=19.7<20",
        "ROE=19.5%>10%",
        "股息率=3.3%>2%",
        "营收增长=28.5%>25%"
      ],
      "indicators": {
        "pe": 19.7,
        "roe": 19.5,
        "dividend_yield": 3.3
      }
    }
    // ... 更多股票
  ]
}
```

**运行命令**:
```bash
python3 daily_stock_selection.py
```

**输出文件**:
- `reports/stock_selection_YYYY-MM-DD.json`

---

### 2️⃣ 交易计划通知 (09:15)

**目标**: 发送钉钉消息，通知今日交易计划

**通知内容**:
```
📈 交易计划 - 2026-03-02

【选股结果】
✅ 选出 100 只股票

【买入清单】(15 只)
1. 002625.SZ - 价值 + 成长 + 质量 + 高息
   原因：PE=19.7, ROE=19.5%, 股息率=3.3%
   
2. 600036.SH - 价值 + 质量 + 高息
   原因：PE=5.8, ROE=12.5%, 股息率=5.2%
   
... (最多显示 5 只)

【卖出清单】(6 只)
1. 600489.SH - 不再符合策略
2. 688506.SH - 基本面恶化
...

【仓位配置】
总仓位：80%
单只：3%

【风险提示】
市场震荡，注意控制仓位
```

**运行命令**:
```bash
python3 send_notification.py --type trading_plan
```

---

### 3️⃣ 消息面分析 (09:30)

**目标**: 分析宏观、行业、公司消息，整合到选股

**分析内容**:
- 宏观政策 (央行、财政部等)
- 行业动态 (新能源、半导体、医药等)
- 公司公告 (业绩、回购、新产品等)
- 市场情绪 (成交量、北向资金等)

**输出内容**:
```json
{
  "date": "2026-03-02",
  "macro": [
    {
      "title": "央行宣布降准 0.25 个百分点",
      "impact": "positive",
      "sectors": ["银行", "券商", "保险"]
    }
  ],
  "sentiment": {
    "score": 55,
    "overall": "neutral"
  },
  "summary": [
    "宏观面：3 条利好政策",
    "行业面：3 个行业利好",
    "市场情绪：55 分 (中性)"
  ]
}
```

**运行命令**:
```bash
python3 news_analyzer.py
```

---

### 4️⃣ 执行交易 (14:50)

**目标**: 执行交易计划，记录成交

**执行流程**:
1. 读取交易计划
2. 计算仓位和订单
3. 执行买入/卖出
4. 记录成交价格
5. 更新持仓

**输出内容**:
```json
{
  "date": "2026-03-02",
  "trades": [
    {
      "symbol": "002625.SZ",
      "direction": "buy",
      "volume": 3800,
      "price": 26.50,
      "amount": 100700,
      "commission": 30.21
    }
  ],
  "total_buy": 15,
  "total_sell": 6,
  "success_rate": 95.5
}
```

**运行命令**:
```bash
python3 execute_trading.py
```

**输出文件**:
- `paper_trading/trades.csv`
- `paper_trading/positions.json`

---

### 5️⃣ 每日复盘 (20:00)

**目标**: 总结当日交易，分享心得

**复盘内容**:
1. **当日收益**
   - 初始资金、当前总值
   - 当日盈亏、收益率

2. **交易执行**
   - 买入/卖出数量
   - 成交率、滑点
   - 手续费

3. **策略评估**
   - 各策略表现
   - 最佳/最差策略

4. **个股表现**
   - 最佳 Top 3
   - 最差 Top 3

5. **心得分享**
   - 当日经验
   - 教训总结

6. **明日展望**
   - 市场预判
   - 操作策略
   - 仓位建议

**输出内容**:
```
======================================================================
                    每日复盘 - 2026-03-02
======================================================================

【1. 当日收益】
  初始资金：¥1,000,000
  当前总值：¥1,001,348
  当日盈亏：¥1,348
  当日收益率：+0.13%

【2. 交易执行】
  买入：6 只
  卖出：3 只
  成交率：89.9%

【3. 选股策略评估】
  价值策略：+3.87%
  成长策略：+4.05%
  质量策略：+2.94%

【4. 个股表现】
  最佳：301750.SZ +6.77%
  最差：308989.SZ -4.71%

【5. 今日心得】
  • 质量因子表现突出，ROE>15% 跑赢大盘
  • 明日关注成交量变化

【6. 明日展望】
  预计开盘：震荡
  操作策略：逢低布局
  仓位建议：80%
```

**运行命令**:
```bash
python3 daily_review.py
```

**输出文件**:
- `reports/daily/daily_review_YYYY-MM-DD.json`

---

### 6️⃣ 周总结 (周六 10:00)

**目标**: 总结一周交易，分析策略表现

**总结内容**:
1. **本周收益**
   - 周收益率
   - 每日收益曲线

2. **策略表现**
   - 各策略周收益
   - 最佳/最弱策略

3. **交易统计**
   - 买入/卖出总数
   - 胜率、盈亏比

4. **个股表现**
   - 本周最佳 Top 5
   - 本周最差 Top 5

5. **经验总结**
   - 成功经验
   - 失败教训

6. **下周计划**
   - 仓位目标
   - 关注板块
   - 策略优化

**输出内容**:
```
======================================================================
                  周总结 (03.02-03.06)
======================================================================

【1. 本周收益】
  本周收益率：+2.01%
  周一：-0.19%  周二：+0.04%  周三：-0.19%
  周四：+1.76%  周五：+1.00%

【2. 策略表现】
  价值策略：+3.29% ⭐
  成长策略：+2.80%
  质量策略：+2.19%
  高息策略：+1.60%

【3. 交易统计】
  买入：35 只次  卖出：23 只次
  胜率：59.5%
  盈亏比：1.09

【4. 个股表现】
  最佳：601811.SZ +11.62%
  最差：607477.SZ -9.33%

【5. 经验总结】
  • 多策略分散降低波动
  • 早盘交易滑点较小
  • 成长股需加强止损

【6. 下周计划】
  仓位目标：74%
  关注板块：金融
  优化策略：加强成长股选股标准
```

**运行命令**:
```bash
python3 weekly_summary.py
```

**输出文件**:
- `reports/weekly/weekly_summary_YYYYMMDD.json`

---

## ⚙️ 自动化配置

### Cron 定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下任务 (北京时间)

# 每日 09:00 选股
0 9 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 daily_stock_selection.py >> logs/selection.log 2>&1

# 每日 09:15 发送交易计划
15 9 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 send_notification.py --type trading_plan >> logs/notification.log 2>&1

# 每日 09:30 消息面分析
30 9 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 news_analyzer.py >> logs/news.log 2>&1

# 每日 14:50 执行交易
50 14 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 execute_trading.py >> logs/trading.log 2>&1

# 每日 20:00 每日复盘
0 20 * * 1-5 cd ~/projects/vnpy/examples/alpha_research && python3 daily_review.py >> logs/review.log 2>&1

# 每周六 10:00 周总结
0 10 * * 6 cd ~/projects/vnpy/examples/alpha_research && python3 weekly_summary.py >> logs/weekly.log 2>&1
```

### 一键启动脚本

创建 `run_all.sh`:
```bash
#!/bin/bash
# 一键启动所有任务 (用于测试)

cd ~/projects/vnpy/examples/alpha_research

echo "🚀 启动完整交易流程..."

echo "【09:00】多策略选股..."
python3 daily_stock_selection.py

echo "【09:15】发送交易计划..."
python3 send_notification.py --type trading_plan

echo "【09:30】消息面分析..."
python3 news_analyzer.py

echo "【14:50】执行交易..."
python3 execute_trading.py

echo "【20:00】每日复盘..."
python3 daily_review.py

echo "✅ 所有任务完成!"
```

---

## 📁 文件结构

```
examples/alpha_research/
├── config/
│   ├── paper_config.yaml      # 模拟配置
│   ├── live_config.yaml       # 实盘配置
│   └── auto_config.yaml       # 自动化配置
├── reports/
│   ├── stock_selection_*.json # 选股报告
│   ├── trading_plan_*.json    # 交易计划
│   ├── daily/                 # 每日复盘
│   │   └── daily_review_*.json
│   ├── weekly/                # 周总结
│   │   └── weekly_summary_*.json
│   └── news/                  # 消息面分析
│       └── news_analysis_*.json
├── paper_trading/
│   ├── positions.json         # 持仓
│   ├── trades.csv             # 成交记录
│   └── portfolio_summary.json # 组合统计
├── logs/
│   ├── selection.log          # 选股日志
│   ├── notification.log       # 通知日志
│   ├── trading.log            # 交易日志
│   ├── review.log             # 复盘日志
│   └── weekly.log             # 周报日志
├── daily_stock_selection.py   # 选股脚本
├── send_notification.py       # 通知脚本
├── news_analyzer.py           # 消息分析
├── execute_trading.py         # 交易执行
├── daily_review.py            # 每日复盘
├── weekly_summary.py          # 周总结
└── start_trading.py           # 启动脚本
```

---

## 🎯 开始使用

### 第一步：测试运行

```bash
cd ~/projects/vnpy/examples/alpha_research

# 1. 测试选股
python3 daily_stock_selection.py

# 2. 测试复盘
python3 daily_review.py

# 3. 测试周报
python3 weekly_summary.py
```

### 第二步：配置通知

编辑 `config/notification_config.yaml`:
```yaml
notification:
  enabled: true
  channel: dingtalk
  recipient: "manager9593"
  time:
    trading_plan: "09:15"
    daily_review: "20:00"
    weekly_summary: "Saturday 10:00"
```

### 第三步：设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加定时任务 (见上文)
```

### 第四步：监控运行

```bash
# 查看日志
tail -f logs/selection.log
tail -f logs/trading.log
tail -f logs/review.log

# 查看报告
ls -lt reports/
```

---

## 📊 输出示例

### 选股报告
```json
{
  "date": "2026-03-02",
  "total_selected": 100,
  "stocks": [
    {
      "symbol": "002625.SZ",
      "strategies": ["价值", "成长", "质量", "高息"],
      "score": 10,
      "reasons": ["PE=19.7", "ROE=19.5%", "股息率=3.3%"],
      "pe": 19.7,
      "roe": 19.5,
      "dividend_yield": 3.3
    }
  ]
}
```

### 交易计划通知
```
📈 交易计划 - 2026-03-02

【选股结果】✅ 100 只

【买入】15 只
1. 002625.SZ (价值 + 成长 + 质量 + 高息)
2. 600036.SH (价值 + 质量 + 高息)
...

【卖出】6 只
1. 600489.SH
2. 688506.SH
...

【仓位】80%
```

### 每日复盘
```
【当日收益】+0.13%
【交易执行】买入 6 只，卖出 3 只
【策略评估】成长策略 +4.05% 最佳
【今日心得】质量因子表现突出
【明日展望】震荡，逢低布局，80% 仓位
```

---

## ⚠️ 注意事项

1. **模拟≠实盘**: 当前为模拟交易，实盘需额外配置
2. **数据质量**: 财务数据需定期更新
3. **网络依赖**: 部分功能需要网络连接
4. **定时任务**: 确保 cron 服务运行正常
5. **日志监控**: 定期检查日志，发现异常及时处理

---

## 📞 支持

- **文档**: `docs/alpha/`
- **日志**: `logs/`
- **报告**: `reports/`
- **配置**: `config/`

---

**流程制定完成时间**: 2026-03-02  
**状态**: 🟢 可执行

[耶]
