# AKShare 依赖管理指南

## 📦 当前环境状态

### 已安装版本
```bash
AKShare 版本：1.18.30 (最新版)
Python 版本：3.14.3
依赖检查：✓ 无冲突
```

### 检查命令
```bash
# 查看 AKShare 版本
source ~/projects/vnpy/venv/bin/activate
python -c "import akshare; print('AKShare 版本:', akshare.__version__)"

# 检查依赖冲突
pip check

# 查看已安装版本
pip show akshare
```

---

## 🔧 升级 AKShare

### 方法 1: 标准升级

```bash
source ~/projects/vnpy/venv/bin/activate
pip install --upgrade akshare
```

### 方法 2: 强制升级（忽略缓存）

```bash
source ~/projects/vnpy/venv/bin/activate
pip install --upgrade --no-cache-dir akshare
```

### 方法 3: 升级到指定版本

```bash
source ~/projects/vnpy/venv/bin/activate
pip install akshare==1.18.30
```

### 方法 4: 从 GitHub 安装（开发版）

```bash
source ~/projects/vnpy/venv/bin/activate
pip install git+https://github.com/akfamily/akshare.git
```

---

## 🩺 诊断流程

### Step 1: 检查版本

```bash
python -c "import akshare; print(akshare.__version__)"
```

**期望**: 1.18.30 或更高

---

### Step 2: 检查依赖冲突

```bash
pip check
```

**期望**: `No broken requirements found.`

---

### Step 3: 测试基础接口

```bash
python diagnose_akshare.py
```

**期望**: 至少有一个接口成功

---

### Step 4: 测试单一股票下载

```bash
# 单只股票测试
source ~/projects/vnpy/venv/bin/activate
cd ~/projects/vnpy/examples/alpha_research
PYTHONPATH=../.. python -c "
import akshare as ak
df = ak.stock_zh_a_hist(symbol='000001', period='daily', start_date='20240101', end_date='20240131')
print(f'成功获取 {len(df)} 条数据')
print(df.head())
"
```

---

## 📋 常见问题排查

### 问题 1: 接口调用失败

**症状**: `RemoteDisconnected` 或 `Connection aborted`

**排查步骤**:

```bash
# 1. 检查版本
python -c "import akshare; print(akshare.__version__)"

# 2. 重新安装
pip uninstall akshare -y
pip install akshare

# 3. 清除缓存后重试
pip install --upgrade --no-cache-dir akshare
```

---

### 问题 2: 模块导入错误

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:

```bash
# 重新安装依赖
pip install -r ~/projects/vnpy/requirements.txt

# 或单独安装缺失的模块
pip install <missing-module>
```

---

### 问题 3: 数据格式变更

**症状**: 列名不匹配或数据结构变化

**解决**:

```bash
# 1. 升级到最新版
pip install --upgrade akshare

# 2. 查看接口文档
python -c "import akshare as ak; help(ak.stock_zh_a_hist)"

# 3. 检查返回数据
python -c "
import akshare as ak
df = ak.stock_zh_a_hist(symbol='000001')
print('列名:', df.columns.tolist())
print('数据类型:')
print(df.dtypes)
"
```

---

### 问题 4: 虚拟环境问题

**症状**: 系统 Python 和虚拟环境版本不一致

**解决**:

```bash
# 1. 确认使用虚拟环境
which python
# 应该显示：/Users/rowang/projects/vnpy/venv/bin/python

# 2. 重新创建虚拟环境（最后手段）
cd ~/projects/vnpy
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📊 依赖版本兼容性

### 核心依赖

| 库 | 最低版本 | 推荐版本 | 说明 |
|----|----------|----------|------|
| akshare | 1.15.0 | 1.18.30+ | 数据下载 |
| pandas | 2.0.0 | 2.2.0+ | 数据处理 |
| numpy | 1.24.0 | 1.26.0+ | 数值计算 |
| requests | 2.28.0 | 2.31.0+ | HTTP 请求 |
| baostock | 0.8.8 | 0.8.15+ | 备选数据源 |

---

### 检查依赖版本

```bash
# 查看所有已安装的包
pip list

# 查看特定包的版本
pip show akshare pandas numpy requests

# 检查过期的包
pip list --outdated
```

---

## 🔄 完整升级流程

### 安全升级（推荐）

```bash
# 1. 备份当前环境
cd ~/projects/vnpy
pip freeze > requirements_backup.txt

# 2. 升级 pip
source venv/bin/activate
pip install --upgrade pip

# 3. 升级 AKShare
pip install --upgrade akshare

# 4. 验证升级
python -c "import akshare; print('版本:', akshare.__version__)"

# 5. 测试基础功能
python examples/alpha_research/diagnose_akshare.py
```

---

### 完整重装（问题严重时）

```bash
# 1. 删除虚拟环境
cd ~/projects/vnpy
rm -rf venv

# 2. 重新创建
python3 -m venv venv
source venv/bin/activate

# 3. 升级 pip
pip install --upgrade pip

# 4. 安装依赖
pip install -r requirements.txt

# 5. 验证安装
python -c "import akshare; print('AKShare:', akshare.__version__)"
```

---

## 📝 最佳实践

### 1. 定期检查更新

```bash
# 每月检查一次
pip list --outdated
```

### 2. 使用 requirements.txt

```bash
# 固定依赖版本
echo "akshare>=1.18.0" >> requirements.txt
echo "pandas>=2.0.0" >> requirements.txt

# 安装固定版本
pip install -r requirements.txt
```

### 3. 测试后再升级

```bash
# 1. 在测试环境先升级
python -m venv test_env
source test_env/bin/activate
pip install akshare

# 2. 测试功能
python test_script.py

# 3. 确认无误后升级主环境
```

### 4. 记录版本变更

```bash
# 记录升级日志
echo "$(date): 升级 akshare 1.18.20 -> 1.18.30" >> upgrade_log.txt
```

---

## 🌐 相关资源

- **AKShare GitHub**: https://github.com/akfamily/akshare
- **AKShare 文档**: https://akshare.akfamily.xyz/
- **PyPI 页面**: https://pypi.org/project/akshare/
- **更新日志**: https://github.com/akfamily/akshare/releases

---

## 📞 获取帮助

### 查看接口帮助

```bash
python -c "import akshare as ak; help(ak.stock_zh_a_hist)"
```

### 查看版本信息

```bash
python -c "import akshare; print(akshare.__version__)"
python -c "import akshare; ak.show_progress()"
```

### 报告问题

如果遇到接口问题，可以：

1. 查看 GitHub Issues
2. 检查是否已有类似问题
3. 提供详细的错误信息和版本信息

---

**当前状态**: ✅ AKShare 1.18.30 (最新版)，无依赖冲突

**建议**: 版本已是最新，问题可能来自服务器限流，建议使用模拟数据或夜间下载模式。
