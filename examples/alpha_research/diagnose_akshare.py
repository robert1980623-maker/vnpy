"""
AKShare 连接问题诊断脚本

详细记录 AKShare 失败的错误信息和原因
"""

import akshare as ak
import pandas as pd
import traceback
import sys
from datetime import datetime


def test_akshare_connection():
    """测试 AKShare 连接"""
    print("=" * 70)
    print("AKShare 连接诊断")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python 版本：{sys.version}")
    print(f"AkShare 版本：{ak.__version__ if hasattr(ak, '__version__') else 'unknown'}")
    print("=" * 70)
    
    # 测试 1: 获取股票列表
    print("\n[测试 1] 获取 A 股股票列表...")
    try:
        df = ak.stock_info_a_code_name()
        print(f"✓ 成功：获取到 {len(df)} 只股票")
        if len(df) > 0:
            print(f"  示例：{df.iloc[0].tolist()}")
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}")
        print(f"  错误信息：{e}")
        print(f"  完整堆栈:\n{traceback.format_exc()}")
    
    # 测试 2: 获取单只股票 K 线
    print("\n[测试 2] 获取单只股票 K 线 (000001.SZ)...")
    try:
        df = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20240101",
            end_date="20240131",
            adjust="qfq"
        )
        print(f"✓ 成功：获取到 {len(df)} 条 K 线")
        if len(df) > 0:
            print(f"  列名：{df.columns.tolist()}")
            print(f"  示例数据:\n{df.head(2)}")
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}")
        print(f"  错误信息：{e}")
        print(f"  完整堆栈:\n{traceback.format_exc()}")
    
    # 测试 3: 获取指数成分股
    print("\n[测试 3] 获取沪深 300 成分股...")
    try:
        df = ak.index_stock_cons(symbol="000300")
        print(f"✓ 成功：获取到 {len(df)} 只成分股")
        if len(df) > 0:
            print(f"  列名：{df.columns.tolist()}")
    except Exception as e:
        print(f"✗ 失败：{type(e).__name__}")
        print(f"  错误信息：{e}")
        print(f"  完整堆栈:\n{traceback.format_exc()}")
    
    # 测试 4: 获取财务数据
    print("\n[测试 4] 获取财务数据 (000001.SZ)...")
    try:
        # 尝试不同的接口
        interfaces = [
            ("stock_value_em", {"symbol": "000001"}),
            ("stock_financial_analysis_indicator", {"symbol": "000001"}),
        ]
        
        for interface_name, params in interfaces:
            print(f"\n  尝试接口：{interface_name}")
            try:
                func = getattr(ak, interface_name)
                df = func(**params)
                if df is not None and not df.empty:
                    print(f"  ✓ 成功：{interface_name}")
                    print(f"    列名：{df.columns.tolist()[:10]}...")  # 只显示前 10 个
                    break
                else:
                    print(f"  ✗ 返回空数据：{interface_name}")
            except Exception as e:
                print(f"  ✗ 失败：{interface_name} - {type(e).__name__}: {e}")
    except Exception as e:
        print(f"✗ 财务数据测试失败：{type(e).__name__}")
        print(f"  错误信息：{e}")
    
    # 测试 5: 网络连接测试
    print("\n[测试 5] 网络连接测试...")
    try:
        import requests
        urls = [
            "https://www.eastmoney.com/",
            "https://www.akshare.xyz/",
        ]
        for url in urls:
            try:
                response = requests.get(url, timeout=5)
                print(f"  ✓ {url}: {response.status_code}")
            except Exception as e:
                print(f"  ✗ {url}: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"✗ 网络测试失败：{e}")
    
    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)


def test_with_retry():
    """测试带重试的下载"""
    print("\n" + "=" * 70)
    print("带重试的下载测试")
    print("=" * 70)
    
    import time
    import random
    
    vt_symbol = "000001.SZ"
    max_retries = 3
    
    for attempt in range(max_retries):
        print(f"\n[尝试 {attempt + 1}/{max_retries}] 下载 {vt_symbol}...")
        try:
            start_time = datetime.now()
            df = ak.stock_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20240101",
                end_date="20240131",
                adjust="qfq"
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✓ 成功！耗时：{duration:.2f}秒")
            print(f"  数据量：{len(df)} 条")
            print(f"  时间范围：{df['日期'].min()} - {df['日期'].max()}")
            return True
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            print(f"✗ 失败：{error_type}")
            print(f"  错误信息：{error_msg}")
            
            # 详细分析错误类型
            if "RemoteDisconnected" in error_msg:
                print(f"  原因：远程服务器断开连接（服务器端问题）")
            elif "Connection aborted" in error_msg:
                print(f"  原因：连接被中止（网络不稳定或服务器限流）")
            elif "timeout" in error_msg.lower():
                print(f"  原因：请求超时（网络慢或服务器负载高）")
            elif "403" in error_msg:
                print(f"  原因：访问被拒绝（可能被限流或封 IP）")
            elif "404" in error_msg:
                print(f"  原因：接口不存在或代码错误")
            else:
                print(f"  原因：未知错误")
            
            if attempt < max_retries - 1:
                wait_time = random.uniform(3, 6) * (attempt + 1)
                print(f"  等待 {wait_time:.1f}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"\n  已达到最大重试次数，下载失败")
                print(f"  完整错误堆栈:\n{traceback.format_exc()}")
    
    return False


if __name__ == "__main__":
    test_akshare_connection()
    test_with_retry()
    
    print("\n" + "=" * 70)
    print("建议")
    print("=" * 70)
    print("""
如果 AKShare 持续失败，可能的原因：

1. 服务器负载高
   - 解决：使用夜间模式（22:00-06:00）下载
   - 命令：python download_data_akshare.py --night-mode

2. 请求频率限制
   - 解决：减少单次下载数量，增加延迟
   - 命令：python download_data_akshare.py --max 3

3. 网络问题
   - 解决：检查网络连接，使用代理

4. 数据源变更
   - 解决：更新 AKShare 到最新版本
   - 命令：pip install --upgrade akshare

5. 临时方案
   - 使用模拟数据：python generate_mock_data.py
   - 使用其他数据源：Baostock、Tushare
""")
    print("=" * 70)
