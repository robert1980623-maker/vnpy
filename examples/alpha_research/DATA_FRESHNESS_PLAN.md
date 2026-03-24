# 数据新鲜度保证方案 - 实施文档

**创建时间:** 2026-03-20  
**状态:** 已实施 ✅

---

## 📋 方案概述

本方案通过以下机制保证数据永远是最新的：

1. **智能下载判断** - 只在交易日且数据发布后下载
2. **下载后验证** - 自动验证数据日期是否符合预期
3. **持续监控** - 每 30 分钟检查新鲜度，自动修复滞后数据
4. **失败重试** - 下载失败自动重试，连续失败告警

---

## 🛠️ 已创建的工具

### 1. 交易日历工具 (`trading_calendar.py`)

```bash
# 功能
- 判断是否为 A 股交易日
- 获取最近交易日
- 判断数据是否已发布（16:30 后）

# 使用示例
python3 trading_calendar.py
```

### 2. 数据新鲜度守护者 (`data_freshness_guard.py`)

```bash
# 功能
- 智能判断是否需要下载
- 检查所有持仓数据新鲜度
- 自动触发补充下载
- 下载后验证

# 使用示例
python3 data_freshness_guard.py              # 完整检查 + 自动修复
python3 data_freshness_guard.py --check-only # 只检查不修复
```

### 3. 增强版下载器 (`enhanced_download_with_validation.py`)

```bash
# 功能
- 下载前检查（交易日 + 数据发布）
- 批量下载股票数据
- 下载后自动验证
- 失败自动重试

# 使用示例
python3 enhanced_download_with_validation.py
```

---

## ⏰ Cron 配置

### 新的定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 凌晨数据下载 | 02:30 | 等美股收盘后 |
| 下午数据下载 | 17:30 (工作日) | 等 A 股数据发布后 |
| 新鲜度守护 | 每 30 分钟 (9-23 点，工作日) | 持续监控 + 自动修复 |
| 每日选股 | 09:00 (工作日) | 原有任务 |
| 每日复盘 | 20:00 (工作日) | 原有任务 |

### 安装 Cron 配置

由于系统权限限制，需要手动安装：

```bash
# 1. 查看当前 crontab
crontab -l

# 2. 备份当前配置
crontab -l > ~/cron_backup_$(date +%Y%m%d).txt

# 3. 安装新配置
cat /tmp/new_crontab.txt | crontab -

# 4. 验证安装
crontab -l
```

如果 `crontab -` 命令失败，请手动编辑：

```bash
crontab -e
```

然后粘贴 `/tmp/new_crontab.txt` 的内容。

---

## 📊 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                    数据新鲜度保障流程                     │
└─────────────────────────────────────────────────────────┘

[定时触发] 每 30 分钟
       ↓
┌──────────────────┐
│ 1. 下载前检查     │
│ - 是否交易日？    │
│ - 数据已发布？    │
└────────┬─────────┘
         │
    ┌────┴────┐
    │  否     │ 是
    │  ↓      ↓
    │ 跳过  ┌─────────────┐
    │      │ 2. 检查新鲜度 │
    │      │ - 新鲜率？   │
    │      │ - 滞后股票？ │
    │      └──────┬──────┘
    │             │
    │       ┌─────┴─────┐
    │       │ <80% 新鲜 │ ≥80% 新鲜
    │       │    ↓      │    ↓
    │       │ 触发下载  │  跳过
    │       └─────┬─────┘
    │             │
    │      ┌──────┴──────┐
    │      │ 3. 执行下载 │
    │      │ - 批量下载  │
    │      │ - 自动重试  │
    │      └──────┬──────┘
    │             │
    │      ┌──────┴──────┐
    │      │ 4. 验证结果 │
    │      │ - 日期正确？│
    │      │ - 数据完整？│
    │      └──────┬──────┘
    │             │
    │       ┌─────┴─────┐
    │       │ 成功 ✓    │ 失败 ✗
    │       │  ↓        │   ↓
    │       │ 记录成功  │ 重试/告警
    │       └───────────┘
    │
    ↓
[生成报告] → reports/data_freshness/
```

---

## 📁 报告位置

### 新鲜度报告
```
reports/data_freshness/
├── guard_report_YYYYMMDD_HHMMSS.json  # 每次检查报告
├── latest_report.json                  # 最新报告
└── download_report_YYYYMMDD_HHMMSS.json # 下载报告
```

### 日志文件
```
.openclaw/logs/
├── cron_data_download_night.log   # 凌晨下载日志
├── cron_data_download_day.log     # 下午下载日志
├── cron_freshness_guard.log       # 新鲜度守护日志
├── cron_stock_selection.log       # 选股日志
└── cron_daily_review.log          # 复盘日志
```

---

## 🔍 常用命令

### 检查数据新鲜度
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 data_freshness_guard.py --check-only
```

### 手动触发下载
```bash
python3 enhanced_download_with_validation.py
```

### 查看最新报告
```bash
cat reports/data_freshness/latest_report.json | jq .
```

### 查看日志
```bash
tail -50 /Users/rowang/.openclaw/logs/cron_freshness_guard.log
```

---

## ⚠️ 注意事项

1. **非交易日自动跳过** - 周末和节假日不会执行下载
2. **数据发布时间** - A 股数据通常在交易日 16:00-17:00 发布
3. **重试机制** - 下载失败会自动重试（最多 3 次）
4. **告警阈值** - 连续 3 次失败需要人工介入

---

## 🚨 故障排查

### 问题 1: 数据持续滞后

```bash
# 检查下载日志
tail -100 /Users/rowang/.openclaw/logs/cron_data_download_day.log

# 手动执行下载
python3 enhanced_download_with_validation.py

# 检查网络
ping www.baidu.com
```

### 问题 2: 验证失败

```bash
# 检查数据文件
ls -la data/akshare/bars/*.csv | head -10

# 查看数据日期
tail -1 data/akshare/bars/000630_SZ.csv
```

### 问题 3: Cron 未执行

```bash
# 检查 crontab
crontab -l

# 检查 cron 服务
sudo systemctl status cron  # Linux
sudo launchctl list | grep cron  # macOS

# 手动测试脚本
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 data_freshness_guard.py --check-only
```

---

## 📈 后续优化建议

1. **接入 Tushare 交易日历** - 获取准确的 A 股休市安排
2. **添加告警通知** - 连续失败时发送飞书/微信通知
3. **数据质量评分** - 不仅检查日期，还检查数据完整性
4. **多数据源冗余** - Tushare → AkShare → Baostock 自动切换

---

**文档版本:** v1.0  
**最后更新:** 2026-03-20
