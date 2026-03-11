#!/usr/bin/env python3
"""
配置 Tushare Pro Token

使用方法:
1. 从 https://tushare.pro/user/token 获取你的 token
2. 运行此脚本配置
"""

import os
import json
from pathlib import Path

def configure_tushare():
    print("=" * 70)
    print(" " * 20 + "配置 Tushare Pro")
    print("=" * 70)
    
    # 检查现有配置
    token = os.environ.get('TUSHARE_TOKEN', '')
    
    if token:
        print(f"\n✅ 检测到现有配置:")
        print(f"   Token: {token[:10]}...{token[-6:]}")
        
        # 验证 token
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            # 尝试获取用户信息
            user_info = pro.user()
            if user_info is not None and not user_info.empty:
                print(f"   用户：{user_info.iloc[0].get('name', 'N/A')}")
                print(f"   积分：{user_info.iloc[0].get('total_score', 'N/A')}")
                print(f"\n✅ Token 有效!")
                return True
        except Exception as e:
            print(f"\n⚠️ Token 无效：{e}")
    
    print("\n❌ 未配置有效的 Tushare Token")
    print("\n获取 Token 步骤:")
    print("1. 访问 https://tushare.pro/user/token")
    print("2. 登录/注册账号")
    print("3. 复制你的 API Token")
    print("4. 运行以下命令:")
    print()
    print("   export TUSHARE_TOKEN='your_token_here'")
    print()
    print("或者添加到 ~/.zshrc:")
    print("   echo \"export TUSHARE_TOKEN='your_token_here'\" >> ~/.zshrc")
    print("   source ~/.zshrc")
    print()
    
    return False

if __name__ == '__main__':
    configure_tushare()
