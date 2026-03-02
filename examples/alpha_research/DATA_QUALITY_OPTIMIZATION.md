# 📊 数据质量检查优化方案

**创建时间**: 2026-03-03 00:01  
**脚本位置**: `check_data_quality.py`  
**当前状态**: 已创建基础版本

---

## ✅ 当前功能

### 已实现的检查项

| 检查项 | 说明 | 状态 |
|--------|------|------|
| 文件检查 | 检查 CSV 文件是否存在 | ✅ |
| 数据结构 | 检查列名是否完整 | ✅ |
| 数据完整性 | 检查缺失值 | ✅ |
| 异常值检测 | 价格异常、涨跌幅异常 | ✅ |
| 数据连续性 | 检查数据中断 | ✅ |
| 逻辑一致性 | OHLC 逻辑、量价匹配 | ✅ |
| 质量评分 | 100 分制评分 | ✅ |
| 报告生成 | JSON 格式报告 | ✅ |

---

## 🔧 测试结果

**测试数据**: 48 只股票，11,343 条记录

```
【问题统计】
  总问题数：2289
  严重问题：0
  警告问题：2289
  提示信息：0

【质量评分】
  得分：0/100 ❌ 需要改进
```

**主要问题**:
- 异常值：20 个 (涨跌幅 > 20%)
- 数据中断：144 处 (周末/节假日正常)
- 逻辑错误：2125 处 (量价计算差异)

---

## 🚀 优化建议

### 1. 智能规则配置 ⭐⭐⭐⭐⭐

**当前问题**: 规则太严格，误报多

**优化方案**:
```python
# 优化前
'max_price_change': 0.20,  # 固定 20%

# 优化后 - 根据市场调整
'max_price_change': {
    'main_board': 0.10,      # 主板 10%
    'chi_next': 0.20,        # 创业板 20%
    'star_market': 0.20,     # 科创板 20%
    'st_stock': 0.05         # ST 股 5%
}
```

**实现**:
- 根据股票代码自动识别板块
- 不同板块使用不同阈值
- 考虑除权除息日

---

### 2. 数据连续性优化 ⭐⭐⭐⭐

**当前问题**: 周末和节假日被误报为数据中断

**优化方案**:
```python
# 加载中国节假日日历
import holidays
cn_holidays = holidays.China()

# 检查时跳过节假日
for date in date_range:
    if date.weekday() >= 5 or date in cn_holidays:
        continue  # 跳过
```

**实现**:
- 集成中国节假日日历
- 自动识别交易日
- 只检查交易日连续性

---

### 3. 量价匹配优化 ⭐⭐⭐⭐

**当前问题**: 成交量与成交额计算差异大

**原因分析**:
- 成交额 = 成交量 × 成交均价
- 成交均价 ≠ 收盘价
- 可能包含大宗交易

**优化方案**:
```python
# 优化前
if abs(avg_price - close_p) / close_p > 0.1:  # 10% 阈值
    report_issue()

# 优化后
expected_turnover = volume * (open_p + close_p) / 2
if abs(turnover - expected_turnover) / turnover > 0.2:  # 20% 阈值
    report_issue()
```

---

### 4. 异常值检测优化 ⭐⭐⭐⭐

**当前问题**: 无法区分真实异常和极端行情

**优化方案**:

**a. 多维度检测**:
```python
# 价格异常检测
- 单日涨跌幅 > 20%
- 连续 3 日累计涨跌 > 30%
- 与大盘偏离度 > 15%

# 成交量异常检测
- 成交量/20 日均量 > 5 倍
- 连续 3 日放量 > 3 倍
- 成交量为 0 (停牌)
```

**b. 上下文检测**:
```python
# 检查是否为真实异常
if price_jump and market_also_jumped:
    # 大盘也涨了，可能是系统性行情
    severity = 'info'
elif price_jump and has_news:
    # 有重大新闻，可能是合理反应
    severity = 'warning'
else:
    # 无明显原因的异常
    severity = 'critical'
```

---

### 5. 数据质量趋势 ⭐⭐⭐

**功能**: 跟踪数据质量变化

**实现**:
```python
# 每日记录质量分数
quality_history = {
    '2026-03-01': 95,
    '2026-03-02': 92,
    '2026-03-03': 88
}

# 检测质量下降
if quality_score < avg_last_7_days - 10:
    alert("数据质量显著下降!")
```

---

### 6. 自动修复建议 ⭐⭐⭐

**功能**: 对常见问题提供修复建议

**示例**:
```
【问题】000999.SZ 在 2024-01-15 数据缺失

【建议修复方案】:
1. 重新下载该日数据:
   python download_data_akshare.py --symbol 000999.SZ --date 2024-01-15

2. 从备用数据源获取:
   python download_data_baostock.py --symbol 000999.SZ

3. 手动标记为停牌日:
   echo "2024-01-15,停牌" >> suspension_days.txt
```

---

### 7. 可视化报告 ⭐⭐⭐

**功能**: 生成可视化质量报告

**实现**:
```python
import matplotlib.pyplot as plt

# 质量分数趋势图
plt.plot(dates, scores)
plt.savefig('quality_trend.png')

# 问题分布饼图
plt.pie([critical, warning, info], labels=['Critical', 'Warning', 'Info'])
plt.savefig('issues_distribution.png')
```

---

### 8. 增量检查 ⭐⭐

**当前问题**: 每次都检查全部数据，效率低

**优化方案**:
```python
# 只检查新增/修改的文件
def check_incremental():
    last_check_time = get_last_check_time()
    
    for csv_file in data_dir.glob('*.csv'):
        mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
        if mtime > last_check_time:
            check_file(csv_file)  # 只检查新文件
```

---

### 9. 并行检查 ⭐⭐

**功能**: 加速检查过程

**实现**:
```python
from concurrent.futures import ProcessPoolExecutor

def check_all_parallel():
    csv_files = list(data_dir.glob('*.csv'))
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = executor.map(check_file, csv_files)
    
    return aggregate_results(results)
```

---

### 10. 集成到 Cron ⭐⭐⭐⭐⭐

**配置定时检查**:

```bash
# 每天 02:00 自动检查
cron add --job '{
  "name": "数据质量检查",
  "schedule": {
    "kind": "cron",
    "expr": "0 2 * * *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "systemEvent",
    "text": "🔍 数据质量检查：开始检查数据质量..."
  },
  "sessionTarget": "main",
  "enabled": true
}'
```

---

## 📋 优化优先级

### 高优先级 (立即实施) ⭐⭐⭐⭐⭐

1. **智能规则配置** - 减少误报
2. **集成节假日日历** - 避免周末误报
3. **集成到 Cron** - 自动化检查

### 中优先级 (本周实施) ⭐⭐⭐⭐

4. **量价匹配优化** - 改进算法
5. **异常值检测优化** - 多维度检测
6. **自动修复建议** - 提供解决方案

### 低优先级 (未来实施) ⭐⭐⭐

7. **数据质量趋势** - 长期跟踪
8. **可视化报告** - 图表展示
9. **增量检查** - 提升效率
10. **并行检查** - 加速处理

---

## 🎯 下一步行动

### 立即执行

```bash
# 1. 测试当前脚本
python3 check_data_quality.py

# 2. 查看报告
cat reports/quality/quality_report_*.json | jq '.'

# 3. 配置 Cron (每天 02:00)
python3 -c "
import json
job = {
    'name': '数据质量检查',
    'schedule': {'kind': 'cron', 'expr': '0 2 * * *', 'tz': 'Asia/Shanghai'},
    'payload': {'kind': 'systemEvent', 'text': '🔍 数据质量检查：开始检查...'},
    'sessionTarget': 'main',
    'enabled': True
}
print(json.dumps(job, ensure_ascii=False))
"
```

### 本周完成

- [ ] 集成中国节假日日历
- [ ] 优化量价匹配算法
- [ ] 添加自动修复建议
- [ ] 配置 Cron 定时任务

### 本月完成

- [ ] 数据质量趋势跟踪
- [ ] 可视化报告
- [ ] 增量检查优化

---

## 📊 质量评分标准

| 分数 | 等级 | 说明 |
|------|------|------|
| 90-100 | ✅ 优秀 | 数据质量很高，可直接使用 |
| 80-89 | ⚠️ 良好 | 少量问题，不影响使用 |
| 70-79 | ⚠️ 及格 | 有问题，需要关注 |
| 60-69 | ❌ 较差 | 问题较多，建议修复 |
| 0-59 | ❌ 不可用 | 严重问题，需要重新下载 |

---

## 🎊 总结

**当前状态**: 基础版本已完成，可以检测主要问题

**优化方向**:
- ✅ 减少误报 (智能规则、节假日)
- ✅ 提高准确性 (多维度检测)
- ✅ 提升效率 (增量、并行)
- ✅ 增强可用性 (自动修复、可视化)

**建议**: 先实施高优先级优化，再逐步完善其他功能！

---

**数据质量是量化交易的基础，务必重视！** [耶]
