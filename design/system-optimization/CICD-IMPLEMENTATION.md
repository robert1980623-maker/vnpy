# VNPY CI/CD 实施报告

> **文档版本**: 1.0.0  
> **实施日期**: 2026-06-21  
> **实施状态**: ✅ 已完成阶段 1  
> **依据设计**: `CICD-ARCHITECTURE.md` v1.0.0

---

## 📋 实施摘要

已按设计文档完成 CI/CD 流水线的阶段 1 实施，包括：

- ✅ 创建 `.github/workflows/ci.yml`（5 个 jobs）
- ✅ 更新 `pyproject.toml`（补充依赖 + 工具配置）
- ✅ 创建 `.env.example` 环境变量模板
- ✅ 验证 YAML / TOML 配置合法性

---

## 1. 变更清单

### 1.1 新增文件

| 文件 | 用途 | 行数 |
|---|---|---|
| `.github/workflows/ci.yml` | GitHub Actions CI 主流程 | ~170 |
| `.env.example` | 环境变量模板（secrets 安全） | 17 |
| `design/system-optimization/CICD-IMPLEMENTATION.md` | 本文档 | - |

### 1.2 修改文件

| 文件 | 变更内容 |
|---|---|
| `pyproject.toml` | 补充 `pyyaml`/`pydantic` 依赖、`[test]`/`[dev]` extras、pytest/coverage/ruff/mypy 工具配置 |

### 1.3 未修改文件

| 文件 | 理由 |
|---|---|
| `.gitignore` | `.env` 已在 gitignore 中，无需修改 |
| `.coveragerc` | 保留作为本地开发 fallback；CI 优先使用 `pyproject.toml` 的 `[tool.coverage.*]` 配置 |

---

## 2. Workflow 结构

### 2.1 Job 拓扑

```
┌────────────┐
│   lint     │  ruff check + ruff format --check (~10s)
└─────┬──────┘
      │
      ├──▶ ┌────────────┐
      │    │ typecheck  │  mypy (continue-on-error: true)
      │    └────────────┘
      │
      ├──▶ ┌────────────────┐
      │    │ test (matrix)  │  Python 3.11 / 3.12 / 3.13 / 3.14
      │    └───────┬────────┘
      │            │
      │            ├──▶ ┌────────────┐
      │            │    │   build    │  sdist + wheel → artifact
      │            │    └────────────┘
      │            │
      │            └──▶ ┌────────────────┐
      │                 │  integration   │  可选（push to main / manual）
      │                 └────────────────┘
```

### 2.2 触发条件

| 事件 | 触发 | 说明 |
|---|---|---|
| `push` to main/master | ✅ | `paths-ignore` 过滤 docs/markdown |
| `pull_request` to main/master | ✅ | 自动取消前一次运行（concurrency） |
| `workflow_dispatch` | ✅ | 支持手动触发 + `run_integration` 可选参数 |

### 2.3 缓存策略

- `actions/setup-python@v5` 内置 `cache: 'pip'`
- 缓存键基于 `pyproject.toml` hash
- lint 步骤不缓存（单步安装 ruff 已足够快）

---

## 3. pyproject.toml 变更详情

### 3.1 依赖补充

```diff
 dependencies = [
     "click>=8.0",
+    "pyyaml>=6.0",     # cli/utils/config.py 使用
+    "pydantic>=2.0",   # cli/utils/cron_schema.py 使用
 ]

+[project.optional-dependencies]
+test = [
+    "pytest>=7.0",
+    "pytest-cov>=4.0",
+    "pytest-mock>=3.10",
+    "coverage>=7.0",
+]
+dev = [
+    "ruff>=0.6.0",
+    "mypy>=1.10",
+    "types-PyYAML",
+    "types-click",
+    "build>=1.0",
+]
```

### 3.2 工具配置

| 工具 | 配置项 | 关键设置 |
|---|---|---|
| pytest | `testpaths` | `tests/unit`, `tests/cli`, `tests/integration` |
| coverage | `source` | `alpha`, `cli`, `core`, `vnpy` |
| ruff | `select` | `E, F, W, I, UP, B, SIM` |
| ruff | `ignore` | `E501` (line-too-long), `B008` (function-call-in-default) |
| mypy | `python_version` | `3.11` |
| mypy | `ignore_missing_imports` | `true` |

---

## 4. 验证结果

### 4.1 配置合法性

| 检查项 | 状态 | 详情 |
|---|---|---|
| YAML 语法 | ✅ | `yaml.safe_load()` 通过 |
| TOML 语法 | ✅ | `tomllib.load()` 通过 |
| 依赖声明 | ✅ | `click>=8.0`, `pyyaml>=6.0`, `pydantic>=2.0` |
| pytest 配置 | ✅ | `testpaths` 3 个目录均存在 |
| ruff 配置 | ✅ | `select` 规则集合法 |
| .env gitignore | ✅ | `.env` 已在 `.gitignore` 中 |

### 4.2 本地预跑（建议）

```bash
# 安装开发依赖
pip install -e ".[test,dev]"

# 跑 lint
ruff check alpha/ core/ cli/ tests/
ruff format --check alpha/ core/ cli/ tests/

# 跑 typecheck
mypy alpha/ core/ cli/

# 跑测试
pytest tests/unit tests/cli --cov=. --cov-report=term-missing

# 验证打包
python -m build
```

> **注意**: 阶段 1 不要求代码通过 ruff/mypy 检查（typecheck 为 `continue-on-error: true`）。阶段 3 将执行 `ruff check --fix` + `ruff format` 做一次性合规化。

---

## 5. 阶段性推进计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| **阶段 1** | 添加 `ci.yml` + 工具配置 + `.env.example` | ✅ 已完成 |
| **阶段 2** | 观察 CI 运行结果，调整 ruff/mypy 规则 | 待执行 |
| **阶段 3** | 执行 `ruff check --fix` + `ruff format` 一次性合规化 | 待执行 |
| **阶段 4** | 启用 mypy `--strict` 模式（移除 `continue-on-error`） | 待执行 |
| **阶段 5** | 配置 `TUSHARE_TOKEN` secret，启用 integration job | 待执行 |
| **阶段 6** | 添加 CD（PyPI 发布、Docker 镜像） | 待规划 |

---

## 6. Secrets 管理

### 6.1 当前状态

| Secret | 必需 | CI 中状态 |
|---|---|---|
| `TUSHARE_TOKEN` | ❌ (仅 integration) | 未配置，integration job `continue-on-error: true` |
| `AKSHARE_PROXY` | ❌ | 未配置，可选 |

### 6.2 配置步骤

```bash
# 1. GitHub 仓库 → Settings → Secrets and variables → Actions
# 2. 添加:
#    - TUSHARE_TOKEN: <your_token>
#    - AKSHARE_PROXY: <your_proxy_url>  (可选)

# 3. 本地开发
cp .env.example .env
# 编辑 .env 填入真实值
```

---

## 7. 验收清单

部署后验证：

- [ ] 创建 PR，CI 跑通（lint + test + build）
- [ ] PR comment 显示覆盖率数字
- [ ] 修改 `alpha/strategy/industry_rotation.py` 引入 bug → test 失败 → CI 标红
- [ ] 合并到 main 后 CI 成功，artifacts 可下载
- [ ] `workflow_dispatch` 手动触发可选 `run_integration`
- [ ] 修改 `README.md` 不触发 CI（`paths-ignore` 生效）
- [ ] 重复推送同一 PR，后一次自动取消前一次

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| ruff 检查大量失败 | 高 | 低（lint 阻塞但可修复） | 阶段 3 执行自动修复 |
| mypy 类型错误过多 | 高 | 无（`continue-on-error`） | 阶段 4 逐步启用 strict |
| integration 测试失败 | 中 | 无（`continue-on-error`） | 仅 push / 手动触发时跑 |
| pip 缓存未命中 | 低 | 中（CI 变慢） | 检查 `cache-dependency-path` |
| Python 3.14 兼容性问题 | 低 | 中（矩阵 1/4 失败） | `fail-fast: false` 不影响其他版本 |

---

## 9. 参考

- 设计文档: `design/system-optimization/CICD-ARCHITECTURE.md`
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Ruff 规则集](https://docs.astral.sh/ruff/rules/)
- [pytest-cov 配置](https://pytest-cov.readthedocs.io/)

---

**实施完成**: 2026-06-21
