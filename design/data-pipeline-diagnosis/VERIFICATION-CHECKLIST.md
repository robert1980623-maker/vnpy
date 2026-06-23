# 验证清单

> 制定日期：2026-06-24  
> 用于验证 FIX-PLAN.md 中每个修复项的正确性  
> 每个修复项必须全部通过才能标记为完成

---

## P0-1：Token 加载验证

### 单元测试
- [ ] 无环境变量时，脚本从 `.env` 加载 Token
  ```bash
  env -i HOME=$HOME PATH=$PATH python3 -c "
  import sys; sys.path.insert(0, 'examples/alpha_research')
  from download_data_akshare import USE_TUSHARE, TUSHARE_TOKEN
  assert USE_TUSHARE == True, 'Tushare should be enabled'
  assert len(TUSHARE_TOKEN) == 56, f'Token length wrong: {len(TUSHARE_TOKEN)}'
  print('✅ Token 加载成功')
  "
  ```

- [ ] 有环境变量时，优先使用环境变量
  ```bash
  TUSHARE_TOKEN=test_token python3 -c "
  import sys; sys.path.insert(0, 'examples/alpha_research')
  from download_data_akshare import TUSHARE_TOKEN
  assert TUSHARE_TOKEN == 'test_token'
  print('✅ 环境变量优先')
  "
  ```

- [ ] `.env` 不存在时，不报错
  ```bash
  mv examples/alpha_research/.env examples/alpha_research/.env.bak
  python3 -c "import sys; sys.path.insert(0, 'examples/alpha_research'); import download_data_akshare"
  mv examples/alpha_research/.env.bak examples/alpha_research/.env
  # 期望：无异常
  ```

### 集成测试
- [ ] Cron 环境模拟
  ```bash
  # 模拟 cron 环境（无 TUSHARE_TOKEN）
  /usr/bin/env -i PATH=$PATH SHELL=/bin/bash \
    bash examples/alpha_research/run_download_with_env.sh --dry-run
  # 期望：日志显示 "Tushare 已配置"
  ```

---

## P0-2：下载超时验证

### 功能测试
- [ ] 3 只股票下载成功
  ```bash
  cd examples/alpha_research
  export TUSHARE_TOKEN=$(grep TUSHARE_TOKEN .env | cut -d= -f2 | tr -d '"')
  time python3 download_data_akshare.py --max 3 --no-cache
  # 期望：3/3 成功，耗时 < 2 分钟
  ```

- [ ] 10 只股票在超时内完成
  ```bash
  time python3 download_data_akshare.py --max 10 --night-mode
  # 期望：10/10 成功，耗时 < 10 分钟
  ```

- [ ] 50 只股票在 30 分钟超时内完成
  ```bash
  time python3 download_data_akshare.py --max 50 --night-mode
  # 期望：成功率 > 90%，耗时 < 30 分钟
  ```

### 回归测试
- [ ] 夜间模式延迟正确
  ```bash
  python3 download_data_akshare.py --max 5 --night-mode 2>&1 | grep "休息"
  # 期望：每 2 只股票休息 8-12 秒
  ```

- [ ] 缓存命中正常工作
  ```bash
  # 第一次下载
  python3 download_data_akshare.py --max 3
  # 第二次下载（应命中缓存）
  python3 download_data_akshare.py --max 3 2>&1 | grep "缓存"
  # 期望：显示缓存命中
  ```

---

## P0-3：Cron 任务验证

### 安装验证
- [ ] Crontab 包含所有关键任务
  ```bash
  crontab -l | grep -c "download\|stock_selection\|stop_loss\|rebalance\|virtual_account"
  # 期望：>= 5
  ```

- [ ] Cron wrapper 脚本可执行
  ```bash
  ls -la examples/alpha_research/run_download_with_env.sh
  # 期望：-rwxr-xr-x
  ```

- [ ] Wrapper 脚本独立运行
  ```bash
  examples/alpha_research/run_download_with_env.sh --dry-run
  # 期望：正常运行，无 Token 相关错误
  ```

### 调度验证
- [ ] 下载任务按时触发
  ```bash
  # 检查 cron 日志
  grep "download" /var/log/cron 2>/dev/null || \
  grep "download" ~/.openclaw/logs/cron_data_download.log 2>/dev/null | tail -5
  ```

---

## P1-1：止盈止损 Bug 修复验证

### 单元测试
- [ ] profit_rate 正确计算
  ```python
  # 测试用例
  from strict_stop_loss import StrictStopLoss
  executor = StrictStopLoss()
  # 模拟：成本 10 元，现价 8 元 → 亏损 20%
  # 期望：profit_rate = -0.2
  ```

- [ ] pos_info 结构完整
  ```python
  # 检查 pos_info 包含所有必要字段
  assert 'symbol' in pos_info
  assert 'profit_rate' in pos_info
  assert 'profit_amount' in pos_info
  assert 'market_value' in pos_info
  ```

- [ ] 除零保护
  ```python
  # 成本价为 0 时不应崩溃
  # 期望：profit_rate = 0.0
  ```

### 集成测试
- [ ] 完整流程运行
  ```bash
  cd examples/alpha_research
  python3 strict_stop_loss.py
  # 期望：正常输出，无 NameError
  # 期望：显示止损/止盈/预警/持有统计
  ```

- [ ] 报告文件生成
  ```bash
  ls -la reports/stop_loss_check_*.json | tail -1
  # 期望：生成报告文件
  ```

### 边界测试
- [ ] 空持仓不崩溃
- [ ] NaN/Inf 价格处理
- [ ] 0 数量持仓处理

---

## P1-2：DB symbol_name 回填验证

### 数据验证
- [ ] 所有 virtual_2026 持仓的 symbol_name 非空
  ```bash
  sqlite3 accounts/trading.db \
    "SELECT COUNT(*) FROM positions WHERE account_id='virtual_2026' AND (symbol_name IS NULL OR symbol_name = '');"
  # 期望：0
  ```

- [ ] 名称与 JSON 一致
  ```bash
  sqlite3 accounts/trading.db \
    "SELECT symbol, symbol_name FROM positions WHERE account_id='virtual_2026';"
  # 对比 virtual_2026_account.json 中的 stock_code → stock_name
  ```

### 回归测试
- [ ] 新建持仓时 symbol_name 被正确写入
  ```python
  # 通过 account_db.py 买入一只股票
  # 检查 DB 中 symbol_name 是否正确
  ```

- [ ] DB 备份存在
  ```bash
  ls -la accounts/trading.db.bak
  # 期望：备份文件存在
  ```

---

## P1-3：数据补全验证

### 数据完整性
- [ ] CSV 数据更新到 06-24
  ```bash
  tail -1 data/akshare/bars/000001_sz.csv
  # 期望：20260624,...
  ```

- [ ] 数据天数正确
  ```bash
  wc -l data/akshare/bars/000001_sz.csv
  # 期望：~25 行（1 header + 22 交易日）
  ```

- [ ] 持仓相关股票数据完整
  ```bash
  for code in 600035 601187 601818 000528 000563; do
    echo "=== $code ==="
    tail -1 data/akshare/bars/${code}_*.csv 2>/dev/null || echo "NOT FOUND"
  done
  # 期望：全部显示 06-24 数据
  ```

### 价格同步
- [ ] 持仓价格更新
  ```bash
  sqlite3 accounts/trading.db \
    "SELECT symbol, current_price, updated_at FROM positions WHERE account_id='virtual_2026';"
  # 期望：updated_at 为今天
  ```

- [ ] 市值重新计算
  ```bash
  # 验证 market_value = quantity × current_price
  sqlite3 accounts/trading.db \
    "SELECT symbol, quantity, current_price, market_value, 
            quantity * current_price as expected_mv
     FROM positions WHERE account_id='virtual_2026';"
  # 期望：market_value ≈ expected_mv
  ```

---

## P2-1：交易执行链路验证

### 功能测试
- [ ] 交易信号正确生成
  ```bash
  cd examples/alpha_research
  python3 daily_stock_selection.py
  ls -la reports/stock_selection_$(date +%Y-%m-%d).json
  # 期望：选股报告生成
  ```

- [ ] 交易计划正确生成
  ```bash
  ls -la reports/trading_plan_$(date +%Y-%m-%d).json
  # 期望：交易计划生成
  ```

- [ ] 执行脚本 dry_run 模式正常
  ```bash
  python3 execute_trading.py --dry-run
  # 期望：执行日志生成，无错误
  ```

### 实盘验证（谨慎）
- [ ] 小额测试交易成功
  ```bash
  # 手动执行 1 笔小额交易
  # 验证：
  # 1. 交易记录写入 DB
  # 2. 持仓更新正确
  # 3. 现金扣减正确
  ```

- [ ] 飞书通知发送成功
  ```bash
  # 检查飞书消息
  ```

---

## 全量回归测试

### 数据管道
- [ ] 凌晨下载任务成功（01:00）
- [ ] 下午下载任务成功（17:00）
- [ ] 数据新鲜度检查通过
  ```bash
  python3 examples/alpha_research/stale_data_updater.py --check-only
  # 期望：无陈旧数据
  ```

### 交易链路
- [ ] 09:00 选股执行成功
- [ ] 15:00 止损检查正常
- [ ] 17:30 调仓执行成功
- [ ] 20:00 每日复盘生成

### 监控链路
- [ ] 虚拟账户同步正常（每 15 分钟）
- [ ] 数据质量检查通过（23:00）
- [ ] Agent 健康检查通过（每 30 分钟）

### 端到端测试
```bash
# 模拟完整交易日
# 1. 数据下载
python3 examples/alpha_research/download_data_akshare.py --max 10

# 2. 选股
python3 examples/alpha_research/daily_stock_selection.py

# 3. 止损检查
python3 examples/alpha_research/strict_stop_loss.py

# 4. 交易执行（dry_run）
python3 examples/alpha_research/execute_trading.py --dry-run

# 5. 检查所有输出
ls -la examples/alpha_research/reports/
# 期望：所有报告文件存在且内容正确
```

---

## 验收标准

| 指标 | 目标 | 当前状态 |
|------|------|----------|
| 数据下载成功率 | > 95% | 0% |
| 数据最新日期 | T+0（当天） | T-22（06-02） |
| DB symbol_name 完整率 | 100% | 0% |
| 止损检查无报错 | ✅ | NameError |
| 交易执行记录 | 每日 | 12 天无记录 |
| Cron 任务安装率 | 100% | ~10% |

---

## 验证执行顺序

```
Day 1 验证:
  1. P0-1 验证 → Token 加载
  2. P0-2 验证 → 下载超时
  3. P1-1 验证 → 止损 Bug
  4. P1-2 验证 → DB 回填
  5. P1-3 验证 → 数据补全

Day 2 验证:
  6. P0-3 验证 → Cron 任务
  7. P2-1 验证 → 交易链路
  8. 全量回归测试
```
