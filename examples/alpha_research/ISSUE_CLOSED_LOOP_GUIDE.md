# 问题管理闭环流程指南

## 完整闭环流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    问题管理闭环流程                              │
└─────────────────────────────────────────────────────────────────┘

1️⃣ 发现问题 → 2️⃣ 上报 Issue → 3️⃣ Manager 分析 → 4️⃣ 指派工程师
       ↑                                                        │
       │                                                        ↓
       │                                              5️⃣ 工程师修复
       │                                                        │
       │                                                        ↓
       │                                              6️⃣ QA 检查验证
       │                                                        │
       │                                                        ↓
       └──────────────────────────────────────────── 7️⃣ 重新执行任务
```

---

## 详细步骤说明

### 1️⃣ 发现问题

**触发源**:
- Agent 执行失败
- 健康检查异常
- 数据质量检查失败
- 日志分析发现错误
- 监控告警

**示例**:
```python
# data_agent.py 执行失败
try:
    download_data()
except Exception as e:
    # 触发问题上报
    report_issue(...)
```

---

### 2️⃣ 上报 Issue

**上报方式**:

```python
from issue_queue import IssueQueue, Issue

# 创建问题
queue = IssueQueue()
issue = queue.create_issue(
    agent="data-agent",
    severity="P1",              # P0/P1/P2
    error_type="data_download",
    error_message="下载失败：网络超时"
)

# 写入队列
issue_id = queue.write_issue(issue)
print(f"问题已上报：{issue_id}")
```

**问题状态**:
- `pending` - 待处理
- `processing` - 处理中
- `resolved` - 已解决
- `archived` - 已归档

**严重级别**:
- **P0** - 严重（立即处理）
- **P1** - 高优先级（1 小时内）
- **P2** - 普通（24 小时内）

---

### 3️⃣ Manager 分析

**执行者**: `QuantManager` (manager_interface.py)

**触发时间**: 每 5 分钟检查一次（cron 任务）

**分析流程**:

```python
from manager_interface import QuantManager

manager = QuantManager()

# 获取待处理问题
issues = manager.issue_queue.get_pending_issues()

for issue in issues:
    # 1. 分析错误类型
    task_type = manager.analyze_error(issue)
    
    # 2. 选择处理 Agent
    agent = manager.select_agent(task_type)
    
    # 3. 创建任务
    task = manager.handle_error_report(issue)
```

**Agent 映射**:
```python
agent_mapping = {
    'qa': 'qa',                    # QA 问题 → QA Agent
    'trading': 'trading-agent',    # 交易问题 → 交易 Agent
    'risk': 'cro',                 # 风控问题 → 首席风险官
    'data': 'data-agent',          # 数据问题 → 数据 Agent
    'engineering': 'delta',        # 工程问题 → Delta 工程师
    'general': 'delta',            # 通用问题 → Delta 工程师
}
```

---

### 4️⃣ 指派工程师

**Manager 决策**:

```python
# manager_interface.py

def handle_error_report(self, issue: Issue):
    """处理错误上报"""
    
    # 分析错误类型
    task_type = self.analyze_error(issue)
    
    # 选择处理 Agent
    agent = self.agent_mapping.get(task_type, 'delta')
    
    # 创建任务
    task = {
        'issue_id': issue.id,
        'agent': agent,
        'type': task_type,
        'severity': issue.severity,
        'status': 'assigned',
        'assigned_at': datetime.now().isoformat(),
    }
    
    # 更新问题状态
    self.issue_queue.update_status(
        issue.id, 
        'processing', 
        assigned_to=agent
    )
    
    # 根据严重级别处理
    if issue.severity == 'P0':
        self.handle_p0(task, issue)
    elif issue.severity == 'P1':
        self.handle_p1(task, issue)
    else:
        self.handle_p2(task, issue)
    
    return task
```

**严重级别处理策略**:

| 级别 | 响应时间 | 通知方式 | 升级策略 |
|------|---------|---------|---------|
| **P0** | 立即 | Slack + 日志 | 5 分钟未处理升级 |
| **P1** | 1 小时 | 日志 | 1 小时未处理升级 |
| **P2** | 24 小时 | 仅记录 | 每日汇总 |

---

### 5️⃣ 工程师修复

**执行者**: 被指派的 Agent

**修复流程**:

```python
# delta_consumer.py (Delta 工程师)

from issue_queue import IssueQueue

class DeltaConsumer:
    def process_issue(self, issue_id: str):
        """处理问题"""
        queue = IssueQueue()
        issue = queue.read_issue(issue_id)
        
        try:
            # 1. 分析问题
            root_cause = self.analyze_root_cause(issue)
            
            # 2. 制定修复方案
            fix_plan = self.create_fix_plan(root_cause)
            
            # 3. 执行修复
            result = self.execute_fix(fix_plan)
            
            # 4. 验证修复
            if self.verify_fix(result):
                # 修复成功
                queue.update_status(
                    issue_id,
                    'resolved',
                    resolution=str(result),
                    resolved_at=datetime.now().isoformat()
                )
                return True
            else:
                raise Exception("修复验证失败")
        
        except Exception as e:
            # 修复失败，重新上报
            queue.update_status(issue_id, 'pending')
            raise
```

**修复类型**:
- 🐛 **Bug 修复** - 代码问题
- 📊 **数据修复** - 数据质量问题
- ⚙️ **配置修复** - 配置问题
- 🔄 **重试执行** - 临时故障

---

### 6️⃣ QA 检查验证

**执行者**: QA Agent

**检查频率**: 每 20 分钟（QA 变更门禁）

**检查流程**:

```python
# qa_change_gate.py

class QAChangeGate:
    def verify_fix(self, issue_id: str):
        """验证修复"""
        queue = IssueQueue()
        issue = queue.read_issue(issue_id)
        
        # 1. 检查修复代码
        code_quality = self.check_code_quality()
        
        # 2. 运行测试用例
        test_result = self.run_tests()
        
        # 3. 验证功能
        functional_test = self.verify_functionality()
        
        # 4. 生成验证报告
        if all([code_quality, test_result, functional_test]):
            return {
                'status': 'passed',
                'report': '所有检查通过'
            }
        else:
            return {
                'status': 'failed',
                'report': '检查失败',
                'issues': [...]
            }
```

**QA 检查项**:
- ✅ 代码质量检查
- ✅ 单元测试通过率
- ✅ 集成测试通过率
- ✅ 功能验证
- ✅ 回归测试

---

### 7️⃣ 重新执行任务

**触发条件**: QA 验证通过

**执行流程**:

```python
# manager_interface.py

def retry_task(self, issue_id: str):
    """重新执行任务"""
    queue = IssueQueue()
    issue = queue.read_issue(issue_id)
    
    # 获取原始任务信息
    original_task = self.get_original_task(issue)
    
    # 重新执行
    try:
        result = self.execute_task(original_task)
        
        # 执行成功
        queue.update_status(
            issue_id,
            'resolved',
            resolution=f"重新执行成功：{result}"
        )
        
        return True
    
    except Exception as e:
        # 仍然失败，继续上报
        queue.update_status(issue_id, 'pending')
        return False
```

**成功标准**:
- ✅ 任务执行完成
- ✅ 无错误产生
- ✅ 输出符合预期
- ✅ 数据一致性验证通过

---

## 监控与追踪

### 查看待处理问题

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 查看待处理问题
python3 -c "
from issue_queue import IssueQueue
queue = IssueQueue()
issues = queue.get_pending_issues()
print(f'待处理问题：{len(issues)}')
for issue in issues:
    print(f'  - {issue.id}: {issue.error_message[:50]}')
"
```

### 查看处理中问题

```bash
ls -la issues/processing/
```

### 查看已解决问题

```bash
ls -la issues/resolved/
```

---

## 定时任务配置

| 任务 | 频率 | 说明 |
|------|------|------|
| **Manager 问题队列监控** | 每 40 分钟 | 检查队列状态 |
| **Manager 问题自动处理** | 每 50 分钟 | 自动处理问题 |
| **QA 变更门禁检查** | 每 20 分钟 | 质量检查 |
| **QA-Architect 迭代闭环** | 工作日 14:00 | 迭代优化 |
| **QA 测试用例生成** | 工作日 12:00 | 生成测试 |

---

## 实际案例

### 案例 1: 数据下载失败

```
1️⃣ 发现问题：data_agent.py 下载失败
   ❌ 错误：网络超时

2️⃣ 上报 Issue：
   issue_id: issue_20260315_225000_abc123
   severity: P1
   type: data_download

3️⃣ Manager 分析：
   task_type: data
   assigned_to: data-agent

4️⃣ 指派工程师：
   data-agent 接收任务

5️⃣ 工程师修复：
   - 检查网络连接
   - 重试下载
   - 切换备用数据源
   ✅ 修复成功

6️⃣ QA 检查：
   - 数据完整性验证 ✅
   - 数据质量检查 ✅

7️⃣ 重新执行：
   - 重新执行数据下载任务
   ✅ 执行成功
   
🎉 问题关闭：issue_20260315_225000_abc123
```

---

## 关键文件

| 文件 | 功能 |
|------|------|
| `issue_queue.py` | 问题队列管理 |
| `manager_interface.py` | Manager 调度中心 |
| `delta_consumer.py` | Delta 工程师（处理问题） |
| `qa_change_gate.py` | QA 质量检查 |
| `agent_health_check.py` | Agent 健康检查（发现问题） |
| `log_analyzer_agent.py` | 日志分析（发现问题） |

---

## 状态流转图

```
┌─────────┐
│ pending │ 待处理
└────┬────┘
     │ Manager 指派
     ↓
┌─────────────┐
│ processing  │ 处理中
└─────┬───────┘
      │ 工程师修复
      ↓
┌─────────┐    QA 失败    ┌─────────┐
│resolved │ ←──────────── │ pending │
│ 已解决   │              │ 重新处理 │
└────┬────┘              └─────────┘
     │
     │ 定期归档
     ↓
┌─────────┐
│archived │ 已归档
└─────────┘
```

---

## 最佳实践

### ✅ 推荐

1. **及时上报** - 发现问题立即上报
2. **明确级别** - 正确设置 P0/P1/P2
3. **详细记录** - 包含完整错误信息
4. **跟踪进度** - 定期检查处理状态
5. **归档总结** - 解决问题后总结经验

### ❌ 避免

1. ~~隐瞒错误~~ - 不上报问题
2. ~~级别混乱~~ - P0 当 P2 处理
3. ~~信息不全~~ - 缺少关键上下文
4. ~~无人跟进~~ - 指派后不跟踪
5. ~~重复问题~~ - 不总结导致重复发生

---

## 监控命令

```bash
# 查看所有问题统计
echo "待处理：$(ls issues/pending/*.json 2>/dev/null | wc -l)"
echo "处理中：$(ls issues/processing/*.json 2>/dev/null | wc -l)"
echo "已解决：$(ls issues/resolved/*.json 2>/dev/null | wc -l)"

# 查看最新问题
ls -lt issues/pending/ | head -5

# 查看超时未处理问题
find issues/pending/ -mtime +1 -name "*.json"
```

---

## 总结

**闭环流程核心价值**:
1. ✅ **自动化** - 问题发现→上报→处理→验证全自动
2. ✅ **可追溯** - 每个问题都有完整记录
3. ✅ **责任明确** - 每个问题都有明确负责人
4. ✅ **质量保证** - QA 验证确保修复质量
5. ✅ **持续改进** - 经验总结避免重复问题

**当前状态**:
- ✅ 问题队列系统运行正常
- ✅ Manager 每 5 分钟检查一次
- ✅ QA 每 20 分钟检查一次
- ✅ 闭环流程已建立并运行
