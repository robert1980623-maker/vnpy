# 数据同步修复方案

## 问题

检查脚本读取本地文件（trading.db, virtual_account.json），但这些文件与飞书多维表格不同步。

## 根本原因

1. 交易执行后只更新了飞书表格
2. 本地文件没有同步更新
3. 检查脚本读的是旧数据

## 解决方案

### 方案 A：Cron 任务先同步再检查（推荐）

修改 Cron 任务的 message payload，让 Agent 按以下步骤执行：

```
1. 使用 feishu_bitable_app_table_record 从飞书读取：
   - 账户数据 (tblMqYRdqBjhMnik)
   - 持仓数据 (tblLHrg7fFOcN0to)

2. 写入缓存文件：
   - data/feishu_cache/account.json
   - data/feishu_cache/positions.json

3. 运行检查脚本（risk_check.py 等）
   - VirtualAccount 会自动从缓存读取

4. 发送汇报到群聊
```

### 方案 B：检查脚本直接用 OpenClaw 工具

修改检查脚本，内嵌飞书读取逻辑（需要 Agent 上下文）。

## 已完成的修改

1. ✅ `virtual_account.py` 已修改为优先从缓存读取
2. ✅ 缓存目录：`data/feishu_cache/`
3. ✅ 缓存过期检查：超过 1 小时自动回退到本地文件

## 待完成

修改以下 Cron 任务的 message payload，添加同步步骤：

- `1641085f-3ca9-4fd3-a852-392c1cbec074` - 15:30 交易执行检查
- `0bf17a79-ddfa-4f9a-b9c6-dbc3f192c936` - 16:30 复盘前数据验证
- `4da85823-7819-4fd0-8fb4-88d825cea8ba` - 16:30 复盘时段
- 其他 trading Cron 任务

## 测试命令

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 -c "from virtual_account import VirtualAccount; va = VirtualAccount(); print(va.get_positions())"
```
