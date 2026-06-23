# P1-2: 持仓 DB symbol_name 回填

## 问题
trading.db 中 10 只持仓的 `symbol_name` 全部为空，JSON 账户文件有名称但 DB 没有。

## 根因
DB 写入时未填充 `symbol_name` 字段，导致查询持仓时显示空值。

## 修复方案（简化版）
1. 只创建回填脚本 `scripts/backfill_symbol_names.py`
2. 从 JSON 账户文件读取 stock_name
3. 批量更新 trading.db positions 表

**注意**：本任务只做回填，不修改 DB 写入逻辑。写入逻辑修复留到 Phase 7。

## 验收标准
1. 创建 `scripts/backfill_symbol_names.py`
2. 验证：trading.db 中持仓的 symbol_name 字段不再为空
3. 不修改 `~/.openclaw/` 下的任何文件

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `scripts/` 下的文件（不修改 `accounts/`）
- 预估时间：10 分钟
