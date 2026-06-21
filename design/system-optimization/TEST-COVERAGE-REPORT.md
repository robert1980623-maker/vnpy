# CLI 模块测试覆盖率提升报告

> **日期**: 2026-06-21
> **测试框架**: pytest + unittest.mock + Click CliRunner
> **Python 版本**: 3.14.3

---

## 1. 覆盖率对比

### 目标文件覆盖率

| 文件 | 修改前 | 修改后 | 目标 | 状态 |
|------|--------|--------|------|------|
| `cli/utils/wrapper.py` | 20.55% | **86.30%** | 80%+ | ✅ |
| `cli/__main__.py` | 0.00% | **100.00%** | 100% | ✅ |
| `cli/main.py` | 66.00% | **94.34%** | 85%+ | ✅ |
| `cli/commands/cron.py` | 67.50% | **91.50%** | 85%+ | ✅ |
| `cli/commands/download.py` | 67.82% | **93.10%** | 85%+ | ✅ |

### CLI 模块整体覆盖率

| 指标 | 修改前 | 修改后 |
|------|--------|--------|
| CLI 总覆盖率 | 75.25% | **89.97%** |
| 测试总数 | 110 passed, 1 skipped | **271 passed, 1 skipped** |
| 新增测试 | - | **+36 个** |

---

## 2. 新增测试文件

### `tests/cli/test_wrapper.py` (新建)

测试 `cli/utils/wrapper.py` 中的 legacy script 执行桥接模块。

#### TestRunLegacy (8 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_run_legacy_success` | subprocess.run 成功返回 |
| `test_run_legacy_failure` | 非零退出码 → DependencyError |
| `test_run_legacy_check_false` | check=False 时不抛异常 |
| `test_run_legacy_not_found` | 脚本文件不存在 |
| `test_run_legacy_with_args` | 参数正确传递到命令列表 |
| `test_run_legacy_with_env` | 环境变量合并 + TRACEPARENT 注入 |
| `test_run_legacy_file_not_found` | subprocess FileNotFoundError |
| `test_run_legacy_unexpected_error` | subprocess 通用异常 |

#### TestRunLegacyImport (5 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_run_legacy_import_success` | runpy.run_path 成功 |
| `test_run_legacy_import_not_found` | 脚本不存在 |
| `test_run_legacy_import_system_exit_error` | SystemExit(非零) → DependencyError |
| `test_run_legacy_import_system_exit_zero` | SystemExit(0) → 返回空字典 |
| `test_run_legacy_import_exception` | runpy 通用异常 |

#### TestLegacyCommand (3 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_legacy_command_creates_click_command` | 装饰器生成正确的 Click command |
| `test_legacy_command_invocation` | 通过 CliRunner 调用, 验证 run_legacy 被调用 |
| `test_legacy_command_failure` | DependencyError → ctx.fail() → 非零退出 |

---

### `tests/cli/test_commands.py` (扩展)

在已有文件中新增 6 个测试类、20 个测试用例。

#### TestMainEntry (1 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_main_entry_callable` | `python -m cli` 入口点验证 (runpy) |

#### TestMainFunction (4 个测试)

| 测试用例 | 覆盖场景 | 退出码 |
|----------|----------|--------|
| `test_main_usage_error` | click.UsageError 处理 | 2 |
| `test_main_click_exception` | click.ClickException 处理 | 1 |
| `test_main_keyboard_interrupt` | KeyboardInterrupt (Ctrl+C) | 130 |
| `test_main_unexpected_error` | 通用 Exception → handle_error | 1 |

#### TestCronEnableDisable (3 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_enable_success` | 启用禁用任务 → YAML 更新 |
| `test_disable_success` | 禁用启用任务 → YAML 更新 |
| `test_enable_not_found` | 不存在的任务 → 非零退出 |

#### TestCronInstallExtended (3 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_install_success` | openclaw 安装成功 → ✅ |
| `test_install_subprocess_failure` | openclaw 返回错误 → ❌ |
| `test_install_openclaw_not_found` | openclaw 命令不存在 |

#### TestCronRunExtended (3 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_run_success` | 任务执行成功 → ✅ |
| `test_run_failure` | 任务执行失败 (非零退出码) |
| `test_run_timeout` | 执行超时 → TimeoutExpired |

#### TestDownloadExecution (6 个测试)

| 测试用例 | 覆盖场景 |
|----------|----------|
| `test_akshare_execution` | akshare 下载 → run_legacy 调用验证 |
| `test_tushare_execution` | tushare 下载 → run_legacy 调用验证 |
| `test_policy_execution` | policy 下载 → run_legacy 调用验证 |
| `test_geopolitics_execution` | geopolitics 下载 → run_legacy 调用验证 |
| `test_news_execution` | news 下载 → run_legacy + 参数验证 |
| `test_all_execution` | all 命令 → 遍历所有子命令 |

---

## 3. 技术方案

### Mock 策略

| Mock 目标 | 用途 |
|-----------|------|
| `cli.utils.wrapper.subprocess.run` | 避免实际 subprocess 调用 |
| `cli.utils.wrapper.runpy.run_path` | 避免实际脚本执行 |
| `cli.utils.wrapper.LEGACY_SCRIPTS_DIR` | 重定向到 tmp_path |
| `cli.utils.wrapper.get_current_trace_id` | 确定性 trace ID |
| `cli.utils.wrapper.run_legacy` | download 命令的延迟导入 |
| `cli.commands.cron.subprocess.run` | cron install/run 命令 |
| `cli.main.cli` | main() 错误路径测试 |

### 关键设计决策

1. **延迟导入的 mock**: `download.py` 中 `run_legacy` 在函数体内延迟导入，需要 mock 源模块 `cli.utils.wrapper.run_legacy` 而非目标模块属性。
2. **__main__.py 测试**: 使用 `runpy.run_module` 执行模块代码，patch `cli.main.cli` 防止 `sys.exit()`。
3. **YAML 文件验证**: enable/disable 测试通过 `tmp_path` 创建临时 YAML，执行后读取验证文件内容变更。
4. **Click CliRunner**: 所有 CLI 命令测试使用 `CliRunner.invoke()`，捕获输出和退出码。

---

## 4. 运行结果

```
$ python3 -m pytest tests/ -v
=========================== 271 passed, 1 skipped in 1.83s ===========================
```

```
$ python3 -m pytest tests/cli/ --cov=cli --cov-report=term-missing
TOTAL    917    92   89.97%
125 passed, 2 warnings in 0.66s
```

### 按文件覆盖率明细

```
Name                       Stmts   Miss   Cover   Missing
---------------------------------------------------------
cli/__init__.py                1      1   0.00%   2
cli/__main__.py                2      0 100.00%
cli/commands/__init__.py       0      0 100.00%
cli/commands/cron.py         200     17  91.50%
cli/commands/download.py      87      6  93.10%
cli/commands/health.py        96     20  79.17%
cli/commands/report.py        59      9  84.75%
cli/commands/trade.py         63     11  82.54%
cli/main.py                   53      3  94.34%
cli/utils/__init__.py          0      0 100.00%
cli/utils/config.py           73      9  87.67%
cli/utils/cron_schema.py      90      0 100.00%
cli/utils/errors.py           48      5  89.58%
cli/utils/logging.py          72      1  98.61%
cli/utils/wrapper.py          73     10  86.30%
---------------------------------------------------------
TOTAL                        917     92  89.97%
```

---

## 5. 后续建议

1. **`cli/commands/health.py`** (79.17%): 补充实际健康检查执行路径测试
2. **`cli/commands/report.py`** (84.75%): 补充实际报告生成路径测试
3. **`cli/commands/trade.py`** (82.54%): 补充实际交易执行路径测试
4. **`cli/utils/config.py`** (87.67%): 补充嵌套配置合并、环境变量解析测试

目标: CLI 模块整体覆盖率达到 95%+
