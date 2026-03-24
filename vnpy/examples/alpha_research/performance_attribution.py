#!/usr/bin/env python3
"""
绩效归因 Agent

功能:
- 收益来源分析 (选股 vs 择时)
- 策略贡献度分解
- 行业贡献分析
- 个股贡献分析
- Brinson 模型归因
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))


class PerformanceAttribution:
    """绩效归因分析器"""
    
    def __init__(self, account_file: str = None):
        if account_file is None:
            account_file = './accounts/virtual_2026_account.json'
        
        self.account_file = Path(account_file)
        self.benchmark_return = 0.0  # 基准收益 (如沪深 300)
    
    def load_account(self) -> Dict:
        """加载账户数据"""
        if not self.account_file.exists():
            raise FileNotFoundError(f"账户文件不存在：{self.account_file}")
        
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def calculate_daily_return(self, snapshots: List[Dict]) -> Dict:
        """
        计算每日收益归因
        
        Brinson 模型:
        总收益 = 配置收益 + 选股收益 + 交互收益
        """
        if len(snapshots) < 2:
            return {'error': '数据不足'}
        
        attribution_results = []
        
        for i in range(1, len(snapshots)):
            prev = snapshots[i-1]
            curr = snapshots[i]
            
            # 计算总收益
            total_return = (curr['total_value'] - prev['total_value']) / prev['total_value']
            
            # 计算市场收益 (假设基准收益)
            market_return = self.benchmark_return
            
            # 超额收益
            excess_return = total_return - market_return
            
            # 配置收益 (行业配置贡献)
            # 简化计算：行业权重变化 * 行业收益
            allocation_return = self._calculate_allocation_return(prev, curr)
            
            # 选股收益 (个股选择贡献)
            # 简化计算：行业内个股收益差异
            selection_return = self._calculate_selection_return(prev, curr)
            
            # 交互收益
            interaction_return = excess_return - allocation_return - selection_return
            
            attribution_results.append({
                'date': curr['date'],
                'total_return': total_return,
                'market_return': market_return,
                'excess_return': excess_return,
                'allocation_return': allocation_return,
                'selection_return': selection_return,
                'interaction_return': interaction_return,
                'daily_profit': curr['total_value'] - prev['total_value']
            })
        
        return {
            'daily_attribution': attribution_results,
            'summary': self._summarize_attribution(attribution_results)
        }
    
    def _calculate_allocation_return(self, prev: Dict, curr: Dict) -> float:
        """计算配置收益"""
        # 简化：假设行业收益等于市场收益
        # 实际应该使用行业指数收益
        return 0.0
    
    def _calculate_selection_return(self, prev: Dict, curr: Dict) -> float:
        """计算选股收益"""
        # 简化：选股收益 = 超额收益 - 配置收益
        total_return = (curr['total_value'] - prev['total_value']) / prev['total_value']
        return total_return - self.benchmark_return
    
    def _summarize_attribution(self, attribution_results: List[Dict]) -> Dict:
        """汇总归因结果"""
        if not attribution_results:
            return {}
        
        total_days = len(attribution_results)
        total_profit = sum(r['daily_profit'] for r in attribution_results)
        
        avg_total_return = sum(r['total_return'] for r in attribution_results) / total_days
        avg_excess_return = sum(r['excess_return'] for r in attribution_results) / total_days
        avg_allocation_return = sum(r['allocation_return'] for r in attribution_results) / total_days
        avg_selection_return = sum(r['selection_return'] for r in attribution_results) / total_days
        
        # 计算贡献度
        total_contrib = abs(avg_allocation_return) + abs(avg_selection_return)
        if total_contrib > 0:
            allocation_contrib = abs(avg_allocation_return) / total_contrib * 100
            selection_contrib = abs(avg_selection_return) / total_contrib * 100
        else:
            allocation_contrib = selection_contrib = 0
        
        return {
            'total_days': total_days,
            'total_profit': total_profit,
            'avg_total_return': avg_total_return,
            'avg_excess_return': avg_excess_return,
            'avg_allocation_return': avg_allocation_return,
            'avg_selection_return': avg_selection_return,
            'allocation_contrib_pct': allocation_contrib,
            'selection_contrib_pct': selection_contrib,
            'win_rate': sum(1 for r in attribution_results if r['daily_profit'] > 0) / total_days * 100
        }
    
    def analyze_position_contribution(self, positions: List[Dict], 
                                     start_value: float, end_value: float) -> Dict:
        """分析持仓贡献度"""
        total_profit = end_value - start_value
        
        contributions = []
        for pos in positions:
            profit = pos.get('profit', 0)
            contrib_pct = profit / total_profit * 100 if total_profit != 0 else 0
            
            contributions.append({
                'symbol': pos['symbol'],
                'name': pos['name'],
                'profit': profit,
                'contribution_pct': contrib_pct,
                'profit_rate': pos.get('profit_rate', 0)
            })
        
        # 按贡献排序
        contributions.sort(key=lambda x: x['profit'], reverse=True)
        
        return {
            'total_profit': total_profit,
            'contributions': contributions,
            'top_contributor': contributions[0] if contributions else None,
            'top_detractor': contributions[-1] if contributions else None
        }
    
    def analyze_industry_contribution(self, positions: List[Dict]) -> Dict:
        """分析行业贡献度"""
        industry_stats = {}
        
        for pos in positions:
            industry = pos.get('industry', '未知')
            if industry not in industry_stats:
                industry_stats[industry] = {
                    'count': 0,
                    'market_value': 0,
                    'profit': 0,
                    'stocks': []
                }
            
            industry_stats[industry]['count'] += 1
            industry_stats[industry]['market_value'] += pos.get('market_value', 0)
            industry_stats[industry]['profit'] += pos.get('profit', 0)
            industry_stats[industry]['stocks'].append(pos['name'])
        
        # 计算行业平均收益率
        for industry in industry_stats:
            mv = industry_stats[industry]['market_value']
            profit = industry_stats[industry]['profit']
            industry_stats[industry]['return_rate'] = profit / mv * 100 if mv > 0 else 0
        
        # 按利润排序
        sorted_industries = sorted(
            industry_stats.items(), 
            key=lambda x: x[1]['profit'], 
            reverse=True
        )
        
        return {
            'industry_stats': industry_stats,
            'sorted_industries': sorted_industries,
            'best_industry': sorted_industries[0][0] if sorted_industries else None,
            'worst_industry': sorted_industries[-1][0] if sorted_industries else None
        }
    
    def generate_report(self) -> str:
        """生成绩效归因报告"""
        try:
            account = self.load_account()
        except FileNotFoundError as e:
            return f"❌ {e}"
        
        report = []
        report.append("=" * 70)
        report.append("📊 绩效归因报告")
        report.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        # 账户概览
        cash = account.get('cash', 0)
        positions = account.get('positions', [])
        total_value = cash + sum(p.get('market_value', 0) for p in positions)
        
        report.append(f"\n💰 账户概览:")
        report.append(f"  总资产：¥{total_value:,.2f}")
        report.append(f"  现金：¥{cash:,.2f}")
        report.append(f"  持仓：{len(positions)} 只")
        
        # 收益归因
        snapshots = account.get('daily_snapshots', [])
        if len(snapshots) >= 2:
            attribution = self.calculate_daily_return(snapshots)
            summary = attribution.get('summary', {})
            
            report.append(f"\n📈 收益归因 (Brinson 模型):")
            report.append(f"  统计天数：{summary.get('total_days', 0)} 天")
            report.append(f"  总盈利：¥{summary.get('total_profit', 0):,.2f}")
            report.append(f"  胜率：{summary.get('win_rate', 0):.1f}%")
            report.append(f"\n  收益来源分解:")
            report.append(f"    配置收益贡献：{summary.get('allocation_contrib_pct', 0):.1f}%")
            report.append(f"    选股收益贡献：{summary.get('selection_contrib_pct', 0):.1f}%")
        
        # 持仓贡献
        if positions:
            initial_value = account.get('initial_capital', total_value)
            position_contrib = self.analyze_position_contribution(positions, initial_value, total_value)
            
            report.append(f"\n🎯 持仓贡献度 TOP5:")
            for i, contrib in enumerate(position_contrib['contributions'][:5], 1):
                report.append(f"  {i}. {contrib['name']}: ¥{contrib['profit']:,.2f} "
                            f"({contrib['contribution_pct']:+.1f}%)")
            
            if position_contrib['top_detractor'] and position_contrib['top_detractor']['profit'] < 0:
                report.append(f"\n  最大拖累：{position_contrib['top_detractor']['name']}: "
                            f"¥{position_contrib['top_detractor']['profit']:,.2f}")
        
        # 行业贡献
        if positions:
            industry_contrib = self.analyze_industry_contribution(positions)
            
            report.append(f"\n🏭 行业贡献:")
            for industry, stats in industry_contrib['sorted_industries'][:5]:
                report.append(f"  {industry}: ¥{stats['profit']:,.2f} "
                            f"({stats['return_rate']:+.2f}%, {stats['count']}只)")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)
    
    def save_report(self, output_dir: str = './reports/performance'):
        """保存报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_report()
        report_file = output_path / f'performance_attribution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 同时保存 JSON 格式
        json_file = output_path / f'performance_attribution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        try:
            account = self.load_account()
            snapshots = account.get('daily_snapshots', [])
            positions = account.get('positions', [])
            
            json_data = {
                'timestamp': datetime.now().isoformat(),
                'account_summary': {
                    'total_value': account.get('cash', 0) + sum(p.get('market_value', 0) for p in positions),
                    'cash': account.get('cash', 0),
                    'positions_count': len(positions)
                },
                'attribution': self.calculate_daily_return(snapshots) if len(snapshots) >= 2 else {},
                'position_contribution': self.analyze_position_contribution(
                    positions, 
                    account.get('initial_capital', 0),
                    account.get('cash', 0) + sum(p.get('market_value', 0) for p in positions)
                ),
                'industry_contribution': self.analyze_industry_contribution(positions)
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ JSON 保存失败：{e}")
        
        print(f"✅ 报告已保存：{report_file}")
        print(f"✅ JSON 已保存：{json_file}")
        
        return report


def main():
    """主函数"""
    attributor = PerformanceAttribution()
    report = attributor.generate_report()
    print(report)
    attributor.save_report()


if __name__ == '__main__':
    main()
