# Baostock 备选数据源使用指南

## ✅ 安装完成

```bash
Baostock 版本：00.8.90
安装时间：2026-03-01
状态：✓ 已安装并可用
```

---

## 📊 数据源对比

| 特性 | AKShare | Baostock |
|------|---------|----------|
| **数据源** | 东方财富等 | 上交所/深交所 |
| **稳定性** | ⭐⭐⭐ (可能限流) | ⭐⭐⭐⭐⭐ (官方数据) |
| **速度** | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **数据质量** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **复权支持** | ✓ | ✓ |
| **财务数据** | ✓ | 有限 |
| **指数成分股** | ✓ | ✓ (沪深 300) |

---

## 🔄 自动切换机制

下载脚本已配置自动切换：

```python
# 1. 首先尝试 AKShare
bars = get_stock_bars_akshare(vt_symbol, start_date, end_date)

# 2. 如果失败，自动切换到 Baostock
if bars is None:
    print("  尝试 Baostock...")
    bars = get_stock_bars_baostock(vt_symbol, start_date, end_date)
```

**你不需要手动选择**，脚本会自动使用可用的数据源！

---

## 🚀 使用方法

### 基本用法

```bash
# 自动选择数据源（推荐）
python download_data_akshare.py --max 5
```

### 强制使用 Baostock

如果需要专门测试 Baostock：

```bash
# 测试 Baostock 连接
python test_baostock.py

# 下载脚本会自动使用 Baostock（当 AKShare 失败时）
python download_data_akshare.py --max 3
```

---

## 📋 Baostock 支持的数据

### 1. K 线数据 ✓

```python
import baostock as bs

# 登录
bs.login()

# 获取日线数据（前复权）
rs = bs.query_history_k_data_plus(
    "sh.600000",
    "date,open,high,low,close,volume,amount",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="d",
    adjustflag="3"  # 前复权
)

# 登出
bs.logout()
```

**支持的频率**:
- `d` - 日线
- `w` - 周线
- `m` - 月线
- `5` - 5 分钟
- `15` - 15 分钟
- `30` - 30 分钟
- `60` - 60 分钟

---

### 2. 指数成分股 ✓

```python
# 获取沪深 300 成分股
rs = bs.query_hs300_stocks()

# 获取上证 50 成分股
rs = bs.query_sz50_stocks()

# 获取中证 500 成分股
rs = bs.query_zz500_stocks()
```

---

### 3. 股票基本信息 ✓

```python
# 获取股票基本信息
rs = bs.query_stock_basic("sh.600000")
```

---

### 4. 财务数据 ⚠️

Baostock 的财务数据有限，主要使用 AKShare 获取。

---

## 🎯 代码格式转换

### 股票代码格式

| 格式 | AKShare | Baostock |
|------|---------|----------|
| 浦发银行 | `600000` | `sh.600000` |
| 平安银行 | `000001` | `sz.000001` |
| 沪深 300 | `000300` | (指数接口) |

**下载脚本已自动处理格式转换**，你只需要使用标准格式：
```python
vt_symbol = "600000.SH"  # 或 "000001.SZ"
```

---

### 日期格式

| 格式 | AKShare | Baostock |
|------|---------|----------|
| 标准格式 | `20240101` | `2024-01-01` |

**下载脚本已自动处理格式转换**。

---

## 📊 测试流程

### 测试 Baostock 连接

```bash
cd ~/projects/vnpy/examples/alpha_research
source ../../venv/bin/activate
python test_baostock.py
```

**期望输出**:
```
✓ 登录成功
✓ 成功获取 22 条数据 (K 线测试)
✓ 成功获取基本信息
✓ 成功获取 300 只成分股 (沪深 300)
✓ 已登出
```

---

### 测试自动切换

```bash
# 下载 3 只股票（观察数据源切换）
python download_data_akshare.py --max 3
```

**期望输出**:
```
[1/3] 下载 600000.SH...
  重试 1/3, 等待 5.7 秒...
  ✗ AKShare 失败：Connection aborted
  尝试 Baostock...
  ✓ K 线数据：242 条 (Baostock)
```

---

## 🛠️ 故障排查

### 问题 1: Baostock 登录失败

**症状**: `login failed` 或连接超时

**解决**:
```bash
# 检查网络连接
ping www.baostock.com

# 检查是否安装
pip show baostock

# 重新安装
pip uninstall baostock -y
pip install baostock
```

---

### 问题 2: 日期格式错误

**症状**: `日期格式不正确`

**原因**: Baostock 需要 `YYYY-MM-DD` 格式

**解决**: 下载脚本已自动转换，无需手动处理

---

### 问题 3: 代码格式错误

**症状**: `code error` 或 `no data`

**原因**: Baostock 需要 `sh.600000` 格式

**解决**: 下载脚本已自动转换，使用标准格式即可：
```python
"600000.SH"  # ✓ 正确
"sh.600000"  # ✗ 不需要手动转换
```

---

### 问题 4: 数据为空

**症状**: 获取到 0 条数据

**可能原因**:
1. 日期范围无交易数据
2. 股票代码错误
3. 停牌期间

**解决**:
```bash
# 检查日期范围是否合理
# 检查股票代码是否正确
# 尝试其他股票
```

---

## 📈 最佳实践

### 1. 优先使用 AKShare

```bash
# AKShare 数据更全面（尤其是财务数据）
python download_data_akshare.py --max 5
```

### 2. AKShare 失败时自动切换

脚本会自动检测 AKShare 失败并切换到 Baostock。

### 3. 夜间下载更稳定

```bash
# 凌晨 1 点自动执行（定时任务已设置）
# 两个数据源成功率都更高
```

### 4. 小批量多次下载

```bash
# 每次下载 3-5 只，降低限流风险
python download_data_akshare.py --max 3
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `download_data_akshare.py` | 主下载脚本（支持自动切换） |
| `test_baostock.py` | Baostock 测试脚本 |
| `DEPENDENCY_GUIDE.md` | 依赖管理指南 |
| `DATA_DOWNLOAD.md` | 数据下载完整指南 |

---

## 🌐 相关资源

- **Baostock 官网**: http://baostock.com/
- **Baostock GitHub**: https://github.com/baostock/baostock
- **文档**: http://baostock.com/baostock/index.php/%E9%A6%96%E9%A1%B5
- **论坛**: http://baostock.com/baostock/index.php/%E8%AE%BA%E5%9D%9B

---

## ✅ 总结

**Baostock 优势**:
- ✅ 官方数据源，稳定性高
- ✅ 不易被限流
- ✅ 数据质量好
- ✅ 免费无需 token

**Baostock 局限**:
- ⚠️ 财务数据有限
- ⚠️ 指数成分股支持较少
- ⚠️ 需要格式转换（已自动处理）

**推荐策略**:
1. 默认使用 AKShare（数据全面）
2. AKShare 失败时自动切换到 Baostock
3. 定时任务在凌晨执行（两个数据源都更稳定）

---

**状态**: ✅ Baostock 已安装并集成到下载脚本中 [耶]
