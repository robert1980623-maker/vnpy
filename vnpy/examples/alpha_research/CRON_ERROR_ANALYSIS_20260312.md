# 定时任务错误分析报告

**日期**: 2026-03-12 20:52  
**分析师**: OpenClaw

---

## 🔴 错误任务

### 任务 1: 数据新鲜度监控 (Job ID: 1f751de7)

**状态**: error (超时)  
**计划**: 每小时整点  
**命令**: `python3 data_freshness_monitor.py --once`

**问题**:
- 任务执行超时 (>120 秒)
- 可能原因：数据下载脚本卡住、API 响应慢

**建议修复**:
1. 增加超时时间到 300 秒
2. 优化数据新鲜度检查逻辑
3. 添加超时保护机制

---

### 任务 2: 消息面数据下载 (Job ID: 198f2ee0)

**状态**: error  
**计划**: 每日 17:00  
**命令**: 未知 (data-agent)

**问题**:
```
ModuleNotFoundError: No module named 'akshare'
```

**根本原因**: 
- 定时任务未激活虚拟环境
- data-agent 没有使用正确的 Python 环境

**建议修复**:
1. 修改任务命令，添加虚拟环境激活
2. 或者在 data-agent 配置中指定 Python 路径

---

## 🔧 修复方案

### 方案 1: 修改定时任务命令

```bash
# 消息面数据下载
openclaw cron edit 198f2ee0-1eed-4a80-a1dc-0e75fd4462cb \
  --message "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_news_data.py"
```

### 方案 2: 删除并重新创建任务

```bash
# 删除旧任务
openclaw cron rm 198f2ee0-1eed-4a80-a1dc-0e75fd4462cb

# 重新创建 (带虚拟环境)
openclaw cron add --name "消息面数据下载" \
  --cron "0 17 * * *" \
  --message "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_news_data.py" \
  --model "lmstudio/zai-org/glm-4.7-flash" \
  --timeout-seconds 600 \
  --session "isolated" \
  --tz "Asia/Shanghai"
```

---

## ✅ 验证步骤

1. 手动测试命令：
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate
python3 download_news_data.py
```

2. 检查输出是否正常

3. 重新运行定时任务：
```bash
openclaw cron run <job_id>
```

---

## 📝 待办事项

- [ ] 修复消息面数据下载任务 (添加虚拟环境)
- [ ] 优化数据新鲜度监控任务 (增加超时)
- [ ] 验证所有定时任务使用正确的 Python 环境
- [ ] 添加环境检查到所有脚本

---

**创建时间**: 2026-03-12 20:52  
**状态**: 待修复
