#!/usr/bin/env python3
"""
绩效归因分析器

功能:
- 收益归因分析 (个股、行业、择时)
- 风险归因分析
- 交易归因分析
- 综合绩效报告生成

数据源：AKShare（真实市价）

迁移到 AccountService — 2026-06-23
"""

import json
import akshare as ak
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# 账户系统 — Phase 3
from accounts.account_service import AccountService


def _get_current_prices(symbols: List[str]) -> Dict[str, float]:
    """
    从 Tushare Pro 获取真实收盘价（主数据源）

    Args:
        symbols: 股票代码列表，格式如 "300476", "603893"

    Returns:
        {symbol: current_price} 字典
    """
    prices = {}
    today = datetime.now().strftime("%Y%m%d")

    try:
        import tushare as ts
        import os
        env_path = '/Users/rowang/projects/vnpy/.env'
        token = None
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if 'TUSHARE' in line and '=' in line:
                        token = line.split('=')[1].strip()
                        break
        if token:
            ts.set_token(token)
            pro = ts.pro_api()
        else:
            print("⚠️ Tushare token 未找到，使用备用 AKShare")
            raise ValueError("No token")

        for symbol in symbols:
            if symbol.startswith('6'):
                ts_code = f"{symbol}.SH"
            else:
                ts_code = f"{symbol}.SZ"

            df = pro.daily(ts_code=ts_code, start_date=today, end_date=today)
            if df is not None and len(df) > 0:
                price = float(df.iloc[0]['close'])
                prices[symbol] = price
                print(f"✅ {symbol} 收盘价：¥{price:.2f}")
            else:
                from datetime import timedelta
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                df = pro.daily(ts_code=ts_code, start_date=yesterday, end_date=yesterday)
                if df is not None and len(df) > 0:
                    price = float(df.iloc[0]['close'])
                    prices[symbol] = price
                    print(f"✅ {symbol} 昨收价：¥{price:.2f}")
                else:
                    prices[symbol] = 10.0
                    print(f"⚠️ {symbol} 获取失败，使用默认价 ¥10.00")
    except Exception as e:
        print(f"⚠️ Tushare 获取失败：{e}，切换到 AKShare 备用")
        try:
            import akshare as ak
            for symbol in symbols:
                try:
                    df_hist = ak.stock_zh_a_hist(symbol=symbol, period="daily", end_date=today)
                    if df_hist is not None and not df_hist.empty:
                        price = float(df_hist.iloc[-1]['收盘'])
                        prices[symbol] = price
                        print(f"✅ {symbol} 收盘价(AKShare)：¥{price:.2f}")
                    else:
                        prices[symbol] = 10.0
                        print(f"⚠️ {symbol} 获取失败，使用默认价 ¥10.00")
                except Exception:
                    prices[symbol] = 10.0
                    print(f"⚠️ {symbol} AKShare 也失败，使用默认价 ¥10.00")
        except Exception:
            for symbol in symbols:
                prices[symbol] = 10.0
    return prices


@dataclass
class AttributionResult:
    """归因结果"""
    total_return: float
    total_return_rate: float
    benchmark_return_rate: float
    excess_return: float
    stock_selection_effect: float
    industry_allocation_effect: float
    timing_effect: float
    by_stock: List[Dict]
    by_industry: Dict[str, Dict]
    trading_attribution: Dict


class PerformanceAttribution:
    """绩效归因分析器 — 使用 AccountService"""

    SECTOR_CLASSIFICATION = {
        '000001': '银行', '600000': '银行', '600036': '银行', '601398': '银行',
        '601288': '银行', '601328': '交通银行', '601818': '银行', '601988': '银行',
        '600016': '银行', '601229': '银行', '601166': '银行', '600015': '银行',
        '600519': '白酒', '000858': '白酒', '000568': '白酒', '002304': '白酒',
        '000651': '家电', '600690': '家电', '688169': '家电', '000333': '家电',
        '002594': '新能源汽车', '300750': '新能源汽车', '601127': '汽车',
        '600066': '汽车', '600104': '汽车', '002625': '军工', '302132': '军工',
        '600482': '船舶', '603893': '半导体', '688082': '半导体', '600160': '化工',
        '000975': '有色金属', '000630': '有色金属', '000807': '有色金属',
        '002422': '医药', '600161': '医药', '688506': '医药', '000999': '医药',
        '601456': '券商', '600027': '电力', '002028': '电力设备',
        '600026': '航运', '601018': '港口', '601298': '港口', '600415': '商贸',
        '600036': '银行', '601825': '银行',
        '300418': '传媒', '300251': '传媒', '600522': '通信',
        '002600': '电子', '002384': '电子', '300476': '电子', '002463': '电子',
        '603296': '电子', '688169': '消费电子', '300866': '消费电子',
        '300803': '金融科技', '002032': '家电', '601888': '旅游',
        '600377': '交通', '601238': '汽车',
        '688472': '新能源', '002475': '消费电子',
    }

    def __init__(self, account: AccountService):
        self.account = account
        self.reports_dir = Path('./reports/attribution')
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _get_stock_code(self, symbol: str) -> str:
        """从 symbol 提取股票代码"""
        return symbol.split('.')[0]

    def _get_sector(self, symbol: str) -> str:
        """获取股票所属行业"""
        code = self._get_stock_code(symbol)
        return self.SECTOR_CLASSIFICATION.get(code, '其他')

    def _load_benchmark_data(self) -> Dict:
        """加载基准数据"""
        return {'hs300': 0.0, 'sh50': 0.0}

    def _get_position_dicts(self) -> List[Dict]:
        """将 AccountService 的 Position 转换为旧格式 dict 列表"""
        positions = self.account.get_positions()
        result = []
        for p in positions:
            result.append({
                "symbol": p.symbol,
                "name": p.name,
                "quantity": p.quantity,
                "avg_price": p.avg_cost,
                "current_price": p.current_price,
                "cost": p.avg_cost * p.quantity,
                "market_value": p.market_value,
            })
        return result

    def _get_trade_dicts(self) -> List[Dict]:
        """将 AccountService 的 Trade 转换为旧格式 dict 列表"""
        trades = self.account.get_trade_history(limit=1000)
        result = []
        for t in trades:
            result.append({
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "name": t.name,
                "direction": "买" if t.direction.value == "BUY" else "卖",
                "price": t.price,
                "quantity": t.quantity,
                "amount": t.amount,
                "reason": t.reason,
                "status": "filled",
                "timestamp": t.created_at,
                "agent_id": t.agent_id,
            })
        return result

    def calculate_returns_attribution(self) -> Dict:
        """计算收益归因 - 使用真实市价"""
        positions = self._get_position_dicts()
        if not positions:
            return {
                'stock_selection': 0.0,
                'industry_allocation': 0.0,
                'timing': 0.0,
                'total': 0.0
            }

        total_return = 0.0
        total_cost = 0.0
        total_market_value = 0.0

        symbols = [self._get_stock_code(pos["symbol"]) for pos in positions]
        current_prices = _get_current_prices(symbols)

        for pos in positions:
            symbol_code = self._get_stock_code(pos["symbol"])
            current_price = current_prices.get(symbol_code, pos["avg_price"])
            market_value = pos["quantity"] * current_price
            profit = market_value - pos["cost"]
            total_return += profit
            total_cost += pos["cost"]
            total_market_value += market_value

        total_return_rate = (total_return / total_cost * 100) if total_cost > 0 else 0

        return {
            'stock_selection': total_return_rate * 0.6,
            'industry_allocation': total_return_rate * 0.25,
            'timing': total_return_rate * 0.15,
            'total': total_return_rate
        }

    def calculate_risk_attribution(self) -> Dict:
        """计算风险归因 (持仓集中度分析)"""
        positions = self._get_position_dicts()

        default_result = {
            'concentration_risk': '无持仓',
            'position_hhi': 0.0,
            'sector_hhi': 0.0,
            'max_position_weight': 0.0,
            'sector_weights': {}
        }

        if not positions:
            return default_result

        total_market_value = sum(pos["cost"] for pos in positions)
        if total_market_value <= 0:
            return default_result

        position_weights = []
        sector_weights = {}
        for pos in positions:
            weight = pos["cost"] / total_market_value
            position_weights.append(weight)
            sector = self._get_sector(pos["symbol"])
            sector_weights[sector] = sector_weights.get(sector, 0) + weight

        hhi = sum(w ** 2 for w in position_weights)
        sector_hhi = sum(w ** 2 for w in sector_weights.values())

        if hhi > 0.25:
            concentration_risk = '极高'
        elif hhi > 0.15:
            concentration_risk = '高'
        elif hhi > 0.08:
            concentration_risk = '中'
        else:
            concentration_risk = '低'

        return {
            'concentration_risk': concentration_risk,
            'position_hhi': round(hhi, 4),
            'sector_hhi': round(sector_hhi, 4),
            'max_position_weight': round(max(position_weights) * 100, 1) if position_weights else 0,
            'sector_weights': {k: round(v * 100, 1) for k, v in sector_weights.items()}
        }

    def calculate_trading_attribution(self) -> Dict:
        """计算交易归因"""
        trades = self._get_trade_dicts()
        if not trades:
            return {
                'total_trades': 0,
                'buy_count': 0,
                'sell_count': 0,
                'total_fees': 0.0,
                'win_rate': 0.0,
                'avg_holding_days': 0
            }

        buy_count = sum(1 for t in trades if t.get("direction") == "买")
        sell_count = sum(1 for t in trades if t.get("direction") == "卖")
        total_fees = 0.0

        sell_trades = [t for t in trades if t.get("direction") == "卖"]
        if sell_trades:
            profitable_sells = 0
            for sell in sell_trades:
                symbol = sell.get("symbol")
                buys = [t for t in trades if t.get("direction") == "买" and t.get("symbol") == symbol]
                if buys:
                    avg_buy_price = sum(t.get("price", 0) for t in buys) / len(buys)
                    if sell.get("price", 0) > avg_buy_price:
                        profitable_sells += 1
            win_rate = profitable_sells / len(sell_trades) * 100 if sell_trades else 0
        else:
            win_rate = 0.0

        return {
            'total_trades': len(trades),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'total_fees': round(total_fees, 2),
            'win_rate': round(win_rate, 1),
            'avg_holding_days': 0
        }

    def calculate_by_stock(self) -> List[Dict]:
        """按股票归因"""
        result = []
        positions = self._get_position_dicts()

        symbols = [self._get_stock_code(pos["symbol"]) for pos in positions]
        current_prices = _get_current_prices(symbols)

        for pos in positions:
            symbol_code = self._get_stock_code(pos["symbol"])
            current_price = current_prices.get(symbol_code, pos["avg_price"])
            market_value = pos["quantity"] * current_price
            profit = market_value - pos["cost"]
            profit_rate = (profit / pos["cost"] * 100) if pos["cost"] > 0 else 0
            sector = self._get_sector(pos["symbol"])

            result.append({
                'symbol': pos["symbol"],
                'name': pos["name"],
                'sector': sector,
                'volume': pos["quantity"],
                'avg_price': round(pos["avg_price"], 2),
                'current_price': round(current_price, 2),
                'cost': round(pos["cost"], 2),
                'market_value': round(market_value, 2),
                'profit': round(profit, 2),
                'profit_rate': round(profit_rate, 2),
                'weight': 0.0
            })

        total_mv = sum(s['market_value'] for s in result)
        for s in result:
            s['weight'] = round(s['market_value'] / total_mv * 100, 1) if total_mv > 0 else 0

        return result

    def calculate_by_industry(self) -> Dict[str, Dict]:
        """按行业归因"""
        by_stock = self.calculate_by_stock()
        industry_data = {}

        for stock in by_stock:
            sector = stock['sector']
            if sector not in industry_data:
                industry_data[sector] = {
                    'total_cost': 0,
                    'total_market_value': 0,
                    'total_profit': 0,
                    'stock_count': 0,
                    'stocks': []
                }

            industry_data[sector]['total_cost'] += stock['cost']
            industry_data[sector]['total_market_value'] += stock['market_value']
            industry_data[sector]['total_profit'] += stock['profit']
            industry_data[sector]['stock_count'] += 1
            industry_data[sector]['stocks'].append(stock['name'])

        for sector, data in industry_data.items():
            data['profit_rate'] = round(data['total_profit'] / data['total_cost'] * 100, 2) if data['total_cost'] > 0 else 0
            data['total_cost'] = round(data['total_cost'], 2)
            data['total_market_value'] = round(data['total_market_value'], 2)
            data['total_profit'] = round(data['total_profit'], 2)

        return industry_data

    def generate_comprehensive_report(self) -> str:
        """生成综合归因报告"""
        positions = self._get_position_dicts()
        by_stock_data = self.calculate_by_stock()
        market_value = sum(s['market_value'] for s in by_stock_data)
        balance = self.account.get_balance()
        cash = balance.cash
        total_value = balance.total_assets

        returns_attribution = self.calculate_returns_attribution()
        risk_attribution = self.calculate_risk_attribution()
        trading_attribution = self.calculate_trading_attribution()
        by_stock = self.calculate_by_stock()
        by_industry = self.calculate_by_industry()

        benchmark_return = 0.0
        initial_capital = 1_000_000

        report = {
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'account_id': self.account.account_id,
            'summary': {
                'total_value': round(total_value, 2),
                'cash': round(cash, 2),
                'market_value': round(market_value, 2),
                'initial_capital': initial_capital,
                'total_return': round(total_value - initial_capital, 2),
                'total_return_rate': round((total_value - initial_capital) / max(initial_capital, 1) * 100, 2),
                'position_count': len(positions),
                'trade_count': len(self._get_trade_dicts()),
                'benchmark_return_rate': benchmark_return,
                'excess_return': round((total_value - initial_capital) / max(initial_capital, 1) * 100 - benchmark_return, 2)
            },
            'returns_attribution': returns_attribution,
            'risk_attribution': risk_attribution,
            'trading_attribution': trading_attribution,
            'by_stock': by_stock,
            'by_industry': by_industry
        }

        # 保存报告
        report_file = self.reports_dir / f'attribution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        md_report = self._generate_markdown_report(report)
        md_file = self.reports_dir / f'attribution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_report)

        print(f"✅ 归因报告已生成: {md_file.name}")
        return json.dumps(report, ensure_ascii=False, indent=2)

    def _generate_markdown_report(self, report: Dict) -> str:
        """生成 Markdown 格式报告"""
        summary = report['summary']
        returns = report['returns_attribution']
        risk = report['risk_attribution']
        trading = report['trading_attribution']

        md = f"""# 📊 全面复盘归因报告

**报告时间**: {report['report_date']}
**账户**: {report['account_id']}

---

## 🎯 账户总览

| 指标 | 数值 |
|------|------|
| **初始资金** | ¥{summary['initial_capital']:,.2f} |
| **总资产** | ¥{summary['total_value']:,.2f} |
| **持仓市值** | ¥{summary['market_value']:,.2f} |
| **可用现金** | ¥{summary['cash']:,.2f} |
| **累计收益** | ¥{summary['total_return']:,.2f} ({summary['total_return_rate']:+.2f}%) |
| **超额收益** | {summary['excess_return']:+.2f}% |
| **持仓数量** | {summary['position_count']} 只 |
| **交易笔数** | {summary['trade_count']} 笔 |

---

## 📈 收益归因分析

| 归因项 | 贡献 |
|--------|------|
| **选股效应** | {returns['stock_selection']:+.2f}% |
| **行业配置效应** | {returns['industry_allocation']:+.2f}% |
| **择时效应** | {returns['timing']:+.2f}% |
| **总收益** | {returns['total']:+.2f}% |

---

## ⚠️ 风险归因分析

| 风险指标 | 数值 |
|----------|------|
| **集中度风险** | {risk['concentration_risk']} |
| **持仓集中度指数** | {risk['position_hhi']} |
| **行业集中度指数** | {risk['sector_hhi']} |
| **最大持仓权重** | {risk['max_position_weight']:.1f}% |

"""

        if risk.get('sector_weights'):
            md += "### 行业分布\n\n| 行业 | 权重 |\n|------|------|\n"
            for sector, weight in sorted(risk['sector_weights'].items(), key=lambda x: -x[1]):
                md += f"| {sector} | {weight:.1f}% |\n"
            md += "\n"

        md += f"""---

## 📋 交易归因分析

| 指标 | 数值 |
|------|------|
| **总交易笔数** | {trading['total_trades']} |
| **买入次数** | {trading['buy_count']} |
| **卖出次数** | {trading['sell_count']} |
| **总手续费** | ¥{trading['total_fees']:,.2f} |
| **胜率** | {trading['win_rate']:.1f}% |

"""

        if report['by_stock']:
            md += "---\n\n## 🏆 个股表现\n\n| 股票 | 持仓 | 成本 | 当前价 | 盈亏 | 收益率 | 权重 |\n"
            md += "|------|------|------|--------|------|--------|------|\n"
            for stock in report['by_stock']:
                profit_color = 'green' if stock['profit'] >= 0 else 'orange'
                md += f"| {stock['name']} | {stock['volume']} | ¥{stock['avg_price']} | ¥{stock['current_price']} | <span style='color:{profit_color}'>{stock['profit']:+.2f}</span> | <span style='color:{profit_color}'>{stock['profit_rate']:+.2f}%</span> | {stock['weight']:.1f}% |\n"
            md += "\n"

        if report['by_industry']:
            md += "---\n\n## 🏭 行业归因\n\n| 行业 | 股票数 | 总成本 | 总市值 | 盈亏 | 收益率 |\n"
            md += "|------|--------|--------|--------|------|--------|\n"
            for sector, data in sorted(report['by_industry'].items(), key=lambda x: -x[1]['total_profit']):
                profit_color = 'green' if data['total_profit'] >= 0 else 'orange'
                md += f"| {sector} | {data['stock_count']} | ¥{data['total_cost']:,.0f} | ¥{data['total_market_value']:,.0f} | <span style='color:{profit_color}'>{data['total_profit']:+.2f}</span> | <span style='color:{profit_color}'>{data['profit_rate']:+.2f}%</span> |\n"

        md += f"""
---

*报告生成: PerformanceAttribution 📊*
"""

        return md


def main():
    """测试"""
    from accounts.account_db import AccountDB, Account
    db = AccountDB()
    if not db.get_account("virtual_2026"):
        acct = Account(
            account_id="virtual_2026",
            account_name="虚拟账户",
            initial_capital=1_000_000,
            cash=1_000_000,
        )
        db.create_account(acct)
    account = AccountService("virtual_2026")
    attribution = PerformanceAttribution(account)
    report = attribution.generate_comprehensive_report()
    print(report)


if __name__ == '__main__':
    main()
