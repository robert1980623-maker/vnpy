# 🎯 虚拟账户模拟交易系统

**创建时间**: 2026-03-02 23:40  
**系统位置**: `~/projects/vnpy/examples/alpha_research`  
**初始资金**: ¥1,000,000 (可配置)  
**开始日期**: 2026-03-03 (明天)

---

## 📋 系统功能

### ✅ 核心功能

1. **虚拟账户管理**
   - 初始资金可配置 (默认 100 万)
   - 实时持仓跟踪
   - 交易记录保存
   - 账户快照

2. **每日自动交易**
   - 每天 17:00 下载数据
   - 每天 17:30 执行交易
   - 基于真实股价
   - 模拟滑点和手续费

3. **自动复盘**
   - 每日复盘 (工作日 20:00)
   - 每周总结 (周六 10:00)
   - 收益统计
   - 风险分析

4. **定时任务**
   - OpenClaw Cron 自动调度
   - 钉钉消息通知
   - 异常告警

---

## 🚀 快速启动

### 1. 初始化虚拟账户

```bash
cd ~/projects/vnpy/examples/alpha_research

# 创建虚拟账户 (初始资金 100 万)
python3 virtual_account.py
```

输出:
```
账户 ID: virtual_2026
初始资金：¥1,000,000
当前现金：¥1,000,000.00
当前持仓：0 只
总交易：0 笔

✅ 账户已保存：accounts/virtual_2026_account.json
```

---

### 2. 手动执行第一次交易 (测试)

```bash
# 执行每日交易 (可以指定日期测试)
python3 daily_trading.py
```

---

### 3. 生成复盘报告

```bash
# 生成每日/每周报告
python3 generate_reports.py
```

交互式选择:
```
选择报告类型:
  1. 每日复盘
  2. 每周复盘
  3. 两者都生成

请输入选择 (1/2/3): 3
```

---

### 4. 配置定时任务

```bash
# 生成 Cron 配置
python3 setup_virtual_account_cron.py

# 查看配置
cat cron_config.json
```

然后手动添加 Cron 任务:
```bash
# 添加每日数据下载 (17:00)
cron add --job '{"name":"虚拟账户 - 每日数据下载","schedule":{"kind":"cron","expr":"0 17 * * *","tz":"Asia/Shanghai"},"payload":{"kind":"systemEvent","text":"📊 虚拟账户：开始下载当日股票数据..."},"sessionTarget":"main","enabled":true}'

# 添加每日交易 (17:30)
cron add --job '{"name":"虚拟账户 - 每日自动交易","schedule":{"kind":"cron","expr":"30 17 * * *","tz":"Asia/Shanghai"},"payload":{"kind":"systemEvent","text":"💼 虚拟账户：开始执行每日交易..."},"sessionTarget":"main","enabled":true}'

# 添加每日复盘 (工作日 20:00)
cron add --job '{"name":"虚拟账户 - 每日复盘","schedule":{"kind":"cron","expr":"0 20 * * 1-5","tz":"Asia/Shanghai"},"payload":{"kind":"systemEvent","text":"📝 虚拟账户：生成每日复盘报告..."},"sessionTarget":"main","enabled":true}'

# 添加每周总结 (周六 10:00)
cron add --job '{"name":"虚拟账户 - 每周总结","schedule":{"kind":"cron","expr":"0 10 * * 6","tz":"Asia/Shanghai"},"payload":{"kind":"systemEvent","text":"📈 虚拟账户：生成每周总结报告..."},"sessionTarget":"main","enabled":true}'
```

---

## 📁 文件结构

```
~/projects/vnpy/examples/alpha_research/
├── virtual_account.py           # 虚拟账户核心
├── daily_trading.py             # 每日交易执行
├── generate_reports.py          # 复盘报告生成
├── setup_virtual_account_cron.py # Cron 配置
├── cron_config.json             # Cron 配置文件
│
├── accounts/                    # 账户数据
│   └── virtual_2026_account.json
│
├── reports/
│   ├── daily/                   # 每日报告
│   │   └── daily_report_YYYY-MM-DD.json
│   └── weekly/                  # 每周报告
│       └── weekly_report_YYYY-MM-DD.json
│
└── data/akshare/
    └── bars/                    # 股票数据
```

---

## 📊 交易规则

### 费用设置

| 项目 | 费率 | 说明 |
|------|------|------|
| 手续费 | 0.03% | 万分之三 |
| 最低手续费 | ¥5 | 不足 5 元按 5 元 |
| 滑点 | 0.1% | 千一 (买入加价，卖出减价) |

### 交易策略

**简单动量策略**:

1. **卖出规则**:
   - 亏损超过 5% 止损
   - 调仓时清空持仓

2. **买入规则**:
   - 选择价格最高的 10 只股票
   - 排除已持仓股票
   - 最多买入 5 只
   - 平均分配资金
   - 留 10% 现金

3. **仓位控制**:
   - 单只股票最多 20% 仓位
   - 总仓位最多 90%

---

## 📈 示例输出

### 每日交易

```
======================================================================
  每日交易 - 2026-03-03
======================================================================

【加载数据】2026-03-03
  加载 48 只股票

【执行交易】
  卖出 601127.SH (赛力斯)
    1700 股 @ ¥132.27
  买入 000999.SZ (华润三九)
    2100 股 @ ¥33.41

【账户快照】
  日期：2026-03-03
  现金：¥234,567.89
  总值：¥1,012,345.67
  市值：¥777,777.78
  当日收益：¥12,345.67 (+1.23%)
  持仓：5 只

======================================================================
```

### 每日复盘

```
======================================================================
                    每日复盘 - 2026-03-03
======================================================================

【1. 当日收益】
  账户总值：¥1,012,345.67
  当日盈亏：¥12,345.67
  当日收益率：+1.23%

【2. 交易执行】
  买入：1 只
  卖出：1 只
  持仓：5 只
  手续费：¥62.60

【3. 持仓情况】
  000999.SZ (华润三九)
    持仓：2100 股
    成本：¥33.41
    现价：¥33.80
    盈亏：¥819.00 (+1.17%)

【4. 累计收益】
  初始资金：¥1,000,000
  当前总值：¥1,012,345.67
  累计收益：¥12,345.67
  累计收益率：+1.23%
  交易天数：1 天
  总交易：2 笔

【5. 风险控制】
  最大回撤：0.00%
  日均收益：+1.23%
  最大单日收益：+1.23%
  最大单日亏损：0.00%

======================================================================
```

---

## 🔧 常用命令

### 账户管理

```bash
# 查看账户状态
python3 virtual_account.py

# 查看账户文件
cat accounts/virtual_2026_account.json | jq '.'

# 重置账户 (删除重来)
rm accounts/virtual_2026_account.json
python3 virtual_account.py
```

### 交易执行

```bash
# 执行今日交易
python3 daily_trading.py

# 执行指定日期交易 (测试用)
python3 -c "
from daily_trading import DailyTrading
from virtual_account import VirtualAccount
account = VirtualAccount('virtual_2026')
trading = DailyTrading(account)
trading.run_daily('2024-01-02')
"
```

### 报告生成

```bash
# 生成每日报告
python3 generate_reports.py  # 选择 1

# 生成每周报告
python3 generate_reports.py  # 选择 2

# 查看报告
cat reports/daily/daily_report_*.json | jq '.'
cat reports/weekly/weekly_report_*.json | jq '.'
```

### Cron 管理

```bash
# 查看任务
cron list

# 查看任务历史
cron runs --jobId <jobId>

# 立即运行任务
cron run --jobId <jobId>

# 删除任务
cron remove --jobId <jobId>
```

---

## 📅 定时任务时间表

| 任务 | 时间 | 频率 | 说明 |
|------|------|------|------|
| 数据下载 | 17:00 | 每日 | 下载当日股票数据 |
| 自动交易 | 17:30 | 每日 | 执行交易策略 |
| 每日复盘 | 20:00 | 工作日 | 生成每日报告 |
| 每周总结 | 10:00 | 周六 | 生成周度报告 |

---

## 🎯 从明天开始执行

### 2026-03-03 (明天) 流程

**17:00** - 数据下载
```
📊 虚拟账户：开始下载当日股票数据...
   - 从 AKShare 下载 48 只股票数据
   - 保存到 data/akshare/bars/
```

**17:30** - 自动交易
```
💼 虚拟账户：开始执行每日交易...
   - 读取 2026-03-03 收盘价
   - 执行买卖交易
   - 更新持仓
```

**20:00** - 每日复盘
```
📝 虚拟账户：生成每日复盘报告...
   - 统计当日收益
   - 分析交易执行
   - 保存到 reports/daily/
```

---

## 📊 业绩跟踪

### 查看实时业绩

```bash
python3 -c "
from virtual_account import VirtualAccount
account = VirtualAccount('virtual_2026')
perf = account.get_performance()

print('【业绩统计】')
print(f'初始资金：¥{perf[\"initial_capital\"]:,.0f}')
print(f'当前总值：¥{perf[\"current_value\"]:,.2f}')
print(f'总收益：¥{perf[\"total_return\"]:,.2f}')
print(f'总收益率：{perf[\"total_return_rate\"]:+.2f}%')
print(f'交易天数：{perf[\"trading_days\"]} 天')
print(f'最大回撤：{perf[\"max_drawdown\"]:.2f}%')
"
```

---

## ⚠️ 注意事项

1. **数据依赖**
   - 需要真实的股票数据
   - 目前使用 2024 年历史数据
   - 如需实时数据，需接入实时数据源

2. **交易时间**
   - A 股交易时间：9:30-11:30, 13:00-15:00
   - 模拟交易使用收盘价
   - 实际执行在 17:30 (盘后)

3. **资金管理**
   - 初始资金可配置
   - 建议从 100 万开始
   - 可根据实际情况调整

4. **风险控制**
   - 设置止损线 (-5%)
   - 控制仓位 (最多 90%)
   - 分散投资 (最多 5 只)

---

## 🎊 总结

**虚拟账户模拟交易系统已就绪！**

- ✅ 账户管理：初始资金 100 万
- ✅ 每日交易：自动执行策略
- ✅ 自动复盘：每日 + 每周报告
- ✅ 定时任务：Cron 自动调度
- ✅ 从明天 (2026-03-03) 开始执行

**下一步**:
1. 运行 `python3 virtual_account.py` 初始化账户
2. 运行 `python3 daily_trading.py` 测试交易
3. 配置 Cron 任务
4. 等待明天 17:00 第一次自动执行

---

**祝交易顺利！** [耶]
