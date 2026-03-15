# Agent 报告模板使用指南

## 快速开始

### 1. 自动模板检测

```python
from agent_report import create_report

# 创建报告器（自动检测模板）
reporter = create_report("数据下载 Agent")
# 自动使用 'data_download' 模板

reporter = create_report("选股 Agent")
# 自动使用 'stock_selection' 模板

reporter = create_report("风控 Agent")
# 自动使用 'risk_control' 模板
```

### 2. 手动指定模板

```python
from agent_report import AgentReporter

# 手动指定模板
reporter = AgentReporter(
    agent_name="我的 Agent",
    template_name="trading"  # 交易模板
)
```

---

## 可用模板

### 1. 📥 数据下载模板 (data_download)

**适用**: 数据下载类 Agent

**指标**:
- 状态、耗时、处理数量、成功率

**表格**:
- 下载详情（股票代码、数据类别、状态、耗时、错误）
- 数据分类统计

**示例**:
```python
reporter = create_report("数据下载 Agent")

# 添加数据
reporter.add_section("下载详情", {
    'table_data': [
        {'股票代码': '600519.SH', '数据类别': '日线', '状态': '✅ 成功', '耗时': '1.2s'},
        {'股票代码': '300750.SZ', '数据类别': '日线', '状态': '❌ 失败', '错误': '超时'},
    ]
})

reporter.finish('success')
```

---

### 2. 🎯 选股模板 (stock_selection)

**适用**: 选股类 Agent

**指标**:
- 状态、候选股票数、最终选股数、入选率

**表格**:
- 最终选股结果（代码、名称、理由、评分、风险）
- 筛选过程（条件、筛选前、筛选后、淘汰率）

**示例**:
```python
reporter = create_report("精英选股 Agent")

reporter.add_section("选股结果", {
    'table_data': [
        {'股票代码': '600519.SH', '股票名称': '贵州茅台', '入选理由': '基本面优秀', '评分': '95', '风险提示': '估值较高'},
    ],
    'total_candidates': 100,
    'selected_count': 5,
    'selection_rate': 0.05,
})

reporter.finish('success')
```

---

### 3. 💰 交易模板 (trading)

**适用**: 交易执行类 Agent

**指标**:
- 状态、总交易数、买入数、卖出数、交易金额

**表格**:
- 交易明细（代码、方向、价格、数量、金额、状态）
- 持仓变化（代码、原持仓、新持仓、变化、市值）

**示例**:
```python
reporter = create_report("自动交易 Agent")

reporter.add_section("交易明细", {
    'table_data': [
        {'股票代码': '600519.SH', '交易方向': '买入', '价格': '1800.00', '数量': '100', '金额': '180000', '状态': '已成交'},
    ],
    'total_trades': 5,
    'buy_count': 3,
    'sell_count': 2,
    'total_amount': 500000,
})

reporter.finish('success')
```

---

### 4. 🛡️ 风控模板 (risk_control)

**适用**: 风险控制类 Agent

**指标**:
- 状态、风险等级、持仓数量、风险评分

**表格**:
- 仓位风险检查（代码、占比、预警线、状态、建议）
- 止盈止损检查（代码、当前价、成本价、盈亏率、触发状态）

**示例**:
```python
reporter = create_report("首席风险官 Agent")

reporter.add_section("仓位风险", {
    'table_data': [
        {'股票代码': '600519.SH', '持仓占比': '20%', '预警线': '20%', '状态': '⚠️ 预警', '建议': '减仓'},
    ],
    'risk_level': 'medium',
    'total_positions': 14,
    'risk_score': 65,
})

reporter.finish('warning')
```

---

### 5. 📊 监控模板 (monitoring)

**适用**: 监控类 Agent

**指标**:
- 状态、监控任务数、健康数、警告数、异常数

**表格**:
- 任务状态（名称、状态、上次运行、下次运行、连续错误）

**示例**:
```python
reporter = create_report("Agent 健康检查 Agent")

reporter.add_section("任务状态", {
    'table_data': [
        {'任务名称': '数据下载', '状态': '✅ ok', '上次运行': '1h ago', '下次运行': 'in 23h', '连续错误': '0'},
    ],
    'total_tasks': 34,
    'healthy_count': 32,
    'warning_count': 2,
    'error_count': 0,
})

reporter.finish('success')
```

---

### 6. 📝 复盘模板 (daily_review)

**适用**: 每日复盘类 Agent

**指标**:
- 状态、交易日期、今日盈亏、收益率

**表格**:
- 持仓表现（代码、名称、持仓、盈亏、盈亏率、建议）
- 交易记录（时间、代码、方向、价格、数量、盈亏）

**示例**:
```python
reporter = create_report("每日复盘 Agent")

reporter.add_section("持仓表现", {
    'table_data': [
        {'股票代码': '600519.SH', '股票名称': '贵州茅台', '持仓': '100', '盈亏': '+5000', '盈亏率': '+2.8%', '操作建议': '持有'},
    ],
    'total_return': 12345,
    'return_rate': 0.0123,
    'summary': '今日市场上涨，持仓表现良好',
})

reporter.finish('success')
```

---

### 7. 🤖 通用模板 (generic)

**适用**: 其他所有 Agent

**指标**:
- 状态、耗时、处理数、成功数、失败数

**表格**:
- 详细结果（项目、状态、详情）

**示例**:
```python
reporter = create_report("其他 Agent")

reporter.add_section("执行结果", {
    'table_data': [
        {'项目': '任务 A', '状态': '✅ 成功', '详情': '完成'},
        {'项目': '任务 B', '状态': '❌ 失败', '详情': '超时'},
    ],
})

reporter.finish('success')
```

---

## 模板自动检测规则

| Agent 名称关键词 | 使用模板 |
|-----------------|---------|
| 数据下载、data | data_download |
| 选股、stock | stock_selection |
| 交易、trading | trading |
| 风控、risk | risk_control |
| 监控、monitor | monitoring |
| 复盘、review | daily_review |
| 其他 | generic |

---

## 数据格式

### metrics 数据

```python
metrics = {
    'status': 'success',           # success/failed/warning/running
    'duration_seconds': 15.23,     # 耗时（秒）
    'items_processed': 100,        # 处理数量
    'items_success': 95,           # 成功数量
    'items_failed': 5,             # 失败数量
}
```

### table_data 数据

```python
data = {
    'table_data': [
        {'列 1': '值 1', '列 2': '值 2', '列 3': '值 3'},
        {'列 1': '值 4', '列 2': '值 5', '列 3': '值 6'},
    ]
}
```

### list_data 数据

```python
data = {
    'list_data': [
        {'error_type': '网络错误', 'count': 3, 'example': '超时'},
        {'error_type': '数据错误', 'count': 2, 'example': '格式错误'},
    ]
}
```

---

## 完整示例

```python
from agent_report import create_report

def run_data_download_agent():
    # 创建报告器（自动使用 data_download 模板）
    reporter = create_report("统一数据下载 Agent")
    
    try:
        # 业务逻辑
        stocks = ['600519.SH', '000858.SZ', '300750.SZ']
        results = []
        
        for stock in stocks:
            try:
                success = download_data(stock)
                if success:
                    results.append({
                        '股票代码': stock,
                        '数据类别': '日线',
                        '状态': '✅ 成功',
                        '耗时': '1.2s',
                        '错误信息': '-'
                    })
                    reporter.increment_counter('items_success')
                else:
                    results.append({
                        '股票代码': stock,
                        '状态': '❌ 失败',
                        '错误信息': '下载失败'
                    })
                    reporter.increment_counter('items_failed')
            except Exception as e:
                reporter.increment_counter('errors')
        
        # 添加章节
        reporter.add_section("下载详情", {
            'table_data': results,
            'success_rate': reporter.metrics['items_success'] / len(stocks)
        })
        
        # 更新指标
        reporter.update_metric('items_processed', len(stocks))
        
        # 完成报告
        result = reporter.finish('success')
        
    except Exception as e:
        reporter.increment_counter('errors')
        result = reporter.finish('failed')
        raise
    
    return result
```

---

## 输出示例

```
======================================================================
📥 数据下载 Agent 报告
生成时间：2026-03-15 22:50:00
======================================================================

【执行概览】
  状态：✅ 成功
  耗时：15.23 秒
  处理数量：14
  成功率：92.9%

【下载详情】
  ┌──────────┬──────────┬──────────┬──────────┬──────────┐
  │  股票代码  │  数据类别  │   状态   │   耗时   │  错误信息  │
  ├──────────┼──────────┼──────────┼──────────┼──────────┤
  │ 600519.SH │   日线   │ ✅ 成功  │  1.2s   │    -     │
  │ 000858.SZ │   日线   │ ✅ 成功  │  0.9s   │    -     │
  │ 300750.SZ │   日线   │ ❌ 失败  │    -    │   超时   │
  └──────────┴──────────┴──────────┴──────────┴──────────┘

【问题汇总】
  • 网络超时：1 个 - 300750.SZ

======================================================================
数据下载完成 | 2026-03-15 22:50:15
======================================================================
```

---

## 下一步

1. 在 Agent 中使用模板
2. 根据需要自定义模板
3. 添加更多模板类型
4. 优化表格格式
