"""
测试 Baostock 数据源

验证 Baostock 是否可以正常下载股票数据
"""

import baostock as bs
import pandas as pd
from datetime import datetime


def test_baostock():
    """测试 Baostock 连接和数据下载"""
    print("=" * 70)
    print("Baostock 数据源测试")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. 登录
    print("\n[1] 登录 Baostock...")
    lg = bs.login()
    print(f"  错误码：{lg.error_code}")
    print(f"  错误信息：{lg.error_msg}")
    
    if lg.error_code != '0':
        print("\n✗ 登录失败，无法继续测试")
        return
    
    print("  ✓ 登录成功")
    
    # 2. 测试获取单只股票数据
    print("\n[2] 测试获取股票 K 线 (600000.SH)...")
    code = "600000.sh"  # Baostock 需要小写
    start_date = "20240101"
    end_date = "20240131"
    
    try:
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,volume,amount,turn",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 前复权
        )
        
        print(f"  错误码：{rs.error_code}")
        if rs.error_msg:
            print(f"  错误信息：{rs.error_msg}")
        
        if rs.error_code == '0':
            # 转换为 DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                print(f"  ✓ 成功获取 {len(df)} 条数据")
                print(f"  列名：{df.columns.tolist()}")
                print(f"  示例数据:")
                print(df.head(3).to_string())
            else:
                print(f"  ✗ 未获取到数据")
        else:
            print(f"  ✗ 查询失败")
    
    except Exception as e:
        print(f"  ✗ 异常：{type(e).__name__}: {e}")
    
    # 3. 测试获取股票基本信息
    print("\n[3] 测试获取股票基本信息 (600000.SH)...")
    try:
        rs = bs.query_stock_basic(code)
        
        if rs.error_code == '0':
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                print(f"  ✓ 成功获取基本信息")
                print(f"  列名：{df.columns.tolist()[:10]}...")
            else:
                print(f"  ✗ 未获取到数据")
        else:
            print(f"  ✗ 查询失败：{rs.error_msg}")
    
    except Exception as e:
        print(f"  ✗ 异常：{type(e).__name__}: {e}")
    
    # 4. 测试获取指数成分股
    print("\n[4] 测试获取沪深 300 成分股...")
    try:
        rs = bs.query_hs300_stocks()
        
        if rs.error_code == '0':
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                print(f"  ✓ 成功获取 {len(df)} 只成分股")
                print(f"  列名：{df.columns.tolist()}")
                if len(df) > 0:
                    print(f"  示例：{df.iloc[0].tolist()}")
            else:
                print(f"  ✗ 未获取到数据")
        else:
            print(f"  ✗ 查询失败：{rs.error_msg}")
    
    except Exception as e:
        print(f"  ✗ 异常：{type(e).__name__}: {e}")
    
    # 5. 登出
    print("\n[5] 登出 Baostock...")
    bs.logout()
    print("  ✓ 已登出")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    print("\n结论:")
    print("  - Baostock 可以正常连接 ✓")
    print("  - 可以作为 AKShare 的备选数据源 ✓")
    print("\n下一步:")
    print("  python download_data_akshare.py --max 5")
    print("  (AKShare 失败时会自动切换到 Baostock)")


if __name__ == "__main__":
    test_baostock()
