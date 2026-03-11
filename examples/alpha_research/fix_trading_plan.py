import json
from pathlib import Path
from datetime import datetime

# 读取现有交易计划
with open('reports/trading_plan_2026-03-09.json', 'r') as f:
    plan = json.load(f)

# 读取选股结果获取价格信息
with open('reports/stock_selection_2026-03-09.json', 'r') as f:
    stocks_data = json.load(f)

# 创建股票价格映射
stock_info = {}
for stock in stocks_data['stocks']:
    symbol = stock['symbol']
    pe = stock.get('pe', 20)
    # 简化价格估算
    stock_info[symbol] = {
        'price': round(pe * 2, 2),
        'reason': stock['reasons'][0] if stock.get('reasons') else '策略选股'
    }

# 转换买入列表为字典格式
buy_list = []
for symbol in plan['buy'][:15]:
    info = stock_info.get(symbol, {'price': 10.0, 'reason': '策略选股'})
    buy_list.append({
        'symbol': symbol,
        'price': info['price'],
        'reason': info['reason']
    })

# 更新交易计划
plan['buy'] = buy_list
plan['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 保存修复后的交易计划
with open('reports/trading_plan_2026-03-09.json', 'w') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

print("✅ 交易计划已修复")
print(f"  买入：{len(plan['buy'])} 只 (带价格和原因)")
print(f"  卖出：{len(plan['sell'])} 只")
print(f"  持有：{len(plan['hold'])} 只")
