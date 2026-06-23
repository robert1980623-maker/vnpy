# VNPY 安全加固 - 任务拆分

> **文档版本**: 1.0.0
> **创建日期**: 2026-06-23
> **作者**: Atlas (Chief Architect AI)
> **依据调研**: `RESEARCH-REPORT.md` v1.0.0
> **总预估**: 12 个子任务 / ~6.5 小时 / 4 个并发组

---

## 📋 任务总览

| ID | 名称 | 复杂度 | 时间 | 依赖 | 并发组 |
|---|---|---|---|---|---|
| T-01 | Control UI device auth 启用 | 🟢 | 5 min | — | G1 |
| T-02 | Control UI bind 限制 127.0.0.1 | 🟢 | 3 min | T-01 | G1 |
| T-03 | 一次性配对 CLI 命令 | 🟡 | 10 min | T-01 | G1 |
| T-04 | groupPolicy="restricted" | 🟢 | 5 min | — | G1 |
| T-05 | 工具默认拒绝 + 白名单 | 🟡 | 10 min | T-04 | G1 |
| T-06 | requireMention=true | 🟢 | 3 min | T-04 | G1 |
| T-07 | 35B agent Docker 沙箱镜像 | 🟡 | 10 min | — | G2 |
| T-08 | agent.yaml 启用沙箱 | 🟢 | 5 min | T-07 | G2 |
| T-09 | 35B 工具白名单配置 | 🟢 | 5 min | T-08 | G2 |
| T-10 | architect-agent 心跳任务 | 🟢 | 5 min | — | G3 |
| T-11 | 心跳告警 + 飞书/Slack 投递 | 🟡 | 8 min | T-10 | G3 |
| T-12 | 验证 + 文档更新 | 🟢 | 10 min | T-01~T-11 | G4 |

**复杂度图例**: 🟢 简单（< 5 min）/ 🟡 中等（5-10 min）/ 🔴 复杂（> 10 min）

---

## 🎯 并发执行计划

```
G1 (5 min)        G2 (20 min)        G3 (13 min)      G4 (10 min)
─────────         ──────────         ──────────       ──────────
T-01 ─┐                                                       │
T-02 ─┤                                                       │
T-03 ─┤ (依赖 T-01)       T-07 ─┐                              │
T-04 ─┤                       T-08 ─┤ (依赖 T-07)               │
T-05 ─┤ (依赖 T-04)           T-09 ─┘ (依赖 T-08)             │
T-06 ─┘ (依赖 T-04)                                          T-12
                                                            (依赖全部)
```

**关键路径**: T-01 → T-03 → T-12（**约 25 min 串行**）
**最大并发**: G1 + G2 + G3 可同时执行（**总耗时 ~25 min**）

---

## 📦 任务详细说明

### T-01: Control UI device auth 启用 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 在 OpenClaw `gateway.yaml` 中启用 `device_auth: true` |
| **涉及文件** | `~/.openclaw/gateway.yaml` (1) |
| **预估时间** | 5 min |
| **复杂度** | 🟢 |
| **前置依赖** | 无 |
| **后置依赖** | T-02、T-03、T-12 |

**变更详情**:
```diff
 control_ui:
   enabled: true
+  device_auth: true
+  pair_token_ttl: 600
+  session_ttl: 3600
```

**回滚**:
```bash
sed -i '' 's/device_auth: true/device_auth: false/' ~/.openclaw/gateway.yaml
```

**验收**:
- [ ] 配置已保存
- [ ] OpenClaw gateway 重启后 `/ui` 路径返回 401
- [ ] 无现有会话被强制踢出（向后兼容）

---

### T-02: Control UI bind 限制 127.0.0.1 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 限制 Control UI 仅本机访问，禁止网络监听 |
| **涉及文件** | `~/.openclaw/gateway.yaml` (1) |
| **预估时间** | 3 min |
| **复杂度** | 🟢 |
| **前置依赖** | T-01 |
| **后置依赖** | T-12 |

**变更详情**:
```diff
 control_ui:
-  bind: 0.0.0.0
+  bind: 127.0.0.1
   port: 8080
```

**注意**: 如需远程访问 Control UI，需通过 SSH 隧道转发。

**验收**:
- [ ] `netstat -an | grep 8080` 仅显示 127.0.0.1
- [ ] 远程 IP 访问 `http://<host>:8080` 被拒

---

### T-03: 一次性配对 CLI 命令 🟡

| 字段 | 内容 |
|---|---|
| **目标** | 在 VNPY CLI 中新增 `vnpy security pair-device` 命令，简化首次配对 |
| **涉及文件** | `cli/commands/security.py` (新), `cli/main.py` (1) |
| **预估时间** | 10 min |
| **复杂度** | 🟡 |
| **前置依赖** | T-01 |
| **后置依赖** | T-12 |

**新增文件骨架** (`cli/commands/security.py`):
```python
"""vnpy security - 安全相关命令组"""
from __future__ import annotations
import time
import secrets
import click
from ..utils.logging import get_logger

logger = get_logger(__name__)

@click.group(name='security', short_help='安全配置')
def security():
    """安全配置子命令"""
    pass

@security.command(name='pair-device')
@click.option('--gateway', default='http://127.0.0.1:8080', help='Gateway URL')
@click.option('--ttl', default=600, help='配对令牌 TTL (秒)')
def pair_device(gateway: str, ttl: int):
    """生成一次性设备配对令牌"""
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ttl
    click.echo(f"配对令牌: {token}")
    click.echo(f"过期时间: {expires_at} (TTL={ttl}s)")
    click.echo(f"使用方法: 在 Control UI 登录页输入令牌")
    logger.info(f"Generated device pair token, expires_at={expires_at}")
```

**修改 `cli/main.py`** (1 行):
```diff
+from .commands.security import security
 ...
 cli.add_command(cron)
+cli.add_command(security)
```

**验收**:
- [ ] `vnpy security pair-device` 输出 32 字符 token
- [ ] token 可在 Control UI 配对页使用
- [ ] 过期后 token 失效

---

### T-04: groupPolicy="restricted" 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 将 OpenClaw 投递策略从 `open` 改为 `restricted` |
| **涉及文件** | `~/.openclaw/cron/jobs.json` (1) |
| **预估时间** | 5 min |
| **复杂度** | 🟢 |
| **前置依赖** | 无 |
| **后置依赖** | T-05、T-06、T-12 |

**变更详情**:
```diff
 {
   "delivery": {
-    "groupPolicy": "open",
+    "groupPolicy": "restricted",
     "allowFrom": ["U0AHSM009ML"]
   }
 }
```

**回滚**:
```bash
jq '.delivery.groupPolicy = "open"' ~/.openclaw/cron/jobs.json > /tmp/jobs.json.bak
```

**验收**:
- [ ] 飞书/Slack 群内非白名单用户消息不触发
- [ ] 现有白名单用户仍可触发

---

### T-05: 工具默认拒绝 + 白名单 🟡

| 字段 | 内容 |
|---|---|
| **目标** | agent 工具默认拒绝，仅允许显式白名单 |
| **涉及文件** | `~/.openclaw/cron/jobs.json` (1) |
| **预估时间** | 10 min |
| **复杂度** | 🟡 |
| **前置依赖** | T-04 |
| **后置依赖** | T-12 |

**变更详情**:
```diff
 {
   "delivery": {
     "groupPolicy": "restricted",
     "allowFrom": ["U0AHSM009ML"],
+    "toolPolicy": "deny_by_default",
+    "toolAllowlist": [
+      "http_get",
+      "read_file",
+      "summarize"
+    ]
   }
 }
```

**白名单选择依据**:
- `http_get` — 只读 HTTP（agent 任务必需）
- `read_file` — 只读文件（数据访问必需）
- `summarize` — 文本摘要（35B 模型核心能力）
- ❌ 排除: `shell.exec`, `file.write`, `http.post`（高危）

**验收**:
- [ ] agent 尝试调用 `shell.exec` 被拒绝
- [ ] 白名单内工具正常工作

---

### T-06: requireMention=true 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 群组消息需 @bot 才触发（防噪声消息误触发） |
| **涉及文件** | `~/.openclaw/cron/jobs.json` (1) |
| **预估时间** | 3 min |
| **复杂度** | 🟢 |
| **前置依赖** | T-04 |
| **后置依赖** | T-12 |

**变更详情**:
```diff
 {
   "delivery": {
     "groupPolicy": "restricted",
     "allowFrom": ["U0AHSM009ML"],
+    "requireMention": true
   }
 }
```

**验收**:
- [ ] 不 @bot 的消息不触发
- [ ] @bot 后正常触发

---

### T-07: 35B agent Docker 沙箱镜像 🟡

| 字段 | 内容 |
|---|---|
| **目标** | 创建最小化 Python 3.11 沙箱镜像 |
| **涉及文件** | `docker/sandbox-agent.Dockerfile` (新) |
| **预估时间** | 10 min |
| **复杂度** | 🟡 |
| **前置依赖** | 无 |
| **后置依赖** | T-08、T-09 |

**新增文件**:
```dockerfile
# docker/sandbox-agent.Dockerfile
FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -s /bin/bash agent && \
    mkdir -p /workspace && \
    chown agent:agent /workspace

# 安装最小依赖
RUN pip install --no-cache-dir \
    pyarrow==15.0.0 \
    pandas==2.1.4 \
    requests==2.31.0

# 移除高危工具
RUN apt-get purge -y --auto-remove \
    curl wget openssh-client netcat-openbsd ncat 2>/dev/null || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /workspace

# 默认无网络（由 OpenClaw 注入需要时再开）
ENV PYTHONUNBUFFERED=1
```

**验收**:
- [ ] `docker build -f docker/sandbox-agent.Dockerfile -t openclaw/sandbox:agent-1.0 .` 成功
- [ ] 镜像中无 `curl`/`wget`/`ssh`
- [ ] 镜像以 `agent` 用户运行（非 root）

---

### T-08: agent.yaml 启用沙箱 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 在 OpenClaw agent 配置中启用 Docker 沙箱 |
| **涉及文件** | `~/.openclaw/agents/architect-agent.yaml` (1) |
| **预估时间** | 5 min |
| **复杂度** | 🟢 |
| **前置依赖** | T-07 |
| **后置依赖** | T-09、T-12 |

**变更详情**:
```diff
 agents:
   - name: architect-agent
     model: qwen3.7-plus
+    sandbox:
+      enabled: true
+      image: openclaw/sandbox:agent-1.0
+      network: restricted
+      filesystem: ro
+      tmpfs:
+        - /tmp
+        - /workspace
+      memory_limit: 512m
+      cpu_limit: 1.0
```

**验收**:
- [ ] agent 启动时进入 Docker 容器
- [ ] 容器内文件系统只读
- [ ] 网络出站受限（仅白名单域名）

---

### T-09: 35B 工具白名单配置 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 限制 35B agent 可调用的工具 |
| **涉及文件** | `~/.openclaw/agents/architect-agent.yaml` (1) |
| **预估时间** | 5 min |
| **复杂度** | 🟢 |
| **前置依赖** | T-08 |
| **后置依赖** | T-12 |

**变更详情**:
```diff
 agents:
   - name: architect-agent
     model: qwen3.7-plus
+    tools:
+      - web.summarize
+      - read.parquet
+      - analyze.metrics
+      # ❌ 明确排除高危工具
+      # - shell.exec
+      # - file.write
+      # - http.post
```

**验收**:
- [ ] agent 工具列表仅含 3 个白名单项
- [ ] 调用 `shell.exec` 返回 "工具未授权" 错误

---

### T-10: architect-agent 心跳任务 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 在 VNPY cron 配置中新增 architect-agent 心跳任务 |
| **涉及文件** | `config/cron_config.yaml` (1) |
| **预估时间** | 5 min |
| **复杂度** | 🟢 |
| **前置依赖** | 无 |
| **后置依赖** | T-11、T-12 |

**变更详情** (`config/cron_config.yaml` 末尾追加):
```yaml
  # ============== 安全监控组 ==============
  - id: monitor-architect-heartbeat
    name: architect-agent 心跳监控
    group: monitor
    schedule: "*/2 * * * *"
    command: "vnpy health agent --target architect-agent"
    timeout: 30
    enabled: true
    on_failure:
      notify: ["feishu", "slack"]
      message: "🚨 architect-agent 心跳丢失 (连续 3 次失败)"
    retry:
      max_attempts: 1
    tags: [monitor, security, heartbeat]
```

**验收**:
- [ ] `vnpy cron list --group monitor` 显示新任务
- [ ] 任务在 2 分钟周期内执行
- [ ] agent 健康时无告警

---

### T-11: 心跳告警 + 飞书/Slack 投递 🟡

| 字段 | 内容 |
|---|---|
| **目标** | 实现 `vnpy health agent` 子命令 + 告警去重 |
| **涉及文件** | `cli/commands/health.py` (1) |
| **预估时间** | 8 min |
| **复杂度** | 🟡 |
| **前置依赖** | T-10 |
| **后置依赖** | T-12 |

**变更详情** (`cli/commands/health.py` 追加):
```python
@health.command(name='agent')
@click.option('--target', required=True, help='目标 agent 名称')
@click.option('--max-failures', default=3, help='最大连续失败次数')
def health_agent(target: str, max_failures: int):
    """检查 agent 健康状态"""
    import subprocess
    from pathlib import Path
    
    state_file = Path(f'/tmp/openclaw-agent-{target}.state')
    failures = 0
    
    if state_file.exists():
        try:
            failures = int(state_file.read_text().strip())
        except ValueError:
            failures = 0
    
    try:
        # Ping agent 进程
        result = subprocess.run(
            ['pgrep', '-f', f'agent.*--name.*{target}'],
            capture_output=True, timeout=10
        )
        alive = result.returncode == 0
        
        if alive:
            state_file.write_text('0')
            click.echo(f"✅ {target} 健康")
        else:
            failures += 1
            state_file.write_text(str(failures))
            if failures >= max_failures:
                click.echo(f"🚨 {target} 连续失败 {failures} 次，触发告警")
                # 触发飞书/Slack 通知
                _send_alert(target, failures)
            else:
                click.echo(f"⚠️ {target} 失败 {failures}/{max_failures}")
    except Exception as e:
        click.echo(f"❌ 检查失败: {e}", err=True)


def _send_alert(target: str, failures: int):
    """发送告警（简化实现）"""
    import os
    import requests
    webhook = os.environ.get('FEISHU_WEBHOOK') or os.environ.get('SLACK_WEBHOOK')
    if webhook:
        try:
            requests.post(webhook, json={
                'msgtype': 'text',
                'text': {'content': f'🚨 {target} 心跳丢失 {failures} 次'}
            }, timeout=5)
        except Exception:
            pass
```

**验收**:
- [ ] agent 正常时输出 ✅
- [ ] agent 异常时计数递增
- [ ] 3 次连续失败后发送飞书/Slack 告警

---

### T-12: 验证 + 文档更新 🟢

| 字段 | 内容 |
|---|---|
| **目标** | 端到端验证 + 更新项目文档 |
| **涉及文件** | `CHANGELOG.md` (1), `AGENTS.md` (1) |
| **预估时间** | 10 min |
| **复杂度** | 🟢 |
| **前置依赖** | T-01 ~ T-11 |
| **后置依赖** | 无 |

**变更 1**: `CHANGELOG.md` 追加条目
```markdown
## [Unreleased]

### Security
- **Control UI device auth 启用** (T-01~T-03)
  - `gateway.yaml` 启用 `device_auth: true`
  - 限制 `bind: 127.0.0.1`
  - 新增 `vnpy security pair-device` 命令
- **群组策略收紧** (T-04~T-06)
  - `groupPolicy: open` → `restricted`
  - 工具默认拒绝 + 白名单（http_get, read_file, summarize）
  - 群组消息需 @bot 触发
- **35B agent Docker 沙箱** (T-07~T-09)
  - 新增 `docker/sandbox-agent.Dockerfile`
  - `architect-agent.yaml` 启用沙箱 + 工具白名单
- **architect-agent 心跳监控** (T-10~T-11)
  - 新增 cron 任务 `monitor-architect-heartbeat`
  - 连续 3 次失败触发飞书/Slack 告警

### Planned
- 补齐核心模块测试覆盖（cross_sectional_engine, data_source_router, circuit_breaker）
- CI 配置（GitHub Actions）
- 配置管理统一化
```

**变更 2**: `AGENTS.md` 追加安全章节（末尾）
```markdown
---

## 🔒 安全配置（2026-06-23 更新）

### OpenClaw Control UI
- 访问方式：`http://127.0.0.1:8080/ui`（仅本机）
- 首次配对：`vnpy security pair-device`
- 会话 TTL：3600s

### Agent 沙箱
- 35B 模型运行在 Docker 沙箱中（`openclaw/sandbox:agent-1.0`）
- 文件系统：只读（`/tmp` 与 `/workspace` 临时可写）
- 网络：受限出站

### 工具权限
- 投递策略：`groupPolicy: restricted`
- 工具白名单：`http_get`, `read_file`, `summarize`
- 群组触发：需 @bot

### 监控
- architect-agent 心跳：每 2 分钟
- 告警通道：飞书 / Slack（连续 3 次失败触发）

```

**验证清单**:
- [ ] T-01~T-11 全部任务已执行
- [ ] 端到端测试：模拟攻击场景（P0-1、P1-1、P1-2）确认防护生效
- [ ] 所有 cron 任务正常运行
- [ ] 现有功能（数据下载、选股、监控）未受影响
- [ ] CHANGELOG.md 已更新
- [ ] AGENTS.md 已更新
- [ ] 文档提交：`git commit -m "security: 启用 Control UI auth + 35B 沙箱 + groupPolicy 收紧 + 心跳监控"`

---

## 🚦 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| OpenClaw 重启失败 | 低 | 高 | 保留配置备份 `cp gateway.yaml gateway.yaml.bak` |
| 沙箱镜像构建失败 | 中 | 中 | 本地先用 `docker run -it openclaw/sandbox:agent-1.0 bash` 验证 |
| 心跳误报 | 中 | 低 | 连续 3 次失败才告警（`max_failures=3`） |
| 团队成员被锁出 | 中 | 中 | T-12 验证前通知团队 + 提供 CLI 配对文档 |
| 飞书/Slack Webhook 失效 | 低 | 低 | `os.environ.get()` 静默失败，仅日志记录 |

---

## ✅ 完成定义（DoD）

- [ ] 所有 12 个子任务已完成
- [ ] 端到端验证清单全部勾选
- [ ] `CHANGELOG.md` 与 `AGENTS.md` 已更新
- [ ] Git 提交信息符合规范
- [ ] PR 描述包含：本调研报告 + 任务拆分链接
- [ ] 团队已通知新安全策略

---

**下一步**: 等待用户审查 → 启动 G1/G2/G3 并发执行 → G4 验证与文档收尾
