"""
配置并测试 akshare-proxy-patch

用于修复 AKShare 连接问题
"""

import akshare_proxy_patch
import akshare as ak
import pandas as pd
from datetime import datetime


def setup_proxy_patch():
    """安装 akshare-proxy-patch"""
    print("=" * 70)
    print("配置 akshare-proxy-patch")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"akshare-proxy-patch 版本：{akshare_proxy_patch.__version__}")
    print("=" * 70)
    
    # 安装补丁
    print("\n[1] 安装 akshare-proxy-patch...")
    try:
        # 参数说明:
        # auth_ip: "101.201.173.125" (固定，不可修改)
        # auth_token: "" (空字符串，每天免费使用一定次数)
        # retry: 30 (重试次数)
        akshare_proxy_patch.install_patch("101.201.173.125", "", 30)
        print("  ✓ 补丁安装成功")
        print("  说明：使用免费 AUTH_TOKEN，每天有一定免费次数")
    except Exception as e:
        print(f"  ✗ 补丁安装失败：{e}")
        return False
    
    return True


def test_akshare_with_patch():
    """测试安装补丁后的 AKShare"""
    print("\n" + "=" * 70)
    print("测试 AKShare (已安装补丁)")
    print("=" * 70)
    
    # 测试 1: 获取单只股票 K 线
    print("\n[测试 1] 获取股票 K 线 (000001.SZ)...")
    try:
        df = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20240101",
            end_date="20240131",
            adjust="qfq"
        )
        
        if df is not None and not df.empty:
            print(f"✓ 成功：获取到 {len(df)} 条 K 线")
            print(f"  列名：{df.columns.tolist()}")
            print(f"  示例数据:")
            print(df.head(2).to_string())
            return True
        else:
            print(f"✗ 失败：返回空数据")
            return False
    
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}: {e}")
        return False


def test_multiple_stocks():
    """测试多只股票下载"""
    print("\n" + "=" * 70)
    print("测试多只股票下载")
    print("=" * 70)
    
    test_stocks = [
        ("000001", "平安银行"),
        ("600000", "浦发银行"),
        ("000002", "万科 A"),
    ]
    
    success_count = 0
    
    for code, name in test_stocks:
        print(f"\n下载 {code} ({name})...")
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date="20240101",
                end_date="20240115",
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                print(f"  ✓ 成功：{len(df)} 条数据")
                success_count += 1
            else:
                print(f"  ✗ 失败：空数据")
        except Exception as e:
            print(f"  ✗ 失败：{type(e).__name__}: {e}")
    
    print(f"\n统计：{success_count}/{len(test_stocks)} 成功")
    return success_count == len(test_stocks)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("akshare-proxy-patch 配置与测试")
    print("=" * 70)
    
    # 1. 安装补丁
    if not setup_proxy_patch():
        print("\n✗ 补丁安装失败，无法继续")
        exit(1)
    
    # 2. 测试单只股票
    test1_success = test_akshare_with_patch()
    
    # 3. 测试多只股票
    test2_success = test_multiple_stocks()
    
    # 4. 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"单只股票测试：{'✓ 成功' if test1_success else '✗ 失败'}")
    print(f"多只股票测试：{'✓ 成功' if test2_success else '✗ 失败'}")
    
    if test1_success or test2_success:
        print("\n✓ akshare-proxy-patch 工作正常！")
        print("\n下一步:")
        print("  python download_data_akshare.py --max 5")
    else:
        print("\n⚠️ akshare-proxy-patch 未能解决问题")
        print("建议:")
        print("  1. 使用 Baostock 作为数据源")
        print("  2. 使用模拟数据进行开发")
        print("  3. 等待凌晨时段再尝试")
    
    print("=" * 70)
