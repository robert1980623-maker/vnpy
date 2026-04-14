#!/usr/bin/env python3
"""
持仓行情同步脚本 - 每天 15:30 执行
从 Tushare 获取持仓股票最新价，更新到飞书多维表格
"""
import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('sync_holdings')

# 持仓数据（必须与飞书持仓记录表一致）
POSITIONS = [
    {
        "record_id": "recvf5pWMeFM24",
        "stock_code": "300476.SZ",
        "stock_name": "胜宏科技",
        "quantity": 32200,
        "avg_cost": 12.162,
    },
    {
        "record_id": "recvf5pWMeYjGt",
        "stock_code": "603893.SH",
        "stock_name": "瑞芯微",
        "quantity": 30100,
        "avg_cost": 10.13,
    },
    {
        "record_id": "recvf5pWMe5E5H",
        "stock_code": "300251.SZ",
        "stock_name": "光线传媒",
        "quantity": 30000,
        "avg_cost": 10.0,
    },
]

FEISHU_APP_TOKEN = "YpWLbsLAfaXw3HsprKfcj0AFnrh"
POSITIONS_TABLE_ID = "tblLHrg7fFOcN0to"

def get_latest_prices():
    """从 Tushare 获取持仓股票的最新价格"""
    try:
        import tushare as ts
        from datetime import timedelta
        
        token = None
        env_path = "/Users/rowang/projects/vnpy/.env"
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("TUSHARE_TOKEN"):
                        token = line.split("=")[1].strip()
        
        if not token:
            log.error("Tushare token 未找到")
            return None
        
        ts.set_token(token)
        pro = ts.pro_api()
        
        today = datetime.now()
        prices = {}
        max_retry_days = 5  # 最多尝试前 5 个交易日
        
        for pos in POSITIONS:
            code = pos["stock_code"]
            success = False
            
            # 尝试今天及前几个交易日
            for days_ago in range(max_retry_days):
                try_date = (today - timedelta(days=days_ago)).strftime("%Y%m%d")
                try:
                    df = pro.daily(ts_code=code, trade_date=try_date)
                    if df is not None and not df.empty:
                        prices[code] = {
                            "close": float(df.iloc[0]["close"]),
                            "pct_chg": float(df.iloc[0]["pct_chg"]),
                            "trade_date": try_date
                        }
                        if days_ago == 0:
                            log.info(f"  {pos["stock_name"]}({code}): ¥{prices[code]["close"]} ({prices[code]["pct_chg"]:+.2f}%) [今日]")
                        else:
                            log.info(f"  {pos["stock_name"]}({code}): ¥{prices[code]["close"]} ({prices[code]["pct_chg"]:+.2f}%) [{days_ago}日前，{try_date}]")
                        success = True
                        break
                except Exception as e:
                    log.warning(f"  {pos["stock_name"]}({code}) {try_date}: 获取失败 - {e}")
            
            if not success:
                log.error(f"  {pos["stock_name"]}({code}): 连续{max_retry_days}个交易日无数据，可能停牌或退市")
        
        return prices if prices else None
    
    except Exception as e:
        log.error(f"Tushare 调用失败：{e}")
        return None

def calc_updates(prices):
    """计算各持仓更新值"""
    updates = []
    total_mktval = 0
    total_cost = 0
    
    for pos in POSITIONS:
        code = pos["stock_code"]
        if code not in prices:
            log.warning(f"跳过 {pos['stock_name']}，无价格")
            continue
        
        price = prices[code]["close"]
        mktval = pos["quantity"] * price
        cost = pos["quantity"] * pos["avg_cost"]
        pnl = mktval - cost
        ret_pct = (price / pos["avg_cost"] - 1) * 100
        
        updates.append({
            "record_id": pos["record_id"],
            "stock_name": pos["stock_name"],
            "current_price": price,
            "mktval": round(mktval, 2),
            "cost": round(cost, 2),
            "pnl": round(pnl, 2),
            "ret_pct": round(ret_pct, 2),
        })
        
        total_mktval += mktval
        total_cost += cost
    
    return updates, total_mktval, total_cost

def main():
    log.info("=" * 60)
    log.info("持仓行情同步 - " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)
    
    # 1. 获取最新价格
    log.info("📡 从 Tushare 获取最新价格...")
    prices = get_latest_prices()
    if not prices:
        log.error("获取价格失败，退出")
        sys.exit(1)
    
    # 2. 计算更新值
    updates, total_mktval, total_cost = calc_updates(prices)
    
    # 3. 输出结果（供外部调用）
    result = {
        "timestamp": datetime.now().isoformat(),
        "updates": updates,
        "total_mktval": round(total_mktval, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_mktval - total_cost, 2),
    }
    
    # 保存结果到 JSON
    output_path = "/Users/rowang/projects/vnpy/examples/alpha_research/data/market_mood/holdings_price_update.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    log.info("-" * 60)
    for u in updates:
        log.info(f"  {u['stock_name']}: ¥{u['current_price']} | 浮盈 ¥{u['pnl']:,.2f} ({u['ret_pct']:+.2f}%)")
    log.info("-" * 60)
    log.info(f"  总市值: ¥{total_mktval:,.2f} | 总浮盈: ¥{total_mktval - total_cost:,.2f}")
    log.info(f"  结果已保存: {output_path}")
    log.info("=" * 60)
    log.info("✅ 持仓价格同步完成（飞书更新需调用 API）")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
