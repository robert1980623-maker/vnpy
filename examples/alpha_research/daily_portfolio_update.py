#!/usr/bin/env python3
"""
每日持仓盈亏自动更新

功能：
- 获取最新市场价格
- 更新持仓盈亏
- 生成每日快照
- 发送通知（可选）
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import tushare as ts

# 初始化 Tushare
ts.set_token('612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5')
pro = ts.pro_api()

# 导入模拟交易系统
sys.path.insert(0, str(Path(__file__).parent))
from paper_trading_system import PaperTradingAccount


def update_portfolio():
    """更新持仓盈亏"""
    print("=" * 80)
    print(" " * 25 + "📊 每日持仓更新")
    print("=" * 80)
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载账户
    account = PaperTradingAccount()
    
    # 获取最新价格并更新
    print("【更新持仓价格】")
    print("-" * 80)
    
    updated_positions = account.update_positions()
    
    for ts_code, pos in updated_positions.items():
        print(f"  {pos['stock_name']} ({ts_code})")
        print(f"    现价：¥{pos['current_price']:.2f}")
        print(f"    盈亏：¥{pos['profit']:,.2f} ({pos['return_pct']:+.2f}%)")
        print(f"    日期：{pos.get('trade_date', 'N/A')}")
        print()
    
    # 创建快照
    print("【创建账户快照】")
    print("-" * 80)
    
    snapshot = account.create_snapshot()
    
    print(f"  日期：{snapshot.date}")
    print(f"  总资产：¥{snapshot.total_value:,.2f}")
    print(f"  盈亏：¥{snapshot.total_profit:,.2f} ({snapshot.total_return_pct:+.2f}%)")
    print()
    
    # 保存汇总
    summary = account.get_portfolio_summary()
    
    output_dir = Path('paper_trading_demo')
    output_dir.mkdir(exist_ok=True)
    
    # 保存每日快照
    snapshot_file = output_dir / f'snapshot_{snapshot.date}.json'
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 更新最新汇总
    latest_file = output_dir / 'portfolio_summary.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 快照已保存：{snapshot_file}")
    print(f"✅ 汇总已更新：{latest_file}")
    print()
    
    # 打印简报
    print("【今日简报】")
    print("-" * 80)
    print(f"  总资产：    ¥{summary['total_value']:>14,.2f}")
    print(f"  可用现金：  ¥{summary['cash']:>14,.2f}")
    print(f"  持仓市值：  ¥{summary['position_value']:>14,.2f}")
    print(f"  累计盈亏：  ¥{summary['total_profit']:>14,.2f}")
    print(f"  累计收益率：{summary['total_return_pct']:>+13.2f}%")
    print(f"  持仓数量：  {summary['position_count']:>14} 只")
    print()
    
    return summary


def main():
    """主函数"""
    try:
        summary = update_portfolio()
        print("=" * 80)
        print("✅ 持仓更新完成！")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"❌ 更新失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
