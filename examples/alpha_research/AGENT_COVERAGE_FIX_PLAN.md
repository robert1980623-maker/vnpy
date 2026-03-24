# Agent 缺失与代码覆盖率问题修复方案

**分析时间**: 2026-03-20 08:30  
**分析师**: Subagent  
**任务等级**: P0 (关键系统问题)

---

## 📊 问题摘要

### P0 关键 Agent 缺失问题

| Agent | 文件状态 | Cron 配置 | 执行状态 | 问题 |
|-------|---------|----------|---------|------|
| 虚拟账户交易 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |
| 数据下载 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |
| 每日选股 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |
| 每日复盘 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |
| 止盈止损执行 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |
| 首席风险官 | ✅ 存在 | ✅ 已配置 | ⚠️ PATH 错误 | openclaw command not found |

**根本原因**: Cron 环境中 PATH 不包含 `/usr/local/bin`

### P1 代码覆盖率问题

| 项目 | 目标 | 当前 | 状态 |
|------|------|------|------|
| 覆盖率阈值 | 85% | 93.97% (2026-03-15) | ✅ 已达成 |
| 配置文件 | - | ⚠️ 排除过多文件 | 需优化 |
| slack_digest.py | - | ❌ 语法错误 | ✅ 已修复 |

---

## 🔧 修复方案

### 方案 1: 修复 Cron PATH 问题 (P0)

**问题**: Cron 任务使用 `openclaw` 命令但找不到

**解决**:
1. 在 cron 表达式中使用绝对路径 `/usr/local/bin/openclaw`
2. 或者在 cron 脚本中显式设置 PATH

**修复后的 Cron 配置**:
```bash
# 数据下载 (17:00)
0 17 * * * cd /Users/rowang/.openclaw && /usr/local/bin/openclaw cron run "数据下载" >> /Users/rowang/.openclaw/logs/cron_data_download.log 2>&1

# 每日选股 (09:00, 周一 - 五)
0 9 * * 1-5 cd /Users/rowang/.openclaw && /usr/local/bin/openclaw cron run "每日选股" >> /Users/rowang/.openclaw/logs/cron_stock_selection.log 2>&1

# 每日复盘 (20:00, 周一 - 五)
0 20 * * 1-5 cd /Users/rowang/.openclaw && /usr/local/bin/openclaw cron run "每日复盘" >> /Users/rowang/.openclaw/logs/cron_daily_review.log 2>&1
```

### 方案 2: 优化覆盖率配置 (P1)

**问题**: `.coveragerc` 排除了太多关键文件

**解决**:
1. 移除对关键业务文件的排除 (virtual_account.py, daily_*.py 等)
2. 仅排除测试辅助文件和临时文件
3. 重新运行覆盖率测试

**更新后的 .coveragerc 排除列表**:
```ini
omit = 
    venv/*
    tests/*
    test_*.py
    data/*
    accounts/*
    issues/*
    reports/*
    change_logs/*
    htmlcov/*
    *.bak
    *_old.py
    *_fixed.py
    *_demo.py
    logger.py
```

---

## ✅ 已完成修复

1. **slack_digest.py 语法错误** (Line 166)
   - 错误：`[t in trades if ...]` 
   - 修复：`[t for t in trades if ...]`
   - 状态：✅ 已修复

---

## 📋 待执行任务

### P0 任务 (立即执行)

1. [ ] 更新所有 cron 任务使用绝对路径 `/usr/local/bin/openclaw`
2. [ ] 验证 cron 任务执行日志
3. [ ] 确认所有关键 Agent 正常运行

### P1 任务 (今日完成)

1. [ ] 更新 `.coveragerc` 配置文件
2. [ ] 清除旧覆盖率数据
3. [ ] 重新运行覆盖率测试
4. [ ] 生成新的覆盖率报告
5. [ ] 验证覆盖率 ≥85%

---

## 📈 预期结果

### P0 修复后
- ✅ 所有 6 个关键 Agent cron 任务正常执行
- ✅ 日志中无 "command not found" 错误
- ✅ 数据流正常：数据下载 → 选股 → 交易 → 复盘

### P1 修复后
- ✅ 代码覆盖率准确反映实际测试覆盖情况
- ✅ 关键业务文件 (virtual_account.py, daily_*.py) 纳入覆盖率统计
- ✅ 覆盖率 ≥85% 持续保持

---

**下一步**: 执行 P0 修复 → 验证 → 执行 P1 修复 → 验证
