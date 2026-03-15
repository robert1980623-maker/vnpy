# Human 风格报告指南

## 为什么要 Human 化？

### ❌ 机器风格 (之前)

```
The cron job for QA change gate check has been executed successfully.
The script qa_change_gate.py ran in the virtual environment.
No errors were reported in the execution log.
No follow-up steps are needed at this time.
```

**问题**:
- 冷冰冰的机器语言
- 全是被动语态
- 没有情感色彩
- 读起来累

### ✅ Human 风格 (现在)

```
📋 QA 门禁检查完成 (23:00)

今晚的检查一切正常：
✅ 代码变更：无
✅ 测试覆盖率：95.2% (达标)
✅ 质量评分：A

简单来说：没啥问题，代码挺健康，可以继续睡个好觉 😴

下次检查：23:20
```

**优点**:
- 像人在说话
- 有情感有温度
- 重点突出
- 读起来轻松

---

## 使用指南

### 1. QA 检查报告

```python
from human_report import human_qa_report

# QA 检查结果
qa_result = {
    'changes': [],
    'coverage': 95.2,
    'passed': True,
    'issues': []
}

# 生成人话报告
report = human_qa_report(qa_result)
print(report)
```

**输出**:
```
📋 QA 门禁检查完成 (23:00)

今晚的检查一切正常：
✅ 代码变更：无
✅ 测试覆盖率：95.2% (达标)
✅ 质量评分：A

简单来说：没啥问题，代码挺健康，可以继续睡个好觉 😴

下次检查：23:20
```

---

### 2. Manager 问题队列报告

```python
from human_report import human_manager_report

# Manager 检查结果
manager_result = {
    'pending': 0,
    'processing': 0,
    'resolved': 499
}

report = human_manager_report(manager_result)
print(report)
```

**输出**:
```
📊 Manager 问题队列报告

好消息！问题队列清空了 🎉

当前状态：
  ✅ 待处理：0 个
  ✅ 处理中：0 个
  ✅ 已解决：499 个

系统运行平稳，可以安心 😌

下次检查：23:20
```

---

### 3. Agent 健康检查报告

```python
from human_report import human_health_report

# 健康检查结果
health_result = {
    'healthy': True,
    'agents_ok': 34,
    'agents_total': 34,
    'issues': []
}

report = human_health_report(health_result)
print(report)
```

**输出**:
```
💓 Agent 健康检查

所有 Agent 都活着，状态不错！💪

  ✅ 健康：34/34 个
  📊 健康率：100%

系统很健康，继续保持 👍

下次检查：23:20
```

---

### 4. 每日总结报告

```python
from human_report import human_daily_summary

# 每日数据
daily_result = {
    'trades': 5,
    'profit': 12345.67,
    'profit_rate': 0.0123,
    'positions': 14,
    'total_value': 1012345.67,
    'tasks_ok': 32,
    'tasks_total': 34,
    'issues': 0
}

report = human_daily_summary(daily_result)
print(report)
```

**输出**:
```
📝 每日总结 (03-15)

🎉 今天赚了 ¥12,345.67 (+1.23%)

  • 交易次数：5 次
  • 持仓数量：14 只
  • 账户总额：¥1,012,345.67

系统运行：
  ✅ 任务执行：32/34 成功
  ⚠️ 问题数量：0 个

今天辛苦了，明天继续！💪
```

---

## 报告风格

### 语气特点

| 特点 | 说明 | 示例 |
|------|------|------|
| **口语化** | 像朋友聊天 | "没啥问题"、"不着急" |
| **有情感** | 表达情绪 | "好消息！"、"辛苦了" |
| **用 Emoji** | 增强可读性 | ✅ ⚠️ 🎉 😴 |
| **简洁** | 不说废话 | 直接说重点 |
| **有温度** | 关心用户 | "可以安心"、"继续睡个好觉" |

### 不同场景的语气

| 场景 | 语气 | 示例 |
|------|------|------|
| **一切正常** | 轻松愉快 | "没啥问题，继续睡个好觉 😴" |
| **有小问题** | 温和提醒 | "建议有空看看，不着急 🔍" |
| **有问题** | 关心建议 | "看看日志，找找原因 🔍" |
| **赚钱了** | 开心庆祝 | "今天赚了，厉害！🎉" |
| **亏钱了** | 安慰鼓励 | "今天亏了，明天赚回来 😅" |

---

## 集成到现有 Agent

### 在 QA 门禁中使用

```python
# qa_change_gate.py
from human_report import human_qa_report

class QAChangeGate:
    def run_check(self):
        # ... QA 检查逻辑 ...
        
        result = {
            'changes': changes,
            'coverage': coverage,
            'passed': passed,
            'issues': issues
        }
        
        # 生成人话报告
        report = human_qa_report(result)
        print(report)
        
        return report
```

### 在 Manager 中使用

```python
# manager_interface.py
from human_report import human_manager_report

class QuantManager:
    def check_queue(self):
        # ... 检查队列逻辑 ...
        
        result = {
            'pending': pending_count,
            'processing': processing_count,
            'resolved': resolved_count
        }
        
        # 生成人话报告
        report = human_manager_report(result)
        print(report)
        
        return report
```

### 在健康检查中使用

```python
# agent_health_check.py
from human_report import human_health_report

class AgentHealthChecker:
    def check_health(self):
        # ... 健康检查逻辑 ...
        
        result = {
            'healthy': is_healthy,
            'agents_ok': ok_count,
            'agents_total': total_count,
            'issues': issues
        }
        
        # 生成人话报告
        report = human_health_report(result)
        print(report)
        
        return report
```

---

## 对比示例

### QA 报告对比

| 机器风格 | Human 风格 |
|---------|-----------|
| `Execution completed successfully` | `今晚的检查一切正常` |
| `No errors detected` | `没啥问题，代码挺健康` |
| `Coverage: 95.2%` | `测试覆盖率：95.2% (达标)` |
| `Next check in 20 minutes` | `下次检查：23:20` |

### Manager 报告对比

| 机器风格 | Human 风格 |
|---------|-----------|
| `Queue status: empty` | `好消息！问题队列清空了 🎉` |
| `Pending: 0, Processing: 0` | `待处理：0 个，处理中：0 个` |
| `System operating normally` | `系统运行平稳，可以安心 😌` |

### 健康检查对比

| 机器风格 | Human 风格 |
|---------|-----------|
| `Health check completed` | `💓 Agent 健康检查` |
| `All agents healthy` | `所有 Agent 都活着，状态不错！💪` |
| `Health rate: 100%` | `健康率：100%` |
| `Continue monitoring` | `系统很健康，继续保持 👍` |

---

## 最佳实践

### ✅ 推荐

1. **用口语** - "没啥问题" 而不是 "未发现问题"
2. **有情感** - "好消息！" 而不是 "状态：成功"
3. **用 Emoji** - 适当使用增强可读性
4. **说人话** - "可以安心" 而不是 "无需进一步操作"
5. **有关心** - "辛苦了" 而不是 "任务完成"

### ❌ 避免

1. ~~机器术语~~ - "执行成功"、"无错误报告"
2. ~~被动语态~~ - "被发现"、"被处理"
3. ~~冷冰冰~~ - "无"、"零"、"空"
4. ~~太长~~ - 超过 10 行的段落
5. ~~太正式~~ - "尊敬的用戶"、"谨此通知"

---

## 测试

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 测试报告生成
python3 human_report.py

# 查看示例输出
cat HUMAN_REPORT_GUIDE.md
```

---

## 总结

**Human 风格报告核心价值**:
1. ✅ **易读** - 一眼看懂
2. ✅ **友好** - 像朋友聊天
3. ✅ **有温度** - 不是冷机器
4. ✅ **高效** - 重点突出
5. ✅ **愉快** - 读起来开心

**目标**: 让每次查看报告都成为一种享受，而不是负担！😊
