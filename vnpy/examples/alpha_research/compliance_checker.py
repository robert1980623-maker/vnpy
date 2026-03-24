#!/usr/bin/env python3
"""
合规检查 Agent

功能:
- 交易前合规验证
- 持仓合规检查
- 禁止股票筛选 (ST、停牌)
- 流动性检查
- 行业集中度控制
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


class ComplianceChecker:
    """合规检查器"""
    
    def __init__(self):
        # 合规规则
        self.rules = {
            'max_single_position': 0.15,      # 单只股票最大持仓 15%
            'max_industry_weight': 0.30,      # 行业集中度 30%
            'min_liquidity': 10000000,        # 最小日均成交 1000 万
            'forbid_st': True,                # 禁止 ST 股票
            'forbid_suspended': True,         # 禁止停牌股票
        }
        
        # 数据目录
        self.data_dir = Path('./data')
        self.cache_dir = self.data_dir / 'compliance_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载缓存
        self.stocks_cache = self._load_stocks_cache()
    
    def _load_stocks_cache(self) -> Dict:
        """加载股票基础信息缓存"""
        cache_file = self.cache_dir / 'stocks_info.json'
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'stocks': {}, 'last_update': None}
    
    def _save_stocks_cache(self):
        """保存股票基础信息缓存"""
        cache_file = self.cache_dir / 'stocks_info.json'
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.stocks_cache, f, ensure_ascii=False, indent=2)
    
    def is_st_stock(self, symbol: str, name: str = "") -> bool:
        """检查是否为 ST 股票"""
        # 从名称判断
        if name and ('ST' in name.upper() or '*ST' in name.upper()):
            return True
        
        # 从代码判断 (创业板 ST 有特殊标记)
        code = symbol.split('.')[0]
        if code.startswith('300') and name and 'ST' in name.upper():
            return True
        
        return False
    
    def is_suspended(self, symbol: str) -> bool:
        """检查是否停牌 (需要实时数据，这里简化处理)"""
        # TODO: 接入实时停牌数据
        # 目前返回 False，实际使用需要接入交易所数据
        return False
    
    def check_liquidity(self, symbol: str, min_avg_volume: float = None) -> Tuple[bool, float]:
        """
        检查流动性
        
        Returns:
            (是否合格，日均成交额)
        """
        if min_avg_volume is None:
            min_avg_volume = self.rules['min_liquidity']
        
        # TODO: 接入真实流动性数据
        # 目前简化处理，返回合格
        return True, min_avg_volume * 2
    
    def check_single_position(self, position_value: float, total_value: float) -> Tuple[bool, float]:
        """
        检查单只股票持仓比例
        
        Returns:
            (是否合格，当前比例)
        """
        if total_value == 0:
            return True, 0.0
        
        ratio = position_value / total_value
        return ratio <= self.rules['max_single_position'], ratio
    
    def check_industry_concentration(self, positions: List[Dict], total_value: float) -> Dict:
        """
        检查行业集中度
        
        Returns:
            {
                'passed': bool,
                'industry_weights': Dict[str, float],
                'max_industry': str,
                'max_weight': float
            }
        """
        if total_value == 0:
            return {
                'passed': True,
                'industry_weights': {},
                'max_industry': None,
                'max_weight': 0.0
            }
        
        # 按行业统计市值
        industry_values = {}
        for pos in positions:
            industry = pos.get('industry', '未知')
            market_value = pos.get('market_value', 0)
            industry_values[industry] = industry_values.get(industry, 0) + market_value
        
        # 计算行业权重
        industry_weights = {
            ind: value / total_value 
            for ind, value in industry_values.items()
        }
        
        # 找出最大行业权重
        max_industry = max(industry_weights, key=industry_weights.get) if industry_weights else None
        max_weight = industry_weights.get(max_industry, 0) if max_industry else 0
        
        return {
            'passed': max_weight <= self.rules['max_industry_weight'],
            'industry_weights': industry_weights,
            'max_industry': max_industry,
            'max_weight': max_weight
        }
    
    def pre_trade_check(self, symbol: str, name: str, price: float, volume: int, 
                       current_positions: Dict, total_value: float) -> Dict:
        """
        交易前合规检查
        
        Returns:
            {
                'passed': bool,
                'violations': List[str],
                'warnings': List[str]
            }
        """
        violations = []
        warnings = []
        
        trade_value = price * volume
        
        # 1. 检查 ST 股票
        if self.rules['forbid_st'] and self.is_st_stock(symbol, name):
            violations.append(f"❌ 禁止买入 ST 股票：{name}")
        
        # 2. 检查停牌
        if self.rules['forbid_suspended'] and self.is_suspended(symbol):
            violations.append(f"❌ 股票停牌：{name}")
        
        # 3. 检查流动性
        liquidity_ok, avg_volume = self.check_liquidity(symbol)
        if not liquidity_ok:
            violations.append(f"❌ 流动性不足：{name} (日均成交 {avg_volume/10000:.0f}万 < {self.rules['min_liquidity']/10000:.0f}万)")
        
        # 4. 检查单只股票持仓
        if symbol in current_positions:
            current_value = current_positions[symbol].get('market_value', 0)
            new_value = current_value + trade_value
            passed, ratio = self.check_single_position(new_value, total_value + trade_value)
            if not passed:
                violations.append(f"❌ 单只股票超仓：{name} ({ratio*100:.1f}% > {self.rules['max_single_position']*100:.0f}%)")
        else:
            passed, ratio = self.check_single_position(trade_value, total_value + trade_value)
            if not passed:
                violations.append(f"❌ 单只股票超仓：{name} ({ratio*100:.1f}% > {self.rules['max_single_position']*100:.0f}%)")
        
        # 5. 检查现金是否足够
        cash_needed = trade_value * 1.001  # 包含手续费
        # 这里不检查现金，由交易模块负责
        
        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }
    
    def portfolio_check(self, positions: List[Dict], total_value: float) -> Dict:
        """
        持仓组合合规检查
        
        Returns:
            {
                'passed': bool,
                'violations': List[str],
                'warnings': List[str],
                'details': Dict
            }
        """
        violations = []
        warnings = []
        details = {}
        
        # 1. 检查单只股票持仓
        for pos in positions:
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')
            market_value = pos.get('market_value', 0)
            
            passed, ratio = self.check_single_position(market_value, total_value)
            if not passed:
                violations.append(f"❌ 单只股票超仓：{name} ({ratio*100:.1f}% > {self.rules['max_single_position']*100:.0f}%)")
            
            details[symbol] = {
                'ratio': ratio,
                'passed': passed
            }
        
        # 2. 检查行业集中度
        industry_check = self.check_industry_concentration(positions, total_value)
        if not industry_check['passed']:
            violations.append(
                f"❌ 行业集中度过高：{industry_check['max_industry']} "
                f"({industry_check['max_weight']*100:.1f}% > {self.rules['max_industry_weight']*100:.0f}%)"
            )
        details['industry'] = industry_check
        
        # 3. 检查 ST 股票
        for pos in positions:
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')
            if self.is_st_stock(symbol, name):
                warnings.append(f"⚠️ 持仓包含 ST 股票：{name}")
        
        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'details': details
        }
    
    def generate_report(self, positions: List[Dict], total_value: float, 
                       pending_trades: List[Dict] = None) -> str:
        """生成合规报告"""
        report = []
        report.append("=" * 60)
        report.append("📋 合规检查报告")
        report.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        # 持仓检查
        portfolio_check = self.portfolio_check(positions, total_value)
        
        report.append(f"\n总资产：¥{total_value:,.2f}")
        report.append(f"持仓数量：{len(positions)} 只")
        
        report.append(f"\n✅ 合规状态：{'通过' if portfolio_check['passed'] else '不通过'}")
        
        if portfolio_check['violations']:
            report.append("\n❌ 违规项:")
            for v in portfolio_check['violations']:
                report.append(f"  {v}")
        
        if portfolio_check['warnings']:
            report.append("\n⚠️ 警告项:")
            for w in portfolio_check['warnings']:
                report.append(f"  {w}")
        
        # 行业分布
        if 'industry' in portfolio_check['details']:
            industry = portfolio_check['details']['industry']
            report.append("\n📊 行业分布:")
            for ind, weight in sorted(industry['industry_weights'].items(), 
                                     key=lambda x: x[1], reverse=True)[:5]:
                report.append(f"  {ind}: {weight*100:.1f}%")
        
        # 待交易检查
        if pending_trades:
            report.append("\n" + "=" * 60)
            report.append("📝 待交易合规检查")
            report.append("=" * 60)
            
            for trade in pending_trades:
                check = self.pre_trade_check(
                    trade['symbol'],
                    trade.get('name', ''),
                    trade['price'],
                    trade['volume'],
                    {p['symbol']: p for p in positions},
                    total_value
                )
                
                status = "✅" if check['passed'] else "❌"
                report.append(f"\n{status} {trade['symbol']} {trade.get('name', '')}: "
                            f"{trade['direction'].upper()} {trade['volume']}股 @ ¥{trade['price']}")
                
                if check['violations']:
                    for v in check['violations']:
                        report.append(f"    {v}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


def main():
    """测试合规检查器"""
    checker = ComplianceChecker()
    
    # 模拟持仓
    positions = [
        {'symbol': '000001.SZ', 'name': '平安银行', 'market_value': 100000, 'industry': '银行'},
        {'symbol': '600036.SS', 'name': '招商银行', 'market_value': 150000, 'industry': '银行'},
        {'symbol': '300750.SZ', 'name': '宁德时代', 'market_value': 200000, 'industry': '新能源汽车'},
    ]
    
    total_value = 1000000
    
    # 生成报告
    report = checker.generate_report(positions, total_value)
    print(report)
    
    # 保存报告
    report_file = Path('./reports/compliance/compliance_check_' + 
                      datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt')
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存：{report_file}")


if __name__ == '__main__':
    main()
