# VNPY CI/CD 架构设计

> **文档版本**: 1.0.0
> **最后更新**: 2026-06-21
> **作者**: Atlas (Chief Architect AI)
> **状态**: 设计阶段（CHANGELOG 标记为 Unreleased 计划项）

---

## 📋 概述

为 VNPY Alpha 量化交易系统设计基于 **GitHub Actions** 的 CI/CD 流水线，目标是：

1. 推送/合并代码时自动验证变更质量
2. 防止 P0 级别问题（如 `industry_rotation.py` 四个边界条件）再次引入
3. 提供测试覆盖率的可观测性
4. 为后续 CD（PyPI 发布、镜像部署）保留扩展点

---

## 1. 调研结果

### 1.1 项目现状

| 维度 | 现状 | 影响 |
|---|---|---|
| 包管理 | `pyproject.toml` (setuptools >= 61) | 可用 `pip install -e .` 和 `python -m build` |
| Python 版本 | 声明 `>=3.9`，本地用 3.14 | 矩阵应覆盖 3.11–3.14 |
| 显式依赖 | `click>=8.0` | **缺口**: 实际使用 `pyyaml>=6.0`, `pydantic>=2.0` |
| 入口点 | `vnpy = "cli.main:main"` | 可用 `pipx run` 或 `vnpy --help` 验证 |
| 测试 | 14 个文件 (unit 4 + cli 3 + integration 4 + fixtures) | 单元/CLI 测试无需外部服务 |
| 覆盖率 | `.coveragerc` 已存在 | 可直接对接 `pytest-cov` |
| pytest 配置 | `pyproject.toml` 中**无** `[tool.pytest.ini_options]` | 需要在 workflow 中传 `-ra -q` 或补配置 |
| 现有 CI | 无 `.github/workflows/` | 全新搭建 |
| 部署目标 | 单机 + cron 调度 | 暂无 PyPI 发布需求，CD 可选 |

### 1.2 Secrets 使用面

代码中通过 `os.environ` / `os.getenv` 访问的变量：

| Secret | 必填 | 使用位置 | CI 建议 |
|---|---|---|---|
| `TUSHARE_TOKEN` | 否 | `alpha/strategy/industry_rotation.py` (ValuationFetcher) | 仅 integration 集成测试需要 |
| `AKSHARE_PROXY` | 否 | `core/proxy_pool.py` | 不需要 |
| `BAOSTOCK_ENABLED` | 否 | 数据源开关 | 不需要 |
| `NEO4J_URI/USER/PASSWORD` | 否 | 知识图谱模块 | 不需要 |
| `REDIS_HOST/PORT` | 否 | 可选缓存 | 不需要 |

**结论**: 默认 CI 流程（unit + cli 测试）**不需要任何 secret**。integration 测试如需真实 Tushare API，应通过 `repository secrets` 注入并在 integration job 单独启用。

### 1.3 配置与现有约定

- `cli/utils/config.py` 提供 `_resolve_env_vars()` 自动展开 `${VAR}`
- `tests/fixtures/` 已有 mock 数据
- `pytest` 收集依赖 `tests/unit`、`tests/cli`、`tests/integration` 三个目录
- CHANGELOG 明确把 "CI 配置（GitHub Actions）" 列为 Unreleased 计划项

---

## 2. 工具链选型

| 类别 | 工具 | 选型理由 |
|---|---|---|
| **Lint** | `ruff` | 比 flake8/isort/pyupgrade 更快，集成度高，单一工具覆盖 E/F/W/I/UP/B 规则 |
| **Format check** | `ruff format` (Black 兼容) | 与 Black 100% 兼容，零额外配置 |
| **Type check** | `mypy --strict` (可选) | 项目使用 `from __future__ import annotations`，类型注解存在但不强 |
| **Test** | `pytest` + `pytest-cov` | 已是项目测试框架 |
| **Build** | `python -m build` | PEP 517 标准 |
| **Coverage** | `coverage` + `pytest-cov` | `.coveragerc` 已存在 |
| **Cache** | `actions/setup-python` 内置 pip cache | 官方支持，无需额外 action |
| **Runner** | `ubuntu-latest` | 免费、Python 3.14 已预装 |

### 2.1 拒绝的方案

- **Black + isort 单独使用**: Ruff 已包含，无需重复
- **pre-commit 作为 CI 必需步骤**: 可作为本地开发工具，但 CI 直接跑 `ruff` 更简单
- **Tox / Nox**: 项目只有 Python 包，CI 矩阵已能覆盖多版本
- **Codecov 上传**: 国内访问不稳定，先用 artifact + PR comment

---

## 3. Workflow 设计

### 3.1 文件结构

```
.github/
└── workflows/
    ├── ci.yml              # 主流程：lint + typecheck + test + build
    ├── coverage.yml        # 周报：跑全量测试并归档覆盖率
    └── release-drafter.yml # 可选：自动生成 release notes（未启用）
```

### 3.2 ci.yml 触发条件

```yaml
on:
  push:
    branches: [main, master]
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'design/**'
      - '.gitignore'
  pull_request:
    branches: [main, master]
  workflow_dispatch:
    inputs:
      run_integration:
        description: '运行集成测试（需 secrets）'
        type: boolean
        default: false
```

**设计要点**:
- `paths-ignore` 减少文档/markdown 变更触发的无意义 CI
- `workflow_dispatch` 允许手动触发并选择是否跑集成测试
- 通过 branch 名同时支持 `main` 和 `master`（仓库同时存在两个分支，HEAD 指向 `master`）

### 3.3 Job 拓扑

```
┌────────────┐
│   lint     │  ruff check + ruff format --check
└─────┬──────┘
      │ (no dependency, always run)
      ▼
┌────────────┐
│ typecheck  │  mypy alpha/ core/ cli/  (continue-on-error: true)
└─────┬──────┘
      ▼
┌────────────┐
│  test      │  矩阵: 3.11, 3.12, 3.13, 3.14
│ (matrix)   │  跑 tests/unit + tests/cli
└─────┬──────┘
      ▼
┌────────────┐
│   build    │  python -m build → 上传 dist artifact
└─────┬──────┘
      ▼
┌────────────┐
│ integration│  (可选) tests/integration + TUSHARE_TOKEN secret
└────────────┘
```

**并发控制**:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```
- 同分支的 PR 推送会自动取消上一次未完成的运行
- push 到 main/master 不取消（保留完整记录）

### 3.4 完整 ci.yml 草案

```yaml
name: CI

on:
  push:
    branches: [main, master]
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - 'design/**'
  pull_request:
    branches: [main, master]
  workflow_dispatch:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

env:
  PYTHON_DEFAULT: '3.14'
  PIP_DISABLE_PIP_VERSION_CHECK: '1'

jobs:
  # ===========================================================================
  # Job 1: Lint (最快，~10s)
  # ===========================================================================
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_DEFAULT }}

      - name: Install ruff
        run: pip install "ruff>=0.6.0"

      - name: ruff check
        run: ruff check alpha/ core/ cli/ tests/

      - name: ruff format --check
        run: ruff format --check alpha/ core/ cli/ tests/

  # ===========================================================================
  # Job 2: Type check (可选，非阻塞)
  # ===========================================================================
  typecheck:
    name: Type check (mypy)
    runs-on: ubuntu-latest
    continue-on-error: true   # 项目类型注解不完整，先记录不阻塞
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_DEFAULT }}
      - name: Install mypy
        run: pip install "mypy>=1.10" types-PyYAML types-click
      - name: mypy
        run: |
          mypy alpha/ core/ cli/ \
            --ignore-missing-imports \
            --no-strict-optional \
            --show-error-codes \
            --pretty

  # ===========================================================================
  # Job 3: Test (矩阵，覆盖 4 个 Python 版本)
  # ===========================================================================
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    needs: [lint]
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12', '3.13', '3.14']
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
          cache-dependency-path: |
            pyproject.toml

      - name: Install package + test deps
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[test]"
          # 补齐未在 pyproject 声明但代码实际使用的依赖
          pip install pyyaml pydantic pytest pytest-cov

      - name: Run unit + CLI tests
        env:
          # CI 中显式禁用外部数据源
          TUSHARE_TOKEN: ''
          BAOSTOCK_ENABLED: 'false'
        run: |
          pytest tests/unit tests/cli \
            --cov=. \
            --cov-report=xml \
            --cov-report=term-missing:skip-covered \
            -ra -q \
            --junitxml=junit-${{ matrix.python-version }}.xml

      - name: Upload coverage to artifacts
        if: matrix.python-version == env.PYTHON_DEFAULT
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: |
            coverage.xml
            htmlcov/
            junit-${{ matrix.python-version }}.xml

      - name: Annotate PR with coverage
        if: github.event_name == 'pull_request' && matrix.python-version == env.PYTHON_DEFAULT
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const coverage = fs.readFileSync('coverage.xml', 'utf8');
            const match = coverage.match(/line-rate="([0-9.]+)"/);
            const rate = match ? (parseFloat(match[1]) * 100).toFixed(2) : 'N/A';
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `📊 **Coverage Report**\n\nLine coverage: **${rate}%**\n\n<details><summary>Details</summary>\n\nSee \`coverage-report\` artifact for full report.</details>`
            });

  # ===========================================================================
  # Job 4: Build (验证包可正常打包)
  # ===========================================================================
  build:
    name: Build package
    runs-on: ubuntu-latest
    needs: [lint]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_DEFAULT }}
      - name: Install build
        run: pip install build
      - name: Build sdist + wheel
        run: python -m build
      - name: Verify build artifacts
        run: |
          ls -la dist/
          python -m zipfile -l dist/*.whl | head -20
      - name: Upload dist
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  # ===========================================================================
  # Job 5: Integration (可选，默认禁用)
  # ===========================================================================
  integration:
    name: Integration tests
    runs-on: ubuntu-latest
    needs: [test]
    if: github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.run_integration)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_DEFAULT }}
          cache: 'pip'
      - name: Install
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run integration tests
        env:
          TUSHARE_TOKEN: ${{ secrets.TUSHARE_TOKEN }}
          AKSHARE_PROXY: ${{ secrets.AKSHARE_PROXY }}
        run: |
          pytest tests/integration -v --tb=short -ra
        continue-on-error: true   # 数据源依赖外部 API，失败不阻塞合并
```

### 3.5 关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| `paths-ignore` | docs / markdown | 减少 80% 误触，节省 CI 配额 |
| `continue-on-error: typecheck` | 是 | 项目类型注解覆盖率低，先观察不阻塞 |
| `fail-fast: false` | 是 | 矩阵中一个版本失败不影响其他版本 |
| `cache: pip` | 是 | `actions/setup-python` 原生支持，命中率高 |
| 默认 skip integration | 是 | 单元 + CLI 测试覆盖 90% 价值，集成测试耗时长且依赖外部 API |
| `workflow_dispatch.run_integration` | 是 | 允许 release 前手动跑全套 |
| Coverage 上传位置 | PR comment + artifact | 不强依赖第三方服务 |

---

## 4. Secrets 管理

### 4.1 必需 vs 可选

| Secret | 必需 | 提供方 | 用法 |
|---|---|---|---|
| `TUSHARE_TOKEN` | ❌ (仅 integration) | 仓库 Owner | 集成测试中 ValuationFetcher 真实 API |
| `AKSHARE_PROXY` | ❌ | 仓库 Owner | 代理池（如有企业代理） |

### 4.2 配置流程

```bash
# 1. 在 GitHub 仓库设置中添加 (Settings → Secrets and variables → Actions)
#    - TUSHARE_TOKEN: <your_token>
#    - AKSHARE_PROXY: <your_proxy_url>  (可选)

# 2. Fork 仓库或 PR 来自 fork 时，secrets 不可访问
#    → integration job 自动跳过 (因为 env 变量为空字符串)

# 3. 本地开发复制 .env.example
cp .env.example .env
# 编辑填入真实 token
```

### 4.3 安全原则

1. **绝不在 workflow 中 echo secrets** —— GitHub 会自动 mask，但仍要避免
2. **绝不在 PR 中暴露 secret 值** —— `pull_request` 触发的 workflow **不继承** secrets
3. **`.env` 已 gitignore** —— 验证 `.gitignore` 包含 `.env`
4. **`.env.example` 提供模板** —— 提交到仓库，仅含 key 名不含 value

### 4.4 建议的 `.env.example`

```bash
# VNPY 数据下载服务 - 环境变量模板
# 复制为 .env 并填入真实值

# Tushare Pro API Token (https://tushare.pro)
TUSHARE_TOKEN=

# AKShare 代理 (可选)
AKSHARE_PROXY=

# 备用数据源开关
BAOSTOCK_ENABLED=false

# Neo4j (知识图谱，可选)
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=

# Redis (可选)
REDIS_HOST=
REDIS_PORT=
```

---

## 5. 依赖与配置变更建议

### 5.1 pyproject.toml 需补充

```toml
[project]
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",       # 新增：cli/utils/config.py 使用
    "pydantic>=2.0",     # 新增：cli/utils/cron_schema.py 使用
]

[project.optional-dependencies]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.10",
    "coverage>=7.0",
]
dev = [
    "ruff>=0.6.0",
    "mypy>=1.10",
    "types-PyYAML",
    "types-click",
    "build>=1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/cli", "tests/integration"]
addopts = "-ra -q --strict-markers"
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["alpha", "cli", "core", "vnpy"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/venv/*",
    "*/examples/*",
    "*/scripts/*",
    "*/docs/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
precision = 2
show_missing = true

[tool.ruff]
target-version = "py39"
line-length = 100
extend-exclude = ["venv", "examples", "docs"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501", "B008"]  # E501: line-too-long (formatter 负责)

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
no_strict_optional = true
show_error_codes = true
files = ["alpha", "cli", "core"]
```

### 5.2 阶段性推进

| 阶段 | 内容 | 影响 |
|---|---|---|
| **阶段 1 (本 PR)** | 添加 `.github/workflows/ci.yml` + 本文档 | 启用 CI，不改代码 |
| **阶段 2** | 补 `pyproject.toml` 依赖 + pytest 配置 + ruff 配置 | 代码可被 ruff 格式化 |
| **阶段 3** | 跑 `ruff check --fix` + `ruff format` 自动修复 | 一次性合规化 |
| **阶段 4** | 引入 mypy strict 模式 | 长期类型安全 |
| **阶段 5** | 启用 integration job（需 secrets） | release 前验证 |

---

## 6. 故障排查手册

### 6.1 常见失败模式

| 症状 | 原因 | 解决 |
|---|---|---|
| `pip install -e .` 失败 | pyproject 缺 `pyyaml` / `pydantic` | 补充依赖后重跑 |
| `pytest: command not found` | 未安装 pytest | 改用 `python -m pytest` |
| `ModuleNotFoundError: cli` | 未运行 `pip install -e .` | 在 install 步骤加 `-e .[test]` |
| Coverage 0% | `.coveragerc` 路径不匹配 | 删除 `.coveragerc` 改用 `pyproject.toml` |
| Fork PR 跑 integration 失败 | secrets 不可访问 | 这是预期行为，integration job 应允许失败 |

### 6.2 调试技巧

```bash
# 本地复现 CI 环境
python -m pip install -e ".[test]"
pytest tests/unit tests/cli -ra -q --cov=. --cov-report=term-missing

# 单独跑 ruff
ruff check alpha/ core/ cli/ tests/
ruff format --check alpha/ core/ cli/ tests/

# 验证 build
python -m build
ls -la dist/
```

---

## 7. 扩展点（未来 CD）

> 当前文档聚焦 CI，CD 部分列出预留接口。

### 7.1 可选 Workflow

| 场景 | 触发 | 输出 |
|---|---|---|
| **PyPI 发布** | 推送 `v*` tag | `twine upload dist/*` |
| **Docker 镜像** | push to main | `docker build → ghcr.io` |
| **自动 Release Notes** | push to main | 基于 conventional commits |
| **Cron 健康检查** | schedule: `0 14 * * 1-5` | 跑 smoke test |

### 7.2 Environments

建议在 GitHub 创建两个 environment：

- `dev`: 自动部署到开发机，push to main 触发
- `prod`: 手动审批，发布 tag 触发

---

## 8. 验收清单

部署本 CI 后验证：

- [ ] 在 fork 上创建 PR，CI 跑通（lint + test + build）
- [ ] PR comment 显示覆盖率数字
- [ ] 修改 `alpha/strategy/industry_rotation.py` 引入 `1/0`，test 失败，CI 标红
- [ ] 合并到 main 后，CI 成功且 artifacts 可下载
- [ ] `workflow_dispatch` 手动触发可选参数 `run_integration`
- [ ] 修改 `README.md` 不触发 CI（`paths-ignore` 生效）
- [ ] 重复推送同一 PR，后一次自动取消前一次

---

## 📚 参考

- [GitHub Actions 官方文档](https://docs.github.com/actions)
- [setup-python action](https://github.com/actions/setup-python)
- [Ruff 规则集](https://docs.astral.sh/ruff/rules/)
- [pytest-cov 配置](https://pytest-cov.readthedocs.io/)
- [PEP 517 构建规范](https://peps.python.org/pep-0517/)
- 本仓库 `AGENTS.md` / `CONTRIBUTING.md`

---

**最后更新**: 2026-06-21 by Atlas
