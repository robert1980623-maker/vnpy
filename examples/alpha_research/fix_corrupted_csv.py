#!/usr/bin/env python3
"""
修复损坏的 CSV 文件

问题：CSV 文件列数不一致（第一行有 datetime 列，后续行没有）
解决方案：
1. 检测并修复格式错误的 CSV 文件
2. 删除无法修复的文件（等待重新下载）
"""

import pandas as pd
from pathlib import Path
import shutil

def fix_csv_file(filepath: Path) -> bool:
    """修复单个 CSV 文件"""
    print(f"检查：{filepath.name}")
    
    try:
        # 尝试读取文件
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            print(f"  ⚠️  文件太短，跳过")
            return True
        
        # 检查第一行
        header = lines[0].strip()
        header_fields = header.split(',')
        
        # 检查第二行
        second_line = lines[1].strip()
        second_fields = second_line.split(',')
        
        # 如果列数不一致，需要修复
        if len(header_fields) != len(second_fields):
            print(f"  ❌ 列数不一致：表头{len(header_fields)}列，数据{len(second_fields)}列")
            
            # 创建备份
            backup_path = filepath.with_suffix('.csv.bak')
            shutil.copy(filepath, backup_path)
            print(f"  💾 已备份：{backup_path.name}")
            
            # 删除原文件（等待重新下载）
            filepath.unlink()
            print(f"  🗑️  已删除损坏文件，等待重新下载")
            return False
        
        # 列数一致，尝试读取
        df = pd.read_csv(filepath)
        print(f"  ✅ 格式正常，{len(df)} 行数据")
        return True
        
    except Exception as e:
        # 读取失败，删除文件
        print(f"  ❌ 读取失败：{e}")
        try:
            backup_path = filepath.with_suffix('.csv.bak')
            shutil.copy(filepath, backup_path)
            filepath.unlink()
            print(f"  💾 已备份并删除损坏文件")
        except:
            pass
        return False


def main():
    data_dir = Path('./data/akshare/bars')
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在：{data_dir}")
        return
    
    csv_files = list(data_dir.glob('*.csv'))
    print(f"发现 {len(csv_files)} 个 CSV 文件\n")
    
    fixed = 0
    deleted = 0
    skipped = 0
    
    for filepath in csv_files:
        result = fix_csv_file(filepath)
        if result:
            fixed += 1
        else:
            deleted += 1
    
    print(f"\n{'='*60}")
    print(f"修复完成:")
    print(f"  正常/已修复：{fixed}")
    print(f"  已删除（需重下）: {deleted}")
    print(f"  总计：{len(csv_files)}")


if __name__ == '__main__':
    main()
