# VNPY 修复计划 — 详细迁移方案

> **编制：** Atlas（首席架构师）  
> **日期：** 2026-04-14  
> **状态：** 待评审  
> **基于：** Q-Trade 评估意见 + 实际代码核实

---

## 📊 修复状态总览

| 任务 | 原状态 | 核实结果 | 实际状态 |
|------|--------|---------|---------|
| P0-4 估值数据真实化 | ✅ 完成 | 个股 ✅ 行业 ❌ | ⚠️ 行业估值已修复（本次） |
| P0-3 Industry Rotation 签名 | ✅ 完成 | 文档签名与实际不一致 | ✅ 代码无问题，文档已更新 |
| P1-1 配置迁移 | ✅ 完成 | 配置文件路径错误导致 import 失败 | ✅ 已修复（本次） |
| P1-2 retry_count 修复 | ✅ 完成 | 确认无误 | ✅ |
| P1-3 时区处理 | ✅ 完成 | 向后兼容 | ✅ |
| P1-4 _get_price 返回类型 | ✅ 完成 | 确认返回 Optional[float] | ✅ |
| P1-5 LRU 缓存 | ✅ 完成 | 向后兼容 | ✅ |
| P1-6 仓位计算 | ✅ 完成 | 确认改用 total_assets | ✅ |
| P2-1 Issue Queue SQLite | ✅ 完成 | 确认迁移完成 | ✅ |
| P2-2 回测细节完善 | ✅ 完成 | 方法存在于 cross_sectional_engine.py | ✅ Q-Trade 评估有误 |
| P2-3 集成测试 | ✅ 完成 | - | ✅ |
| P2-4 告警多渠道 | ✅ 完成 | 向后兼容 | ✅ |
| P2-5 股票池扩充 | ✅ 完成 | __init__ 自动调用扩展 | ✅ 文档已更新 |

---

## 🔧 本次已完成的修复

### 1. P1-1 配置文件路径修复
**问题：** `vnpy_config.py` 和 `vnpy_config.yaml` 放在 `vnpy_analysis/` 目录下，但 `delta_consumer.py` 的 `from vnpy_config import get_delta_consumer_config` 无法 import。

**修复：** 已将配置文件复制到 `examples/alpha_research/` 目录下。

```
✅ vnpy_analysis/vnpy_config.py  →  examples/alpha_research/vnpy_config.py
✅ vnpy_analysis/vnpy_config.yaml  →  examples/alpha_research/vnpy_config.yaml
```

### 2. P0-4 行业估值真实化
**问题：** `_get_industry_valuation()` 使用硬编码固定值（bank PE=5.0, liquor PE=25.0...），未接入真实数据。

**修复：** 改为从行业成分股计算平均 PE/PB（前 50 只股票）。

```python
# 修改前：硬编码
valuations = {
    "bank": (5.0, 0.6),
    "liquor": (25.0, 5.0),
    ...
}

# 修改后：从成分股计算
def _get_industry_valuation(self, industry: str) -> Tuple[float, float]:
    industry_stocks = self.INDUSTRY_STOCKS.get(industry, [])
    pe_values, pb_values = [], []
    for stock in industry_stocks[:50]:
        stock_data = funda.get_stock_valuation(stock)
        if stock_data:
            if stock_data.get('pe') and stock_data['pe'] > 0:
                pe_values.append(stock_data['pe'])
            if stock_data.get('pb') and stock_data['pb'] > 0:
                pb_values.append(stock_data['pb'])
    avg_pe = sum(pe_values) / len(pe_values) if pe_values else 15.0
    avg_pb = sum(pb_values) / len(pb_values) if pb_values else 2.0
    return (avg_pe, avg_pb)
```

### 3. 文档更新
- **P0-3 签名**：更新为实际签名（含 `lookback_momentum`、`top_industries` 等额外参数）
- **P2-5 股票池**：明确说明 `__init__` 中自动调用 `_expand_industry_pool()`
- **P0-4 估值**：补充行业估值从硬编码改为动态计算的说明

---

## 📋 迁移方案（分三阶段）

### 阶段一：环境准备（Day 1，1-2 小时）

#### 1.1 代码更新
```bash
cd /Users/rowang/projects/vnpy
git pull origin main  # 或合并修复分支
```

#### 1.2 配置文件确认
确认以下文件存在且可 import：
```python
# 在 examples/alpha_research/ 目录下运行
python3 -c "from vnpy_config import get_delta_consumer_config; print('✅ 配置加载成功')"
```

#### 1.3 环境变量检查
```bash
# 确认 Tushare Token 已配置
echo $TUSHARE_TOKEN

# 如未配置，添加到 ~/.zshrc
export TUSHARE_TOKEN="your_token_here"
```

#### 1.4 财务数据缓存构建
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 build_fina_cache.py
# 预计 25 分钟，构建 4627 只股票的财务指标缓存
```

---

### 阶段二：回测验证（Day 2-3，4-6 小时）

#### 2.1 基准回测（使用修复前代码）
```bash
# 切回修复前版本
git checkout <修复前 commit>

# 运行标准回测
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 backtest_runner.py --strategy industry_rotation --start 2025-01-01 --end 2026-04-01
```

**保存基线指标：**
- 年化收益率
- 最大回撤
- Sharpe 比率
- 胜率
- 交易次数

#### 2.2 修复后回测
```bash
git checkout main  # 切回修复后版本

# 运行相同参数回测
python3 backtest_runner.py --strategy industry_rotation --start 2025-01-01 --end 2026-04-01
```

#### 2.3 差异对比
| 指标 | 修复前 | 修复后 | 差异 | 可接受范围 |
|------|--------|--------|------|-----------|
| 年化收益率 | TBD | TBD | TBD | ±20% |
| 最大回撤 | TBD | TBD | TBD | ±10% |
| Sharpe 比率 | TBD | TBD | TBD | ±0.3 |
| 胜率 | TBD | TBD | TBD | ±10% |
| 交易次数 | TBD | TBD | TBD | ±30% |

**判断标准：**
- 差异在可接受范围内 → 直接进入阶段三
- 差异超出范围 → 需要调整策略参数

#### 2.4 参数调优（如需要）
```python
# 重点调整的参数
strategy_params = {
    'max_pe': 20,           # P0-4 后 PE 变为真实值，可能需要调整阈值
    'max_pb': 3,            # 同上
    'min_dividend_yield': 1, # 股息率数据源变更
    'lookback_momentum': 20, # 动量回看周期
    'top_industries': 3,     # 选股行业数量
}
```

---

### 阶段三：生产切换（Day 4-5，1 小时）

#### 3.1 切换检查清单
- [ ] 回测差异在可接受范围内
- [ ] 财务数据缓存已构建完成
- [ ] 配置文件路径正确
- [ ] Tushare Token 有效
- [ ] 策略参数已调优（如有需要）

#### 3.2 灰度切换
```python
# 第一步：先在模拟账户运行 1-2 天
python3 paper_trading.py --strategy industry_rotation --account virtual_2026

# 第二步：确认无异常后切到实盘
python3 live_trading.py --strategy industry_rotation
```

#### 3.3 监控指标
切换后 48 小时内重点关注：
- 选股结果是否合理（PE/PB 分布）
- 交易信号是否与预期一致
- 有无异常报错日志
- 行业轮动是否正常触发

---

## 👥 分工建议

| 任务 | 负责人 | 预计工时 |
|------|--------|---------|
| 阶段一：环境准备 | 量化交易助理 | 1-2h |
| 阶段二：回测验证 | 量化交易助理 + QFS | 4-6h |
| 阶段二：参数调优 | QFS | 2-3h |
| 阶段三：生产切换 | 量化交易助理 | 1h |
| 阶段三：监控 | 量化交易助理 | 48h |

---

## ⚠️ 风险提示

### 高风险
1. **P0-4 估值数据真实化** — PE/PB 从 hash() 改为真实数据，策略信号会完全改变
   - **缓解措施：** 阶段二充分回测对比，必要时调整参数阈值

### 中风险
2. **P1-6 仓位计算逻辑** — initial_capital → total_assets，收益曲线会变化
   - **缓解措施：** 对比前后收益曲线，确认变化方向合理

3. **P2-5 股票池扩充** — 医药 5→479，制造 4→533
   - **缓解措施：** 确认新增股票的因子有效性，必要时设置过滤条件

### 低风险
4. **P1-4 _get_price 返回类型** — float → Optional[float]
   - **缓解措施：** 调用方加 None 检查，已有防护

---

## 📞 问题反馈

遇到问题请在群内 @Atlas 或 @Quantitative Finance Specialist 协助排查。
