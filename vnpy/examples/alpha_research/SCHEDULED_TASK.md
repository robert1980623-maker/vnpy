# 定时下载任务管理

## 📅 任务配置

### 当前任务

| 项目 | 配置 |
|------|------|
| **任务名称** | 股票数据下载（凌晨 1 点） |
| **任务 ID** | `112fa164-4b47-4723-9d0a-6d5d495aafa5` |
| **执行时间** | 每天凌晨 1:00 (Asia/Shanghai) |
| **Cron 表达式** | `0 1 * * *` |
| **执行模式** | 夜间模式（长延迟） |
| **下载数量** | 最多 20 只股票 |
| **缓存** | 自动启用 |
| **通知** | 完成后通过钉钉通知 |

---

## ⏰ Cron 表达式说明

```
0 1 * * *
│ │ │ │ │
│ │ │ │ └─ 星期几 (0-6, 0=周日)
│ │ │ └─── 月份 (1-12)
│ │ └───── 日期 (1-31)
│ └─────── 小时 (0-23)
└───────── 分钟 (0-59)
```

**当前配置**: 每天凌晨 1 点整执行

---

## 🚀 管理命令

### 查看任务状态

```bash
# 查看所有定时任务
openclaw cron list

# 查看任务详情
openclaw cron list --include-disabled
```

### 手动触发任务

```bash
# 立即执行一次下载任务
openclaw cron run 112fa164-4b47-4723-9d0a-6d5d495aafa5
```

### 暂停任务

```bash
# 禁用定时任务
openclaw cron update 112fa164-4b47-4723-9d0a-6d5d495aafa5 --patch '{"enabled": false}'
```

### 恢复任务

```bash
# 启用定时任务
openclaw cron update 112fa164-4b47-4723-9d0a-6d5d495aafa5 --patch '{"enabled": true}'
```

### 删除任务

```bash
# 删除定时任务
openclaw cron remove 112fa164-4b47-4723-9d0a-6d5d495aafa5
```

---

## 📝 手动执行下载

### 使用脚本（推荐）

```bash
# 执行定时下载脚本
~/projects/vnpy/examples/alpha_research/download_scheduled.sh
```

### 直接执行

```bash
cd ~/projects/vnpy/examples/alpha_research
source ../../venv/bin/activate
PYTHONPATH=../.. python download_data_akshare.py --night-mode --max 20
```

### 自定义参数

```bash
# 下载更多股票
python download_data_akshare.py --night-mode --max 50

# 下载指定指数
python download_data_akshare.py --index 000016 --night-mode --max 10

# 不使用缓存
python download_data_akshare.py --no-cache --max 10
```

---

## 📊 查看下载结果

### 查看缓存数据

```bash
# 查看缓存文件
ls -lh ~/projects/vnpy/examples/alpha_research/cache/

# 查看已下载的股票数据
ls -lh ~/projects/vnpy/examples/alpha_research/data/akshare/bars/
```

### 查看任务历史

```bash
# 查看任务执行历史
openclaw cron runs 112fa164-4b47-4723-9d0a-6d5d495aafa5
```

---

## 🔔 通知机制

任务完成后会自动发送钉钉消息通知，包括：

- ✅ 下载成功：显示下载的股票数量、缓存命中情况
- ❌ 下载失败：显示错误信息
- 📊 统计信息：累计下载股票数量

---

## ⚙️ 修改执行时间

### 改为凌晨 2 点执行

```bash
openclaw cron update 112fa164-4b47-4723-9d0a-6d5d495aafa5 \
  --patch '{"schedule": {"kind": "cron", "expr": "0 2 * * *", "tz": "Asia/Shanghai"}}'
```

### 改为每周一、三、五执行

```bash
openclaw cron update 112fa164-4b47-4723-9d0a-6d5d495aafa5 \
  --patch '{"schedule": {"kind": "cron", "expr": "0 1 * * 1,3,5", "tz": "Asia/Shanghai"}}'
```

### 改为每小时执行（测试用）

```bash
openclaw cron update 112fa164-4b47-4723-9d0a-6d5d495aafa5 \
  --patch '{"schedule": {"kind": "cron", "expr": "0 * * * *", "tz": "Asia/Shanghai"}}'
```

---

## 🛠️ 故障排查

### 任务未执行

1. **检查任务状态**
   ```bash
   openclaw cron list
   ```

2. **检查任务历史**
   ```bash
   openclaw cron runs 112fa164-4b47-4723-9d0a-6d5d495aafa5
   ```

3. **手动触发测试**
   ```bash
   openclaw cron run 112fa164-4b47-4723-9d0a-6d5d495aafa5
   ```

### 下载失败

1. **检查网络连接**
   ```bash
   ping www.eastmoney.com
   ```

2. **检查虚拟环境**
   ```bash
   source ~/projects/vnpy/venv/bin/activate
   python -c "import akshare; print(akshare.__version__)"
   ```

3. **查看错误日志**
   - 检查定时任务执行日志
   - 手动运行脚本查看详细错误

### AKShare 连接问题

如果 AKShare 连接失败，这是正常现象。脚本会自动：

- ✅ 使用缓存数据
- ✅ 重试最多 3 次
- ✅ 使用更长延迟（夜间模式）
- ✅ 跳过失败的股票，继续下载其他股票

---

## 📈 最佳实践

### 1. 首次运行

```bash
# 手动执行一次，确保配置正确
~/projects/vnpy/examples/alpha_research/download_scheduled.sh
```

### 2. 定期检查

每周检查一次任务执行历史：

```bash
openclaw cron runs 112fa164-4b47-4723-9d0a-6d5d495aafa5
```

### 3. 清理缓存

每月清理一次过期缓存：

```bash
# 查看缓存大小
du -sh ~/projects/vnpy/examples/alpha_research/cache/

# 清理缓存（如果需要）
rm -rf ~/projects/vnpy/examples/alpha_research/cache/*
```

### 4. 备份数据

定期备份下载的数据：

```bash
# 备份到外部存储
cp -r ~/projects/vnpy/examples/alpha_research/data/akshare \
  /path/to/backup/stock_data_$(date +%Y%m%d)
```

---

## 📞 支持

如有问题，请检查：

1. 定时任务状态：`openclaw cron list`
2. 任务执行历史：`openclaw cron runs <task-id>`
3. 下载脚本日志：手动运行脚本查看详细输出

---

**下次执行时间**: 明天凌晨 1:00 [耶]
