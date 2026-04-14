# VNPY 量化交易系统 — AgentSkill 详细设计 v1.1

> **版本：** v1.1.0  
> **日期：** 2026-04-14  
> **状态：** 终稿（已纳入三位同事 review）  
> **Reviewers：** 量化交易助理、Data Engineer、Quantitative Finance Specialist

---

## 一、设计目标

### 1.1 核心痛点

| 痛点 | 场景 | 解法 |
|------|------|------|
| 命令/路径记不住 | "数据在哪？怎么跑选股？" | 自然语言驱动，自动定位 |
| 数据格式混乱 | CSV/Parquet/JSON 三套格式 | 自动化转换 + 验证 |
| "文件有了但数据是旧的" | 4579 个文件但只到 3/18 | 检查最新日期，不只数文件 |
| 问题排查困难 | Round 3 报告误判 5 项全未修复 | 自动诊断 + 实时验证 |

### 1.2 设计原则

1. **操作优先，理论后置** — "帮我选股" → 直接执行
2. **诊断 → 修复 → 验证** 三步不能乱 — 先查再修再验
3. **CSV 是 source of truth** — Parquet 随时可重建
4. **自然语言 CLI** — Skill 本身就是"会说话的命令行"

---

## 二、系统架构

### 2.1 目录结构（已统一路径）

```
/Users/rowang/projects/vnpy/
│
├── alpha/strategy/
│   ├── cross_sectional_engine.py     # 截面回测引擎
│   │   └── 含涨跌停/T+1/流动性/滑点/最小交易单位
│   ├── industry_rotation.py          # 行业轮动策略
│   │   └── 继承 StockScreenerStrategy
│   └── strategies/                   # 预设策略
│
├── examples/alpha_research/          # ⭐ 运行工作目录
│   ├── csv_to_parquet.py             # CSV → Parquet（双格式）
│   ├── tushare_pro_downloader.py     # Tushare 数据下载
│   ├── build_fina_cache.py           # 财务缓存构建
│   ├── check_data_freshness.py       # 数据新鲜度诊断（v1.1 新增）
│   ├── daily_stock_selection.py      # 每日选股
│   ├── vnpy_config.yaml              # 统一配置
│   ├── vnpy_config.py
│   ├── accounts/virtual_2026_account.json
│   ├── cache/fundamental/            # 财务缓存 9397 文件
│   └── lab/                          # AlphaLab 工作目录
│       ├── test/daily/*.parquet      # ⭐ 主数据 4579 只
│       ├── test_lab/daily/           # 测试副本
│       └── test_engine/daily/        # 回测副本
│
├── lab/data/daily/                   # ⭐ AlphaLab 默认路径
│   └── *.parquet                     # 9128 文件（已同步）
│
├── vnpy/lab/data/daily/              # ⭐ 另一个默认路径
│   └── *.parquet                     # 4579 文件（已同步）
│
├── data/akshare/bars/*.csv           # 原始数据 4627 只
│
└── vnpy-skill/                       # ⭐ AgentSkill 包
    ├── SKILL.md
    ├── scripts/
    │   ├── check_data_freshness.py   # 数据诊断
    │   ├── rebuild_positions.py      # 持仓重建
    │   └── daily_workflow.py         # 每日工作流（待实现）
    └── references/
        └── architecture.md
```

### 2.2 数据流（含降级策略）

```
                    ┌─────────────────┐
                    │   Tushare Pro   │ ← 优先数据源
                    │  (15:00 后当天)  │
                    └────────┬────────┘
                             │ 失败
                             ▼
                    ┌─────────────────┐
                    │    AKShare      │ ← 降级数据源
                    │  (网络可能不通)  │
                    └────────┬────────┘
                             │ 失败
                             ▼
                    ┌─────────────────┐
                    │  告警 + 用旧缓存  │
                    └─────────────────┘
                             │
                    ┌────────┴────────┐
                    │  CSV (source of │
                    │  truth, 4627只)  │
                    └────────┬────────┘
                             │ csv_to_parquet.py
                             ▼
                    ┌─────────────────┐
                    │  Parquet 格式   │ ← AlphaLab 读取
                    │  3个目录同步     │
                    └────────┬────────┘
                             │ load_bar_data()
                             ▼
                    ┌─────────────────┐
                    │  验证: 数量>4000 │
                    │  日期=最近交易日  │
                    │  可加载>0 条     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  回测 / 选股    │
                    └─────────────────┘
```

### 2.3 数据下载时间窗口

| 时段 | 可下载 | 说明 |
|------|--------|------|
| 盘中 9:30-15:00 | 历史数据（昨天及以前） | 当天数据未发布 |
| 盘后 15:00-23:00 | 当天数据 + 历史 | 最佳下载窗口 |
| 非交易日 | 最近交易日数据 | 节假日自动跳过 |

---

## 三、场景设计

### 场景 1：每日选股（最常用）

**触发词：** "选股"、"今天买什么"、"daily selection"

**执行流程（四步法）：**

```
1. 诊断
   └── check_data_freshness()
       ├── Parquet 数量 ≥ 4000？
       ├── 抽样最新日期 = 最近交易日？（≤ 5 天）
       ├── AlphaLab 加载测试 > 0 条？
       ├── 财务缓存存在？
       └── 持仓非空？

2. 修复（如需）
   ├── CSV 有但 Parquet 缺 → csv_to_parquet.py
   ├── CSV 也缺 → tushare_pro_downloader.py
   ├── 持仓为空 → rebuild_positions.py
   └── 财务缓存缺 → build_fina_cache.py

3. 验证
   └── 重新 check_data_freshness()
       └── status == OK？→ 继续
       └── status == ERROR？→ 告警，人工介入

4. 执行
   └── python3 daily_stock_selection.py
       ├── 多策略选股
       ├── 生成交易计划
       └── 同步飞书多维表格
```

**用户对话示例：**
```
用户：帮我选股
AI：  [诊断] Parquet: 4579 ✅ 日期: 4/13 ✅ 加载: 9条 ✅
      [执行] 选股完成，10 只
      Top 3:
      1. 宇通客车 600066 - 价值+质量 (PE=6.5, ROE=13.4%)
      2. 招商银行 600036 - 价值 (PE=6.5, 股息率=7.7%)
      3. 中国平安 601318 - 价值 (PE=7.8, 股息率=4.5%)
```

---

### 场景 2：数据新鲜度检查

**触发词：** "数据"、"过期"、"freshness"、"download"

**核心改进（v1.1）：** 不仅数文件数量，还要检查最新日期

**检查项：**

| 检查项 | 阈值 | 动作 |
|--------|------|------|
| Parquet 数量 | ≥ 4000 | 低于则转换/下载 |
| Parquet 最新日期 | ≤ 5 天前 | 过期则更新 |
| AlphaLab 加载 | > 0 条（近 14 天） | 为 0 则诊断 |
| 财务缓存 | ≥ 1000 文件 | 不足则重建 |
| 持仓数组 | > 0（有 trades 时） | 为空则重建 |
| Tushare Token | 已设置 | 未设置则提示 |

**输出示例：**
```
📊 VNPY 数据新鲜度报告
状态: WARNING

📊 检查项:
  parquet_count: 4579 ✅
  parquet_date_range: 2026-03-18 ~ 2026-04-13
  alphalab_load: 9 条 ✅
  fundamental_cache: 9397 ✅
  positions: 8 ✅
  tushare: ✅ 连通

⚠️ 问题:
  1. 部分股票数据仅到 3/18（35 只）

🔧 建议:
  → 运行: python3 csv_to_parquet.py 更新缺失文件
```

---

### 场景 3：持仓重建

**触发词：** "持仓丢了"、"positions 为空"、"rebuild"

**执行流程：**
```
1. 读取 trades 数组
2. 按 symbol 汇总（buy +, sell -）
3. 过滤 quantity > 0
4. 计算 avg_cost
5. 写回 account JSON
6. 验证: positions 数量 matches 预期
```

---

### 场景 4：回测验证

**触发词：** "回测"、"backtest"、"验证"

**前置条件：**
- Parquet > 4000 只
- 最新日期 = 最近交易日
- AlphaLab 加载验证通过
- 持仓非空

**执行流程：**
```
1. 初始化 AlphaLab
2. 验证数据可加载
3. 配置截面回测引擎
4. 设置策略和参数（从 vnpy_config.yaml 读取调仓周期等）
5. 执行回测
6. 输出报告（年化、回撤、Sharpe、交易明细）
```

**关键参数（可配置，非硬编码）：**

| 参数 | 默认 | 来源 |
|------|------|------|
| `max_pe` | 20 | vnpy_config.yaml |
| `max_pb` | 3 | vnpy_config.yaml |
| `top_industries` | 3 | vnpy_config.yaml |
| `rebalance_days` | 5-20 | vnpy_config.yaml |
| `initial_capital` | 1,000,000 | 回测脚本参数 |

---

### 场景 5：生产迁移（五步法）

**触发词：** "切生产"、"迁移"、"migrate"

```
Step 1: 代码就绪
  ├── P0-4 行业估值真实化 ✅
  ├── P1-1 配置路径修复 ✅
  ├── P2-2 回测约束实现 ✅
  └── import 路径修正 ✅

Step 2: 数据就绪
  ├── Parquet > 4000 只 ✅
  ├── 最新日期 = 最近交易日 ✅
  └── 持仓重建完成 ✅

Step 3: 回测对比
  ├── 基准回测（修复前 commit）
  ├── 新版回测
  └── 信号相关性 < 0.7 → 重新调参

Step 4: 虚拟盘验证
  ├── 运行 1-2 个调仓周期（5-20 天，从 vnpy_config.yaml 读取）
  ├── 监控信号合理性
  └── 对比回测与虚拟盘差异

Step 5: 逐步切换
  ├── 30% 资金 → 观察 1 周
  ├── 50% 资金 → 观察 1 周
  └── 100% 资金 → 正式生产
```

**⚠️ 数据回滚机制：**
- CSV 是 source of truth，不会被 Parquet 覆盖
- Parquet 有问题时：删除 → 重新 csv_to_parquet.py → 验证
- 关键数据变更前后自动备份到 `lab/backup/YYYYMMDD/`

---

## 四、脚本清单

| 脚本 | 功能 | 输入 | 输出 | 状态 |
|------|------|------|------|------|
| `check_data_freshness.py` | 数据诊断（数量+日期+加载） | lab 路径 | 诊断报告 | ✅ 已实现 |
| `csv_to_parquet.py` | CSV→Parquet（双格式） | CSV 目录 | Parquet | ✅ 已测试 |
| `rebuild_positions.py` | 持仓重建 | account JSON | 更新的 JSON | ✅ 已测试 |
| `build_fina_cache.py` | 财务缓存构建 | Tushare Token | JSON 缓存 | ✅ 已测试 |
| `tushare_pro_downloader.py` | 数据下载 | 股票代码 | CSV | ✅ 已存在 |
| `daily_workflow.py` | 每日工作流（诊断→修复→验证→选股） | 无 | 选股结果 | 🔄 待实现 |

---

## 五、错误处理与 FAQ

### 5.1 常见错误速查

| 错误 | 原因 | 解决命令 |
|------|------|---------|
| `ModuleNotFoundError: vnpy.alpha...` | 不在项目根目录 | `cd /Users/rowang/projects/vnpy` |
| `AlphaLab 加载 0 条` | Parquet 目录无数据 | `python3 csv_to_parquet.py --lab-dir ./lab/test` |
| `positions 数组为空` | 4·13 事故后遗症 | `python3 rebuild_positions.py` |
| `ValueError: 'daily' is not valid Interval` | 传了字符串而非枚举 | 用 `Interval.DAILY`，不要用 `'daily'` |
| `ProxyError`（AKShare） | 网络代理问题 | Tushare 正常即可，AKShare 为降级 |
| `Your token is wrong` | Tushare Token 无效 | `export TUSHARE_TOKEN=xxx` |
| `lab/data/daily 空目录` | 数据在 examples/ 下 | 已同步到所有默认路径 |

### 5.2 自动诊断

用户说"系统出问题了" → 自动运行 diagnose()：

```python
def diagnose():
    """自动诊断，返回问题列表和修复命令"""
    issues = []
    
    # 1. Python 路径
    try:
        from vnpy.alpha.lab import AlphaLab
    except ImportError:
        return ["❌ 运行: cd /Users/rowang/projects/vnpy"]
    
    # 2. 数据（数量 + 日期）
    pq = len(list(Path('./lab/test/daily').glob('*.parquet')))
    if pq < 100:
        return ["❌ Parquet 仅 " + str(pq) + "，运行: python3 csv_to_parquet.py"]
    
    # 3. 持仓
    acc = Path('./accounts/virtual_2026_account.json')
    if acc.exists():
        with open(acc) as f:
            account = json.load(f)
        if not account.get('positions'):
            trades = len(account.get('trades', []))
            if trades > 0:
                return ["⚠️ 持仓为空，运行: python3 rebuild_positions.py"]
    
    # 4. Token
    if not os.environ.get('TUSHARE_TOKEN'):
        return ["⚠️ TUSHARE_TOKEN 未设置"]
    
    return ["✅ 系统状态正常"]
```

---

## 六、Skill 使用方式

### 6.1 部署

```bash
cp -r vnpy-skill ~/.openclaw/skills/vnpy-quant/
```

### 6.2 自然语言交互

| 用户输入 | 识别 | 执行 |
|---------|------|------|
| "帮我选股" | 场景 1 | 诊断→修复→验证→选股→输出 |
| "数据过期了吗" | 场景 2 | check_data_freshness.py |
| "持仓丢了" | 场景 3 | rebuild_positions.py |
| "跑个回测" | 场景 4 | 验证→配置→执行→报告 |
| "系统出问题了" | 诊断 | diagnose() |
| "怎么切生产" | 场景 5 | 五步 checklist |

---

## 七、迭代计划

| 版本 | 内容 | 优先级 | 时间 |
|------|------|--------|------|
| v1.1 | check_data_freshness.py + 路径同步 + 降级策略 | ✅ 完成 | 今天 |
| v1.2 | daily_workflow.py + 数据备份机制 | P0 | 明天 |
| v1.3 | 回测可视化报告（HTML）+ 飞书通知自动化 | P1 | 下周 |
| v1.4 | vnpy-cli 统一入口 + 参数网格搜索 | P2 | 待定 |
