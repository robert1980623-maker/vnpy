# 数据管道修复方案

> 制定日期：2026-06-24  
> 基于：DIAGNOSIS-REPORT.md  
> 预估总时间：~4 小时（含验证）

---

## 修复优先级

| 优先级 | 问题 | 预估时间 | 依赖 |
|--------|------|----------|------|
| P0-1 | Token 加载机制修复 | 15 min | 无 |
| P0-2 | 下载超时修复 | 30 min | P0-1 |
| P0-3 | Cron 任务重新安装 | 30 min | P0-1, P0-2 |
| P1-1 | strict_stop_loss.py Bug 修复 | 15 min | 无 |
| P1-2 | DB symbol_name 回填 | 20 min | 无 |
| P1-3 | 数据补全（06-03 到 06-24） | 60 min | P0-2 |
| P2-1 | 交易执行链路恢复 | 30 min | P0-3, P1-3 |

---

## P0-1：Token 加载机制修复

### 问题
Cron 直接调用 `download_data_akshare.py`，不加载 `.env` 或 `.zshrc`。

### 修复方案

**方案 A（推荐）：在 `download_data_akshare.py` 中添加 .env 自动加载**

```python
# 在文件顶部，import 之后，配置加载之前添加：
from pathlib import Path
import os

# 自动加载 .env 文件
def _load_env():
    """从 .env 文件加载环境变量（cron 环境兼容）"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env()
```

**方案 B（补充）：在 `config/auto_config.yaml` 中添加 token 后备**

```yaml
data:
  tushare_token: "612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5"
```

> 注意：方案 B 会将 token 写入 git 跟踪的文件，不推荐。应使用 `.env` + gitignore。

### 验证
```bash
# 模拟 cron 环境（无 TUSHARE_TOKEN）
env -i PATH=$PATH python3 -c "
import sys; sys.path.insert(0, 'examples/alpha_research')
from download_data_akshare import USE_TUSHARE, TUSHARE_TOKEN
print(f'USE_TUSHARE={USE_TUSHARE}, TOKEN_LEN={len(TUSHARE_TOKEN)}')
"
# 期望：USE_TUSHARE=True, TOKEN_LEN=56
```

---

## P0-2：下载超时修复

### 问题
50 只股票 × 3 数据源 × 串行 = 超过 600 秒超时。

### 修复方案

**步骤 1：增加超时时间**

`enhanced_download_with_validation.py:113`：
```python
# 修改前
timeout=600,   # 10 分钟

# 修改后
timeout=1800,  # 30 分钟（50 只股票需要 ~20 分钟）
```

**步骤 2：优化下载策略 — 增量下载**

当前每次下载 50 只全量数据。应改为：
1. 检查本地 CSV 最后更新日期
2. 只下载缺失或过期的股票
3. 分批下载（每批 10 只，中间检查时间）

**步骤 3：修复 cron 命令参数**

`config/cron_config.yaml`：
```yaml
# 修改前
command: "cd ${VNPY_DIR}/${SCRIPTS_DIR} && ${PYTHON} download_data_akshare.py --end $(date +\\%Y-\\%m-\\%d)"
# ↑ 缺少 --max 参数，默认只有 5 只

# 修改后
command: "cd ${VNPY_DIR}/${SCRIPTS_DIR} && ${PYTHON} download_data_akshare.py --end $(date +\\%Y-\\%m-\\%d) --max 50 --night-mode"
```

**步骤 4：添加下载 wrapper 脚本**

创建 `run_download_with_env.sh`（类似 `run_stock_selection_with_sync.sh`）：
```bash
#!/bin/bash
# 加载环境变量
source /Users/rowang/projects/vnpy/examples/alpha_research/.env 2>/dev/null
export TUSHARE_TOKEN

cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 download_data_akshare.py --end $(date +%Y-%m-%d) --max 50 --night-mode
```

### 验证
```bash
# 手动测试下载 3 只股票
cd examples/alpha_research && python3 download_data_akshare.py --max 3 --no-cache
# 期望：3/3 成功

# 测试 10 只股票在超时内完成
python3 download_data_akshare.py --max 10 --night-mode
# 期望：10/10 成功，耗时 < 10 分钟
```

---

## P0-3：Cron 任务重新安装

### 问题
`config/cron_config.yaml` 定义了 31 个任务，但 crontab 只有 3 个交易任务。

### 修复方案

**步骤 1：生成完整的 crontab**

```bash
cd /Users/rowang/projects/vnpy
# 如果项目有 vnpy cron install 命令
python3 -m vnpy cron install --config config/cron_config.yaml

# 或手动合并到 crontab
python3 -c "
import yaml
with open('config/cron_config.yaml') as f:
    config = yaml.safe_load(f)
for task in config['tasks']:
    if task.get('enabled', True):
        schedule = task['schedule']
        command = task['command']
        print(f'{schedule} {command}')
" | crontab -
```

**步骤 2：确保关键任务优先安装**

至少需要安装以下任务：
```
# 数据下载（使用 wrapper 脚本）
0 1 * * * /Users/rowang/projects/vnpy/examples/alpha_research/run_download_with_env.sh >> logs/cron_download.log 2>&1
0 17 * * * /Users/rowang/projects/vnpy/examples/alpha_research/run_download_with_env.sh >> logs/cron_download.log 2>&1

# 选股 + 交易执行
0 9 * * 1-5 cd examples/alpha_research && bash run_stock_selection_with_sync.sh >> logs/stock_selection.log 2>&1
30 17 * * 1-5 cd examples/alpha_research && python3 rebalance_portfolio.py >> logs/rebalance.log 2>&1

# 止损检查 + 执行
0 15 * * 1-5 cd examples/alpha_research && python3 strict_stop_loss.py >> logs/stop_loss.log 2>&1
0 16 * * 1-5 cd examples/alpha_research && python3 stop_loss_executor.py >> logs/stop_loss_exec.log 2>&1

# 账户同步
*/15 * * * * cd examples/alpha_research && python3 virtual_account.py >> logs/account.log 2>&1
```

### 验证
```bash
# 确认 crontab 已安装
crontab -l | wc -l
# 期望：>= 15 行

# 检查 cron 服务运行
launchctl list | grep cron
```

---

## P1-1：strict_stop_loss.py Bug 修复

### 问题
`check_positions()` 方法中 `profit_rate` 和 `pos_info` 未定义。

### 修复方案

在 `strict_stop_loss.py:97` 之前添加：

```python
# 计算盈亏比例
if cost_price > 0:
    profit_rate = (current_price - cost_price) / cost_price
else:
    profit_rate = 0.0

# 构建持仓信息
pos_info = {
    'symbol': symbol,
    'cost_price': cost_price,
    'current_price': current_price,
    'volume': volume,
    'profit_rate': profit_rate,
    'profit_amount': (current_price - cost_price) * volume,
    'market_value': current_price * volume,
}
```

### 验证
```bash
cd examples/alpha_research
python3 strict_stop_loss.py
# 期望：正常输出止盈止损检查结果，无 NameError
```

---

## P1-2：DB symbol_name 回填

### 问题
trading.db 中 virtual_2026 账户的 positions 表 `symbol_name` 全部为空。

### 修复方案

```python
# 从 JSON 账户文件回填 DB
import json
import sqlite3

# 加载 JSON 数据
with open('examples/alpha_research/accounts/virtual_2026_account.json') as f:
    account = json.load(f)

# 建立 code → name 映射
name_map = {}
for pos in account['positions']:
    code = pos.get('stock_code', '')
    name = pos.get('stock_name', '')
    if code and name:
        name_map[code] = name

# 回填 DB
conn = sqlite3.connect('accounts/trading.db')
cursor = conn.cursor()

for code, name in name_map.items():
    cursor.execute(
        "UPDATE positions SET symbol_name = ? WHERE account_id = 'virtual_2026' AND symbol = ?",
        (name, code)
    )
    print(f"  更新 {code} → {name} ({cursor.rowcount} 行)")

conn.commit()
conn.close()
print(f"✅ 回填完成：{len(name_map)} 只股票")
```

### 修复 account_db.py 防止再犯

在 `buy_position()` 方法中，确保 symbol_name 参数被正确传递和存储。检查所有写入 positions 表的代码路径。

### 验证
```bash
sqlite3 accounts/trading.db "SELECT symbol, symbol_name FROM positions WHERE account_id='virtual_2026';"
# 期望：所有 symbol_name 非空
```

---

## P1-3：数据补全（06-03 到 06-24）

### 问题
CSV 数据停在 06-02，缺失 22 个交易日的数据。

### 修复方案

**步骤 1：手动触发全量补数据**

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 设置 token
export TUSHARE_TOKEN=$(grep TUSHARE_TOKEN .env | cut -d= -f2 | tr -d '"')

# 补下载 06-03 到 06-24 的数据
python3 download_data_akshare.py \
  --start 20260603 \
  --end 20260624 \
  --max 50 \
  --night-mode
```

**步骤 2：验证数据完整性**

```bash
# 检查最新数据日期
tail -1 data/akshare/bars/000001_sz.csv
# 期望：20260624,...

# 检查数据覆盖天数
wc -l data/akshare/bars/000001_sz.csv
# 期望：~25 行（1 header + 22 交易日）
```

**步骤 3：更新持仓价格**

```bash
# 同步最新价格到 DB
python3 accounts/sync_holdings_price.py
# 或
python3 examples/alpha_research/sync_holdings_price.py
```

---

## P2-1：交易执行链路恢复

### 问题
执行脚本以 dry_run 模式运行，无实际交易。

### 修复方案

**步骤 1：确认 dry_run 配置位置**

```bash
grep -rn "dry_run" examples/alpha_research/execute_trading.py
grep -rn "dry_run" config/
```

**步骤 2：切换到实盘模式（谨慎！）**

1. 先验证数据已更新到最新
2. 确认止损检查正常工作
3. 小额测试：先手动执行 1 笔交易验证
4. 确认无误后关闭 dry_run

**步骤 3：建立执行监控**

```bash
# 添加执行结果通知
# 在 execute_trading.py 末尾添加飞书/微信通知
```

---

## 风险与注意事项

1. **Token 安全**：不要将 token 提交到 git，确保 `.env` 在 `.gitignore` 中
2. **数据补全耗时**：50 只股票 × 22 天数据，可能需要 30+ 分钟
3. **实盘交易风险**：恢复交易执行前务必确认数据质量和止损机制
4. **Cron 冲突**：多个下载任务可能并行运行，需要添加锁机制
5. **DB 迁移**：回填 symbol_name 前先备份 trading.db

---

## 修复时间线

```
Day 1 (今天):
  ├── P0-1: Token 加载 (15 min)
  ├── P0-2: 超时修复 (30 min)
  ├── P1-1: 止损 Bug 修复 (15 min)
  ├── P1-2: DB 回填 (20 min)
  └── P1-3: 数据补全 (60 min)

Day 2:
  ├── P0-3: Cron 重装 (30 min)
  ├── P2-1: 交易链路恢复 (30 min)
  └── 全量验证 (30 min)
```
