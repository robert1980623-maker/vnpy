# 综合消息面分析系统

## 🎯 功能概述

整合四大维度进行股票综合分析：
- **基本面 (40%)**: PE、ROE、增长率等财务指标
- **消息面 (25%)**: 个股新闻、公告、回购、资金流向
- **时政面 (20%)**: 宏观政策、行业政策、政府规划
- **国际形势 (15%)**: 中美关系、全球经济、地缘政治、行业国际竞争

## 📁 文件结构

```
alpha_research/
├── download_policy_data.py          # 政策数据下载器
├── download_geopolitics_data.py     # 国际形势数据下载器
├── comprehensive_analyzer.py        # 综合分析器
├── setup_comprehensive_cron.py      # 定时任务配置
├── data/
│   ├── policy/                      # 政策数据
│   │   ├── macro_policy_YYYY-MM-DD.json
│   │   └── industry_policy_YYYY-MM-DD.json
│   └── geopolitics/                 # 国际形势数据
│       ├── us_china_YYYY-MM-DD.json
│       ├── global_economy_YYYY-MM-DD.json
│       ├── geopolitics_YYYY-MM-DD.json
│       └── industry_competition_YYYY-MM-DD.json
└── reports/
    └── comprehensive/               # 综合分析报告
        └── comprehensive_analysis_YYYY-MM-DD.json
```

## 🚀 使用方法

### 手动运行

```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research
source /Users/rowang/projects/vnpy/venv/bin/activate

# 1. 下载政策数据
python3 download_policy_data.py

# 2. 下载国际形势数据
python3 download_geopolitics_data.py

# 3. 运行综合分析
python3 comprehensive_analyzer.py
```

### 定时任务 (建议配置)

```bash
# 每天凌晨 3 点：下载政策数据
0 3 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_policy_data.py

# 每天凌晨 4 点：下载国际形势数据
0 4 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_geopolitics_data.py

# 每天凌晨 5 点：运行综合分析
0 5 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 comprehensive_analyzer.py
```

### 在 OpenClaw 中创建 cron 任务

```bash
openclaw cron create --name "政策数据下载" --schedule "0 3 * * *" --command "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_policy_data.py"

openclaw cron create --name "国际形势数据下载" --schedule "0 4 * * *" --command "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 download_geopolitics_data.py"

openclaw cron create --name "综合消息面分析" --schedule "0 5 * * *" --command "cd /Users/rowang/projects/vnpy/examples/alpha_research && source /Users/rowang/projects/vnpy/venv/bin/activate && python3 comprehensive_analyzer.py"
```

## 📊 综合评分说明

### 评分等级

| 分数范围 | 评级 | 图标 | 建议 |
|---------|------|------|------|
| 80-100 | 强烈推荐 | ⭐⭐⭐⭐⭐ | 积极建仓 |
| 70-79 | 推荐 | ⭐⭐⭐⭐ | 适度配置 |
| 60-69 | 谨慎推荐 | ⭐⭐⭐ | 观望为主 |
| 50-59 | 观望 | ⭐⭐ | 暂不操作 |
| 0-49 | 回避 | ⭐ | 避免买入 |

### 权重配置

```python
weights = {
    'fundamental': 0.40,    # 基本面 (PE/ROE/增长)
    'news': 0.25,           # 消息面 (个股新闻/公告)
    'policy': 0.20,         # 时政面 (宏观/行业政策)
    'geopolitics': 0.15     # 国际形势 (中美/全球经济/地缘)
}
```

## 📈 分析示例

以宁德时代 (300750.SZ) 为例：

```
📊 综合评分：78.5 / 100
   行业：新能源汽车
   建议：⭐⭐⭐⭐ 推荐

📈 分项评分:
   基本面：100 (权重 40%)  ← PE=19.7, ROE=19.9%, 增长 54%
   消息面：59 (权重 25%)   ← 43 亿回购 + 业务扩张
   时政面：70 (权重 20%)   ← 新能源政策支持
   国际形势：65 (权重 15%) ← 中美关系缓和 + 全球市场份额 37%
```

## 🔧 自定义配置

### 修改权重

编辑 `comprehensive_analyzer.py`:

```python
self.weights = {
    'fundamental': 0.40,    # 调整基本面权重
    'news': 0.25,           # 调整消息面权重
    'policy': 0.20,         # 调整时政面权重
    'geopolitics': 0.15     # 调整国际形势权重
}
```

### 添加新的数据源

1. 在 `download_policy_data.py` 或 `download_geopolitics_data.py` 中添加新的 API 调用
2. 更新 `comprehensive_analyzer.py` 中的数据加载逻辑
3. 调整评分算法

## 📝 数据说明

### 政策数据

- **宏观政策**: 央行降准、财政政策、GDP 目标等
- **行业政策**: 产业扶持、税收优惠、监管政策等

### 国际形势数据

- **中美关系**: 贸易磋商、科技对话、关税政策
- **全球经济**: 美联储利率、汇率、大宗商品
- **地缘政治**: 中东局势、俄乌冲突、一带一路
- **行业竞争**: 全球市场份额、技术封锁、反补贴调查

## ⚠️ 注意事项

1. **数据时效性**: 政策数据每日更新，建议在凌晨运行
2. **备用数据**: 如果 API 获取失败，系统会自动使用模拟数据
3. **评分参考**: 综合评分仅供参考，不构成投资建议
4. **风险提示**: 投资有风险，决策需谨慎

## 📞 技术支持

如有问题，请查看：
- 日志文件：`logs/` 目录
- 数据文件：`data/policy/` 和 `data/geopolitics/`
- 报告文件：`reports/comprehensive/`

---

**版本**: v1.0  
**创建日期**: 2026-03-09  
**最后更新**: 2026-03-09
