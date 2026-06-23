# T-01: Control UI device auth 启用

## 目标
在 OpenClaw `gateway.yaml` 中启用 `device_auth: true`

## 涉及文件
- `~/.openclaw/gateway.yaml`

## 变更内容
```diff
 control_ui:
   enabled: true
+  device_auth: true
+  pair_token_ttl: 600
+  session_ttl: 3600
```

## 验收标准
1. 配置已保存
2. OpenClaw gateway 重启后 `/ui` 路径返回 401
3. 无现有会话被强制踢出（向后兼容）

## 回滚
```bash
sed -i '' 's/device_auth: true/device_auth: false/' ~/.openclaw/gateway.yaml
```

## 预估时间
5 分钟
