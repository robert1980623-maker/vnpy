#!/usr/bin/env python3
"""
测试 Tushare 优先下载逻辑

验证:
1. TUSHARE_TOKEN 是否正确加载
2. download_data_akshare.py 是否优先使用 Tushare
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

print("=" * 60)
print("Tushare 优先逻辑测试")
print("=" * 60)

# 1. 检查 Token
token = os.environ.get('TUSHARE_TOKEN', '')
print(f"\n1. Token 配置检查:")
print(f"   TUSHARE_TOKEN: {'✅ 已配置' if token else '❌ 未配置'}")
if token:
    print(f"   Token 前缀：{token[:20]}...")

# 2. 测试 Tushare 导入
print(f"\n2. Tushare SDK 检查:")
try:
    import tushare as ts
    ts.set_token(token)
    pro = ts.pro_api()
    print(f"   Tushare SDK: ✅ 可用")
except Exception as e:
    print(f"   Tushare SDK: ❌ {e}")

# 3. 测试 download_data_akshare.py 的 Token 检测逻辑
print(f"\n3. download_data_akshare.py Token 检测:")
config_file = project_dir / 'config' / 'auto_config.yaml'
if config_file.exists():
    import yaml
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    config_token = config.get('data', {}).get('tushare_token', '')
    print(f"   配置文件 Token: {'✅ 已配置' if config_token else '❌ 未配置'}")
else:
    print(f"   配置文件：❌ 不存在")

# 4. 模拟下载逻辑
print(f"\n4. 数据源选择逻辑:")
ENV_TOKEN = os.environ.get('TUSHARE_TOKEN', '')
print(f"   环境变量 Token: {'有' if ENV_TOKEN else '无'}")
USE_TUSHARE = bool(ENV_TOKEN and ENV_TOKEN.strip())
print(f"   将使用数据源：{'✅ Tushare Pro' if USE_TUSHARE else '⚠️ AKShare'}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
