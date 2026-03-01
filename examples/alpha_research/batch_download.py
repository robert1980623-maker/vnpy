#!/usr/bin/env python3
"""
分批下载股票数据

- 每批 5 只股票
- 批次间隔 30 秒
- 单只股票间隔 3 秒
- 避免超时和限流
"""

import subprocess
import time
from datetime import datetime


# 配置
BATCH_SIZE = 5  # 每批数量
BATCH_DELAY = 30  # 批次间隔（秒）
STOCK_DELAY = 3  # 单只间隔（秒）
TOTAL_STOCKS = 20  # 总下载数量


def get_stock_list():
    """获取股票列表（从沪深 300）"""
    print("=" * 60)
    print("获取股票列表...")
    print("=" * 60)
    
    # 使用脚本获取股票列表
    cmd = [
        "python3", "-c",
        "import akshare as ak; df = ak.index_stock_cons(symbol='000300'); "
        "print(','.join(df['品种代码'].tolist()[:20]))"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stocks = result.stdout.strip().split(',')
        print(f"✅ 获取到 {len(stocks)} 只股票")
        return stocks
    except Exception as e:
        print(f"⚠️ 获取股票列表失败：{e}")
        # 使用默认列表
        return [
            '000630', '000807', '000975', '000999', '001391',
            '002028', '002384', '002422', '002463', '002600',
            '002625', '300251', '300394', '300418', '300442',
            '300476', '300502', '300803', '300832', '300866'
        ]


def download_batch(batch_num, stocks):
    """下载一批股票"""
    print("\n" + "=" * 60)
    print(f"批次 {batch_num}: 下载 {len(stocks)} 只股票")
    print("=" * 60)
    print(f"股票：{', '.join(stocks)}")
    print(f"开始时间：{datetime.now().strftime('%H:%M:%S')}")
    
    # 下载命令
    cmd = [
        "python3", "download_data_akshare.py",
        "--max", str(len(stocks))
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/Users/rowang/projects/vnpy/examples/alpha_research",
            timeout=300  # 5 分钟超时
        )
        
        if result.returncode == 0:
            print(f"✅ 批次 {batch_num} 完成")
            return True
        else:
            print(f"❌ 批次 {batch_num} 失败")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ 批次 {batch_num} 超时")
        return False
    except Exception as e:
        print(f"❌ 批次 {batch_num} 错误：{e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("        分批下载股票数据")
    print("=" * 60)
    print(f"每批数量：{BATCH_SIZE}")
    print(f"批次间隔：{BATCH_DELAY}秒")
    print(f"单只间隔：{STOCK_DELAY}秒")
    print(f"总数量：{TOTAL_STOCKS}")
    print(f"预计批次：{TOTAL_STOCKS // BATCH_SIZE + (1 if TOTAL_STOCKS % BATCH_SIZE else 0)}")
    print(f"预计时间：{((TOTAL_STOCKS // BATCH_SIZE) * BATCH_DELAY) // 60}分钟")
    print("=" * 60)
    
    # 获取股票列表
    all_stocks = get_stock_list()[:TOTAL_STOCKS]
    
    # 分批
    batches = []
    for i in range(0, len(all_stocks), BATCH_SIZE):
        batches.append(all_stocks[i:i + BATCH_SIZE])
    
    print(f"\n共 {len(batches)} 批次")
    
    # 下载
    success_count = 0
    for i, batch in enumerate(batches, 1):
        print(f"\n>>> 批次 {i}/{len(batches)}")
        
        if download_batch(i, batch):
            success_count += 1
        
        # 批次间隔（最后一批不需要）
        if i < len(batches):
            print(f"\n⏱️  等待 {BATCH_DELAY}秒...")
            for j in range(BATCH_DELAY, 0, -1):
                print(f"   {j}秒", end='\r')
                time.sleep(1)
            print()
    
    # 总结
    print("\n" + "=" * 60)
    print("        下载完成")
    print("=" * 60)
    print(f"总批次：{len(batches)}")
    print(f"成功：{success_count}/{len(batches)}")
    print(f"完成时间：{datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # 验证
    print("\n验证数据...")
    subprocess.run(
        ["ls", "-lh", "data/akshare/bars/*.csv", "|", "wc", "-l"],
        shell=True,
        cwd="/Users/rowang/projects/vnpy/examples/alpha_research"
    )


if __name__ == "__main__":
    main()
