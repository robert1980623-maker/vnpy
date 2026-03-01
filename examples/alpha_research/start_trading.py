#!/usr/bin/env python3
"""
选股策略系统 - 快速启动脚本

用法:
    python3 start_trading.py --mode paper     # 模拟交易
    python3 start_trading.py --mode live      # 实盘交易 (手动确认)
    python3 start_trading.py --mode auto      # 自动化交易
"""

import argparse
import yaml
import sys
from pathlib import Path
from datetime import datetime


def load_config(config_file: str) -> dict:
    """加载配置文件"""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"❌ 配置文件不存在：{config_file}")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def check_environment(config: dict) -> bool:
    """检查运行环境"""
    print("=" * 70)
    print(" " * 25 + "系统环境检查")
    print("=" * 70)
    
    # 检查数据目录
    data_dir = config.get('data', {}).get('data_dir', './data/akshare/bars')
    if not Path(data_dir).exists():
        print(f"❌ 数据目录不存在：{data_dir}")
        print("   请先下载数据：python3 download_optimized.py --max 50 --cache")
        return False
    
    stock_count = len(list(Path(data_dir).glob('*.csv')))
    print(f"✅ 数据目录：{data_dir}")
    print(f"   股票数量：{stock_count}")
    
    if stock_count < 10:
        print("⚠️  数据量较少，建议下载更多股票")
    
    # 检查日志目录
    log_dir = Path(config.get('logging', {}).get('file', 'logs/trading.log')).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 日志目录：{log_dir}")
    
    # 检查报告目录
    report_dir = Path('reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 报告目录：{report_dir}")
    
    print("=" * 70)
    return True


def show_config_summary(config: dict, mode: str):
    """显示配置摘要"""
    print()
    print("=" * 70)
    print(" " * 25 + "交易配置摘要")
    print("=" * 70)
    
    account = config.get('account', {})
    strategy = config.get('strategy', {})
    trading = config.get('trading', {})
    risk = config.get('risk_control', {})
    
    print(f"交易模式：{mode.upper()}")
    print(f"初始资金：¥{account.get('initial_capital', 0):,.0f}")
    print()
    print("策略配置:")
    print(f"  策略名称：{strategy.get('name', 'value')}")
    print(f"  最大 PE: {strategy.get('max_pe', 20)}")
    print(f"  最小 ROE: {strategy.get('min_roe', 10)}%")
    print(f"  最小股息率：{strategy.get('min_dividend_yield', 2.0)}%")
    print(f"  最大持仓：{strategy.get('max_positions', 30)} 只")
    print()
    print("交易参数:")
    print(f"  单只仓位：{trading.get('position_size', 0.03) * 100}%")
    print(f"  调仓周期：{trading.get('rebalance_days', 20)} 天")
    print(f"  手续费率：{trading.get('commission_rate', 0.0003) * 10000:.1f}万")
    print(f"  手动确认：{'✅ 开启' if trading.get('manual_confirm', True) else '❌ 关闭'}")
    print()
    print("风险控制:")
    print(f"  日最大亏损：{risk.get('max_daily_loss', 0.02) * 100}%")
    print(f"  单只止损：{risk.get('stop_loss', 0.10) * 100}%")
    print(f"  最大仓位：{risk.get('max_position_ratio', 0.95) * 100}%")
    print("=" * 70)
    print()


def start_paper_trading(config: dict):
    """启动模拟交易"""
    print("🚀 启动模拟交易...")
    print()
    
    # 调用 paper_trading.py
    import subprocess
    result = subprocess.run(
        ['python3', 'paper_trading.py', '--config', 'config/paper_config.yaml'],
        cwd=Path(__file__).parent
    )
    
    sys.exit(result.returncode)


def start_live_trading(config: dict):
    """启动实盘交易"""
    print("⚠️  警告：即将启动实盘交易！")
    print()
    
    # 检查配置
    broker = config.get('broker', {})
    if not broker.get('account') or broker['account'] == 'your_account':
        print("❌ 请先配置券商账户信息！")
        print("   编辑文件：config/live_config.yaml")
        print("   设置 broker.account, broker.password, broker.api_key")
        sys.exit(1)
    
    # 确认手动确认已开启
    trading = config.get('trading', {})
    if not trading.get('manual_confirm', True):
        print("⚠️  警告：手动确认已关闭！")
        print("   建议首次实盘开启 manual_confirm: true")
        print()
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            print("已取消")
            sys.exit(0)
    
    print("🚀 启动实盘交易...")
    print()
    
    import subprocess
    result = subprocess.run(
        ['python3', 'paper_trading.py', '--config', 'config/live_config.yaml'],
        cwd=Path(__file__).parent
    )
    
    sys.exit(result.returncode)


def start_auto_trading(config: dict):
    """启动自动化交易"""
    print("⚠️  ⚠️  ⚠️  警告：即将启动自动化交易！")
    print()
    print("请确认以下条件:")
    print("  1. ✅ 模拟交易运行 2 周以上")
    print("  2. ✅ 小资金实盘测试 2 周以上")
    print("  3. ✅ 确认策略稳定有效")
    print("  4. ✅ 设置好所有风险控制参数")
    print("  5. ✅ 配置好告警通知")
    print()
    
    response = input("是否确认继续？(yes/no): ")
    if response.lower() != 'yes':
        print("已取消")
        sys.exit(0)
    
    print("🚀 启动自动化交易...")
    print()
    
    import subprocess
    result = subprocess.run(
        ['python3', 'paper_trading.py', '--config', 'config/auto_config.yaml'],
        cwd=Path(__file__).parent
    )
    
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description='选股策略系统启动脚本')
    parser.add_argument('--mode', type=str, required=True, 
                        choices=['paper', 'live', 'auto'],
                        help='交易模式：paper(模拟), live(实盘), auto(自动化)')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径 (可选)')
    
    args = parser.parse_args()
    
    # 确定配置文件
    if args.config:
        config_file = args.config
    else:
        config_map = {
            'paper': 'config/paper_config.yaml',
            'live': 'config/live_config.yaml',
            'auto': 'config/auto_config.yaml'
        }
        config_file = config_map[args.mode]
    
    # 加载配置
    config = load_config(config_file)
    if not config:
        sys.exit(1)
    
    # 检查环境
    if not check_environment(config):
        sys.exit(1)
    
    # 显示配置摘要
    show_config_summary(config, args.mode)
    
    # 启动交易
    if args.mode == 'paper':
        start_paper_trading(config)
    elif args.mode == 'live':
        start_live_trading(config)
    elif args.mode == 'auto':
        start_auto_trading(config)


if __name__ == '__main__':
    main()
