# vnpy 世界模型 - 用户指南
**版本**: 1.0 | **更新日期**: 2026-03-15

## 快速开始

### 系统访问
- **监控仪表板**: http://localhost:5001
- **自动刷新**: 每 10 秒

### 日常操作
```bash
# 数据下载
python3 batch_download_enhanced.py

# 告警检查
python3 world_model/smart_alert.py

# 系统备份
python3 world_model/auto_ops.py

# 健康检查
python3 world_model/predictive_maintenance.py
```

## 核心功能

### 1. 监控仪表板
- 持仓概览、风险指标、规则统计、Agent 状态
- API: /api/portfolio, /api/risk, /api/rules, /api/agents

### 2. 智能告警
- 4 级告警：LOW/MEDIUM/HIGH/CRITICAL
- 多渠道通知：Slack/邮件/日志

### 3. 预测性维护
- 故障预测、健康度评分 (0-100)、扩容建议

### 4. 知识图谱
- 交易建议、规则冲突解决、智能问答

### 5. 自动化运维
- 自动备份、故障自愈、容量规划

## 故障排查

### 常见问题
1. **仪表板无法访问**: 重启 `python3 world_model/vnpy_dashboard.py`
2. **数据同步失败**: 检查 Neo4j 连接
3. **告警不触发**: 运行 `python3 world_model/smart_alert.py`
4. **健康度低**: 执行自愈 `python3 world_model/auto_ops.py`

## 最佳实践

- ✅ 使用 Tushare 主数据源 + Akshare 备份
- ✅ 设置合理告警阈值
- ✅ 每日检查系统健康
- ✅ 每周执行备份
- ✅ 每月执行恢复演练

**详细文档**: 参见 `/docs/` 目录
