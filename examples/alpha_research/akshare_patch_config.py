"""
AKShare 补丁配置模块

在导入 akshare 之前导入此模块，自动安装 proxy patch
"""

try:
    import akshare_proxy_patch
    # 安装补丁
    # 参数:
    #   auth_ip: "101.201.173.125" (固定，不可修改)
    #   auth_token: "" (空字符串，每天免费使用一定次数)
    #   retry: 30 (重试次数)
    akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
    print("✓ akshare-proxy-patch 已加载")
except ImportError:
    print("⚠️ akshare-proxy-patch 未安装，将使用原始 AKShare")
    print("  安装命令：pip install akshare-proxy-patch")
except Exception as e:
    print(f"⚠️ akshare-proxy-patch 加载失败：{e}")
    print("  将使用原始 AKShare")
