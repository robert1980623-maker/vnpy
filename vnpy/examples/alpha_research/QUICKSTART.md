# 5 分钟快速开始

**vnpy 量化交易系统** | 版本：1.0 | 最后更新：2026-03-01

---

## 🎯 目标

**5 分钟内**完成安装并运行第一个量化交易策略！

---

## 📋 前置要求

- ✅ Python 3.8+
- ✅ 基础 Python 知识
- ✅ 网络连接（下载数据用）

---

## 🚀 第一步：安装依赖（2 分钟）

### 1. 进入项目目录

```bash
cd ~/projects/vnpy/examples/alpha_research
```

### 2. 检查依赖（推荐）

```bash
# 运行依赖检查脚本
python3 check_dependencies.py
```

**输出示例**:
```
============================================================
vnpy 量化交易系统 - 依赖检查
============================================================

📦 核心依赖:
  ✅ pandas                - 数据处理
  ✅ numpy                 - 数值计算
  ✅ polars                - 高性能数据处理
  ✅ pyyaml                - 配置文件解析
  ✅ akshare               - AKShare 数据源（推荐）

------------------------------------------------------------
✅ 所有核心依赖已安装！
============================================================
```

如果缺少依赖，脚本会提供安装命令。

### 3. 安装核心依赖

```bash
# 一键安装所有核心依赖
pip3 install pandas numpy polars pyyaml akshare --break-system-packages

# 或查看 QUICKSTART.md 获取详细安装指南
```

### 4. 验证安装

```bash
python3 -c "import pandas; import numpy; import yaml; print('✅ 依赖安装成功')"
```

看到 `✅ 依赖安装成功` 即可继续。

---

## 🚀 第二步：运行第一个策略（2 分钟）

### 方式 1: 一键运行（最简单）

```bash
# 使用默认配置运行完整流程
python3 main.py --strategy value --stocks 5
```

**这将自动执行**:
1. 下载 5 只股票数据
2. 使用价值股策略选股
3. 回测验证
4. 模拟交易

**预计耗时**: 2-3 分钟（首次运行需下载数据）

---

### 方式 2: 快速测试（跳过下载）

```bash
# 如果已有数据，跳过下载和回测
python3 main.py --strategy value --stocks 5 --skip-download --skip-backtest
```

**这将执行**:
1. 选股
2. 模拟交易

**预计耗时**: 10 秒

---

### 方式 3: 仅下载数据

```bash
# 只下载数据，不运行策略
python3 main.py --only-download --max 10
```

**这将**:
- 下载 10 只股票的 K 线数据
- 保存到 `./data/akshare/bars/`

**预计耗时**: 1-2 分钟

---

## 🚀 第三步：查看结果（1 分钟）

### 1. 查看日志输出

运行时会看到类似输出：

```
2026-03-01 12:00:00 - QuantTrading - INFO - 量化交易系统 v1.0
2026-03-01 12:00:00 - QuantTrading - INFO - 策略：value
2026-03-01 12:00:00 - QuantTrading - INFO - 选股数量：5
2026-03-01 12:00:01 - QuantTrading - INFO - 步骤 1/4: 下载数据...
2026-03-01 12:00:30 - QuantTrading - INFO - 数据下载完成
2026-03-01 12:00:30 - QuantTrading - INFO - 步骤 2/4: 选股...
2026-03-01 12:00:31 - QuantTrading - INFO - 选中 5 只股票：000001.SZ, ...
2026-03-01 12:00:31 - QuantTrading - INFO - 步骤 3/4: 回测...
2026-03-01 12:00:35 - QuantTrading - INFO - 回测完成，总收益：15.23%
2026-03-01 12:00:35 - QuantTrading - INFO - 步骤 4/4: 模拟交易...
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 000001.SZ，数量：1000
...
2026-03-01 12:00:36 - QuantTrading - INFO - 系统运行完成！
```

---

### 2. 查看日志文件

```bash
# 查看最新日志
tail -f logs/quant_trading_$(date +%Y%m%d).log

# 或查看完整日志
cat logs/quant_trading_20260301.log
```

---

### 3. 查看模拟交易结果

```bash
# 查看持仓概览
ls -la paper_trading_main/

# 查看交易记录
cat paper_trading_main/trades.json | python3 -m json.tool

# 查看持仓
cat paper_trading_main/positions.json | python3 -m json.tool
```

---

## 🎮 常用命令速查

### 更换策略

```bash
# 价值股策略（低 PE/PB）
python3 main.py --strategy value --stocks 10

# 成长股策略（高 ROE）
python3 main.py --strategy growth --stocks 10

# 动量策略（近期上涨）
python3 main.py --strategy momentum --stocks 10

# 质量因子策略
python3 main.py --strategy quality --stocks 10

# 行业轮动策略
python3 main.py --strategy industry --stocks 10
```

---

### 调整参数

```bash
# 选股数量
python3 main.py --stocks 20

# 初始资金
python3 main.py --capital 2000000

# 每只股票买入数量
python3 main.py --volume 2000

# 组合使用
python3 main.py --strategy momentum --stocks 15 --capital 5000000 --volume 1500
```

---

### 跳过步骤

```bash
# 跳过数据下载（已有数据时）
python3 main.py --skip-download

# 跳过回测
python3 main.py --skip-backtest

# 跳过模拟交易
python3 main.py --skip-trading

# 只下载数据
python3 main.py --only-download --max 20
```

---

### 使用配置文件

```bash
# 使用默认配置
python3 main.py

# 使用自定义配置
python3 main.py --config config.yaml

# 配置文件 + 命令行覆盖
python3 main.py --config config.yaml --stocks 5
```

---

### 查看帮助

```bash
# 查看所有可用选项
python3 main.py --help
```

---

## 📊 预期输出示例

### 完整流程输出

```bash
$ python3 main.py --strategy value --stocks 5

2026-03-01 12:00:00 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:00 - QuantTrading - INFO - 量化交易系统 v1.0
2026-03-01 12:00:00 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:00 - QuantTrading - INFO - 策略：value
2026-03-01 12:00:00 - QuantTrading - INFO - 选股数量：5
2026-03-01 12:00:00 - QuantTrading - INFO - 初始资金：¥1,000,000
2026-03-01 12:00:00 - QuantTrading - INFO - 数据目录：./data/akshare/bars
2026-03-01 12:00:00 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:00 - QuantTrading - INFO - 步骤 1/4: 下载数据...
2026-03-01 12:00:30 - QuantTrading - INFO - 数据下载完成，共下载 5 只股票
2026-03-01 12:00:30 - QuantTrading - INFO - 步骤 2/4: 选股...
2026-03-01 12:00:31 - QuantTrading - INFO - 选中 5 只股票：000001.SZ, 000002.SZ, 000063.SZ, 000858.SZ, 002230.SZ
2026-03-01 12:00:31 - QuantTrading - INFO - 步骤 3/4: 回测...
2026-03-01 12:00:35 - QuantTrading - INFO - 回测完成，总收益：15.23%
2026-03-01 12:00:35 - QuantTrading - INFO - 步骤 4/4: 模拟交易...
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 000001.SZ，数量：1000
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 000002.SZ，数量：1000
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 000063.SZ，数量：1000
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 000858.SZ，数量：1000
2026-03-01 12:00:36 - QuantTrading - INFO - 买入 002230.SZ，数量：1000
2026-03-01 12:00:36 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:36 - QuantTrading - INFO - 模拟交易完成，组合概览:
2026-03-01 12:00:36 - QuantTrading - INFO - 总资产：¥1,000,000.00
2026-03-01 12:00:36 - QuantTrading - INFO - 可用资金：¥500,000.00
2026-03-01 12:00:36 - QuantTrading - INFO - 总盈亏：¥0.00 (0.00%)
2026-03-01 12:00:36 - QuantTrading - INFO - 持仓数量：5
2026-03-01 12:00:36 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:36 - QuantTrading - INFO - 交易记录已保存到：./paper_trading_main
2026-03-01 12:00:36 - QuantTrading - INFO - ============================================================
2026-03-01 12:00:36 - QuantTrading - INFO - 系统运行完成！
2026-03-01 12:00:36 - QuantTrading - INFO - 总耗时：0:00:36
2026-03-01 12:00:36 - QuantTrading - INFO - ============================================================
```

---

## 🐛 常见问题

### Q1: 依赖安装失败？

**错误**: `ModuleNotFoundError: No module named 'pandas'`

**解决**:
```bash
# 方式 1: 运行依赖检查脚本（推荐）
python3 check_dependencies.py

# 方式 2: 手动安装
pip3 install pandas numpy polars pyyaml akshare --break-system-packages

# 验证安装
python3 check_dependencies.py
# 或
python3 -c "import pandas; print('OK')"
```

**预防**: 运行任何功能前，先运行 `python3 check_dependencies.py`

---

### Q2: 数据下载失败？

**错误**: `数据下载失败：...`

**解决**:
```bash
# 1. 检查网络连接
ping www.baidu.com

# 2. 检查 AKShare 安装
pip3 install akshare --break-system-packages

# 3. 使用备选数据源（Baostock）
python3 test_baostock.py

# 4. 使用模拟数据
python3 generate_mock_data.py
```

---

### Q3: 权限错误？

**错误**: `PermissionError: [Errno 13] Permission denied`

**解决**:
```bash
# 确保在项目目录运行
cd ~/projects/vnpy/examples/alpha_research

# 或使用 sudo（不推荐）
sudo python3 main.py
```

---

### Q4: 内存不足？

**错误**: `MemoryError` 或系统卡顿

**解决**:
```bash
# 减少选股数量
python3 main.py --stocks 3

# 减少下载数量
python3 main.py --only-download --max 5

# 关闭其他程序释放内存
```

---

### Q5: 配置文件不生效？

**解决**:
```bash
# 1. 检查配置文件路径
ls -la config.yaml

# 2. 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 3. 使用绝对路径
python3 main.py --config /absolute/path/to/config.yaml
```

---

## 📚 下一步学习

完成快速开始后，你可以：

### 1. 深入了解配置

```bash
# 阅读配置指南
cat CONFIG_GUIDE.md

# 修改配置文件
vim config.yaml
```

**推荐修改**:
- `strategy.default_strategy`: 更换策略
- `trading.initial_capital`: 调整资金
- `logging.level`: 调整日志级别

---

### 2. 学习不同策略

```bash
# 价值股策略
python3 main.py --strategy value

# 成长股策略
python3 main.py --strategy growth

# 动量策略
python3 main.py --strategy momentum
```

**策略文档**:
- `vnpy/vnpy/alpha/strategy/strategies/preset_strategies.py`

---

### 3. 查看示例代码

```bash
# 股票池示例
python3 example_stock_pool.py

# 财务数据示例
python3 example_fundamental_data.py

# 回测示例
python3 test_simple_backtest.py
```

---

### 4. 阅读完整文档

| 文档 | 说明 |
|------|------|
| `SOLUTION_SUMMARY.md` | 完整解决方案总结 |
| `PAPER_TRADING_GUIDE.md` | 模拟交易使用指南 |
| `DATA_DOWNLOAD.md` | 数据下载指南 |
| `CONFIG_GUIDE.md` | 配置文件使用指南 |
| `AUDIT_REPORT.md` | 项目审计报告 |

---

## 🎯 检查清单

完成快速开始后，确认以下各项：

- [ ] ✅ 依赖安装成功
- [ ] ✅ 能运行 `main.py --help`
- [ ] ✅ 能运行完整流程（下载 → 选股 → 回测 → 交易）
- [ ] ✅ 能看到日志输出
- [ ] ✅ 能查看交易结果
- [ ] ✅ 能更换策略（value/growth/momentum）
- [ ] ✅ 能调整参数（stocks/capital/volume）

**全部勾选**？恭喜！你已经掌握了基础用法！🎉

---

## 💡 小贴士

### 1. 首次运行慢？

**正常**！首次运行需要下载数据，后续运行会快很多。

```bash
# 第二次运行（跳过下载）
python3 main.py --skip-download --strategy value --stocks 5
```

---

### 2. 想快速测试？

```bash
# 使用最少数据
python3 main.py --strategy value --stocks 3 --skip-download --skip-backtest
```

---

### 3. 查看详细日志？

```bash
# 设置日志级别为 DEBUG
python3 main.py --log-level DEBUG --stocks 5
```

---

### 4. 保存结果？

```bash
# 交易结果自动保存到 ./paper_trading_main/
ls -la paper_trading_main/

# 日志自动保存到 ./logs/
ls -la logs/
```

---

### 5. 清理缓存？

```bash
# 清理缓存目录
rm -rf cache/

# 清理日志（保留最近 7 天）
find logs/ -name "*.log" -mtime +7 -delete
```

---

## 🎉 恭喜完成！

你现在已经：
- ✅ 安装了依赖
- ✅ 运行了第一个策略
- ✅ 查看了交易结果
- ✅ 掌握了基本用法

**接下来**:
- 尝试不同策略
- 调整配置参数
- 阅读完整文档
- 开发自己的策略

---

**遇到问题？**

1. 查看 `常见问题` 章节
2. 阅读完整文档（`CONFIG_GUIDE.md` 等）
3. 查看日志文件（`logs/`）
4. 在 GitHub 提 Issue

---

**文档版本**: 1.0  
**最后更新**: 2026-03-01  
**维护者**: vnpy 开发团队

[耶]
