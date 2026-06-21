#!/usr/bin/env python3
"""
统一配置加载模块

功能:
- 统一 Tushare Token 加载（从 .env 或环境变量）
- 统一数据源配置加载
- 统一飞书/Telegram 通知 token 加载
- 统一数据目录路径
- 避免各处重复代码

用法:
    from config_loader import (
        get_tushare_token, get_data_source_config,
        get_feishu_config, get_telegram_token, get_data_dir,
    )
"""

import os
from pathlib import Path
from typing import Optional, Dict


# ---------------------------------------------------------------------------
# 统一数据目录常量
# 所有模块应优先使用此常量，避免硬编码路径字符串
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(
    os.environ.get('VNPY_DATA_DIR', '')
).resolve() if os.environ.get('VNPY_DATA_DIR', '').strip() else (
    Path(__file__).parent / 'data' / 'akshare' / 'bars'
)
DATA_DIR_STR: str = str(DATA_DIR)


def get_tushare_token() -> str:
    """
    获取 Tushare Token
    
    优先级:
    1. 环境变量 TUSHARE_TOKEN
    2. .env 文件中的 TUSHARE_TOKEN
    
    Returns:
        str: Tushare Token，未找到返回空字符串
    """
    # 1. 从环境变量
    token = os.environ.get('TUSHARE_TOKEN', '').strip()
    if token:
        return token
    
    # 2. 从 .env 文件（尝试多个可能的位置）
    possible_paths = [
        Path(__file__).parent / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            try:
                for line in open(env_path):
                    line = line.strip()
                    if line.startswith('TUSHARE_TOKEN=') and not line.startswith('#'):
                        token = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if token:
                            print(f"✓ TUSHARE_TOKEN 从 {env_path} 加载")
                            return token
            except Exception:
                pass
    
    return ''


def get_data_source_config() -> Dict:
    """
    获取数据源配置
    
    Returns:
        Dict: 数据源配置
    """
    config = {
        'primary': 'tushare',
        'backup': 'akshare',
        'retry': {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
        },
        'rate_limit': {
            'tushare': 200,  # 每分钟
            'akshare': 60,
        }
    }
    
    # 尝试从配置文件加载
    config_paths = [
        Path(__file__).parent / 'data_source_config.json',
        Path.cwd() / 'data_source_config.json',
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                import json
                with open(config_path) as f:
                    user_config = json.load(f)
                    # 合并配置
                    if 'primary' in user_config:
                        config['primary'] = user_config['primary']
                    if 'backup' in user_config:
                        config['backup'] = user_config['backup']
                    if 'retry' in user_config:
                        config['retry'].update(user_config['retry'])
                    print(f"✓ 数据源配置从 {config_path} 加载")
                    break
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
    
    return config


def get_feishu_config() -> dict:
    """
    获取飞书多维表格配置

    优先级:
    1. 环境变量 FEISHU_APP_TOKEN / FEISHU_TABLE_ID / FEISHU_USER_OPEN_ID
    2. .env 文件中的同名变量

    Returns:
        dict: {'app_token': str, 'table_id': str, 'user_open_id': str}
        未配置的字段值为空字符串
    """
    config = {'app_token': '', 'table_id': '', 'user_open_id': ''}

    # 1. 从环境变量
    for key in config:
        val = os.environ.get(key.upper(), '').strip()
        if val:
            config[key] = val

    # 2. 补充缺失的字段：从 .env 文件读取
    missing = [k for k, v in config.items() if not v]
    if not missing:
        return config

    possible_paths = [
        Path(__file__).parent / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]

    for env_path in possible_paths:
        if env_path.exists():
            try:
                for line in open(env_path):
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    for key in missing:
                        env_key = key.upper()
                        if line.startswith(f'{env_key}='):
                            val = line.split('=', 1)[1].strip().strip('"').strip("'")
                            if val:
                                config[key] = val
                                missing.remove(key)
                            break
                    if not missing:
                        break
                if not missing:
                    break
            except Exception:
                pass

    return config


def get_telegram_token() -> str:
    """
    获取 Telegram Bot Token

    优先级:
    1. 环境变量 TELEGRAM_BOT_TOKEN
    2. .env 文件中的 TELEGRAM_BOT_TOKEN

    Returns:
        str: Telegram Bot Token，未找到返回空字符串
    """
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if token:
        return token

    possible_paths = [
        Path(__file__).parent / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]

    for env_path in possible_paths:
        if env_path.exists():
            try:
                for line in open(env_path):
                    line = line.strip()
                    if line.startswith('TELEGRAM_BOT_TOKEN=') and not line.startswith('#'):
                        token = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if token:
                            return token
            except Exception:
                pass

    return ''


def get_data_dir() -> Path:
    """
    获取统一的数据目录路径

    优先级:
    1. 环境变量 VNPY_DATA_DIR
    2. 默认值: <project_root>/data/akshare/bars

    Returns:
        Path: 数据目录的绝对路径
    """
    env_dir = os.environ.get('VNPY_DATA_DIR', '').strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent / 'data' / 'akshare' / 'bars'


def init_tushare():
    """
    初始化 Tushare Pro API
    
    Returns:
        pro_api 实例，失败返回 None
    """
    token = get_tushare_token()
    if not token:
        print("❌ TUSHARE_TOKEN 未配置")
        return None
    
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api()
        print("✅ Tushare Pro 已初始化")
        return pro
    except ImportError:
        print("❌ tushare 未安装")
        return None
    except Exception as e:
        print(f"❌ Tushare 初始化失败: {e}")
        return None


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("Config Loader 测试")
    print("=" * 60)
    
    token = get_tushare_token()
    print(f"Tushare Token: {'已加载' if token else '未加载'}")
    
    config = get_data_source_config()
    print(f"数据源配置: {config}")
    
    pro = init_tushare()
    print(f"Tushare Pro: {'已初始化' if pro else '未初始化'}")
