#!/usr/bin/env python3
"""
依赖检查脚本

功能:
- 检查所有必需的依赖是否已安装
- 提供友好的错误提示
- 提供一键安装命令

使用:
    python3 check_dependencies.py
"""

import sys
import subprocess
from pathlib import Path

# 定义依赖包
REQUIRED_PACKAGES = {
    # 核心依赖
    'pandas': '数据处理',
    'numpy': '数值计算',
    'polars': '高性能数据处理',
    'pyyaml': '配置文件解析',
    
    # 数据下载（可选）
    'akshare': 'AKShare 数据源（推荐）',
    'baostock': 'Baostock 数据源（备选）',
    
    # 可视化（可选）
    'matplotlib': '图表绘制',
    'plotly': '交互式图表',
}

# 可选依赖
OPTIONAL_PACKAGES = {
    'tqdm': '进度条显示',
    'loguru': '更好的日志',
    'pytest': '单元测试',
}


def check_package(package_name):
    """检查单个包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def get_install_command():
    """获取安装命令"""
    return "pip3 install pandas numpy polars pyyaml akshare --break-system-packages"


def get_missing_packages(packages):
    """获取缺失的包列表"""
    missing = []
    for package in packages:
        if not check_package(package):
            missing.append(package)
    return missing


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60 + "\n")


def print_status(package_name, status, description=""):
    """打印包状态"""
    icon = "✅" if status else "❌"
    desc = f" - {description}" if description else ""
    print(f"  {icon} {package_name:20} {desc}")


def main():
    """主函数"""
    print_header("vnpy 量化交易系统 - 依赖检查")
    
    # 检查核心依赖
    print("📦 核心依赖:")
    missing_core = get_missing_packages(REQUIRED_PACKAGES.keys())
    
    for package, desc in REQUIRED_PACKAGES.items():
        status = package not in missing_core
        print_status(package, status, desc)
    
    # 检查可选依赖
    print("\n📦 可选依赖:")
    missing_optional = get_missing_packages(OPTIONAL_PACKAGES.keys())
    
    for package, desc in OPTIONAL_PACKAGES.items():
        status = package not in missing_optional
        print_status(package, status, desc)
    
    # 总结
    print("\n" + "-" * 60)
    
    if not missing_core:
        print("✅ 所有核心依赖已安装！")
    else:
        print(f"❌ 缺少 {len(missing_core)} 个核心依赖:")
        for pkg in missing_core:
            print(f"   - {pkg}")
        
        print("\n💡 安装命令:")
        print(f"   {get_install_command()}")
        
        print("\n📖 或查看 QUICKSTART.md 获取详细安装指南")
    
    # 可选依赖提示
    if missing_optional:
        print(f"\n⚠️  缺少 {len(missing_optional)} 个可选依赖（不影响基本功能）:")
        for pkg in missing_optional:
            desc = OPTIONAL_PACKAGES.get(pkg, REQUIRED_PACKAGES.get(pkg, ""))
            print(f"   - {pkg} ({desc})")
    
    print("\n" + "=" * 60)
    
    # 返回状态码
    return 0 if not missing_core else 1


if __name__ == "__main__":
    sys.exit(main())
