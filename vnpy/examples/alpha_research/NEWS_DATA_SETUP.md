# 消息面数据集成指南

## 概述

集成 AKShare 和 Tushare Pro 获取股票消息面数据，包括：
- 📰 个股新闻
- 📋 公司公告
- 📊 研报数据
- 🌐 财经新闻

## 配置

### Tushare Pro Token

Token 已通过环境变量配置，无需修改：

```bash
# 环境变量（优先级高）
export TUSHARE_TOKEN='your_token'
```

检查是否已配置：
```bash
echo $TUSHARE_TOKEN
```

### AKShare Proxy

AKShare proxy 已配置在 `akshare_patch_config.py` 中，自动加载。

## 文件说明

| 文件 | 说明 |
|------|------|
| `download_news_data.py` | 主下载脚本，集成 AKShare 和 Tushare Pro |
| `download_news.sh` | Shell 包装脚本，用于定时任务 |
| `setup_news_cron.py` | 配置定时任务的脚本 |
| `get_message_data.py` | 原有消息面获取模块（保留） |
| `news_analyzer.py` | 原有新闻分析模块（保留） |

## 数据目录

```
data/news/
├── 600519_news_2026-03-08.json    # 个股新闻
├── finance_news_2026-03-08.json   # 财经新闻（Tushare）
├── reports_2026-03-08.json        # 研报数据（Tushare）
└── summary_2026-03-08.json        # 汇总信息
```

## 使用方法

### 手动执行

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 方法 1: 直接运行 Python 脚本
python3 download_news_data.py

# 方法 2: 使用 Shell 脚本
./download_news.sh
```

### 定时任务

配置定时任务（每天 17:00 执行）：

```bash
python3 setup_news_cron.py
```

查看已配置的定时任务：

```bash
openclaw cron list
```

## 数据流集成

消息面数据与现有系统集成：

```
数据下载 (17:00) → 消息面下载 (17:00) → 选股 (09:00) → 交易 (17:30) → 复盘 (20:00)
                                              ↓
                                        消息面分析
```

### 与选股联动

在选股策略中可以结合消息面数据：

```python
from download_news_data import load_news_data

# 加载今日新闻
news = load_news_data(f"600519_news_2026-03-08.json")

# 分析新闻情感
positive_count = sum(1 for n in news if '利好' in n.get('内容', ''))

# 根据消息面调整选股评分
if positive_count > 3:
    score += 0.1  # 利好消息多，加分
```

## API 说明

### AKShare 接口

- `ak.stock_news_em(symbol)` - 个股新闻
- `ak.stock_board_industry_name_em(symbol)` - 个股公告

### Tushare Pro 接口

- `pro.news(src, start_date, end_date)` - 财经新闻
- `pro.report_daily(trade_date)` - 研报数据

## 注意事项

1. **Tushare 积分**: 部分接口需要足够的 Tushare 积分
2. **AKShare 频率**: 避免过于频繁的请求，已配置 proxy 和重试
3. **数据质量**: 建议定期检查数据完整性
4. **存储清理**: 定期清理旧数据，避免占用过多空间

## 故障排查

### Tushare 无法使用

```bash
# 检查环境变量
echo $TUSHARE_TOKEN

# 如果为空，需要配置
export TUSHARE_TOKEN='your_token'
```

### AKShare 访问失败

- 检查网络连接
- 检查 `akshare_proxy_patch` 是否安装
- 查看日志文件 `logs/news_*.log`

### 数据为空

- 可能是非交易日
- 可能是股票停牌
- 检查日期范围是否正确

## 扩展

可以添加更多消息面数据源：

- 雪球舆情
- 东方财富股吧
- 龙虎榜数据
- 大宗交易数据

---

**最后更新**: 2026-03-08
