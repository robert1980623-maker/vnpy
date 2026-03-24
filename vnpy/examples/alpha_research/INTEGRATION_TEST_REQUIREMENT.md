# 集成测试强制要求

## 📋 核心原则

**QA 测试中永远包括集成测试** - 这是强制要求，不可跳过。

## 🔗 集成测试套件

每个 QA 流程必须包含以下 4 个集成测试：

### INT-001: 数据管道完整性测试
- **脚本**: `tests/integration/test_data_pipeline.py`
- **目的**: 测试数据下载、处理、存储的完整流程
- **测试项**:
  - 数据目录存在性
  - 数据文件非空验证
  - JSON 格式有效性
  - 选股脚本存在
  - 选股报告生成
  - 虚拟账户文件存在
  - 账户格式验证
  - 账户余额为正
  - 报告目录存在
  - 每日报告生成

### INT-002: 交易流程完整性测试
- **脚本**: `tests/integration/test_trading_flow.py`
- **目的**: 测试选股→交易→复盘的完整流程
- **测试项**:
  - 选股文件存在
  - 交易计划存在
  - 账户更新验证
  - 合规检查脚本
  - 合规报告生成
  - 绩效归因脚本
  - 绩效报告生成
  - QA 脚本存在
  - QA 报告生成
  - 审核历史存在

### INT-003: Agent 系统完整性测试
- **脚本**: `tests/integration/test_agent_system.py`
- **目的**: 测试各个 Agent 的完整功能和数据流
- **测试项**:
  - Manager 接口存在
  - 问题队列存在
  - QA 测试生成器存在
  - 架构师审核器存在
  - 问题目录结构
  - 审核历史目录
  - Cron 任务配置
  - Agent 模型配置
  - Manager 加载测试
  - Manager 状态获取

### INT-004: QA-Architect 闭环测试
- **脚本**: `qa_architect_loop.py`
- **目的**: 测试 QA-Architect 迭代闭环功能
- **测试项**:
  - QA 生成测试用例
  - 架构师审核执行
  - 审核报告生成
  - 测试计划状态更新
  - 自动化测试执行
  - 最终报告生成
  - 迭代状态验证

## 🏗️ 架构师审核规则

**集成测试必须全部通过**，否则整体审核不通过。

```python
# 架构师审核逻辑
integration_suite_review = get_integration_suite()
if not integration_suite_review.passed:
    overall_status = 'rejected'  # 集成测试失败，直接拒绝
else:
    overall_status = 'approved' if all_tests_passed else 'rejected'
```

## 📊 测试统计

当前集成测试总数：**31 个测试用例**

| 测试文件 | 测试用例数 | 状态 |
|----------|-----------|------|
| test_data_pipeline.py | 10 | ✅ |
| test_trading_flow.py | 11 | ✅ |
| test_agent_system.py | 10 | ✅ |
| **总计** | **31** | ✅ |

## 🚀 执行方式

### 手动执行
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate

# 执行所有集成测试
python3 -m pytest tests/integration/ -v

# 执行 QA 闭环测试
python3 qa_architect_loop.py
```

### 自动执行 (Cron)
- **QA 测试用例生成**: 每天 12:00
- **QA-Architect 迭代**: 每天 14:00

## 📁 相关文件

- `qa_test_generator.py` - QA 测试生成器（包含集成测试套件）
- `architect_test_reviewer.py` - 架构师审核器（强制集成测试通过）
- `qa_architect_loop.py` - QA-Architect 迭代协调器
- `tests/integration/` - 集成测试目录

## ⚠️ 重要提醒

1. **不可跳过**: 集成测试是 QA 流程的必要组成部分
2. **优先执行**: 集成测试在其他测试之前执行
3. **一票否决**: 集成测试失败 = 整体审核失败
4. **持续维护**: 随系统演进更新集成测试用例

---

**最后更新**: 2026-03-15  
**维护者**: QA Team
