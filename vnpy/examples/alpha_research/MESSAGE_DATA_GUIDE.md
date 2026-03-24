# 消息面数据获取指南

## 📊 消息面数据类型

| 类型 | 说明 | 用途 | 状态 |
|------|------|------|------|
| **个股新闻** | 个股相关新闻 | 舆情分析、事件驱动 | ✅ 可用 |
| **个股公告** | 公司官方公告 | 重大事项、财报 | ⚠️ 需特定接口 |
| **财经新闻** | 宏观/行业新闻 | 市场情绪分析 | ✅ 可用 |
| **个股资讯** | 股票基本信息 | 基本面分析 | ✅ 可用 |
| **龙虎榜** | 营业部交易数据 | 主力资金追踪 | ✅ 可用 |
| **机构调研** | 机构调研记录 | 机构关注度 | ✅ 可用 |
| **研报数据** | 券商研究报告 | 盈利预测、评级 | ✅ 可用 |
| **主力持仓** | 基金/机构持仓 | 资金面分析 | ⚠️ 部分可用 |

---

## 🚀 快速开始

### 获取所有消息面数据

```bash
cd ~/projects/vnpy/examples/alpha_research
source ../../venv/bin/activate
python get_message_data.py
```

---

## 📋 详细接口说明

### 1. 个股新闻 ⭐⭐⭐⭐⭐

**用途**: 获取个股相关新闻，用于舆情分析、事件驱动策略。

**接口**: `ak.stock_news_em(symbol)`

**示例**:
```python
import akshare as ak

# 获取平安银行新闻
df = ak.stock_news_em(symbol="000001")
print(df.head())
```

**字段说明**:
- `新闻标题`: 新闻标题
- `发布时间`: 发布时间
- `新闻来源`: 新闻来源
- `新闻内容`: 新闻摘要
- `新闻链接`: 原文链接

**参数**:
- `symbol`: 股票代码 (6 位数字)

---

### 2. 龙虎榜数据 ⭐⭐⭐⭐⭐

**用途**: 追踪主力资金动向，识别热门股票。

**接口**: `ak.stock_lhb_detail_em(start_date, end_date)`

**示例**:
```python
import akshare as ak
from datetime import datetime, timedelta

# 获取最近 7 天龙虎榜
end_date = datetime.now().strftime("%Y%m%d")
start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
print(df.head())
```

**字段说明**:
- `交易日期`: 交易日期
- `股票代码`: 股票代码
- `股票名称`: 股票名称
- `收盘价`: 收盘价
- `涨跌幅`: 涨跌幅
- `成交额`: 总成交额
- `买入净额`: 买入净额
- `营业部名称`: 营业部名称

**参数**:
- `start_date`: 开始日期 (YYYYMMDD)
- `end_date`: 结束日期 (YYYYMMDD)

---

### 3. 机构调研 ⭐⭐⭐⭐

**用途**: 了解机构关注度，识别被机构调研的股票。

**接口**: 
- `ak.stock_jgdy_em(start_date, end_date)` - 全部
- `ak.stock_jgdy_detail_em(symbol)` - 个股

**示例**:
```python
import akshare as ak

# 获取全部机构调研
df = ak.stock_jgdy_em(start_date="20240101", end_date="20241231")
print(df.head())

# 获取个股机构调研
df = ak.stock_jgdy_detail_em(symbol="000001")
print(df.head())
```

**字段说明**:
- `接待机构数量`: 接待机构数量
- `接待方式`: 调研方式 (现场/电话等)
- `接待地点`: 调研地点
- `接待人员`: 公司接待人员
- `机构类型`: 机构类型 (基金/券商等)

---

### 4. 研报数据 ⭐⭐⭐⭐⭐

**用途**: 获取券商研究报告，了解盈利预测和评级。

**接口**: `ak.stock_research_report_em(symbol)`

**示例**:
```python
import akshare as ak

# 获取个股研报
df = ak.stock_research_report_em(symbol="000001")
print(df.head())
```

**字段说明**:
- `股票代码`: 股票代码
- `股票简称`: 股票简称
- `报告名称`: 报告标题
- `东财评级`: 评级 (买入/增持/中性等)
- `机构`: 发布机构
- `2025-盈利预测 - 收益`: 盈利预测
- `2025-盈利预测 - 市盈率`: 预测 PE
- `报告 PDF 链接`: PDF 下载链接

**测试结果**:
```
✓ 成功：获取到 224 条研报
最新研报:
  平安银行 2025 年三季报点评：三季度息差阶段企稳，资产质量总体平稳
  评级：买入
  机构：东兴证券
```

---

### 5. 个股基本信息 ⭐⭐⭐⭐

**用途**: 获取股票基本资料。

**接口**: `ak.stock_individual_info_em(symbol)`

**示例**:
```python
import akshare as ak

# 获取股票基本信息
df = ak.stock_individual_info_em(symbol="000001")
print(df)
```

**字段说明**:
- `公司代码`: 公司代码
- `公司名称`: 公司名称
- `成立日期`: 成立日期
- `上市日期`: 上市日期
- `注册资本`: 注册资本
- `法人代表`: 法人代表
- `董事会秘书`: 董秘
- `注册地址`: 注册地址
- `经营范围`: 经营范围

---

### 6. 主力持仓 ⭐⭐⭐

**用途**: 了解基金和机构持仓情况。

**接口**: 
- `ak.stock_report_fund_hold(symbol)` - 个股
- `ak.fund_portfolio_hold_em()` - 基金持仓

**示例**:
```python
import akshare as ak

# 获取基金持仓
df = ak.fund_portfolio_hold_em(symbol="000001")
print(df.head())
```

**字段说明**:
- `基金代码`: 基金代码
- `基金名称`: 基金名称
- `持仓股票代码`: 持仓股票
- `持仓市值`: 持仓市值
- `占净值比`: 占净值比例

---

## 🎯 实战应用

### 应用 1: 舆情监控

```python
def monitor_stock_news(symbol, days=7):
    """监控股票最近 N 天的新闻"""
    from datetime import datetime, timedelta
    
    # 获取新闻
    df = ak.stock_news_em(symbol=symbol)
    
    # 筛选最近 N 天
    df['发布时间'] = pd.to_datetime(df['发布时间'])
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_news = df[df['发布时间'] >= cutoff_date]
    
    print(f"最近{days}天新闻数量：{len(recent_news)}")
    
    # 情感分析（简单版）
    positive_words = ['增长', '盈利', '利好', '突破', '创新高']
    negative_words = ['下跌', '亏损', '利空', '违规', '调查']
    
    positive_count = sum(1 for news in recent_news['新闻内容'] 
                        if any(word in news for word in positive_words))
    negative_count = sum(1 for news in recent_news['新闻内容'] 
                        if any(word in news for word in negative_words))
    
    print(f"正面新闻：{positive_count}")
    print(f"负面新闻：{negative_count}")
    
    return recent_news
```

---

### 应用 2: 龙虎榜选股

```python
def select_from_billboard(days=5):
    """从龙虎榜选股"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    # 获取龙虎榜
    df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
    
    # 筛选：机构买入 > 卖出
    df['买入净额'] = pd.to_numeric(df['买入净额'], errors='coerce')
    net_buy = df.groupby('股票代码')['买入净额'].sum()
    
    # 排序
    top_stocks = net_buy.nlargest(10)
    
    print("机构净买入前 10:")
    print(top_stocks)
    
    return top_stocks
```

---

### 应用 3: 研报评级统计

```python
def analyze_research_reports(symbol):
    """分析个股研报评级"""
    df = ak.stock_research_report_em(symbol=symbol)
    
    # 统计评级
    rating_counts = df['东财评级'].value_counts()
    
    print(f"研报总数：{len(df)}")
    print("\n评级分布:")
    print(rating_counts)
    
    # 计算平均预测
    if '2025-盈利预测 - 收益' in df.columns:
        avg_eps = df['2025-盈利预测 - 收益'].mean()
        avg_pe = df['2025-盈利预测 - 市盈率'].mean()
        print(f"\n2025 年平均预测:")
        print(f"  EPS: {avg_eps:.2f}")
        print(f"  PE: {avg_pe:.2f}")
    
    return rating_counts
```

---

### 应用 4: 机构调研热度

```python
def track_institution_survey(days=30):
    """追踪机构调研热度"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    # 获取调研数据
    df = ak.stock_jgdy_em(start_date=start_date, end_date=end_date)
    
    # 统计接待机构数量
    survey_count = df.groupby('股票代码')['接待机构数量'].sum()
    
    # 排序
    hot_stocks = survey_count.nlargest(20)
    
    print(f"最近{days}天机构调研热度前 20:")
    print(hot_stocks)
    
    return hot_stocks
```

---

## 📊 数据保存

```python
def save_message_data(symbol="000001", output_dir="./message_data"):
    """保存消息面数据到文件"""
    from pathlib import Path
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"保存 {symbol} 的消息面数据...")
    
    # 1. 新闻
    news_df = ak.stock_news_em(symbol=symbol)
    if news_df is not None:
        news_df.to_csv(output_dir / f"{symbol}_news.csv", index=False)
        print(f"  ✓ 新闻：{len(news_df)} 条")
    
    # 2. 研报
    report_df = ak.stock_research_report_em(symbol=symbol)
    if report_df is not None:
        report_df.to_csv(output_dir / f"{symbol}_research.csv", index=False)
        print(f"  ✓ 研报：{len(report_df)} 条")
    
    # 3. 机构调研
    survey_df = ak.stock_jgdy_detail_em(symbol=symbol)
    if survey_df is not None:
        survey_df.to_csv(output_dir / f"{symbol}_survey.csv", index=False)
        print(f"  ✓ 调研：{len(survey_df)} 条")
    
    # 4. 基本信息
    info_df = ak.stock_individual_info_em(symbol=symbol)
    if info_df is not None:
        info_df.to_csv(output_dir / f"{symbol}_info.csv", index=False)
        print(f"  ✓ 基本信息：已保存")
    
    print(f"\n数据已保存到：{output_dir}")
```

---

## 🛠️ 故障排查

### 问题 1: 接口返回空数据

**原因**: 
- 股票代码错误
- 时间范围无数据
- 接口限流

**解决**:
```python
# 检查股票代码格式
symbol = "000001"  # 6 位数字

# 扩大时间范围
start_date = "20240101"
end_date = "20241231"

# 稍后重试
time.sleep(5)
```

---

### 问题 2: 连接失败

**原因**: AKShare 限流

**解决**:
```python
# 使用 proxy-patch
import akshare_proxy_patch
akshare_proxy_patch.install_patch("101.201.173.125", "", 30)

import akshare as ak
```

---

### 问题 3: 数据格式错误

**原因**: 字段类型转换问题

**解决**:
```python
# 转换数值类型
df['买入净额'] = pd.to_numeric(df['买入净额'], errors='coerce')

# 转换日期
df['发布时间'] = pd.to_datetime(df['发布时间'], errors='coerce')
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `get_message_data.py` | 消息面数据获取脚本 ⭐ |
| `MESSAGE_DATA_GUIDE.md` | 本文档 |

---

## 🌐 相关资源

- **AKShare 文档**: https://akshare.akfamily.xyz/
- **东方财富网**: https://www.eastmoney.com/
- **巨潮资讯**: http://www.cninfo.com.cn/

---

## ✅ 总结

**推荐使用的消息面数据**:

| 数据类型 | 推荐度 | 稳定性 | 用途 |
|----------|--------|--------|------|
| **研报数据** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 盈利预测、评级 |
| **龙虎榜** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 主力资金追踪 |
| **个股新闻** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 舆情分析 |
| **机构调研** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 机构关注度 |
| **个股资讯** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 基本面分析 |
| **主力持仓** | ⭐⭐⭐ | ⭐⭐⭐ | 资金面分析 |

**使用建议**:
1. 优先使用研报和龙虎榜数据（最稳定）
2. 结合多个数据源综合判断
3. 定期更新数据（每天/每周）
4. 保存历史数据用于回测

---

**状态**: ✅ 消息面数据获取脚本已创建，可正常使用 [耶]
