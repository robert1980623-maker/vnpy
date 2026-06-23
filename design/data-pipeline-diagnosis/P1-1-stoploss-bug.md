# P1-1: strict_stop_loss.py Bug 修复

## 问题
`strict_stop_loss.py` 中 `profit_rate` 和 `pos_info` 变量未定义，导致止损检查逻辑崩溃。

## 根因
- 缺少 `profit_rate = (current_price - cost_price) / cost_price` 计算
- 缺少 `pos_info = {'symbol': symbol, ...}` 构造
- 运行时抛出 NameError，止损检查完全无效

## 修复方案
修改 `examples/alpha_research/strict_stop_loss.py`，添加缺失的变量计算：

1. 在止损检查循环中添加 `profit_rate` 计算
2. 构造 `pos_info` 字典用于风控判断
3. 确保所有持仓的市值、盈亏数据正确

## 验收标准
1. 修改 `examples/alpha_research/strict_stop_loss.py`
2. 添加 `profit_rate` 和 `pos_info` 变量定义
3. 验证：手动执行止损检查不抛 NameError
4. 不修改 `~/.openclaw/` 下的任何文件

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `examples/alpha_research/` 下的文件
- 预估时间：15 分钟
