#!/usr/bin/env python3
"""
持仓重组 - 精简至 5 只精英组合

功能:
1. 清理当前 38 只持仓
2. 调仓至精选 5 只
3. 控制仓位比例（单只≤15%）
4. 保留 5-10% 现金
"""

import logging
logger = logging.getLogger(__name__)

import json
from pathlib import Path
from datetime import datetime
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive, confirm_action


class PortfolioRebalancer:
    """持仓重组器"""
    
    def __init__(self, account_file: str = './accounts/virtual_2026_account.json',
                 target_stocks: int = 5):
        self.account_file = Path(account_file)
        self.target_stocks = target_stocks
        self.max_position_ratio = 0.15  # 单只最大 15%
        self.min_cash_ratio = 0.05  # 最小现金 5%
        self.target_cash_ratio = 0.08  # 目标现金 8%
        
    def load_account(self):
        """加载账户"""
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_elite_selection(self):
        """加载精英选股结果，支持回退到最近的结果"""
        today = datetime.now().strftime('%Y-%m-%d')
        selection_file = Path(f'./reports/elite_selection_{today}.json')
        
        if selection_file.exists():
            logger.info(f"✅ 使用今日选股报告：{selection_file}")
            with open(selection_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 回退到最近的结果（最多回退3天）
        logger.info(f"⚠️ 未找到今日选股报告，尝试回退...")
        from datetime import timedelta
        for i in range(1, 4):
            fallback_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            fallback_file = Path(f'./reports/elite_selection_{fallback_date}.json')
            if fallback_file.exists():
                logger.info(f"✅ 使用 {fallback_date} 选股报告（{i}天前）：{fallback_file}")
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        logger.info(f"⚠️ 未找到最近3天的选股报告，请先运行 python3 elite_stock_selector.py")
        return None
    
    def get_current_prices(self):
        """获取最新价格"""
        import csv
        prices = {}
        skipped = 0
        
        for csv_file in Path('./data/akshare/bars').glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) < 2:
                    skipped += 1
                    continue
                # 从最后一行往前找，找到第一条有效数据
                close_price = None
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(',')
                    if len(parts) >= 6:
                        try:
                            close_price = float(parts[5])
                            if close_price > 0:
                                break
                            else:
                                continue
                        except ValueError:
                            continue
                if close_price and close_price > 0:
                    prices[symbol] = close_price
                else:
                    skipped += 1
        
        if skipped > 0:
            logger.info(f"⚠️ 跳过 {skipped} 只无效/缺失价格数据")
        
        return prices
    
    def analyze_current_portfolio(self, account, prices):
        """分析当前持仓"""
        logger.info("=" * 70)
        logger.info(" " * 20 + "当前持仓分析")
        logger.info("=" * 70)
        
        total_assets = account['cash'] + sum(p.get('market_value', 0) for p in account['positions'])
        
        positions = []
        for pos in account['positions']:
            symbol = pos['symbol']
            current_price = prices.get(symbol, pos['current_price'])
            market_value = pos['quantity'] * current_price
            position_ratio = market_value / total_assets if total_assets > 0 else 0
            
            positions.append({
                'symbol': symbol,
                'volume': pos['quantity'],
                'cost': pos.get('cost_basis', pos.get('cost', 0)),
                'market_value': market_value,
                'profit_rate': pos.get('profit_rate', 0),
                'position_ratio': position_ratio,
                'action': 'hold'  # default
            })
        
        # 排序
        positions.sort(key=lambda x: x['market_value'], reverse=True)
        
        logger.info(f"总资产：¥{total_assets:,.2f}")
        logger.info(f"当前现金：¥{account['cash']:,.2f} ({account['cash']/total_assets*100:.1f}%)")
        logger.info(f"持仓数量：{len(positions)} 只")
        logger.info(f"目标持仓：{self.target_stocks} 只")
        logger.info()
        
        logger.info("📊 持仓 Top 10:")
        for i, pos in enumerate(positions[:10], 1):
            logger.info(f"  {i}. {pos['symbol']}: ¥{pos['market_value']:,.2f} ({pos['position_ratio']*100:.1f}%) 盈亏{pos['profit_rate']*100:.1f}%")
        
        return positions, total_assets
    
    def generate_rebalance_plan(self, positions, total_assets, elite_stocks, prices):
        """生成调仓计划"""
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "生成调仓计划")
        logger.info("=" * 70)
        
        plan = {
            'sell': [],
            'buy': [],
            'hold': [],
            'target_cash': total_assets * self.target_cash_ratio,
            'target_position_value': total_assets * (1 - self.target_cash_ratio) / self.target_stocks
        }
        
        # 1. 确定保留的股票（在精英选股中的）
        elite_symbols = set([s['symbol'] for s in elite_stocks]) if elite_stocks else set()
        
        # 2. 卖出计划：不在精英选股中的全部卖出
        for pos in positions:
            if pos['symbol'] not in elite_symbols:
                sell_price = prices.get(pos['symbol'], 0)
                # 🛡️ 安全防护：价格为 0 或不可用时禁止卖出
                if sell_price <= 0:
                    logger.info(f"⚠️ 跳过卖出 {pos['symbol']}：当前价格 ¥{sell_price:.2f} 无效，中止卖出！")
                    continue
                plan['sell'].append({
                    'symbol': pos['symbol'],
                    'volume': pos['volume'],
                    'current_price': sell_price,
                    'estimated_value': pos['market_value'],
                    'reason': '不在精英组合'
                })
            else:
                # 检查是否超配
                pos_price = prices.get(pos['symbol'], 0)
                if pos['position_ratio'] > self.max_position_ratio:
                    excess_ratio = pos['position_ratio'] - self.max_position_ratio
                    excess_value = total_assets * excess_ratio
                    if pos_price <= 0:
                        logger.info(f"⚠️ 跳过 {pos['symbol']} 超配调整：价格为 ¥{pos_price:.2f} 无效")
                    else:
                        excess_volume = int(excess_value / pos_price / 100) * 100
                        
                        if excess_volume > 0:
                            plan['sell'].append({
                                'symbol': pos['symbol'],
                                'volume': excess_volume,
                                'current_price': pos_price,
                                'estimated_value': excess_volume * pos_price,
                                'reason': f'超配 (当前{pos["position_ratio"]*100:.1f}% → 目标{self.max_position_ratio*100:.1f}%)'
                            })
                
                plan['hold'].append(pos['symbol'])
        
        # 3. 买入计划：精英选股中未持仓的
        holding_symbols = set([p['symbol'] for p in positions])
        if elite_stocks:
            for stock in elite_stocks:
                symbol = stock['symbol']
                if symbol not in holding_symbols:
                    target_value = plan['target_position_value']
                    current_price = prices.get(symbol, 0)
                    if current_price > 0:
                        volume = int(target_value / current_price / 100) * 100
                        plan['buy'].append({
                            'symbol': symbol,
                            'target_volume': volume,
                            'current_price': current_price,
                            'estimated_cost': volume * current_price,
                            'reason': '精英选股新标的'
                        })
        
        # 打印计划
        logger.info(f"\n📉 卖出计划：{len(plan['sell'])} 只")
        total_sell_value = sum(s['estimated_value'] for s in plan['sell'])
        for s in plan['sell'][:10]:
            logger.info(f"  - {s['symbol']}: {s['volume']} 股 ≈ ¥{s['estimated_value']:,.2f} ({s['reason']})")
        if len(plan['sell']) > 10:
            logger.info(f"  ... 还有 {len(plan['sell']) - 10} 只")
        logger.info(f"  预计回笼资金：¥{total_sell_value:,.2f}")
        
        logger.info(f"\n📈 买入计划：{len(plan['buy'])} 只")
        total_buy_cost = sum(b['estimated_cost'] for b in plan['buy'])
        for b in plan['buy']:
            logger.info(f"  - {b['symbol']}: {b['target_volume']} 股 ≈ ¥{b['estimated_cost']:,.2f}")
        logger.info(f"  预计使用资金：¥{total_buy_cost:,.2f}")
        
        logger.info(f"\n💰 资金规划:")
        logger.info(f"  当前现金：¥{total_assets - sum(p['market_value'] for p in positions):,.2f}")
        logger.info(f"  卖出所得：¥{total_sell_value:,.2f}")
        logger.info(f"  买入所用：¥{total_buy_cost:,.2f}")
        logger.info(f"  预计现金：¥{total_assets - sum(p['market_value'] for p in positions) + total_sell_value - total_buy_cost:,.2f}")
        logger.info(f"  目标现金：¥{plan['target_cash']:,.2f} ({self.target_cash_ratio*100:.0f}%)")
        
        return plan
    
    def execute_rebalance(self, account, plan, prices):
        """执行调仓"""
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "执行调仓")
        logger.info("=" * 70)
        
        # 1. 执行卖出
        logger.info("\n📉 执行卖出:")
        for sell in plan['sell']:
            symbol = sell['symbol']
            volume = sell['volume']
            sell_price = prices.get(symbol, sell['current_price'])
            # 🛡️ 双重校验：执行时再验一次价格
            if sell_price <= 0:
                logger.info(f"⚠️ 跳过 {symbol}：执行时价格 ¥{sell_price:.2f} 仍为无效值！")
                continue
            sell_value = volume * sell_price
            
            logger.info(f"  卖出 {symbol}: {volume} 股 × ¥{sell_price:.2f} = ¥{sell_value:,.2f}")
            
            # 更新账户
            account['cash'] += sell_value
            
            # 更新或移除持仓
            for pos in account['positions']:
                if pos['symbol'] == symbol:
                    if pos['quantity'] <= volume:
                        # 全部卖出
                        account['positions'].remove(pos)
                    else:
                        # 部分卖出
                        pos['quantity'] -= volume
                        pos['cost_basis'] -= (sell_value * pos['cost_basis'] / pos['market_value']) if pos['market_value'] > 0 else 0
                        pos['market_value'] = pos['quantity'] * sell_price
                    break
        
        # 2. 执行买入
        logger.info("\n📈 执行买入:")
        for buy in plan['buy']:
            symbol = buy['symbol']
            volume = buy['target_volume']
            buy_price = prices.get(symbol, buy['current_price'])
            buy_cost = volume * buy_price
            
            if buy_cost <= account['cash']:
                account['cash'] -= buy_cost
                account['positions'].append({
                    'symbol': symbol,
                    'name': '',
                    'quantity': volume,
                    'avg_price': buy_price,
                    'cost_basis': buy_cost,
                    'current_price': buy_price,
                    'market_value': buy_cost,
                    'profit': 0,
                    'profit_rate': 0
                })
                logger.info(f"  买入 {symbol}: {volume} 股 × ¥{buy_price:.2f} = ¥{buy_cost:,.2f}")
            else:
                logger.info(f"  ⚠️ {symbol}: 现金不足 (需要¥{buy_cost:,.2f}, 可用¥{account['cash']:,.2f})")
        
        # 3. 更新持仓价格
        for pos in account['positions']:
            symbol = pos['symbol']
            current_price = prices.get(symbol, pos['current_price'])
            pos['current_price'] = current_price
            pos['market_value'] = pos['quantity'] * current_price
            pos['profit'] = pos['market_value'] - pos['cost_basis']
            pos['profit_rate'] = pos['profit'] / pos['cost_basis'] if pos['cost_basis'] > 0 else 0
        
        # 4. 计算新状态
        total_market_value = sum(p.get('market_value', 0) for p in account['positions'])
        total_assets = account['cash'] + total_market_value
        cash_ratio = account['cash'] / total_assets if total_assets > 0 else 0
        
        logger.info(f"\n💰 调仓后状态:")
        logger.info(f"  现金：¥{account['cash']:,.2f} ({cash_ratio*100:.1f}%)")
        logger.info(f"  持仓：{len(account['positions'])} 只")
        logger.info(f"  持仓市值：¥{total_market_value:,.2f}")
        logger.info(f"  总资产：¥{total_assets:,.2f}")
        
        return account
    
    def save_report(self, plan, account):
        """保存调仓报告"""
        report = {
            'rebalance_time': datetime.now().isoformat(),
            'plan': plan,
            'result': {
                'cash': account['cash'],
                'position_count': len(account['positions']),
                'positions': account['positions'],
                'total_market_value': sum(p.get('market_value', 0) for p in account['positions']),
                'total_assets': account['cash'] + sum(p.get('market_value', 0) for p in account['positions'])
            }
        }
        
        report_file = Path('./reports/rebalance_' + datetime.now().strftime('%Y%m%d_%H%M') + '.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 调仓报告已保存：{report_file}")
        return report_file
    
    def run(self):
        """执行完整调仓流程"""
        logger.info("=" * 70)
        logger.info(" " * 18 + f"持仓重组 - 精简至 {self.target_stocks} 只精英组合")
        logger.info("=" * 70)
        
        # 加载账户
        account = self.load_account()
        logger.info(f"📊 账户：{account['account_id']}")
        logger.info()
        
        # 获取价格
        prices = self.get_current_prices()
        logger.info(f"✅ 获取价格数据：{len(prices)} 只股票")
        logger.info()
        
        # 加载精英选股
        elite_stocks = self.load_elite_selection()
        if not elite_stocks:
            logger.info("\n🛡️ 风控拦截：未找到精英选股结果，中止调仓！")
            logger.info("   原因：没有选股结果时禁止调仓，防止误操作清空持仓")
            logger.info("   请先运行 python3 elite_stock_selector.py")
            return
        
        if len(elite_stocks.get('stocks', [])) == 0:
            logger.info("\n🛡️ 风控拦截：精英选股结果为空（0只），中止调仓！")
            logger.error("   原因：选股结果为空可能是数据异常或市场极端情况")
            logger.info("   当前持仓保持不变，等待下次选股结果")
            logger.info("   建议：检查 elite_stock_selector.py 运行状态")
            return
        
        logger.info(f"✅ 精英选股：{len(elite_stocks['stocks'])} 只")
        for s in elite_stocks['stocks']:
            logger.info(f"  - {s['symbol']} {s['name']} (评分：{s.get('base_score', s.get('final_score', 'N/A'))})")
        logger.info()
        
        # 分析当前持仓
        positions, total_assets = self.analyze_current_portfolio(account, prices)
        
        # 生成调仓计划
        plan = self.generate_rebalance_plan(positions, total_assets, elite_stocks['stocks'], prices)
        
        # 确认执行
        logger.info("\n" + "=" * 70)
        if not confirm_action("是否执行调仓？", default=True):
            logger.info("❌ 已取消")
            return
        
        # 执行调仓
        account = self.execute_rebalance(account, plan, prices)
        
        # 保存账户
        with open(self.account_file, 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        logger.info(f"\n✅ 账户已保存")
        
        # 保存报告
        self.save_report(plan, account)
        
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "调仓完成")
        logger.info("=" * 70)


def main():
    """主函数"""
    rebalancer = PortfolioRebalancer(target_stocks=5)
    rebalancer.run()


if __name__ == '__main__':
    main()
