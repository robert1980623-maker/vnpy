# Agent 执行报告指南

## 快速开始

### 1. 在 Agent 中使用报告生成器

```python
from agent_report import create_report

def run_your_agent():
    # 创建报告器
    reporter = create_report("你的 Agent 名称")
    
    try:
        # 你的业务逻辑
        items = [...]  # 待处理项
        
        reporter.update_metric('items_processed', len(items))
        
        results = []
        for item in items:
            try:
                # 处理逻辑
                success = process_item(item)
                
                if success:
                    reporter.increment_counter('items_success')
                    results.append({'项目': item, '状态': '✅ 成功'})
                else:
                    reporter.increment_counter('items_failed')
                    results.append({'项目': item, '状态': '❌ 失败'})
            
            except Exception as e:
                reporter.increment_counter('errors')
                reporter.increment_counter('items_failed')
                results.append({'项目': item, '状态': '❌ 错误', '错误': str(e)})
        
        # 添加报告章节
        reporter.add_section("处理结果", results, format_type='table')
        
        # 完成报告
        result = reporter.finish('success')
        
    except Exception as e:
        reporter.increment_counter('errors')
        result = reporter.finish('failed')
        raise
    
    return result
```

### 2. 输出示例

```
======================================================================
📊 数据下载 Agent 执行报告
时间：2026-03-15 22:45:00
======================================================================

【执行概览】
  状态：✅ 成功
  耗时：15.23 秒
  处理：14 项
  成功：13 项
  失败：1 项
  警告：0 个
  错误：0 个

【下载详情】
┌─────────────────┬─────────────────┬─────────────────┐
│      股票       │      状态       │      耗时       │
├─────────────────┼─────────────────┼─────────────────┤
│  600519.SH  │   ✅ 成功   │     1.2s      │
│  000858.SZ  │   ✅ 成功   │     0.9s      │
│  300750.SZ  │   ✅ 成功   │     1.1s      │
│  000001.SZ  │   ❌ 失败   │     超时      │
└─────────────────┴─────────────────┴─────────────────┘

【数据统计】
  • 总数据量：14 条
  • 成功：13 条 (92.9%)
  • 失败：1 条 (7.1%)
  • 平均耗时：1.09 秒/条

======================================================================
报告生成：2026-03-15 22:45:15
======================================================================
```

---

## 集成到现有 Agent

### 示例 1: 数据下载 Agent

```python
# data_agent.py
from agent_report import create_report

class UnifiedDataAgent:
    def run_all(self, symbols: List[str] = None):
        reporter = create_report("统一数据下载 Agent")
        
        try:
            # 1. 下载日线数据
            download_results = self.download_daily_bars(symbols)
            reporter.add_section("日线数据下载", download_results, 'table')
            reporter.update_metric('items_success', len([r for r in download_results if r['status'] == 'success']))
            
            # 2. 下载政策数据
            policy_result = self.download_policy_data()
            reporter.add_section("政策数据", {'状态': policy_result}, 'text')
            
            # 3. 下载新闻数据
            news_results = self.download_news_data()
            reporter.add_section("新闻数据", news_results, 'table')
            
            reporter.finish('success')
            
        except Exception as e:
            reporter.increment_counter('errors')
            reporter.finish('failed')
            raise
```

### 示例 2: 选股 Agent

```python
# elite_stock_selector.py
from agent_report import create_report

class EliteStockSelector:
    def select_stocks(self):
        reporter = create_report("精英选股 Agent")
        
        try:
            # 选股逻辑
            candidates = self.get_candidates()
            reporter.add_section("候选股票池", candidates[:10], 'table')
            
            # 筛选
            selected = self.filter_stocks(candidates)
            reporter.add_section("最终选股", selected, 'table')
            
            # 分析
            analysis = self.analyze_stocks(selected)
            reporter.add_section("股票分析", analysis, 'table')
            
            reporter.update_metric('items_processed', len(selected))
            reporter.update_metric('items_success', len(selected))
            
            reporter.finish('success')
            return selected
            
        except Exception as e:
            reporter.increment_counter('errors')
            reporter.finish('failed')
            raise
```

### 示例 3: 风控 Agent

```python
# chief_risk_officer.py
from agent_report import create_report

class ChiefRiskOfficer:
    def check_risk(self):
        reporter = create_report("首席风险官 Agent")
        
        try:
            # 仓位检查
            position_risks = self.check_position_risk()
            reporter.add_section("仓位风险检查", position_risks, 'table')
            
            # 止盈止损检查
            stop_loss_results = self.check_stop_loss()
            reporter.add_section("止盈止损检查", stop_loss_results, 'table')
            
            # 风险评分
            risk_score = self.calculate_risk_score()
            reporter.add_section("风险评分", risk_score, 'text')
            
            # 统计
            total_positions = len(position_risks)
            risky_positions = len([p for p in position_risks if p.get('risk_level') == 'high'])
            
            reporter.update_metric('items_processed', total_positions)
            reporter.update_metric('items_success', total_positions - risky_positions)
            reporter.update_metric('warnings', risky_positions)
            
            reporter.finish('success' if risky_positions == 0 else 'warning')
            
        except Exception as e:
            reporter.increment_counter('errors')
            reporter.finish('failed')
            raise
```

---

## 报告格式类型

### 1. 表格格式 (table)

适合结构化数据：

```python
reporter.add_section("处理结果", [
    {'股票': '600519.SH', '状态': '成功', '耗时': '1.2s'},
    {'股票': '000858.SZ', '状态': '成功', '耗时': '0.9s'},
    {'股票': '300750.SZ', '状态': '失败', '错误': '超时'},
], format_type='table')
```

### 2. 列表格式 (list)

适合简单列表：

```python
reporter.add_section("警告信息", [
    "数据延迟：300750.SZ",
    "数据延迟：000858.SZ",
    "性能警告：下载速度慢",
], format_type='list')
```

### 3. 文本格式 (text)

适合键值对：

```python
reporter.add_section("统计信息", {
    '总数据量': 100,
    '成功': 95,
    '失败': 5,
    '成功率': '95%',
}, format_type='text')
```

---

## 指标说明

| 指标 | 说明 | 自动计算 |
|------|------|---------|
| `start_time` | 开始时间 | ✅ |
| `end_time` | 结束时间 | ✅ |
| `duration_seconds` | 耗时（秒） | ✅ |
| `status` | 状态 (success/failed/warning) | ❌ |
| `items_processed` | 处理总数 | ❌ |
| `items_success` | 成功数量 | ❌ |
| `items_failed` | 失败数量 | ❌ |
| `warnings` | 警告数量 | ❌ |
| `errors` | 错误数量 | ❌ |

---

## Slack 发送

报告会自动通过 OpenClaw cron 的 delivery 配置发送到 Slack。

无需额外配置，只需要：

1. 在 Agent 中使用 `reporter.finish(send_slack=True)`
2. cron 任务配置了 delivery（已配置）

---

## 最佳实践

### ✅ 推荐

1. **每个 Agent 都使用报告器** - 统一格式
2. **添加关键指标** - 处理数、成功率、耗时
3. **使用表格展示详情** - 清晰易读
4. **失败时记录错误** - 便于排查
5. **定期回顾报告** - 优化性能

### ❌ 避免

1. ~~报告过长~~ - 限制在 50 行内
2. ~~过多细节~~ - 只展示关键信息
3. ~~没有统计~~ - 一定要有汇总指标
4. ~~隐藏错误~~ - 明确标出失败项

---

## 示例输出

查看 `reports/agent_reports/` 目录中的历史报告。

---

## 下一步

1. 在主要 Agent 中集成报告生成器
2. 统一报告格式
3. 添加更多指标
4. 优化表格展示
