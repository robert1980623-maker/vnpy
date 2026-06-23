#!/usr/bin/env python3
"""
持仓 symbol_name 回填脚本

从 JSON 账户文件读取 stock_name，批量更新 trading.db positions 表的 symbol_name 字段。
"""

import json
import sqlite3
import sys
import re
from pathlib import Path
from collections import defaultdict

# 配置路径
ACCOUNTS_DIR = Path(__file__).parent.parent / "accounts"
DB_PATH = ACCOUNTS_DIR / "trading.db"
ACCOUNT_FILE = Path(__file__).parent.parent / "examples/alpha_research/accounts/virtual_2026_account.json"


def load_account_json(json_path: Path) -> dict:
    """加载账户 JSON 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_stock_names_from_text(text: str) -> list:
    """从文本中提取 股票代码+名称 模式，如 '002966苏州银行'"""
    pattern = r'(\d{6})(?![\u4e00-\u9fa5]*\d{6})([\u4e00-\u9fa5]{2,6})'
    matches = re.findall(pattern, text)
    return matches


def build_stock_name_map(account_data: dict) -> dict:
    """
    从账户数据构建 stock_code -> stock_name 映射
    从多个来源收集名称：positions, trades, rebalance_log, 以及文本解析
    """
    stock_map = defaultdict(list)
    
    # 1. positions 数组
    for position in account_data.get("positions", []):
        stock_code = position.get("stock_code", "")
        stock_name = position.get("stock_name", "")
        if stock_code and stock_name:
            stock_map[stock_code].append(stock_name)
    
    # 2. trades 数组
    for trade in account_data.get("trades", []):
        symbol = trade.get("symbol", "")
        name = trade.get("name", "")
        if symbol and name:
            stock_map[symbol].append(name)
    
    # 3. 从文本字段中提取股票名称（如 reason, note 等）
    json_str = json.dumps(account_data, ensure_ascii=False)
    for code, name in extract_stock_names_from_text(json_str):
        if name and name != "—":
            stock_map[code].append(name)
    
    # 4. 从 reports 的 new_positions 中获取
    for report in account_data.get("reports", []):
        for np in report.get("new_positions", []):
            code = np.get("code", "")
            name = np.get("name", "")
            if code and name and name != "—":
                stock_map[code].append(name)
    
    # 去重并返回
    result = {}
    for code, names in stock_map.items():
        # 优先使用最短的名称（可能是简称），过滤掉"—"
        valid_names = [n for n in names if n and n != "—"]
        if valid_names:
            result[code] = valid_names[0]
    
    return result


def normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码格式
    DB 中格式: 600035.SH, 002233
    JSON 中格式: 600035, 002233
    """
    # 移除 .SH, .SZ, .SZSE, .BSE 等后缀
    return symbol.split(".")[0]


def update_positions(db_path: Path, account_id: str, stock_map: dict) -> tuple[int, int]:
    """
    更新持仓表的 symbol_name 字段
    
    Returns:
        (updated_count, total_count)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询需要更新的持仓（symbol_name 为空或 NULL）
    cursor.execute(
        "SELECT id, symbol, symbol_name FROM positions WHERE account_id = ?",
        (account_id,)
    )
    all_positions = cursor.fetchall()
    
    # 过滤出需要更新的
    positions_to_update = [(pid, sym) for pid, sym, name in all_positions 
                           if not name or name.strip() == ""]
    
    updated_count = 0
    for pos_id, symbol in positions_to_update:
        normalized = normalize_symbol(symbol)
        stock_name = stock_map.get(normalized)
        if stock_name:
            cursor.execute(
                "UPDATE positions SET symbol_name = ? WHERE id = ?",
                (stock_name, pos_id)
            )
            updated_count += 1
            print(f"  ✓ {symbol} -> {stock_name}")
        else:
            print(f"  ✗ {symbol} -> 未找到名称")
    
    conn.commit()
    
    # 验证更新
    cursor.execute(
        "SELECT symbol, symbol_name FROM positions WHERE account_id = ?",
        (account_id,)
    )
    print("\n[更新后验证]")
    all_filled = True
    for row in cursor.fetchall():
        status = "✓" if row[1] else "✗"
        if not row[1]:
            all_filled = False
        print(f"  {status} {row[0]}: {row[1] or '(空)'}")
    
    conn.close()
    
    return updated_count, len(positions_to_update), all_filled


def main():
    print("=" * 60)
    print("持仓 symbol_name 回填脚本")
    print("=" * 60)
    
    # 1. 加载 JSON 账户文件
    print(f"\n[1] 加载账户文件: {ACCOUNT_FILE}")
    try:
        account_data = load_account_json(ACCOUNT_FILE)
        account_id = account_data.get("account_id", "virtual_2026")
        print(f"    账户ID: {account_id}")
    except FileNotFoundError:
        print(f"    ✗ 文件不存在: {ACCOUNT_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON 解析失败: {e}")
        sys.exit(1)
    
    # 2. 构建股票名称映射
    print(f"\n[2] 构建 stock_code -> stock_name 映射")
    stock_map = build_stock_name_map(account_data)
    print(f"    共加载 {len(stock_map)} 只股票")
    
    # 3. 更新数据库
    print(f"\n[3] 更新 trading.db")
    print(f"    DB路径: {DB_PATH}")
    print(f"    账户ID: {account_id}")
    
    if not DB_PATH.exists():
        print(f"    ✗ 数据库不存在: {DB_PATH}")
        sys.exit(1)
    
    updated, total, all_filled = update_positions(DB_PATH, account_id, stock_map)
    
    # 4. 汇总
    print("\n" + "=" * 60)
    if all_filled:
        print(f"✓ 成功: 全部 {total} 条记录已更新")
    else:
        print(f"⚠ 部分完成: 更新 {updated}/{total} 条记录")
        print("  注意: 部分持仓可能已平仓或不在账户文件中")
    print("=" * 60)
    
    return 0 if all_filled else 1


if __name__ == "__main__":
    sys.exit(main())
