# 模拟交易使用指南

## ✅ 功能已完成

**模拟交易系统** - 用于验证策略效果，无需真实资金

| 功能 | 状态 | 说明 |
|------|------|------|
| 买入/卖出 | ✅ 完成 | 支持市价单/限价单 |
| 持仓管理 | ✅ 完成 | 自动计算成本价 |
| 盈亏计算 | ✅ 完成 | 实时计算浮动盈亏 |
| 交易记录 | ✅ 完成 | 完整成交历史 |
| 绩效统计 | ✅ 完成 | 组合概览和收益率 |
| 数据保存 | ✅ 完成 | JSON/CSV 格式导出 |

---

## 🚀 快速开始

### 方法 1: 运行演示脚本（推荐新手）

```bash
cd ~/projects/vnpy/examples/alpha_research
source ../../venv/bin/activate
python paper_trading_demo.py
```

**输出示例**:
```
✓ 模拟交易账户已初始化
  初始资金：¥1,000,000.00
  手续费率：0.03%
  滑点：1.0%

✓ 买入 000001.SZ: 38800 股 @ ¥7.80
  手续费：¥90.76
  总成本：¥302,625.64

======================================================================
模拟交易组合概览
======================================================================
初始资金：¥1,000,000.00
当前总值：¥990,331.31
总盈亏：¥-9,668.69 (-0.97%)
持仓数量：3
```

---

### 方法 2: 自定义交易策略

```python
from paper_trading import PaperTradingAccount

# 1. 创建账户
account = PaperTradingAccount(
    initial_capital=1_000_000.0,  # 100 万初始资金
    data_dir="./data/akshare/bars",  # 数据目录
    commission_rate=0.0003,  # 万分之三手续费
    slippage=0.01  # 1% 滑点
)

# 2. 加载数据
account.load_price_data("000001.SZ")
account.load_price_data("600036.SH")

# 3. 执行交易
account.buy("000001.SZ", volume=10000)  # 买入
account.sell("000001.SZ", volume=5000)  # 卖出

# 4. 查看持仓
account.print_portfolio_summary()

# 5. 保存记录
account.save_to_file("./my_trading")
```

---

## 📊 核心功能

### 1. 买入交易

```python
# 市价单（自动获取当前价格）
order_id = account.buy("000001.SZ", volume=10000)

# 限价单（指定价格）
order_id = account.buy("000001.SZ", volume=10000, price=8.0, order_type="limit")
```

**参数说明**:
- `vt_symbol`: 股票代码 (如 "000001.SZ")
- `volume`: 买入数量（股）
- `price`: 价格（市价单可不填）
- `order_type`: 订单类型 ("market" 或 "limit")

**返回**:
- `order_id`: 委托编号
- `None`: 交易失败（资金不足或数据缺失）

---

### 2. 卖出交易

```python
# 市价单
order_id = account.sell("000001.SZ", volume=5000)

# 限价单
order_id = account.sell("000001.SZ", volume=5000, price=8.5, order_type="limit")
```

**参数说明**:
- `vt_symbol`: 股票代码
- `volume`: 卖出数量
- `price`: 价格
- `order_type`: 订单类型

**注意**: 卖出前必须有足够持仓

---

### 3. 持仓查询

```python
# 查询单只股票持仓
pos = account.get_position("000001.SZ")
if pos:
    print(f"持仓数量：{pos.volume}")
    print(f"成本价：¥{pos.avg_price:.2f}")
    print(f"可用数量：{pos.available_volume}")

# 查询所有持仓
all_positions = account.get_all_positions()
for vt_symbol, pos in all_positions.items():
    print(f"{vt_symbol}: {pos.volume}股")
```

---

### 4. 组合概览

```python
# 打印组合概览
account.print_portfolio_summary()

# 获取组合数据
summary = account.get_portfolio_summary()
print(f"总值：¥{summary['total_value']:,.2f}")
print(f"总盈亏：¥{summary['total_profit']:,.2f}")
print(f"收益率：{summary['total_return_pct']:+.2f}%")
```

**输出示例**:
```
======================================================================
模拟交易组合概览
======================================================================
初始资金：¥1,000,000.00
当前总值：¥990,331.31
可用资金：¥51,896.65
总盈亏：¥-9,668.69 (-0.97%)
持仓数量：3

持仓明细:
代码           数量       成本       现价         市值         盈亏      收益率
----------------------------------------------------------------------
000001.SZ    38800     7.80     7.72   299539.49   -3086.16     -1.02%
600036.SH    17200    17.53    17.36   298510.01   -3075.55     -1.02%
600519.SH      300   1146.31  1134.62   340385.17   -3506.99     -1.02%
======================================================================
```

---

### 5. 成交历史

```python
# 获取成交记录
df = account.get_trade_history()
print(df)
```

**输出示例**:
```
   vt_symbol direction      price  volume  commission
0  000001.SZ       buy    7.797291   38800   90.760465
1  600036.SH       buy   17.528785   17200   90.448532
2  600519.SH       buy  1145.963392     300  103.136705
3  000001.SZ      sell    7.642889   19400   44.481614
```

---

### 6. 保存交易记录

```python
# 保存到文件
account.save_to_file("./my_trading")
```

**生成文件**:
- `positions.json`: 持仓数据
- `trades.csv`: 成交记录
- `portfolio_summary.json`: 组合概览

---

## 🎯 实战示例

### 示例 1: 等权重组合

```python
from paper_trading import PaperTradingAccount

# 创建账户
account = PaperTradingAccount(initial_capital=1_000_000.0)

# 加载数据
stocks = ["000001.SZ", "600036.SH", "600519.SH"]
for stock in stocks:
    account.load_price_data(stock)

# 等权重买入
weight = 1.0 / len(stocks)
for stock in stocks:
    price = account.get_current_price(stock)
    volume = int((account.initial_capital * weight) / price / 100) * 100
    account.buy(stock, volume=volume)

# 查看结果
account.print_portfolio_summary()
```

---

### 示例 2: 定投策略

```python
# 每月定投
months = 6
monthly_amount = 100_000

for i in range(months):
    print(f"\n=== 第{i+1}个月 ===")
    
    # 买入
    price = account.get_current_price("000001.SZ")
    volume = int(monthly_amount / price / 100) * 100
    account.buy("000001.SZ", volume=volume)
    
    # 模拟时间流逝（需要重新加载数据）
    # ...

# 查看最终结果
account.print_portfolio_summary()
```

---

### 示例 3: 网格交易

```python
# 网格参数
base_price = 8.0  # 基准价
grid_size = 0.5   # 网格间距
grid_levels = 5   # 网格层数

# 建立网格
for i in range(grid_levels):
    buy_price = base_price * (1 - i * grid_size)
    volume = 1000 * (i + 1)  # 越跌买越多
    
    if account.capital > buy_price * volume * 1.01:
        account.buy("000001.SZ", volume=volume, price=buy_price, order_type="limit")

# 设置卖出网格
for i in range(grid_levels):
    sell_price = base_price * (1 + i * grid_size)
    # ... 类似逻辑

account.print_portfolio_summary()
```

---

### 示例 4: 结合选股策略

```python
from paper_trading import PaperTradingAccount
from vnpy.alpha.lab import AlphaLab

# 1. 创建账户
account = PaperTradingAccount(initial_capital=1_000_000.0)

# 2. 使用选股策略筛选股票
lab = AlphaLab("./lab/test_strategy")
stocks = lab.screen_stocks(
    strategy="value",  # 价值股策略
    max_pe=20,
    max_pb=3
)

# 3. 买入筛选出的股票
for vt_symbol in stocks[:10]:  # 买入前 10 只
    account.load_price_data(vt_symbol)
    price = account.get_current_price(vt_symbol)
    volume = int(100_000 / price / 100) * 100  # 每只 10 万
    account.buy(vt_symbol, volume=volume)

# 4. 查看结果
account.print_portfolio_summary()
```

---

## ⚙️ 参数配置

### 初始化参数

```python
account = PaperTradingAccount(
    initial_capital=1_000_000.0,    # 初始资金
    data_dir="./data/akshare/bars", # K 线数据目录
    commission_rate=0.0003,         # 手续费率（万分之三）
    slippage=0.01                   # 滑点（1%）
)
```

**参数说明**:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_capital` | 1,000,000 | 初始资金（元） |
| `data_dir` | "./data/akshare/bars" | K 线数据目录 |
| `commission_rate` | 0.0003 | 手续费率（万分之三） |
| `slippage` | 0.01 | 滑点（1%） |

---

### 交易成本

**买入成本**:
```
总成本 = 成交价 × 数量 × (1 + 手续费率) × (1 + 滑点)
```

**卖出收入**:
```
总收入 = 成交价 × 数量 × (1 - 手续费率) × (1 - 滑点)
```

**示例**:
```
买入 10000 股 @ ¥8.0
手续费：¥8.0 × 10000 × 0.0003 = ¥24
滑点：¥8.0 × 10000 × 0.01 = ¥800
总成本：¥80,000 + ¥24 + ¥800 = ¥80,824
```

---

## 🛠️ 故障排查

### 问题 1: 无法获取价格

**症状**: `✗ 无法获取 000001.SZ 价格`

**原因**:
- 数据文件不存在
- 股票代码格式错误
- 日期范围无数据

**解决**:
```python
# 1. 检查数据文件
ls ./data/mock/000001.csv

# 2. 使用正确格式
account.buy("000001.SZ", ...)  # ✓ 正确
account.buy("000001", ...)     # ✗ 错误

# 3. 手动加载数据
account.load_price_data("000001.SZ")
```

---

### 问题 2: 资金不足

**症状**: `✗ 资金不足：需要 ¥500,000, 可用 ¥300,000`

**解决**:
```python
# 1. 减少买入数量
account.buy("000001.SZ", volume=5000)  # 减少数量

# 2. 使用更大初始资金
account = PaperTradingAccount(initial_capital=2_000_000.0)
```

---

### 问题 3: 持仓不足

**症状**: `✗ 可用数量不足：可用 5000, 需要 10000`

**解决**:
```python
# 检查持仓
pos = account.get_position("000001.SZ")
print(f"可用数量：{pos.available_volume}")

# 减少卖出数量
account.sell("000001.SZ", volume=pos.available_volume)
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `paper_trading.py` | 模拟交易核心模块 ⭐ |
| `paper_trading_demo.py` | 演示脚本（推荐新手） |
| `PAPER_TRADING_GUIDE.md` | 本文档 |

---

## 🌐 与 vnpy 集成

### 方法 1: 使用 vnpy PaperAccount

vnpy 自带 PaperAccount 模块（主要用于期货）：

```python
# 在 vnpy 启动脚本中
from vnpy_paperaccount import PaperAccountApp

main_engine.add_app(PaperAccountApp)
```

---

### 方法 2: 结合选股策略

```python
# 1. 使用选股策略筛选
from vnpy.alpha.lab import AlphaLab
lab = AlphaLab("./lab/test")
stocks = lab.screen_stocks(strategy="value")

# 2. 使用模拟交易执行
from paper_trading import PaperTradingAccount
account = PaperTradingAccount()

for stock in stocks[:10]:
    account.buy(stock, volume=1000)

# 3. 导出到 vnpy
# 保存持仓，然后在 vnpy 中加载
```

---

## ✅ 总结

**模拟交易系统优势**:
- ✅ 无需真实资金
- ✅ 考虑交易成本（手续费 + 滑点）
- ✅ 完整的持仓和盈亏管理
- ✅ 支持回测验证
- ✅ 数据可导出分析

**使用场景**:
1. 策略开发和验证
2. 参数优化测试
3. 风险控制演练
4. 交易流程熟悉

**推荐流程**:
1. 运行演示脚本 (`paper_trading_demo.py`)
2. 修改策略逻辑
3. 使用真实数据测试
4. 导出结果分析
5. 实盘对接（最后一步）

---

**状态**: ✅ 模拟交易系统已完成，可以开始测试策略了！[耶]
