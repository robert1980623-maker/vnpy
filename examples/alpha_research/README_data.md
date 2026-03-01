# 数据下载总结

## ✅ 已完成

### 1. 模拟数据生成

**脚本**: `generate_mock_data.py`

**功能**: 生成符合真实格式的模拟股票数据

**运行**:
```bash
cd ~/projects/vnpy
source venv/bin/activate
cd vnpy/examples/alpha_research
python generate_mock_data.py
```

**输出**:
```
✅ 生成 10 只股票
✅ 每只股票 303 条记录（1 年数据）
✅ 数据路径：./data/daily/
```

### 2. 数据验证

**脚本**: `test_data.py`

**功能**: 验证生成的数据质量

**运行**:
```bash
python test_data.py
```

**结果**:
```
✅ 10 只股票
✅ 3,030 条总记录
✅ 数据质量良好
```

---

## 📊 生成的数据

### 数据格式

```
data/daily/
├── 000001.SSE.parquet
├── 000002.SSE.parquet
├── ...
└── 000010.SSE.parquet
```

### 数据字段

| 字段 | 类型 | 说明 |
|------|------|------|
| datetime | datetime | 日期时间 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | int | 成交量 |
| turnover | float | 成交额 |
| vt_symbol | str | 股票代码 |

### 数据特征

- **时间范围**: 2025-01-01 到 2026-02-27
- **股票数量**: 10 只
- **每只股票**: 303 个交易日
- **价格范围**: 随机生成（10-100 元初始）
- **波动率**: 日均 2%

---

## 🌐 真实数据下载选项

### 选项 1: AKShare（免费）

**优点**:
- ✅ 完全免费
- ✅ 无需账号
- ✅ 数据丰富

**缺点**:
- ⚠️ 网络连接不稳定（测试中遇到连接问题）
- ⚠️ 可能有反爬虫限制

**脚本**: `download_standalone.py`

**运行**:
```bash
python download_standalone.py
```

**注意**: 如果 AKShare 连接失败，可能是：
1. 网络问题
2. 请求频率过高被限制
3. AKShare 服务暂时不可用

**解决**:
- 稍后重试
- 减少股票数量
- 添加延时和重试

### 选项 2: RQData（付费）

**优点**:
- ✅ 数据质量高
- ✅ 稳定可靠
- ✅ 完整财务数据

**缺点**:
- ⚠️ 需要付费账号
- ⚠️ 需要配置账号信息

**脚本**: `download_data_rq.py`

**配置**:
```python
RQ_USER = "your_username"
RQ_PASSWORD = "your_password"
```

### 选项 3: Tushare（免费 + 付费）

**优点**:
- ✅ 数据质量好
- ✅ 有免费额度

**缺点**:
- ⚠️ 需要注册获取 token
- ⚠️ 免费额度有限

**安装**:
```bash
pip install tushare
```

**使用**:
```python
import tushare as ts

ts.set_token('your_token')
pro = ts.pro_api()

df = pro.daily(ts_code='000001.SZ', start_date='20250101', end_date='20260228')
```

---

## 🎯 使用模拟数据测试回测

### 步骤

1. **生成模拟数据**
   ```bash
   python generate_mock_data.py
   ```

2. **验证数据**
   ```bash
   python test_data.py
   ```

3. **测试回测**（需要解决 talib 依赖）
   ```bash
   # 方法 1: 安装 ta-lib
   brew install ta-lib
   pip install ta-lib
   
   # 方法 2: 绕过 talib 依赖
   # 修改 vnpy/trader/utility.py，注释掉 talib 导入
   ```

---

## 📝 数据下载脚本对比

| 脚本 | 数据源 | 费用 | 状态 | 推荐 |
|------|--------|------|------|------|
| `generate_mock_data.py` | 模拟生成 | 免费 | ✅ 可用 | ⭐⭐⭐ 测试用 |
| `download_standalone.py` | AKShare | 免费 | ⚠️ 网络问题 | ⭐⭐ 免费数据 |
| `download_data_rq.py` | RQData | 付费 | ✅ 可用 | ⭐⭐⭐⭐ 实盘用 |
| `test_data.py` | 验证工具 | - | ✅ 可用 | ⭐⭐⭐⭐ 必用 |

---

## 🔧 环境配置

### 虚拟环境

```bash
cd ~/projects/vnpy
python3 -m venv venv
source venv/bin/activate
```

### 必需依赖

```bash
pip install polars pandas akshare numpy plotly tqdm
```

### 可选依赖

```bash
# RQData
pip install rqdatac

# Tushare
pip install tushare

# TA-Lib（回测需要）
brew install ta-lib
pip install ta-lib
```

---

## 📖 下一步

### 立即可做

1. ✅ **使用模拟数据** - 测试回测引擎
2. ✅ **验证数据质量** - 运行 test_data.py

### 真实数据

1. **选择数据源**
   - 免费：AKShare 或 Tushare
   - 付费：RQData

2. **下载数据**
   - 按照对应脚本说明

3. **运行回测**
   - 使用真实数据测试策略

---

## 💡 建议

### 测试阶段
- ✅ 使用模拟数据（`generate_mock_data.py`）
- 快速验证功能
- 无需等待下载

### 开发阶段
- ⭐ 使用 AKShare 下载少量股票（10-20 只）
- 测试真实数据格式
- 验证策略逻辑

### 实盘准备
- ⭐⭐ 使用 RQData 或 Tushare
- 下载全市场数据
- 完整回测验证

---

**当前状态**: ✅ 模拟数据已生成，可以开始测试！

[耶]
