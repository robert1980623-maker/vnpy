# ⚠️  重要：Neo4j 同步必须在 venv 中执行

## 原因

Neo4j Python 模块安装在 venv 环境中：
- **路径**: `/Users/rowang/projects/vnpy/venv/`
- **模块**: `neo4j` (版本 6.1.0)
- **系统 Python**: ❌ 未安装

## 正确的执行方式

### 方式 1: 激活 venv

```bash
# 激活虚拟环境
source /Users/rowang/projects/vnpy/venv/bin/activate

# 执行同步
python3 sync_agents_to_neo4j.py --auto
```

### 方式 2: 使用 venv 的 Python

```bash
/Users/rowang/projects/vnpy/venv/bin/python3 sync_agents_to_neo4j.py --auto
```

### 方式 3: Cron 任务 (已配置)

```bash
# setup_agent_sync_cron.sh 已配置使用 venv Python
./setup_agent_sync_cron.sh
```

## 错误的执行方式

### ❌ 不要使用系统 Python

```bash
# 错误！会提示 neo4j 模块未安装
python3 sync_agents_to_neo4j.py --auto
```

### ❌ 不要在 venv 外运行

```bash
# 错误！无法导入 neo4j 模块
cd /Users/rowang/projects/vnpy/examples/alpha_research
python3 sync_agents_to_neo4j.py --auto
```

## 检查是否在 venv 中

```bash
# 检查 Python 路径
which python3
# 应该输出：/Users/rowang/projects/vnpy/venv/bin/python3

# 检查是否激活 venv
echo $VIRTUAL_ENV
# 应该输出：/Users/rowang/projects/vnpy/venv
```

## 错误提示

如果看到以下错误，说明不在 venv 中：

```
❌ neo4j 模块未安装
  安装：pip install neo4j
```

**解决方法**: 使用 venv 的 Python

## Cron 配置

Cron 任务已配置为使用 venv Python：

```bash
/Users/rowang/projects/vnpy/venv/bin/python3 /Users/rowang/projects/vnpy/examples/alpha_research/sync_agents_to_neo4j.py --auto
```

## 总结

**记住**: 
- ✅ 总是使用 venv 中的 Python
- ✅ 或者先激活 venv
- ❌ 不要使用系统 Python

**快捷方式**:
```bash
source /Users/rowang/projects/vnpy/venv/bin/activate
python3 sync_agents_to_neo4j.py --auto
```
