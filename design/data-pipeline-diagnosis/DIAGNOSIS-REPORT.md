# 数据管道诊断报告

> 诊断日期：2026-06-24  
> 诊断范围：数据下载管道、持仓管理、交易执行链路  
> 严重等级：P0（数据管道完全中断）

---

## 问题一：P0 数据管道完全中断

### 现象
- TUSHARE_TOKEN 环境变量未设置
- 02:30 下载任务：50 只全部失败，成功率 0%
- 自 06-01 起已连续 23 天下载失败
- CSV 数据仅到 06-02（最后一条记录：`20260602`）

### 根因分析

#### 根因 1：Cron 命令不加载环境变量

**证据链：**
- `.env` 文件存在且包含有效 Token：`examples/alpha_research/.env` → `TUSHARE_TOKEN=612016803b...`
- `~/.zshrc` 也导出了 TUSHARE_TOKEN
- 但 cron 命令直接运行 `download_data_akshare.py`，**不加载 .env 也不 source .zshrc**
- 只有 `run_stock_selection_with_sync.sh` 有 env 加载逻辑（3 种方法），但数据下载的 cron 不走这个 wrapper

```
# Cron 命令（config/cron_config.yaml L33）
cd ${VNPY_DIR}/${SCRIPTS_DIR} && ${PYTHON} download_data_akshare.py --end $(date +%Y-%m-%d)
# ↑ 没有加载 .env 或 .zshrc
```

**影响：** 下载脚本读取 `os.environ.get('TUSHARE_TOKEN', '')` → 空字符串 → `USE_TUSHARE = False` → 降级到 AKShare → AKShare/Baostock 网络失败 → 全部失败。

#### 根因 2：下载 50 只股票 + 10 分钟超时 = 必败

**证据链：**
- 日志 `download_20260623_0230.log`：
  ```
  [02:30:03] 📋 待下载股票：50 只
  [02:30:03] 开始下载 50 只股票...
  [02:40:03] ❌ 下载超时       ← 精确 10 分钟后
  [02:40:03] ✅ 下载完成，成功率：0.0%
  ```
- 超时来自 `enhanced_download_with_validation.py:113`：`subprocess.run(..., timeout=600)`
- 每只股票串行尝试 3 个数据源（Tushare → AKShare → Baostock），每个源有网络延迟
- 50 只 × 3 个源 × 网络延迟 > 600 秒 → 必然超时

#### 根因 3：auto_config.yaml 缺少 tushare_token

**证据链：**
- `download_data_akshare.py:51` → `load_data_config().get('tushare_token', '')`
- `config/auto_config.yaml` 不包含 `data.tushare_token` 配置项
- Token 后备方案也失败

### 影响范围
- 5507 个 CSV 文件全部停留在 06-02 数据（最后更新：`Jun 3 01:01`）
- 所有依赖最新数据的策略计算（行业轮动、选股、止盈止损）都基于 22 天前的数据
- 选股结果不可信

---

## 问题二：P1 持仓数据质量异常

### 现象
- trading.db 中 10 只持仓的 `symbol_name` 全部为空
- JSON 账户文件有 `stock_name` 但 DB 没有
- 最后更新时间 06-02，市值基于 6 天前数据
- 两只曾触发止损预警（300039 -15.2%, 605266 -13.2%）

### 根因分析

#### 根因 1：DB 写入时未填充 symbol_name

**证据链：**
```
# trading.db positions 表查询
sqlite> SELECT symbol, symbol_name FROM positions WHERE account_id='virtual_2026';
002233|          ← 空
600035|          ← 空
601187|          ← 空
...（10 只全部为空）

# 但 JSON 账户有名字
virtual_2026_account.json:
  "stock_code": "600035", "stock_name": "楚天高速"
  "stock_code": "601187", "stock_name": "厦门银行"
```

- `account_db.py:638` → `buy_position()` 接收 `symbol_name` 参数但调用时传入空字符串
- DB schema `symbol_name TEXT` 允许 NULL/空
- 数据导入脚本没有在写入 DB 时同步 symbol_name

#### 根因 2：价格更新机制失效

**证据链：**
- CSV 数据最后更新：`Jun 3 01:01`（数据到 06-02）
- DB 的 `updated_at` 全部为 `2026-06-02T09:40:58`
- `sync_holdings_price.py` 存在但因数据管道中断无法获取最新价格
- 市值计算基于 22 天前的收盘价

#### 根因 3：strict_stop_loss.py 存在代码 Bug

**证据链：**
```python
# strict_stop_loss.py L97-100 — check_positions() 方法
# 变量 symbol, cost_price, current_price, volume 已定义
# 但 profit_rate 和 pos_info 从未定义！

if profit_rate <= self.stop_loss_threshold:     # ← NameError!
    self.actions['stop_loss'].append(pos_info)   # ← NameError!
```

- 缺少 `profit_rate = (current_price - cost_price) / cost_price` 计算
- 缺少 `pos_info = {'symbol': symbol, ...}` 构造
- 运行时必定抛出 `NameError`，止损检查完全无效

### 影响范围
- 所有持仓的市值、盈亏数据不准确
- 止损/止盈判断逻辑崩溃，无法执行风控
- 虚拟账户的 `market_value` 字段与实际严重偏差

---

## 问题三：今日无交易执行

### 现象
- 有 06-22 和 06-23 的选股计划和交易计划
- 但无实际交易执行记录（最后执行日志：06-12）
- 06-12 执行日志显示 `dry_run: true`

### 根因分析

#### 根因 1：执行脚本以 dry_run 模式运行

**证据链：**
```json
// logs/execution_2026-06-12.json
{
    "dry_run": true,          // ← 模拟模式，不实际下单
    "executed_buy": 10,
    "status": "dry_run"
}
```

- 执行脚本默认以 dry_run 模式运行
- 未找到切换到实盘模式的配置变更记录

#### 根因 2：Cron 任务链断裂

**证据链：**
- Crontab 安装的只有 3 个交易相关任务：
  ```
  0 9 * * 1-5  run_stock_selection_with_sync.sh  (选股)
  0 17 * * *   openclaw cron run "数据下载"
  0 20 * * 1-5 openclaw cron run "每日复盘"
  ```
- `config/cron_config.yaml` 定义了 31 个任务，但**大部分未安装到系统 crontab**
- 缺失的关键任务：
  - `trade-rebalance`（17:30 调仓）
  - `trade-stop-loss-executor`（16:00 止损执行）
  - `trade-stop-loss-check`（15:00 止损检查）
  - `monitor-virtual-account`（每 15 分钟账户同步）

#### 根因 3：数据管道中断阻断交易信号

- 交易信号依赖最新数据
- 数据停留在 06-02 → 选股信号不可信 → 交易计划不可执行
- 即使执行了，也是基于 22 天前的数据做出的决策

### 影响范围
- 自 06-12 起无交易执行（12 天）
- 选股计划虽然生成但质量存疑
- 整个交易链路形同虚设

---

## 问题关系图

```
[TUSHARE_TOKEN 未加载] ──────────────────┐
                                          ↓
[数据下载超时 (50只×3源 > 10min)] → 数据管道中断 (23天)
                                          ↓
                    ┌──────────────────────┤
                    ↓                      ↓
         [CSV 数据停在 06-02]    [选股基于旧数据]
                    ↓                      ↓
         [持仓价格过时]          [交易信号不可信]
                    ↓                      ↓
         [止损检查 NameError]    [执行脚本 dry_run]
                    ↓                      ↓
              风控失效              无实际交易执行
```

---

## 证据文件清单

| 文件 | 证据类型 |
|------|----------|
| `examples/alpha_research/.env` | Token 存在但未被 cron 加载 |
| `examples/alpha_research/logs/download_20260623_*.log` | 超时 + 0% 成功率 |
| `config/cron_config.yaml` | 31 个任务定义但大部分未安装 |
| `crontab -l` | 仅 3 个交易任务实际安装 |
| `data/akshare/bars/*.csv` | 5507 文件全部停在 06-02 |
| `accounts/trading.db` | symbol_name 全部为空 |
| `accounts/virtual_2026_account.json` | JSON 有名称但 DB 没有 |
| `strict_stop_loss.py:98` | profit_rate/pos_info 未定义 |
| `logs/execution_2026-06-12.json` | dry_run=true，最后执行记录 |
| `config/auto_config.yaml` | 缺少 data.tushare_token |
