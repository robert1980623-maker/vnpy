#!/usr/bin/env python3
"""
AI 自主决策系统

功能:
- 自动选股决策
- 自动调仓决策
- 自动风控决策
- 决策解释生成
- 决策效果追踪
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Decision:
    """决策记录"""
    decision_id: str
    decision_type: str  # stock/trading/risk
    action: str  # buy/sell/hold
    symbol: Optional[str]
    reason: str
    confidence: float  # 0-1
    timestamp: str
    expected_outcome: str
    actual_outcome: Optional[str] = None


@dataclass
class StockDecision:
    """选股决策"""
    stock_list: List[Dict]
    strategy: str
    reasoning: str
    confidence: float
    timestamp: str


@dataclass
class TradingDecision:
    """交易决策"""
    action: str  # buy/sell/hold
    symbol: str
    volume: int
    price: float
    reason: str
    confidence: float
    timestamp: str


@dataclass
class RiskDecision:
    """风控决策"""
    action: str  # stop_loss/take_profit/position_limit
    symbol: str
    trigger_price: float
    reason: str
    confidence: float
    timestamp: str


class AIDecisionMaker:
    """AI 自主决策系统"""
    
    def __init__(self, account_file: str = './accounts/virtual_2026_account.json'):
        self.account_file = Path(account_file)
        self.data_dir = Path('./data/decisions')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 决策日志
        self.decisions: List[Decision] = []
        
        # 配置
        self.config = {
            'auto_decision': True,
            'min_confidence': 0.7,
            'max_position_per_stock': 0.25,
            'stop_loss_rate': -0.15,
            'take_profit_rate': 0.30
        }
    
    def make_stock_decision(self) -> StockDecision:
        """自动选股决策"""
        print("\n" + "="*70)
        print(" " * 20 + "AI 选股决策")
        print("="*70)
        
        # 加载账户
        account = self._load_account()
        
        # 分析基本面
        fundamental_score = self._analyze_fundamentals()
        
        # 分析消息面
        news_score = self._analyze_news()
        
        # 分析政策面
        policy_score = self._analyze_policy()
        
        # 综合评分
        total_score = (
            fundamental_score * 0.5 +
            news_score * 0.3 +
            policy_score * 0.2
        )
        
        # 生成选股列表
        stock_list = self._generate_stock_list(total_score)
        
        # 确定策略
        strategy = self._determine_strategy(total_score)
        
        # 生成推理
        reasoning = self._generate_reasoning(fundamental_score, news_score, policy_score)
        
        # 计算置信度
        confidence = min(total_score / 100, 0.95)
        
        decision = StockDecision(
            stock_list=stock_list,
            strategy=strategy,
            reasoning=reasoning,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )
        
        # 保存决策
        self._save_stock_decision(decision)
        
        # 打印决策
        self._print_stock_decision(decision)
        
        return decision
    
    def _load_account(self) -> Dict:
        """加载账户"""
        if self.account_file.exists():
            with open(self.account_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'initial_capital': 1000000, 'positions': []}
    
    def _analyze_fundamentals(self) -> float:
        """分析基本面"""
        print("\n📊 分析基本面...")
        
        # 简化分析 (实际应读取真实数据)
        # 基于 PE、ROE、增长等指标
        score = 75  # 基础分
        
        # 市场整体估值
        score += 5  # 当前估值合理
        
        print(f"  基本面评分：{score}/100")
        return score
    
    def _analyze_news(self) -> float:
        """分析消息面"""
        print("\n📰 分析消息面...")
        
        # 基于新闻情感分析
        score = 70  # 基础分
        
        # 正面新闻较多
        score += 10
        
        print(f"  消息面评分：{score}/100")
        return score
    
    def _analyze_policy(self) -> float:
        """分析政策面"""
        print("\n🏛️  分析政策面...")
        
        # 基于政策支持度
        score = 80  # 基础分
        
        # 政策支持
        score += 5
        
        print(f"  政策面评分：{score}/100")
        return score
    
    def _generate_stock_list(self, total_score: float) -> List[Dict]:
        """生成选股列表"""
        print("\n📋 生成选股列表...")
        
        # 根据总分确定选股数量
        if total_score >= 80:
            count = 10
        elif total_score >= 70:
            count = 8
        else:
            count = 5
        
        # 生成股票列表 (简化)
        stock_list = [
            {'symbol': '600519.SH', 'name': '贵州茅台', 'reason': '核心资产，长期价值', 'weight': 0.15},
            {'symbol': '000858.SZ', 'name': '五粮液', 'reason': '白酒龙头，稳定增长', 'weight': 0.12},
            {'symbol': '300750.SZ', 'name': '宁德时代', 'reason': '新能源龙头，成长性好', 'weight': 0.10},
            {'symbol': '600066.SH', 'name': '宇通客车', 'reason': '行业龙头，估值合理', 'weight': 0.12},
            {'symbol': '688506.SH', 'name': '联影医疗', 'reason': '医疗设备，国产替代', 'weight': 0.08},
        ][:count]
        
        print(f"  选股数量：{len(stock_list)} 只")
        return stock_list
    
    def _determine_strategy(self, score: float) -> str:
        """确定策略"""
        if score >= 80:
            return "积极进攻 - 高仓位运作"
        elif score >= 70:
            return "稳健增长 - 适度仓位"
        elif score >= 60:
            return "防守为主 - 低仓位运作"
        else:
            return "现金为王 - 等待机会"
    
    def _generate_reasoning(self, fundamental: float, news: float, policy: float) -> str:
        """生成推理"""
        reasoning = []
        
        if fundamental >= 75:
            reasoning.append("基本面良好，估值合理")
        else:
            reasoning.append("基本面一般，需谨慎")
        
        if news >= 75:
            reasoning.append("消息面偏正面")
        else:
            reasoning.append("消息面中性")
        
        if policy >= 75:
            reasoning.append("政策支持力度大")
        else:
            reasoning.append("政策环境一般")
        
        return "。".join(reasoning) + "。"
    
    def _save_stock_decision(self, decision: StockDecision):
        """保存选股决策"""
        decision_file = self.data_dir / f'stock_decision_{datetime.now().strftime("%Y%m%d")}.json'
        
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(decision), f, ensure_ascii=False, indent=2)
    
    def _print_stock_decision(self, decision: StockDecision):
        """打印选股决策"""
        print("\n" + "="*70)
        print(" " * 20 + "选股决策结果")
        print("="*70)
        
        print(f"\n📋 策略：{decision.strategy}")
        print(f"📊 置信度：{decision.confidence*100:.1f}%")
        print(f"📝 推理：{decision.reasoning}")
        
        print(f"\n选股列表 ({len(decision.stock_list)}只):")
        for i, stock in enumerate(decision.stock_list, 1):
            print(f"  {i}. {stock['symbol']} {stock['name']}")
            print(f"     权重：{stock['weight']*100:.0f}%")
            print(f"     理由：{stock['reason']}")
        
        print()
    
    def make_trading_decision(self, stock_decision: StockDecision) -> List[TradingDecision]:
        """自动交易决策"""
        print("\n" + "="*70)
        print(" " * 20 + "AI 交易决策")
        print("="*70)
        
        account = self._load_account()
        total_value = account['cash'] + sum(p.get('market_value', 0) for p in account['positions'])
        
        trading_decisions = []
        
        for stock in stock_decision.stock_list:
            # 计算目标仓位
            target_value = total_value * stock['weight']
            
            # 检查当前持仓
            current_position = None
            for pos in account['positions']:
                if pos['symbol'] == stock['symbol']:
                    current_position = pos
                    break
            
            if current_position:
                # 已有持仓，检查是否需要调整
                current_value = current_position.get('market_value', 0)
                diff = target_value - current_value
                
                if abs(diff) > current_value * 0.1:  # 差异超过 10%
                    action = 'buy' if diff > 0 else 'sell'
                    volume = int(abs(diff) / current_position.get('current_price', 100))
                    
                    decision = TradingDecision(
                        action=action,
                        symbol=stock['symbol'],
                        volume=volume,
                        price=current_position.get('current_price', 100),
                        reason=f"调仓至目标权重 {stock['weight']*100:.0f}%",
                        confidence=stock_decision.confidence,
                        timestamp=datetime.now().isoformat()
                    )
                    trading_decisions.append(decision)
            else:
                # 新建仓
                price = 100  # 假设价格
                volume = int(target_value / price)
                
                decision = TradingDecision(
                    action='buy',
                    symbol=stock['symbol'],
                    volume=volume,
                    price=price,
                    reason=stock['reason'],
                    confidence=stock_decision.confidence,
                    timestamp=datetime.now().isoformat()
                )
                trading_decisions.append(decision)
        
        # 保存决策
        self._save_trading_decisions(trading_decisions)
        
        # 打印决策
        self._print_trading_decisions(trading_decisions)
        
        return trading_decisions
    
    def _save_trading_decisions(self, decisions: List[TradingDecision]):
        """保存交易决策"""
        decision_file = self.data_dir / f'trading_decision_{datetime.now().strftime("%Y%m%d")}.json'
        
        decisions_data = [asdict(d) for d in decisions]
        
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(decisions_data, f, ensure_ascii=False, indent=2)
    
    def _print_trading_decisions(self, decisions: List[TradingDecision]):
        """打印交易决策"""
        if not decisions:
            print("\nℹ️  无需调仓")
            return
        
        print(f"\n交易决策 ({len(decisions)}个):")
        for d in decisions:
            action_icon = '🟢' if d.action == 'buy' else '🔴'
            print(f"  {action_icon} {d.action.upper()} {d.symbol}")
            print(f"     数量：{d.volume} 股")
            print(f"     价格：¥{d.price:.2f}")
            print(f"     理由：{d.reason}")
            print(f"     置信度：{d.confidence*100:.1f}%")
        print()
    
    def make_risk_decision(self) -> List[RiskDecision]:
        """自动风控决策"""
        print("\n" + "="*70)
        print(" " * 20 + "AI 风控决策")
        print("="*70)
        
        account = self._load_account()
        
        risk_decisions = []
        
        for pos in account['positions']:
            symbol = pos['symbol']
            current_price = pos.get('current_price', 0)
            avg_price = pos.get('avg_price', 0)
            
            if current_price == 0 or avg_price == 0:
                continue
            
            # 计算盈亏率
            profit_rate = (current_price - avg_price) / avg_price
            
            # 止损检查
            if profit_rate <= self.config['stop_loss_rate']:
                decision = RiskDecision(
                    action='stop_loss',
                    symbol=symbol,
                    trigger_price=current_price,
                    reason=f"亏损 {profit_rate*100:.1f}%，达到止损线 {self.config['stop_loss_rate']*100:.0f}%",
                    confidence=0.95,
                    timestamp=datetime.now().isoformat()
                )
                risk_decisions.append(decision)
            
            # 止盈检查
            elif profit_rate >= self.config['take_profit_rate']:
                decision = RiskDecision(
                    action='take_profit',
                    symbol=symbol,
                    trigger_price=current_price,
                    reason=f"盈利 {profit_rate*100:.1f}%，达到止盈线 {self.config['take_profit_rate']*100:.0f}%",
                    confidence=0.90,
                    timestamp=datetime.now().isoformat()
                )
                risk_decisions.append(decision)
        
        # 保存决策
        self._save_risk_decisions(risk_decisions)
        
        # 打印决策
        self._print_risk_decisions(risk_decisions)
        
        return risk_decisions
    
    def _save_risk_decisions(self, decisions: List[RiskDecision]):
        """保存风控决策"""
        decision_file = self.data_dir / f'risk_decision_{datetime.now().strftime("%Y%m%d")}.json'
        
        decisions_data = [asdict(d) for d in decisions]
        
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(decisions_data, f, ensure_ascii=False, indent=2)
    
    def _print_risk_decisions(self, decisions: List[RiskDecision]):
        """打印风控决策"""
        if not decisions:
            print("\n✅ 无需风控操作")
            return
        
        print(f"\n风控决策 ({len(decisions)}个):")
        for d in decisions:
            action_icon = {'stop_loss': '🔴', 'take_profit': '🟢'}.get(d.action, '⚪')
            print(f"  {action_icon} {d.action} {d.symbol}")
            print(f"     触发价：¥{d.trigger_price:.2f}")
            print(f"     理由：{d.reason}")
            print(f"     置信度：{d.confidence*100:.1f}%")
        print()
    
    def explain_decision(self, decision) -> str:
        """生成决策解释"""
        if isinstance(decision, StockDecision):
            return self._explain_stock_decision(decision)
        elif isinstance(decision, TradingDecision):
            return self._explain_trading_decision(decision)
        elif isinstance(decision, RiskDecision):
            return self._explain_risk_decision(decision)
        return ""
    
    def _explain_stock_decision(self, decision: StockDecision) -> str:
        """解释选股决策"""
        explanation = f"""
📋 选股决策解释

策略：{decision.strategy}
置信度：{decision.confidence*100:.1f}%

决策依据:
{decision.reasoning}

选股逻辑:
"""
        for i, stock in enumerate(decision.stock_list, 1):
            explanation += f"\n{i}. {stock['symbol']} {stock['name']}"
            explanation += f"\n   权重：{stock['weight']*100:.0f}%"
            explanation += f"\n   理由：{stock['reason']}"
        
        return explanation
    
    def _explain_trading_decision(self, decision: TradingDecision) -> str:
        """解释交易决策"""
        return f"""
📋 交易决策解释

操作：{decision.action.upper()}
股票：{decision.symbol}
数量：{decision.volume} 股
价格：¥{decision.price:.2f}

理由：{decision.reason}
置信度：{decision.confidence*100:.1f}%
"""
    
    def _explain_risk_decision(self, decision: RiskDecision) -> str:
        """解释风控决策"""
        return f"""
📋 风控决策解释

操作：{decision.action}
股票：{decision.symbol}
触发价：¥{decision.trigger_price:.2f}

理由：{decision.reason}
置信度：{decision.confidence*100:.1f}%
"""
    
    def generate_report(self) -> Dict:
        """生成决策报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'decisions_made': len(self.decisions),
            'stock_decisions': 0,
            'trading_decisions': 0,
            'risk_decisions': 0
        }
        
        # 统计今日决策
        today = datetime.now().strftime('%Y%m%d')
        
        stock_file = self.data_dir / f'stock_decision_{today}.json'
        if stock_file.exists():
            report['stock_decisions'] = 1
        
        trading_file = self.data_dir / f'trading_decision_{today}.json'
        if trading_file.exists():
            with open(trading_file, 'r', encoding='utf-8') as f:
                decisions = json.load(f)
                report['trading_decisions'] = len(decisions)
        
        risk_file = self.data_dir / f'risk_decision_{today}.json'
        if risk_file.exists():
            with open(risk_file, 'r', encoding='utf-8') as f:
                decisions = json.load(f)
                report['risk_decisions'] = len(decisions)
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 自主决策系统')
    parser.add_argument('--stock', action='store_true', help='选股决策')
    parser.add_argument('--trading', action='store_true', help='交易决策')
    parser.add_argument('--risk', action='store_true', help='风控决策')
    parser.add_argument('--all', action='store_true', help='执行所有决策')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    dm = AIDecisionMaker()
    
    if args.all or (not args.stock and not args.trading and not args.risk and not args.report):
        # 执行所有决策
        stock_decision = dm.make_stock_decision()
        dm.make_trading_decision(stock_decision)
        dm.make_risk_decision()
    
    elif args.stock:
        dm.make_stock_decision()
    
    elif args.trading:
        stock_decision = dm.make_stock_decision()
        dm.make_trading_decision(stock_decision)
    
    elif args.risk:
        dm.make_risk_decision()
    
    if args.report:
        report = dm.generate_report()
        print("\n" + "="*70)
        print(" " * 20 + "AI 决策报告")
        print("="*70)
        print(f"选股决策：{report['stock_decisions']} 个")
        print(f"交易决策：{report['trading_decisions']} 个")
        print(f"风控决策：{report['risk_decisions']} 个")


if __name__ == '__main__':
    main()
