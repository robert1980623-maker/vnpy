# P0-2: 下载超时修复

## 问题
数据下载任务超时（600秒），50只股票×3数据源串行下载需要约20分钟。

## 根因
`enhanced_download_with_validation.py` 中 timeout=600 设置过短。

## 修复方案
修改 `examples/alpha_research/enhanced_download_with_validation.py`：

1. 将 timeout 从 600 改为 1800（30分钟）
2. 添加增量下载逻辑：只下载缺失或过期的股票

## 验收标准
1. 修改 `enhanced_download_with_validation.py` 中的 timeout 参数
2. 添加增量下载检查逻辑
3. 验证：脚本能正确识别需要更新的股票
4. 不修改 `~/.openclaw/` 下的任何文件

## 约束
- ⛔ 铁律：永远不要修改 `~/.openclaw/` 的配置文件
- 只修改 `examples/alpha_research/` 下的文件
- 预估时间：30 分钟
