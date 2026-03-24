# 📦 数据新鲜度方案 - 安装指南

**创建时间:** 2026-03-20  
**状态:** ✅ 脚本已就绪，等待 crontab 安装

---

## ✅ 已完成的准备工作

| 项目 | 状态 | 说明 |
|------|------|------|
| trading_calendar.py | ✅ 已测试 | 交易日历判断正常 |
| data_freshness_guard.py | ✅ 已测试 | 新鲜度检查正常 |
| enhanced_download_with_validation.py | ✅ 已测试 | 帮助信息正常 |
| 安装脚本 | ✅ 已创建 | install_crontab.sh |

---

## 🔧 安装 Crontab (三选一)

### 方式 1: 运行安装脚本（最简单）

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
./install_crontab.sh
```

### 方式 2: 手动复制粘贴

```bash
crontab -e
```

然后粘贴以下内容：

```cron
SHELL=/bin/zsh
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# 凌晨数据下载 (02:30)
30 2 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && /usr/local/bin/python3 enhanced_download_with_validation.py --non-interactive >> /Users/rowang/.openclaw/logs/cron_data_download_night.log 2>&1

# 下午数据下载 (17:30, 工作日)
30 17 * * 1-5 cd /Users/rowang/projects/vnpy/examples/alpha_research && /usr/local/bin/python3 enhanced_download_with_validation.py --non-interactive >> /Users/rowang/.openclaw/logs/cron_data_download_day.log 2>&1

# 新鲜度守护 (每 30 分钟，工作日 9-23 点)
*/30 9-23 * * 1-5 cd /Users/rowang/projects/vnpy/examples/alpha_research && /usr/local/bin/python3 data_freshness_guard.py --non-interactive >> /Users/rowang/.openclaw/logs/cron_freshness_guard.log 2>&1

# 每日选股 (09:00, 工作日)
0 9 * * 1-5 cd /Users/rowang/.openclaw && /usr/local/bin/openclaw cron run "每日选股" >> /Users/rowang/.openclaw/logs/cron_stock_selection.log 2>&1

# 每日复盘 (20:00, 工作日)
0 20 * * 1-5 cd /Users/rowang/.openclaw && /usr/local/bin/openclaw cron run "每日复盘" >> /Users/rowang/.openclaw/logs/cron_daily_review.log 2>&1
```

### 方式 3: 使用配置文件

```bash
cat /tmp/new_crontab.txt | crontab -
```

---

## ✅ 验证安装

```bash
# 查看已安装的 crontab
crontab -l

# 应该看到 5 个任务
```

---

## 🧪 手动测试脚本

### 测试交易日历
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 trading_calendar.py
```

### 测试新鲜度检查
```bash
python3 data_freshness_guard.py --check-only --non-interactive
```

### 测试数据下载
```bash
python3 enhanced_download_with_validation.py --non-interactive
```

---

## 📊 预期效果

安装完成后，系统会自动：

| 时间 | 任务 | 说明 |
|------|------|------|
| 02:30 | 凌晨下载 | 等美股收盘后 |
| 17:30 | 下午下载 | 等 A 股数据发布后（仅工作日） |
| 每 30 分钟 | 新鲜度守护 | 持续监控，自动修复（工作日 9-23 点） |
| 09:00 | 每日选股 | 原有任务 |
| 20:00 | 每日复盘 | 原有任务 |

---

## 📁 文件清单

```
/Users/rowang/projects/vnpy/examples/alpha_research/
├── trading_calendar.py              # 交易日历工具
├── data_freshness_guard.py          # 新鲜度守护者
├── enhanced_download_with_validation.py  # 增强版下载器
├── install_crontab.sh               # 安装脚本
├── DATA_FRESHNESS_PLAN.md           # 完整方案文档
└── README_INSTALL.md                # 本文件
```

---

## 🆘 需要帮助？

查看完整文档：
```bash
cat DATA_FRESHNESS_PLAN.md
```

查看日志：
```bash
tail -50 /Users/rowang/.openclaw/logs/cron_freshness_guard.log
```

---

**下一步:** 选择一种方式安装 crontab，然后系统就会自动运行！🚀
