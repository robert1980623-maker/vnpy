# QA 变更闭环工作流

## 📋 核心原则

**每次增加、修改、删除功能或任何代码改动都需要 QA 闭环验证**

这是强制要求，不可绕过。

---

## 🚪 QA 门禁系统

### 工作流程

```
代码变更 → 检测变更 → 集成测试 → QA 闭环 → 质量报告 → 允许/禁止提交
              ↓           ↓          ↓          ↓           ↓
           5 分钟      31 个用例   qa_architect   生成报告   ✅/❌
```

### 组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **门禁系统** | `qa_change_gate.py` | 检测变更、执行测试、生成报告 |
| **Git Hook** | `.git/hooks/pre-commit` | 提交前强制检查 |
| **定时检查** | Cron (每 5 分钟) | 持续监控代码变更 |
| **集成测试** | `tests/integration/` | 31 个自动化测试用例 |
| **QA 闭环** | `qa_architect_loop.py` | QA-Architect 迭代验证 |

---

## 📝 使用方式

### 方式 1: Git 提交（自动触发）

```bash
# 正常提交代码
git add .
git commit -m "feat: 添加新功能"

# Pre-commit hook 自动执行 QA 门禁
# ✅ 通过 → 允许提交
# ❌ 失败 → 阻止提交
```

### 方式 2: 手动触发

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate

# 运行 QA 门禁
python3 qa_change_gate.py
```

### 方式 3: 定时检查（自动）

Cron 任务每 5 分钟自动检查代码变更并触发 QA 验证。

---

## 📊 质量检查项

### 1. 变更检测
- ✅ 新增文件检测
- ✅ 修改文件检测
- ✅ 删除文件检测
- ✅ 文件哈希比对

### 2. 集成测试 (31 个用例)
- ✅ 数据管道测试 (10 个)
- ✅ 交易流程测试 (11 个)
- ✅ Agent 系统测试 (10 个)

### 3. QA 闭环测试
- ✅ QA 测试用例生成
- ✅ 架构师审核
- ✅ 测试计划状态更新
- ✅ 自动化测试执行
- ✅ 最终报告生成

---

## 📁 输出文件

### 质量报告
位置：`change_logs/quality_report_YYYYMMDD_HHMMSS.json`

```json
{
  "report_id": "QA-20260315_022900",
  "generated_at": "2026-03-15T02:29:00",
  "changes": {
    "total": 3,
    "added": 1,
    "modified": 2,
    "deleted": 0
  },
  "qa_results": {
    "qa_loop_passed": true,
    "integration_tests_passed": true,
    "overall_passed": true
  },
  "verdict": "✅ APPROVED",
  "next_action": "允许提交"
}
```

### QA 状态
位置：`.qa_state.json`

记录所有文件的哈希值，用于检测变更。

---

## ⚠️ 失败处理

### 如果 QA 门禁失败

1. **查看质量报告**
   ```bash
   ls -lt change_logs/ | head -1
   cat change_logs/quality_report_YYYYMMDD_HHMMSS.json
   ```

2. **查看失败详情**
   - 集成测试失败 → 查看 pytest 输出
   - QA 闭环失败 → 查看 qa_architect_loop 输出

3. **修复问题**
   - 修复代码 bug
   - 更新测试用例
   - 重新运行 QA 门禁

4. **重新提交**
   ```bash
   git commit -m "fix: 修复 QA 门禁发现的问题"
   ```

---

## 🎯 强制规则

### 必须 QA 验证的场景

| 场景 | QA 要求 |
|------|--------|
| **新增功能** | ✅ 必须 QA 闭环 |
| **修改功能** | ✅ 必须 QA 闭环 |
| **删除功能** | ✅ 必须 QA 闭环 |
| **重构代码** | ✅ 必须 QA 闭环 |
| **修复 bug** | ✅ 必须 QA 闭环 |
| **更新配置** | ✅ 必须 QA 闭环 |
| **修改测试** | ✅ 必须 QA 闭环 |
| **文档更新** | ⚠️ 建议 QA 验证 |

### 禁止行为

❌ **绕过 QA 门禁**
```bash
# 禁止使用 --no-verify 跳过 pre-commit
git commit --no-verify -m "跳过 QA"  # ❌ 禁止！
```

❌ **禁用 Cron 检查**
```bash
# 禁止禁用 QA 变更检查任务
# 会失去持续监控能力
```

---

## 📈 质量指标

### 报告内容

每个质量报告包含：

1. **变更统计**
   - 新增文件数
   - 修改文件数
   - 删除文件数

2. **测试结果**
   - 集成测试通过率
   - QA 闭环通过率
   - 总体通过状态

3. **Verdict**
   - ✅ APPROVED - 允许提交
   - ❌ REJECTED - 禁止提交

---

## 🔧 配置选项

### 调整检查频率

编辑 `~/.openclaw/cron/jobs.json`:

```json
{
  "name": "QA 变更门禁检查",
  "schedule": {
    "expr": "*/5 * * * *"  // 每 5 分钟
    // 改为 "*/10 * * * *" = 每 10 分钟
    // 改为 "*/15 * * * *" = 每 15 分钟
  }
}
```

### 调整超时时间

编辑 `qa_change_gate.py`:

```python
# 集成测试超时 (默认 10 分钟)
timeout=600

# QA 闭环超时 (默认 30 分钟)
timeout=1800
```

---

## 📞 故障排查

### 常见问题

**Q: Git 提交时 hook 不执行？**
```bash
# 检查 hook 是否有执行权限
ls -la .git/hooks/pre-commit
# 如果没有权限
chmod +x .git/hooks/pre-commit
```

**Q: QA 门禁一直失败？**
```bash
# 查看详细输出
python3 qa_change_gate.py 2>&1 | tee qa_debug.log
# 查看日志
tail -100 qa_debug.log
```

**Q: 想查看历史质量报告？**
```bash
# 列出所有报告
ls -lt change_logs/
# 查看最新报告
cat change_logs/$(ls -t change_logs/ | head -1)
```

---

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `qa_change_gate.py` | QA 门禁主程序 |
| `qa_architect_loop.py` | QA-Architect 迭代器 |
| `architect_test_reviewer.py` | 架构师审核器 |
| `qa_test_generator.py` | QA 测试生成器 |
| `tests/integration/` | 集成测试目录 |
| `.git/hooks/pre-commit` | Git pre-commit hook |
| `change_logs/` | 质量报告目录 |
| `.qa_state.json` | QA 状态文件 |

---

## 🎓 最佳实践

1. **小步提交** - 每次提交少量变更，便于 QA 验证
2. **本地先测** - 提交前本地运行 QA 门禁
3. **查看报告** - 每次提交后查看质量报告
4. **及时修复** - QA 失败立即修复，不累积问题
5. **保持绿色** - 确保主分支始终通过 QA

---

**最后更新**: 2026-03-15  
**维护者**: QA Team  
**状态**: ✅ 已启用
