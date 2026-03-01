# 快速启动指南

**版本**: v1.0  
**日期**: 2026-03-02  
**目标**: 5 分钟开始完整交易流程

---

## 🚀 快速开始 (5 分钟)

### 1️⃣ 测试运行 (2 分钟)

```bash
# 进入目录
cd ~/projects/vnpy/examples/alpha_research

# 运行完整流程 (测试模式)
./run_full_flow.sh
```

**输出示例**:
```
======================================================================
                    完整交易流程演示
======================================================================

[INFO] 【09:00】开始多策略选股...
✅ 加载股票池：48 只股票
✅ 选出：40 只
Top 10 股票:
  1. 002625.SZ - 价值 + 成长 + 质量 + 高息
  2. 600036.SH - 价值 + 质量 + 高息
  ...

[INFO] 【09:30】开始消息面分析...
🟢 宏观政策：3 条利好
🟢 行业动态：3 个行业利好

[INFO] 【14:50】开始执行交易...
✅ 买入 6 只，卖出 3 只

[INFO] 【20:00】开始每日复盘...
当日收益：+0.13%
今日心得：质量因子表现突出

======================================================================
                    所有任务完成!
======================================================================
```

---

### 2️⃣ 查看报告 (1 分钟)

```bash
# 选股报告
cat reports/stock_selection_*.json | python3 -m json.tool | head -50

# 交易计划
cat reports/trading_plan_*.json | python3 -m json.tool

# 每日复盘
cat reports/daily/daily_review_*.json | python3 -m json.tool
```

---

### 3️⃣ 设置定时任务 (2 分钟)

```bash
# 方法 1: 手动添加
crontab -e
# 粘贴 crontab.txt 中的内容

# 方法 2: 自动安装
crontab crontab.txt

# 验证
crontab -l
```

---

## 📋 完整流程

### 交易日流程

| 时间 | 任务 | 脚本 | 通知 |
|------|------|------|------|
| 09:00 | 多策略选股 | `daily_stock_selection.py` | ✅ |
| 09:15 | 交易计划 | `send_notification.py` | ✅ |
| 09:30 | 消息面分析 | `news_analyzer.py` | ❌ |
| 14:50 | 执行交易 | `execute_trading.py` | ❌ |
| 20:00 | 每日复盘 | `daily_review.py` | ✅ |

### 周末流程

| 时间 | 任务 | 脚本 | 通知 |
|------|------|------|------|
| 周六 10:00 | 周总结 | `weekly_summary.py` | ✅ |

---

## 📊 输出内容

### 1. 选股报告

**文件**: `reports/stock_selection_YYYY-MM-DD.json`

**内容**:
- 100 只入选股票
- 每只股票的选择原因
- 基于的策略 (价值/成长/质量/高息)
- 财务指标 (PE/ROE/股息率等)

**示例**:
```json
{
  "symbol": "002625.SZ",
  "strategies": ["价值", "成长", "质量", "高息"],
  "reasons": ["PE=19.7", "ROE=19.5%", "股息率=3.3%"],
  "pe": 19.7,
  "roe": 19.5,
  "dividend_yield": 3.3
}
```

---

### 2. 交易计划通知

**方式**: 钉钉消息

**内容**:
```
📈 交易计划 - 2026-03-02

【选股结果】✅ 100 只

【买入清单】(15 只)
1. 002625.SZ - 价值 + 成长 + 质量 + 高息
   原因：PE=19.7, ROE=19.5%, 股息率=3.3%
   
2. 600036.SH - 价值 + 质量 + 高息
   原因：PE=5.8, ROE=12.5%, 股息率=5.2%

【卖出清单】(6 只)
1. 600489.SH - 不再符合策略
2. 688506.SH - 基本面恶化

【仓位配置】
总仓位：80%
单只：3%
```

---

### 3. 每日复盘

**文件**: `reports/daily/daily_review_YYYY-MM-DD.json`

**内容**:
- 当日收益
- 交易执行
- 策略评估
- 个股表现
- 心得分享
- 明日展望

**示例**:
```
【当日收益】+0.13%
【交易执行】买入 6 只，卖出 3 只
【策略评估】成长策略 +4.05% 最佳
【今日心得】质量因子表现突出
【明日展望】震荡，逢低布局，80% 仓位
```

---

### 4. 周总结

**文件**: `reports/weekly/weekly_summary_YYYYMMDD.json`

**内容**:
- 本周收益
- 策略表现
- 交易统计
- 最佳/最差股票
- 经验总结
- 下周计划

---

## 🛠️ 常用命令

### 运行脚本

```bash
# 选股
python3 daily_stock_selection.py

# 消息面分析
python3 news_analyzer.py

# 执行交易
python3 execute_trading.py

# 每日复盘
python3 daily_review.py

# 周总结
python3 weekly_summary.py

# 一键运行
./run_full_flow.sh
```

### 查看报告

```bash
# 最新选股报告
ls -lt reports/ | head -5

# 最新复盘报告
ls -lt reports/daily/ | head -5

# 查看 JSON 内容
cat reports/stock_selection_*.json | python3 -m json.tool | head -50
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/selection.log
tail -f logs/trading.log
tail -f logs/review.log

# 查看最近错误
grep ERROR logs/*.log | tail -20
```

### 管理定时任务

```bash
# 查看当前 crontab
crontab -l

# 编辑 crontab
crontab -e

# 删除所有定时任务
crontab -r

# 安装定时任务
crontab crontab.txt
```

---

## 📁 目录结构

```
examples/alpha_research/
├── config/                    # 配置文件
│   ├── paper_config.yaml     # 模拟配置
│   ├── live_config.yaml      # 实盘配置
│   └── auto_config.yaml      # 自动化配置
├── reports/                   # 报告
│   ├── stock_selection_*.json
│   ├── trading_plan_*.json
│   ├── daily/                # 每日复盘
│   ├── weekly/               # 周总结
│   └── news/                 # 消息分析
├── paper_trading/            # 模拟交易
│   ├── positions.json
│   ├── trades.csv
│   └── portfolio_summary.json
├── logs/                     # 日志
│   ├── selection.log
│   ├── trading.log
│   └── review.log
├── daily_stock_selection.py  # 选股
├── news_analyzer.py          # 消息分析
├── execute_trading.py        # 交易
├── daily_review.py           # 复盘
├── weekly_summary.py         # 周报
├── run_full_flow.sh          # 一键运行
├── crontab.txt              # 定时任务
└── COMPLETE_FLOW.md         # 完整流程文档
```

---

## ⚠️ 注意事项

### 1. 模拟交易

- 当前为**模拟交易**模式
- 使用虚拟资金 (100 万)
- 不涉及真实资金
- 实盘需额外配置券商 API

### 2. 数据更新

- 财务数据需定期更新
- 每日 08:30 自动更新
- 手动更新：`python3 download_optimized.py --max 50 --cache`

### 3. 定时任务

- 确保 cron 服务运行：`sudo systemctl status cron`
- 检查时区：`timedatectl | grep "Time zone"`
- 应为：`Asia/Shanghai`

### 4. 日志监控

- 每日检查日志
- 发现错误及时处理
- 日志保留 30 天

---

## 📞 获取帮助

### 文档

- **完整流程**: `COMPLETE_FLOW.md`
- **实盘计划**: `AUTOMATED_TRADING_PLAN.md`
- **流程体验**: `TRADING_FLOW_EXPERIENCE.md`
- **快速指南**: `docs/alpha/QUICK_START.md`

### 日志

```bash
# 选股日志
tail -f logs/selection.log

# 交易日志
tail -f logs/trading.log

# 复盘日志
tail -f logs/review.log
```

### 报告

```bash
# 选股报告
cat reports/stock_selection_*.json

# 每日复盘
cat reports/daily/daily_review_*.json

# 周总结
cat reports/weekly/weekly_summary_*.json
```

---

## 🎯 下一步

### 今日

- [ ] 运行 `./run_full_flow.sh` 测试
- [ ] 查看生成的报告
- [ ] 熟悉流程

### 明日

- [ ] 设置 crontab 定时任务
- [ ] 验证 09:00 选股是否执行
- [ ] 验证 20:00 复盘是否执行

### 本周

- [ ] 每日查看报告
- [ ] 记录问题和发现
- [ ] 周六查看周总结

---

## ✅ 检查清单

### 环境检查

- [ ] Python 3.10+ 已安装
- [ ] vnpy 项目已克隆
- [ ] 数据已下载 (48 只股票)
- [ ] 依赖已安装

### 功能检查

- [ ] 选股脚本可运行
- [ ] 复盘脚本可运行
- [ ] 报告正常生成
- [ ] 日志正常记录

### 定时任务检查

- [ ] crontab 已配置
- [ ] cron 服务运行中
- [ ] 时区正确 (Asia/Shanghai)
- [ ] 权限正确

---

**准备就绪！开始你的自动化交易之旅吧！** [耶]
