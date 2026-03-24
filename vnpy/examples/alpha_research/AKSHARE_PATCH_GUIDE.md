# akshare-proxy-patch 配置指南

## ✅ 安装完成

```bash
akshare-proxy-patch 版本：0.2.8
安装时间：2026-03-01
状态：✓ 已安装并测试通过
```

---

## 🎯 作用

**akshare-proxy-patch** 是一个 AKShare 补丁，用于解决：

- ✅ AKShare 连接东方财富接口时的限流问题
- ✅ `RemoteDisconnected` 错误
- ✅ `Connection aborted` 错误
- ✅ 接口返回 403/404 错误

**原理**: 自动为东财接口注入代理认证头，绕过限流。

---

## 📦 安装

```bash
# 激活虚拟环境
source ~/projects/vnpy/venv/bin/activate

# 安装补丁
pip install akshare-proxy-patch==0.2.8
```

---

## 🚀 使用方法

### 方法 1: 自动加载（推荐）⭐⭐⭐⭐⭐

下载脚本已自动集成，无需额外配置：

```bash
python download_data_akshare.py --max 5
```

脚本会在导入 AKShare 之前自动加载补丁。

---

### 方法 2: 手动加载

在自己的脚本中使用：

```python
# 1. 先导入补丁（必须在 akshare 之前！）
import akshare_proxy_patch
akshare_proxy_patch.install_patch("101.201.173.125", "", 30)

# 2. 再导入 AKShare
import akshare as ak

# 3. 正常使用
df = ak.stock_zh_a_hist(symbol="000001", period="daily")
```

---

### 方法 3: 使用配置模块

```python
# 导入配置模块（自动安装补丁）
from akshare_patch_config import *

# 然后导入 AKShare
import akshare as ak

# 正常使用
df = ak.stock_zh_a_hist(symbol="000001")
```

---

## ⚙️ 参数说明

```python
akshare_proxy_patch.install_patch(auth_ip, auth_token, retry=30)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| **auth_ip** | `"101.201.173.125"` | 网关地址（固定，不可修改） |
| **auth_token** | `""` | 认证令牌（空字符串使用免费额度） |
| **retry** | `30` | 重试次数（建议保持不变） |

---

## 🔑 AUTH_TOKEN

### 免费使用

```python
# 使用空字符串，每天有一定免费次数
akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
```

### 注册正式 Token（如需更多次数）

1. 访问：https://ak.cheapproxy.net/dashboard/akshare
2. 注册账号
3. 获取 AUTH_TOKEN
4. 替换配置：

```python
akshare_proxy_patch.install_patch("101.201.173.125", "your_token_here", 30)
```

---

## ✅ 测试验证

### 运行测试脚本

```bash
cd ~/projects/vnpy/examples/alpha_research
source ../../venv/bin/activate
python setup_akshare_patch.py
```

### 期望输出

```
✓ akshare-proxy-patch 已加载
✓ 成功：获取到 22 条 K 线
统计：3/3 成功
✓ akshare-proxy-patch 工作正常！
```

---

## 📊 效果对比

### 使用前（无补丁）

```bash
[1/20] 下载 000001.SZ...
  重试 1/3, 等待 5.7 秒...
  重试 2/3, 等待 6.3 秒...
  ✗ AKShare 失败：RemoteDisconnected
```

### 使用后（有补丁）

```bash
[1/20] 下载 000001.SZ...
  ✓ AKShare 成功：242 条数据
```

---

## 🎯 集成到下载脚本

下载脚本已自动集成补丁：

```python
# download_data_akshare.py

# 先加载补丁（在导入 akshare 之前）
try:
    import akshare_proxy_patch
    akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
    print("✓ akshare-proxy-patch 已加载")
except ImportError:
    print("⚠️ akshare-proxy-patch 未安装，将使用原始 AKShare")

# 再导入 AKShare
import akshare as ak

# 正常使用...
```

---

## 🛠️ 故障排查

### 问题 1: 补丁加载失败

**症状**: `install_patch() missing 2 required positional arguments`

**解决**: 确保传入正确的参数：
```python
akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
```

---

### 问题 2: 仍然连接失败

**可能原因**:
1. 免费额度用完
2. 网络问题
3. 补丁版本过旧

**解决**:
```bash
# 1. 检查补丁版本
pip show akshare-proxy-patch

# 2. 重新安装
pip uninstall akshare-proxy-patch -y
pip install akshare-proxy-patch==0.2.8

# 3. 注册正式 Token
# 访问：https://ak.cheapproxy.net/dashboard/akshare
```

---

### 问题 3: 导入顺序错误

**症状**: 补丁不生效

**原因**: 在导入补丁之前已经导入了 akshare

**正确顺序**:
```python
# ✓ 正确
import akshare_proxy_patch
akshare_proxy_patch.install_patch(...)
import akshare as ak

# ✗ 错误
import akshare as ak
import akshare_proxy_patch  # 太晚了！
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `download_data_akshare.py` | 已集成补丁的下载脚本 |
| `setup_akshare_patch.py` | 补丁配置与测试脚本 |
| `akshare_patch_config.py` | 补丁配置模块（可复用） |
| `AKSHARE_PATCH_GUIDE.md` | 本文档 |

---

## 🌐 相关资源

- **GitHub**: https://github.com/helloyie/akshare-proxy-patch
- **PyPI**: https://pypi.org/project/akshare-proxy-patch/
- **注册 Token**: https://ak.cheapproxy.net/dashboard/akshare
- **交流群**: 见 GitHub 页面

---

## 🎯 最佳实践

### 1. 始终先加载补丁

```python
# 在任何使用 AKShare 的脚本顶部添加
import akshare_proxy_patch
akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
```

### 2. 使用下载脚本（已集成）

```bash
# 无需手动配置，脚本自动处理
python download_data_akshare.py --max 5
```

### 3. 结合 Baostock 使用

```python
# 下载脚本会自动选择数据源：
# 1. 优先使用 AKShare + proxy-patch
# 2. 失败时自动切换到 Baostock
# 3. 双重保障
```

### 4. 监控免费额度

如果频繁使用，建议注册正式 Token。

---

## ✅ 总结

**优势**:
- ✅ 解决 AKShare 限流问题
- ✅ 自动注入代理头
- ✅ 无需修改业务代码
- ✅ 每天免费使用一定次数
- ✅ 可选正式 Token

**使用建议**:
1. 始终先加载补丁（在 akshare 之前）
2. 使用下载脚本（已自动集成）
3. 结合 Baostock 作为备选
4. 如需大量使用，注册正式 Token

---

**状态**: ✅ akshare-proxy-patch 已安装并集成到下载脚本中 [耶]
