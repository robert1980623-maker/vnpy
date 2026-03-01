# 数据下载指南

## 📥 下载股票数据

### 基本用法

```bash
# 小批量下载（默认 5 只股票）
python download_data_akshare.py

# 下载沪深 300 成分股（最多 10 只）
python download_data_akshare.py --max 10

# 下载指定指数成分股
python download_data_akshare.py --index 000016  # 上证 50
```

### 完整参数

```bash
python download_data_akshare.py \
  --index 000300 \           # 指数代码 (默认：000300 沪深 300)
  --start 20240101 \         # 开始日期 (默认：20240101)
  --end 20241231 \           # 结束日期 (默认：20241231)
  --max 5 \                  # 最大下载数量 (默认：5)
  --cache ./cache \          # 缓存目录 (默认：./cache)
  --night-mode               # 夜间下载模式
```

---

## 🌙 夜间下载模式

**推荐使用！** 夜间（22:00-06:00）服务器负载低，下载成功率更高。

```bash
# 夜间模式：更长延迟，避免限流
python download_data_akshare.py --night-mode --max 10
```

**夜间模式特点**:
- 每 2 只股票休息 8-12 秒（普通模式：每 3 只休息 3-5 秒）
- 更适合批量下载
- 降低被限流风险

---

## 💾 缓存系统

### 自动缓存

下载的数据会自动保存到 `./cache` 目录：

```
./cache/
├── bars_000001_SZ.csv          # K 线数据
├── fundamental_000001_SZ.json  # 财务数据
└── cache_meta.json             # 缓存元数据
```

### 使用缓存

第二次运行时自动使用缓存：

```bash
# 首次下载
python download_data_akshare.py --max 5
# 输出：下载 000001.SZ... ✓ K 线数据：242 条

# 再次运行（自动使用缓存）
python download_data_akshare.py --max 5
# 输出：下载 000001.SZ... ✓ 从缓存加载 000001.SZ
```

### 不使用缓存

```bash
# 强制重新下载
python download_data_akshare.py --no-cache --max 5
```

---

## 📊 下载策略推荐

### 策略 1: 小批量测试（推荐）

```bash
# 每天下载 5 只股票，测试功能
python download_data_akshare.py --max 5
```

### 策略 2: 夜间批量下载

```bash
# 晚上 10 点开始，下载 20 只股票
python download_data_akshare.py --night-mode --max 20
```

### 策略 3: 分批下载

```bash
# 第 1 天：下载前 10 只
python download_data_akshare.py --max 10

# 第 2 天：继续下载（使用缓存）
python download_data_akshare.py --max 20
```

---

## 🔧 常见问题

### Q: AKShare 连接失败怎么办？

**A**: 使用以下方法：

1. **使用缓存**（最快）
   ```bash
   python download_data_akshare.py  # 自动使用缓存
   ```

2. **夜间下载**（成功率高）
   ```bash
   python download_data_akshare.py --night-mode
   ```

3. **减少数量**（降低限流风险）
   ```bash
   python download_data_akshare.py --max 3
   ```

4. **使用模拟数据**（开发测试）
   ```bash
   python generate_mock_data.py
   ```

### Q: 缓存目录在哪里？

**A**: 默认在 `./cache`，可以通过 `--cache` 参数修改：

```bash
python download_data_akshare.py --cache /path/to/cache
```

### Q: 如何清空缓存？

**A**: 删除缓存目录或使用 `--no-cache`:

```bash
# 方法 1: 删除目录
rm -rf ./cache

# 方法 2: 不使用缓存
python download_data_akshare.py --no-cache
```

---

## 📁 输出数据格式

### K 线数据 (CSV)

```csv
vt_symbol,datetime,open_price,high_price,low_price,close_price,volume,turnover
000001.SZ,2024-01-02,10.5,10.8,10.3,10.7,1000000,10700000
```

### 财务数据 (JSON)

```json
{
  "000001.SZ": {
    "2024-03-01": {
      "vt_symbol": "000001.SZ",
      "report_date": "2024-03-01",
      "pe_ratio": 10.5,
      "pb_ratio": 1.2,
      "dividend_yield": 2.5
    }
  }
}
```

---

## 🚀 下一步

下载完成后，运行回测：

```bash
# 使用下载的数据回测
python run_backtest.py --data ./data/akshare

# 或使用模拟数据回测
python run_backtest.py --data ./data/mock
```

---

**提示**: 建议先用模拟数据测试流程，再用真实数据回测。

```bash
# 1. 生成模拟数据（快速）
python generate_mock_data.py

# 2. 测试回测
python test_simple_backtest.py

# 3. 下载真实数据（夜间）
python download_data_akshare.py --night-mode --max 10

# 4. 真实数据回测
python run_backtest.py --data ./data/akshare
```
