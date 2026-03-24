#!/usr/bin/env python3
"""
环境检查脚本

检查所有必需的环境变量和依赖
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """检查环境配置"""
    print("=" * 60)
    print("🔍 VNPY 环境检查")
    print("=" * 60)
    
    # 加载.env 文件
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ .env 文件已加载：{env_file}")
    else:
        print(f"❌ .env 文件不存在：{env_file}")
        return 1
    
    # 检查关键环境变量
    checks = [
        ('TUSHARE_TOKEN', 'Tushare API Token', True),
        ('NEO4J_URI', 'Neo4j 数据库 URI', False),
        ('AKSHARE_PROXY', 'AKShare 代理', False),
    ]
    
    all_ok = True
    for var, description, required in checks:
        value = os.getenv(var)
        if value:
            masked = value[:20] + '...' if len(value) > 20 else value
            print(f"✅ {var}: {masked} ({description})")
        elif required:
            print(f"❌ {var}: 未设置 ({description}) [必需]")
            all_ok = False
        else:
            print(f"⚠️ {var}: 未设置 ({description}) [可选]")
    
    # 检查 Python 依赖
    print("\n📦 Python 依赖检查:")
    required_packages = [
        ('akshare', 'AKShare 数据源'),
        ('tushare', 'Tushare 数据源'),
        ('pandas', '数据处理'),
        ('polars', '高性能数据处理'),
        ('dotenv', '环境变量管理'),
    ]
    
    for pkg, description in required_packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"✅ {pkg}: {description}")
        except ImportError:
            print(f"❌ {pkg}: {description} [未安装]")
            all_ok = False
    
    # 检查虚拟环境
    print("\n🐍 Python 环境:")
    print(f"Python 版本：{sys.version.split()[0]}")
    venv_path = sys.prefix
    print(f"虚拟环境：{venv_path}")
    
    # 检查关键文件
    print("\n📁 关键文件检查:")
    critical_files = [
        'examples/alpha_research/batch_download_enhanced.py',
        'examples/alpha_research/data_source_manager.py',
        'examples/alpha_research/download_data_akshare.py',
        'examples/alpha_research/config/auto_config.yaml',
        '.env',
    ]
    
    for filepath in critical_files:
        full_path = project_root / filepath
        if full_path.exists():
            print(f"✅ {filepath}")
        else:
            print(f"❌ {filepath} [缺失]")
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ 环境检查通过 - 系统就绪")
        print("\n💡 提示：下次运行下载任务前，请先加载环境:")
        print(f"   source {venv_path}/bin/activate")
        return 0
    else:
        print("❌ 环境检查失败 - 请修复上述问题")
        return 1

if __name__ == '__main__':
    sys.exit(check_environment())
