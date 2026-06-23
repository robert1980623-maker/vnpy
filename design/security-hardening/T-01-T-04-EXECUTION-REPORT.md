# T-01 + T-04 执行报告

## 执行时间
2026-06-23 21:30

## 已完成修复

### T-01: Control UI device auth 启用 ✅

**变更**:
```diff
gateway.controlUi:
-  dangerouslyDisableDeviceAuth: true
+  dangerouslyDisableDeviceAuth: false
```

**验证**:
- dangerouslyDisableDeviceAuth: False ✅
- allowInsecureAuth: False ✅
- bind: loopback (127.0.0.1) ✅

### T-04: 飞书 groupPolicy 收紧 ✅

**变更**: 12 处（1 全局 + 11 bot 账户）
- default, security, study, trading, junior-assistant
- architect-agent, marketing-agent, ota-business-agent
- quant-finance-agent, report-agent, data-agent

```diff
- groupPolicy: "open"
+ groupPolicy: "allowlist"
```

**验证**:
- Global: allowlist ✅
- All 11 bots: True ✅

## 安全收益
1. **P0 修复**: 阻止未授权访问 Control UI
2. **P1 修复**: 阻止任意群组触发飞书 bot
3. **零停机**: 配置已写入 openclaw.json，待 gateway 重启生效

## 下一步
- T-02: bind 限制 127.0.0.1（已默认 loopback，可跳过）
- T-03: 一次性配对 CLI 命令
- T-05: 工具默认拒绝 + 白名单
- T-06: requireMention=true
- T-07~T-09: 35B 沙箱
- T-10~T-11: 心跳
