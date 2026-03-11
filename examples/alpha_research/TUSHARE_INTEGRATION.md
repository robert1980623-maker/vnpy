# Tushare Pro 集成说明

## ✅ 已完成

### 1. Token 配置
- **位置**: `~/.zshrc`
- **环境变量**: `TUSHARE_TOKEN`
- **状态**: ✅ 已配置并验证

### 2. 数据下载器

#### 政策数据 (download_policy_data_tushare.py)
**真实数据**:
- ✅ GDP 数据 (季度) - 2025Q4: 5.0% 增长
- ✅ CPI 数据 (月度) - 202601: 0%
- ✅ PMI 数据 (月度)
- ✅ 货币供应量 M1/M2 - 202601: M2 增长 9.0%

**备用数据** (当 API 权限不足时):
- ⚠️ 政策新闻 (频率限制：每小时 2 次)
- ✅ 手动维护重要政策

#### 国际形势数据 (download_global_data_tushare.py)
**真实数据**:
- ✅ 美股交易日历
- ✅ 外汇数据 (备用)
- ✅ 大宗商品 (原油)

**备用数据**:
- ⚠️ 国际新闻 (频率限制：每分钟 1 次)
- ✅ 手动维护重要国际新闻

---

## 📊 当前数据状态

| 数据类型 | 来源 | 状态 | 更新频率 |
|---------|------|------|----------|
| **GDP** | Tushare Pro | ✅ 真实 | 季度 |
| **CPI** | Tushare Pro | ✅ 真实 | 月度 |
| **PMI** | Tushare Pro | ✅ 真实 | 月度 |
| **M2 货币供应** | Tushare Pro | ✅ 真实 | 月度 |
| **外汇汇率** | Tushare/备用 | ⚠️ 部分真实 | 每日 |
| **原油价格** | Tushare/备用 | ⚠️ 部分真实 | 每日 |
| **政策新闻** | 备用 | ⚠️ 模拟 | 手动 |
| **国际新闻** | 备用 | ⚠️ 模拟 | 手动 |

---

## ⚠️ API 限制

### Tushare Pro 权限
- **新闻接口**: 每小时 2 次
- **财经新闻**: 每分钟 1 次
- **解决方案**: 
  1. 降低调用频率 (已添加 sleep)
  2. 使用备用数据源
  3. 升级 Tushare 会员 (可选)

---

## 🚀 使用方法

### 手动运行
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/.zshrc
source /Users/rowang/projects/vnpy/venv/bin/activate

# 下载政策数据
python3 download_policy_data_tushare.py

# 下载国际数据
python3 download_global_data_tushare.py

# 运行综合分析
python3 comprehensive_analyzer.py
```

### 定时任务
```bash
# 每天凌晨 3 点：政策数据
0 3 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_policy_data_tushare.py

# 每天凌晨 4 点：国际数据
0 4 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_global_data_tushare.py

# 每天凌晨 5 点：综合分析
0 5 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source ~/.zshrc && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 comprehensive_analyzer.py
```

---

## 📁 文件位置

```
alpha_research/
├── download_policy_data_tushare.py     # 政策数据下载 (Tushare)
├── download_global_data_tushare.py     # 国际数据下载 (Tushare)
├── comprehensive_analyzer.py           # 综合分析器
├── data/
│   ├── policy/                         # 政策数据
│   │   ├── macro_economy_YYYY-MM-DD.json   ✅ 真实数据
│   │   └── policy_news_YYYY-MM-DD.json     ⚠️ 备用数据
│   └── geopolitics/                    # 国际数据
│       ├── global_economy_tushare_YYYY-MM-DD.json  ✅ 真实数据
│       └── international_news_YYYY-MM-DD.json      ⚠️ 备用数据
└── reports/
    └── comprehensive/                  # 综合分析报告
```

---

## 💡 改进建议

### 短期
1. ✅ 使用 Tushare 真实宏观经济数据
2. ✅ 备用数据源补充新闻
3. ⚠️ 手动更新重要政策 (每周)

### 中期
1. 添加更多 Tushare 接口 (行业数据、资金流向)
2. 优化 API 调用频率 (缓存机制)
3. 考虑升级 Tushare 会员 (解除限制)

### 长期
1. 接入多个数据源 (新华网、Reuters)
2. 建立数据质量评估
3. 历史数据回测验证

---

## 📈 真实数据示例

### 最新宏观经济数据 (2026-03-09)
```json
{
  "gdp": {
    "quarter": "2025Q4",
    "gdp_yoy": 5.0%
  },
  "cpi": {
    "month": "202601",
    "cpi_yoy": 0%
  },
  "money_supply": {
    "month": "202601",
    "m2_yoy": 9.0%
  }
}
```

**解读**:
- GDP 增长 5.0% - 经济稳定增长
- CPI 0% - 物价稳定，通缩压力
- M2 增长 9% - 货币政策宽松

---

**版本**: v2.0 (Tushare 集成)  
**更新日期**: 2026-03-09
