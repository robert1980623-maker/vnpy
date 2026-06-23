# T-04: 飞书 groupPolicy 收紧

## 目标
将 12 个飞书 bot 的 `groupPolicy` 从 `"open"` 改为 `"allowlist"`，限制可访问的群组

## 当前状态
- 12 个飞书 bot 全部 `groupPolicy: "open"`
- 全部 `allowFrom: ["*"]` 和 `groupAllowFrom: ["*"]`
- 任何人/任何群都可以触发这些 bot

## 涉及文件
- `~/.openclaw/openclaw.json` → `channels.feishu.accounts.<id>.groupPolicy`

## 修复方案
将所有 12 个 bot 的 `groupPolicy` 改为 `"allowlist"`：
- default, security, study, trading, junior-assistant
- architect-agent, marketing-agent, ota-business-agent
- quant-finance-agent, report-agent, data-agent

## 验收标准
1. 所有 bot 的 `groupPolicy` 改为 `"allowlist"`
2. 全局 `channels.feishu.groupPolicy` 也改为 `"allowlist"`
3. 保留 dmPolicy: "open"（个人对话不受影响）

## 预估时间
5 分钟
