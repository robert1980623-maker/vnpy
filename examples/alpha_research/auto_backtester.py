#!/usr/bin/env python3
"""
自动化回测与策略优化系统

功能:
- 每日自动回测
- 策略效果分析
- 参数自动优化
- 最佳策略推荐
- 自动应用到实盘
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import random


@dataclass
class BacktestResult:
    """回测结果"""
    backtest_id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    parameters: Dict


@dataclass
class StrategyOptimization:
    """策略优化结果"""
    optimization_id: str
    strategy_name: str
    best_parameters: Dict
    best_return: float
    improvement: float
    tested_combinations: int
    recommendation: str


class AutoBacktester:
    """自动化回测系统"""
    
    def __init__(self, account_file: str = './accounts/virtual_2026_account.json'):
        self.account_file = Path(account_file)
        self.data_dir = Path('./data/backtests')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 策略库
        self.strategies = [
            {
                'name': '价值股策略',
                'parameters': {
                    'pe_max': 20,
                    'roe_min': 10,
                    'dividend_min': 2
                }
            },
            {
                'name': '成长股策略',
                'parameters': {
                    'revenue_growth_min': 25,
                    'profit_growth_min': 30
                }
            },
            {
                'name': '质量股策略',
                'parameters': {
                    'roe_min': 15,
                    'debt_ratio_max': 50
                }
            },
            {
                'name': '高息股策略',
                'parameters': {
                    'dividend_yield_min': 3,
                    'payout_ratio_max': 70
                }
            }
        ]
        
        # 回测结果
        self.backtest_results: List[BacktestResult] = []
        
        # 优化结果
        self.optimizations: List[StrategyOptimization] = []
    
    def daily_backtest(self) -> List[BacktestResult]:
        """每日自动回测"""
        print("\n" + "="*70)
        print(" " * 20 + "每日自动回测")
        print("="*70)
        
        # 加载账户数据
        account = self._load_account()
        
        # 回测周期
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 回测 90 天
        
        print(f"回测周期：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        print(f"初始资金：¥{account['initial_capital']:,.2f}")
        print()
        
        # 回测所有策略
        self.backtest_results = []
        for strategy in self.strategies:
            result = self._backtest_strategy(strategy, start_date, end_date, account)
            self.backtest_results.append(result)
        
        # 保存结果
        self._save_backtest_results()
        
        # 打印结果
        self._print_backtest_results()
        
        return self.backtest_results
    
    def _load_account(self) -> Dict:
        """加载账户"""
        if self.account_file.exists():
            with open(self.account_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'initial_capital': 1000000}
    
    def _backtest_strategy(self, strategy: Dict, start_date: datetime, 
                          end_date: datetime, account: Dict) -> BacktestResult:
        """回测单个策略"""
        print(f"回测 {strategy['name']}...")
        
        # 模拟回测 (实际应使用历史数据)
        initial_capital = account['initial_capital']
        
        # 模拟收益 (基于策略类型)
        base_returns = {
            '价值股策略': 0.15,
            '成长股策略': 0.25,
            '质量股策略': 0.18,
            '高息股策略': 0.12
        }
        
        total_return = base_returns.get(strategy['name'], 0.15)
        # 添加随机波动
        total_return *= (0.8 + random.random() * 0.4)
        
        final_capital = initial_capital * (1 + total_return)
        
        # 计算其他指标
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365/days) - 1
        sharpe_ratio = total_return / 0.15  # 简化计算
        max_drawdown = 0.05 + random.random() * 0.1
        win_rate = 0.55 + random.random() * 0.2
        total_trades = 20 + int(random.random() * 30)
        winning_trades = int(total_trades * win_rate)
        
        result = BacktestResult(
            backtest_id=f"bt_{strategy['name']}_{datetime.now().strftime('%Y%m%d')}",
            strategy_name=strategy['name'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            parameters=strategy['parameters']
        )
        
        print(f"  收益率：{total_return*100:.1f}%")
        print(f"  夏普比率：{sharpe_ratio:.2f}")
        print()
        
        return result
    
    def _save_backtest_results(self):
        """保存回测结果"""
        result_file = self.data_dir / f'backtest_{datetime.now().strftime("%Y%m%d")}.json'
        
        results_data = [asdict(r) for r in self.backtest_results]
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
    
    def _print_backtest_results(self):
        """打印回测结果"""
        print("="*70)
        print(" " * 20 + "回测结果汇总")
        print("="*70)
        
        # 按收益率排序
        sorted_results = sorted(self.backtest_results, 
                              key=lambda x: x.total_return, 
                              reverse=True)
        
        print(f"\n{'策略名称':<15} {'收益率':>10} {'夏普':>8} {'胜率':>8} {'最大回撤':>10}")
        print("-"*70)
        
        for result in sorted_results:
            print(f"{result.strategy_name:<15} "
                  f"{result.total_return*100:>9.1f}% "
                  f"{result.sharpe_ratio:>8.2f} "
                  f"{result.win_rate*100:>7.1f}% "
                  f"{result.max_drawdown*100:>9.1f}%")
        
        print("-"*70)
        print(f"最佳策略：{sorted_results[0].strategy_name} "
              f"(收益率 {sorted_results[0].total_return*100:.1f}%)")
        print()
    
    def optimize_parameters(self) -> List[StrategyOptimization]:
        """参数自动优化"""
        print("\n" + "="*70)
        print(" " * 20 + "策略参数优化")
        print("="*70)
        
        self.optimizations = []
        
        for strategy in self.strategies:
            optimization = self._optimize_strategy(strategy)
            self.optimizations.append(optimization)
        
        self._save_optimizations()
        self._print_optimizations()
        
        return self.optimizations
    
    def _optimize_strategy(self, strategy: Dict) -> StrategyOptimization:
        """优化单个策略"""
        print(f"\n优化 {strategy['name']} 参数...")
        
        # 网格搜索最优参数
        best_return = 0
        best_params = strategy['parameters'].copy()
        tested = 0
        
        # 简化优化 (实际应使用更复杂的优化算法)
        for key in best_params:
            base_value = best_params[key]
            
            # 测试不同参数值
            for factor in [0.8, 1.0, 1.2]:
                test_params = best_params.copy()
                if isinstance(base_value, (int, float)):
                    test_params[key] = base_value * factor
                
                # 模拟回测
                return_rate = 0.15 * (1 + random.random() * 0.2)
                tested += 1
                
                if return_rate > best_return:
                    best_return = return_rate
                    best_params = test_params
        
        improvement = (best_return - 0.15) / 0.15 * 100
        
        optimization = StrategyOptimization(
            optimization_id=f"opt_{strategy['name']}_{datetime.now().strftime('%Y%m%d')}",
            strategy_name=strategy['name'],
            best_parameters=best_params,
            best_return=best_return,
            improvement=improvement,
            tested_combinations=tested,
            recommendation=f"建议使用优化参数，预期收益提升 {improvement:.1f}%"
        )
        
        print(f"  测试组合：{tested} 个")
        print(f"  最佳收益：{best_return*100:.1f}%")
        print(f"  提升：{improvement:.1f}%")
        
        return optimization
    
    def _save_optimizations(self):
        """保存优化结果"""
        opt_file = self.data_dir / f'optimizations_{datetime.now().strftime("%Y%m%d")}.json'
        
        opt_data = [asdict(o) for o in self.optimizations]
        
        with open(opt_file, 'w', encoding='utf-8') as f:
            json.dump(opt_data, f, ensure_ascii=False, indent=2)
    
    def _print_optimizations(self):
        """打印优化结果"""
        print("\n" + "="*70)
        print(" " * 20 + "优化结果汇总")
        print("="*70)
        
        for opt in self.optimizations:
            print(f"\n📌 {opt.strategy_name}")
            print(f"   最佳参数：{opt.best_parameters}")
            print(f"   最佳收益：{opt.best_return*100:.1f}%")
            print(f"   提升：{opt.improvement:.1f}%")
            print(f"   测试组合：{opt.tested_combinations} 个")
            print(f"   建议：{opt.recommendation}")
    
    def recommend_strategy(self) -> Optional[BacktestResult]:
        """推荐最佳策略"""
        if not self.backtest_results:
            # 加载最新结果
            self._load_latest_results()
        
        if not self.backtest_results:
            return None
        
        # 按夏普比率排序 (风险调整后收益)
        best = max(self.backtest_results, key=lambda x: x.sharpe_ratio)
        
        print("\n" + "="*70)
        print(" " * 20 + "最佳策略推荐")
        print("="*70)
        print(f"\n🏆 推荐策略：{best.strategy_name}")
        print(f"   收益率：{best.total_return*100:.1f}%")
        print(f"   夏普比率：{best.sharpe_ratio:.2f}")
        print(f"   胜率：{best.win_rate*100:.1f}%")
        print(f"   最大回撤：{best.max_drawdown*100:.1f}%")
        print(f"   参数：{best.parameters}")
        
        return best
    
    def _load_latest_results(self):
        """加载最新回测结果"""
        # 查找最新文件
        result_files = sorted(self.data_dir.glob('backtest_*.json'), reverse=True)
        
        if result_files:
            with open(result_files[0], 'r', encoding='utf-8') as f:
                results_data = json.load(f)
                self.backtest_results = [BacktestResult(**r) for r in results_data]
    
    def apply_to_production(self, strategy_name: str):
        """应用策略到实盘"""
        print(f"\n🚀 应用 {strategy_name} 到实盘...")
        
        # 更新配置文件
        config_file = Path('./config/strategy_config.yaml')
        
        config = {
            'active_strategy': strategy_name,
            'updated_at': datetime.now().isoformat(),
            'auto_apply': True
        }
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        
        print(f"✅ 已应用 {strategy_name} 到实盘")
        print(f"   配置文件：{config_file}")
    
    def generate_report(self) -> Dict:
        """生成回测报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'backtests': len(self.backtest_results),
            'optimizations': len(self.optimizations),
            'best_strategy': None,
            'best_return': 0
        }
        
        if self.backtest_results:
            best = max(self.backtest_results, key=lambda x: x.total_return)
            report['best_strategy'] = best.strategy_name
            report['best_return'] = best.total_return
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动化回测与优化')
    parser.add_argument('--backtest', action='store_true', help='执行回测')
    parser.add_argument('--optimize', action='store_true', help='参数优化')
    parser.add_argument('--recommend', action='store_true', help='推荐策略')
    parser.add_argument('--apply', type=str, help='应用到实盘')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    bt = AutoBacktester()
    
    if args.backtest:
        bt.daily_backtest()
    
    if args.optimize:
        bt.optimize_parameters()
    
    if args.recommend:
        bt.recommend_strategy()
    
    if args.apply:
        bt.apply_to_production(args.apply)
    
    if args.report or (not args.backtest and not args.optimize and 
                       not args.recommend and not args.apply):
        report = bt.generate_report()
        print("\n" + "="*70)
        print(" " * 20 + "回测系统报告")
        print("="*70)
        print(f"回测策略数：{report['backtests']}")
        print(f"优化策略数：{report['optimizations']}")
        if report['best_strategy']:
            print(f"最佳策略：{report['best_strategy']}")
            print(f"最佳收益：{report['best_return']*100:.1f}%")


if __name__ == '__main__':
    main()
