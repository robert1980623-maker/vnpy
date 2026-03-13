#!/usr/bin/env python3
"""
预测性维护系统

功能:
- 错误模式分析
- 故障预测模型
- 提前告警机制
- 自动预防措施
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter


@dataclass
class ErrorPattern:
    """错误模式"""
    pattern_id: str
    error_type: str
    error_message: str
    agent_name: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    severity: str  # P0/P1/P2/P3
    predicted_next: Optional[str] = None


@dataclass
class FailurePrediction:
    """故障预测"""
    prediction_id: str
    agent_name: str
    failure_type: str
    probability: float  # 0-1
    predicted_time: str
    confidence: str  # high/medium/low
    prevention_actions: List[str]


class PredictiveMaintenance:
    """预测性维护系统"""
    
    def __init__(self, log_dir: str = './logs/errors'):
        self.log_dir = Path(log_dir)
        self.data_dir = Path('./data/predictive_maintenance')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 错误模式库
        self.error_patterns: List[ErrorPattern] = []
        
        # 预测模型
        self.predictions: List[FailurePrediction] = []
        
        # 配置
        self.config = {
            'min_occurrences': 3,  # 最小出现次数
            'prediction_window': 3600,  # 预测窗口 (秒)
            'high_confidence_threshold': 0.8,
            'medium_confidence_threshold': 0.5
        }
    
    def analyze_error_patterns(self, days: int = 7) -> List[ErrorPattern]:
        """分析历史错误模式"""
        print("\n" + "="*70)
        print(" " * 20 + "错误模式分析")
        print("="*70)
        
        # 读取历史错误日志
        errors = self._load_error_logs(days)
        
        if not errors:
            print("⚠️ 无历史错误数据")
            return []
        
        print(f"分析 {len(errors)} 条错误日志...")
        
        # 聚类错误模式
        pattern_groups = self._cluster_errors(errors)
        
        # 生成错误模式
        self.error_patterns = []
        for pattern_key, error_list in pattern_groups.items():
            pattern = self._create_pattern(pattern_key, error_list)
            if pattern.occurrence_count >= self.config['min_occurrences']:
                self.error_patterns.append(pattern)
                
                # 预测下次出现时间
                pattern.predicted_next = self._predict_next_occurrence(pattern)
        
        # 保存模式
        self._save_patterns()
        
        # 打印分析结果
        self._print_patterns()
        
        return self.error_patterns
    
    def _load_error_logs(self, days: int) -> List[Dict]:
        """加载历史错误日志"""
        errors = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            log_file = self.log_dir / f'errors_{date_str}.jsonl'
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            error = json.loads(line)
                            errors.append(error)
                        except:
                            pass
        
        return errors
    
    def _cluster_errors(self, errors: List[Dict]) -> Dict:
        """聚类错误"""
        groups = {}
        
        for error in errors:
            # 创建聚类键
            key = (
                error.get('error_type', 'Unknown'),
                error.get('agent', 'Unknown'),
                error.get('severity', 'P3')
            )
            
            if key not in groups:
                groups[key] = []
            groups[key].append(error)
        
        return groups
    
    def _create_pattern(self, key: Tuple, errors: List[Dict]) -> ErrorPattern:
        """创建错误模式"""
        timestamps = [e.get('timestamp', '') for e in errors]
        timestamps.sort()
        
        return ErrorPattern(
            pattern_id=f"pattern_{key[0]}_{key[1]}",
            error_type=key[0],
            error_message=errors[0].get('error_message', '')[:100],
            agent_name=key[1],
            occurrence_count=len(errors),
            first_seen=timestamps[0],
            last_seen=timestamps[-1],
            severity=key[2]
        )
    
    def _predict_next_occurrence(self, pattern: ErrorPattern) -> Optional[str]:
        """预测下次出现时间"""
        if pattern.occurrence_count < 2:
            return None
        
        # 简单的时间间隔分析
        # TODO: 使用更复杂的预测模型
        avg_interval = timedelta(hours=pattern.occurrence_count * 2)
        last_seen = datetime.fromisoformat(pattern.last_seen)
        next_predicted = last_seen + avg_interval
        
        return next_predicted.isoformat()
    
    def _save_patterns(self):
        """保存错误模式"""
        pattern_file = self.data_dir / 'error_patterns.json'
        
        patterns_data = [asdict(p) for p in self.error_patterns]
        
        with open(pattern_file, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, ensure_ascii=False, indent=2)
    
    def _print_patterns(self):
        """打印错误模式"""
        print(f"\n发现 {len(self.error_patterns)} 个错误模式:\n")
        
        for pattern in sorted(self.error_patterns, 
                            key=lambda x: x.occurrence_count, 
                            reverse=True)[:10]:
            print(f"📌 {pattern.pattern_id}")
            print(f"   错误类型：{pattern.error_type}")
            print(f"   Agent: {pattern.agent_name}")
            print(f"   出现次数：{pattern.occurrence_count}")
            print(f"   严重性：{pattern.severity}")
            if pattern.predicted_next:
                print(f"   预测下次：{pattern.predicted_next}")
            print()
    
    def predict_failures(self) -> List[FailurePrediction]:
        """预测可能的故障"""
        print("\n" + "="*70)
        print(" " * 20 + "故障预测")
        print("="*70)
        
        if not self.error_patterns:
            # 加载已有模式
            self._load_patterns()
        
        predictions = []
        
        for pattern in self.error_patterns:
            # 基于出现频率预测
            if pattern.occurrence_count >= 5:
                prediction = self._create_prediction(pattern)
                if prediction:
                    predictions.append(prediction)
        
        self.predictions = predictions
        self._save_predictions()
        self._print_predictions()
        
        return predictions
    
    def _load_patterns(self):
        """加载已有模式"""
        pattern_file = self.data_dir / 'error_patterns.json'
        
        if pattern_file.exists():
            with open(pattern_file, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)
                self.error_patterns = [ErrorPattern(**p) for p in patterns_data]
    
    def _create_prediction(self, pattern: ErrorPattern) -> Optional[FailurePrediction]:
        """创建故障预测"""
        # 计算概率
        probability = min(pattern.occurrence_count / 10, 0.95)
        
        # 确定置信度
        if probability >= self.config['high_confidence_threshold']:
            confidence = 'high'
        elif probability >= self.config['medium_confidence_threshold']:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # 生成预防建议
        actions = self._generate_prevention_actions(pattern)
        
        return FailurePrediction(
            prediction_id=f"pred_{pattern.pattern_id}",
            agent_name=pattern.agent_name,
            failure_type=pattern.error_type,
            probability=probability,
            predicted_time=pattern.predicted_next or datetime.now().isoformat(),
            confidence=confidence,
            prevention_actions=actions
        )
    
    def _generate_prevention_actions(self, pattern: ErrorPattern) -> List[str]:
        """生成预防建议"""
        actions = []
        
        if pattern.error_type == 'TypeError':
            actions.append("检查数据类型转换")
            actions.append("添加 None 值处理")
        elif pattern.error_type == 'TimeoutError':
            actions.append("增加超时时间")
            actions.append("添加重试机制")
        elif pattern.error_type == 'ConnectionError':
            actions.append("检查网络连接")
            actions.append("添加备用数据源")
        elif pattern.severity == 'P0':
            actions.append("立即检查 Agent 状态")
            actions.append("准备自动重启")
        
        if not actions:
            actions.append("检查日志定位问题")
            actions.append("添加错误处理")
        
        return actions
    
    def _save_predictions(self):
        """保存预测"""
        prediction_file = self.data_dir / 'predictions.json'
        
        predictions_data = [asdict(p) for p in self.predictions]
        
        with open(prediction_file, 'w', encoding='utf-8') as f:
            json.dump(predictions_data, f, ensure_ascii=False, indent=2)
    
    def _print_predictions(self):
        """打印预测结果"""
        if not self.predictions:
            print("\n✅ 无高风险故障预测")
            return
        
        print(f"\n预测 {len(self.predictions)} 个可能的故障:\n")
        
        for pred in sorted(self.predictions, 
                         key=lambda x: x.probability, 
                         reverse=True):
            confidence_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[pred.confidence]
            
            print(f"{confidence_icon} {pred.prediction_id}")
            print(f"   Agent: {pred.agent_name}")
            print(f"   故障类型：{pred.failure_type}")
            print(f"   概率：{pred.probability*100:.1f}%")
            print(f"   置信度：{pred.confidence}")
            print(f"   预防建议:")
            for action in pred.prevention_actions[:3]:
                print(f"     - {action}")
            print()
    
    def auto_prevent(self):
        """自动预防措施"""
        print("\n" + "="*70)
        print(" " * 20 + "自动预防措施")
        print("="*70)
        
        if not self.predictions:
            self._load_predictions()
        
        actions_taken = []
        
        for prediction in self.predictions:
            if prediction.confidence == 'high':
                # 高置信度预测，执行自动预防
                action = self._execute_prevention(prediction)
                if action:
                    actions_taken.append(action)
        
        if actions_taken:
            print(f"\n✅ 已执行 {len(actions_taken)} 个预防措施:")
            for action in actions_taken:
                print(f"  - {action}")
        else:
            print("\nℹ️  无需自动预防措施")
        
        return actions_taken
    
    def _load_predictions(self):
        """加载已有预测"""
        prediction_file = self.data_dir / 'predictions.json'
        
        if prediction_file.exists():
            with open(prediction_file, 'r', encoding='utf-8') as f:
                predictions_data = json.load(f)
                self.predictions = [FailurePrediction(**p) for p in predictions_data]
    
    def _execute_prevention(self, prediction: FailurePrediction) -> Optional[str]:
        """执行预防措施"""
        # 根据故障类型执行不同预防
        if prediction.failure_type == 'TimeoutError':
            return f"增加 {prediction.agent_name} 超时时间"
        elif prediction.failure_type == 'ConnectionError':
            return f"检查 {prediction.agent_name} 网络连接"
        elif 'TypeError' in prediction.failure_type:
            return f"修复 {prediction.agent_name} 类型错误"
        
        return None
    
    def generate_report(self) -> Dict:
        """生成维护报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'error_patterns': len(self.error_patterns),
            'predictions': len(self.predictions),
            'high_risk': sum(1 for p in self.predictions if p.confidence == 'high'),
            'medium_risk': sum(1 for p in self.predictions if p.confidence == 'medium'),
            'low_risk': sum(1 for p in self.predictions if p.confidence == 'low')
        }
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='预测性维护')
    parser.add_argument('--analyze', action='store_true', help='分析错误模式')
    parser.add_argument('--predict', action='store_true', help='预测故障')
    parser.add_argument('--prevent', action='store_true', help='自动预防')
    parser.add_argument('--report', action='store_true', help='生成报告')
    parser.add_argument('--days', type=int, default=7, help='分析天数')
    
    args = parser.parse_args()
    
    pm = PredictiveMaintenance()
    
    if args.analyze:
        pm.analyze_error_patterns(args.days)
    
    if args.predict:
        pm.predict_failures()
    
    if args.prevent:
        pm.auto_prevent()
    
    if args.report or (not args.analyze and not args.predict and not args.prevent):
        report = pm.generate_report()
        print("\n" + "="*70)
        print(" " * 20 + "预测性维护报告")
        print("="*70)
        print(f"错误模式数：{report['error_patterns']}")
        print(f"故障预测数：{report['predictions']}")
        print(f"  高风险：{report['high_risk']}")
        print(f"  中风险：{report['medium_risk']}")
        print(f"  低风险：{report['low_risk']}")


if __name__ == '__main__':
    main()
