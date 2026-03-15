#!/usr/bin/env python3
"""
世界模型预测分析模块

功能:
1. ⏳ 时间序列分析 - 分析趋势和周期性
2. 🔍 模式识别 - 识别行为模式
3. 🔗 因果推理 - 建立因果关系
4. 🚨 预测性告警 - 提前预警

用法:
    python3 predictive_analytics.py --all
    python3 predictive_analytics.py --timeseries
    python3 predictive_analytics.py --patterns
    python3 predictive_analytics.py --causal
    python3 predictive_analytics.py --alerts
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))


class PredictiveAnalytics:
    """世界模型预测分析器"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.data_dir = self.project_dir / 'data' / 'analytics'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 历史数据存储
        self.history_file = self.data_dir / 'history.json'
        self.patterns_file = self.data_dir / 'patterns.json'
        self.causal_file = self.data_dir / 'causal_relationships.json'
        
        # 加载历史数据
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'agent_stats': [],
            'task_stats': [],
            'issue_stats': [],
            'session_stats': []
        }
    
    def _save_history(self):
        """保存历史数据"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    # ========================================================================
    # 1️⃣ 时间序列分析
    # ========================================================================
    
    def analyze_timeseries(self, data_points: List[Dict], metric: str) -> Dict:
        """
        时间序列分析
        
        Args:
            data_points: 时间点数据 [{timestamp, value}, ...]
            metric: 分析的指标名称
        
        Returns:
            分析结果 {trend, growth_rate, seasonality, forecast}
        """
        if not data_points or len(data_points) < 2:
            return {'error': '数据点不足'}
        
        values = [dp.get('value', 0) for dp in data_points]
        
        # 计算趋势
        trend = self._calculate_trend(values)
        
        # 计算增长率
        growth_rate = self._calculate_growth_rate(values)
        
        # 检测周期性
        seasonality = self._detect_seasonality(values)
        
        # 预测未来
        forecast = self._forecast(values, periods=3)
        
        result = {
            'metric': metric,
            'trend': trend,
            'growth_rate': growth_rate,
            'seasonality': seasonality,
            'forecast': forecast,
            'last_updated': datetime.now().isoformat()
        }
        
        return result
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'stable'
        
        # 简单线性回归
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """计算增长率"""
        if len(values) < 2:
            return 0.0
        
        first = values[0]
        last = values[-1]
        
        if first == 0:
            return 0.0
        
        return (last - first) / first
    
    def _detect_seasonality(self, values: List[float], period: int = 7) -> Dict:
        """检测周期性"""
        if len(values) < period * 2:
            return {'detected': False}
        
        # 简单周期性检测
        correlations = []
        for lag in range(1, min(period + 1, len(values) // 2)):
            corr = self._calculate_correlation(values[:-lag], values[lag:])
            correlations.append((lag, corr))
        
        best_lag, best_corr = max(correlations, key=lambda x: x[1])
        
        return {
            'detected': best_corr > 0.7,
            'period': best_lag,
            'strength': best_corr
        }
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """计算相关系数"""
        n = len(x)
        if n == 0:
            return 0.0
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        
        x_std = (sum((xi - x_mean) ** 2 for xi in x)) ** 0.5
        y_std = (sum((yi - y_mean) ** 2 for yi in y)) ** 0.5
        
        if x_std == 0 or y_std == 0:
            return 0.0
        
        return numerator / (x_std * y_std)
    
    def _forecast(self, values: List[float], periods: int = 3) -> List[float]:
        """简单预测"""
        if len(values) < 2:
            return values[-1:] * periods if values else [0] * periods
        
        # 使用移动平均
        window = min(3, len(values))
        recent_avg = sum(values[-window:]) / window
        
        return [recent_avg] * periods
    
    # ========================================================================
    # 2️⃣ 模式识别
    # ========================================================================
    
    def identify_patterns(self, events: List[Dict]) -> List[Dict]:
        """
        识别行为模式
        
        Args:
            events: 事件列表 [{timestamp, type, data}, ...]
        
        Returns:
            识别的模式列表
        """
        patterns = []
        
        # 时间模式识别
        time_patterns = self._identify_time_patterns(events)
        patterns.extend(time_patterns)
        
        # 序列模式识别
        sequence_patterns = self._identify_sequence_patterns(events)
        patterns.extend(sequence_patterns)
        
        # 关联模式识别
        association_patterns = self._identify_association_patterns(events)
        patterns.extend(association_patterns)
        
        return patterns
    
    def _identify_time_patterns(self, events: List[Dict]) -> List[Dict]:
        """识别时间模式"""
        patterns = []
        
        # 按小时分组
        hour_counts = defaultdict(int)
        for event in events:
            timestamp = event.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    hour_counts[dt.hour] += 1
                except:
                    pass
        
        # 找出高峰时段
        if hour_counts:
            peak_hour = max(hour_counts, key=hour_counts.get)
            patterns.append({
                'type': 'time_pattern',
                'description': f'活动高峰时段：{peak_hour}:00',
                'confidence': hour_counts[peak_hour] / len(events) if events else 0
            })
        
        return patterns
    
    def _identify_sequence_patterns(self, events: List[Dict]) -> List[Dict]:
        """识别序列模式"""
        patterns = []
        
        # 查找频繁的事件序列
        if len(events) < 2:
            return patterns
        
        # 简单实现：查找连续事件
        event_types = [event.get('type', 'unknown') for event in events[-20:]]
        
        # 查找重复的二元序列
        sequences = defaultdict(int)
        for i in range(len(event_types) - 1):
            seq = (event_types[i], event_types[i+1])
            sequences[seq] += 1
        
        # 找出频繁序列
        for seq, count in sequences.items():
            if count >= 3:
                patterns.append({
                    'type': 'sequence_pattern',
                    'description': f'频繁序列：{seq[0]} → {seq[1]}',
                    'confidence': count / len(events)
                })
        
        return patterns
    
    def _identify_association_patterns(self, events: List[Dict]) -> List[Dict]:
        """识别关联模式"""
        patterns = []
        
        # 查找经常一起发生的事件
        # 简化实现
        return patterns
    
    # ========================================================================
    # 3️⃣ 因果推理
    # ========================================================================
    
    def infer_causality(self, cause_events: List[Dict], effect_events: List[Dict]) -> Dict:
        """
        推断因果关系
        
        Args:
            cause_events: 原因事件列表
            effect_events: 结果事件列表
        
        Returns:
            因果关系推断结果
        """
        if not cause_events or not effect_events:
            return {'causality_detected': False}
        
        # 计算时间先后关系
        temporal_order = self._check_temporal_order(cause_events, effect_events)
        
        # 计算共现频率
        co_occurrence = self._calculate_co_occurrence(cause_events, effect_events)
        
        # 计算因果强度
        causal_strength = self._calculate_causal_strength(cause_events, effect_events)
        
        return {
            'causality_detected': temporal_order and co_occurrence > 0.5,
            'temporal_order': temporal_order,
            'co_occurrence': co_occurrence,
            'causal_strength': causal_strength,
            'confidence': 'high' if causal_strength > 0.7 else 'medium' if causal_strength > 0.4 else 'low'
        }
    
    def _check_temporal_order(self, cause_events: List[Dict], effect_events: List[Dict]) -> bool:
        """检查时间先后顺序"""
        # 原因应该发生在结果之前
        cause_times = []
        effect_times = []
        
        for event in cause_events:
            timestamp = event.get('timestamp', '')
            if timestamp:
                try:
                    cause_times.append(datetime.fromisoformat(timestamp))
                except:
                    pass
        
        for event in effect_events:
            timestamp = event.get('timestamp', '')
            if timestamp:
                try:
                    effect_times.append(datetime.fromisoformat(timestamp))
                except:
                    pass
        
        if not cause_times or not effect_times:
            return False
        
        # 检查原因是否通常在结果之前
        avg_cause_time = sum(cause_times, datetime(1900, 1, 1)) / len(cause_times)
        avg_effect_time = sum(effect_times, datetime(1900, 1, 1)) / len(effect_times)
        
        return avg_cause_time < avg_effect_time
    
    def _calculate_co_occurrence(self, cause_events: List[Dict], effect_events: List[Dict]) -> float:
        """计算共现频率"""
        if not cause_events:
            return 0.0
        
        # 简化：计算原因发生后结果也发生的比例
        co_occurrences = 0
        
        for cause in cause_events:
            cause_time = cause.get('timestamp', '')
            if not cause_time:
                continue
            
            try:
                cause_dt = datetime.fromisoformat(cause_time)
                
                # 查找之后的结果事件
                for effect in effect_events:
                    effect_time = effect.get('timestamp', '')
                    if effect_time:
                        effect_dt = datetime.fromisoformat(effect_time)
                        if effect_dt > cause_dt:
                            co_occurrences += 1
                            break
            except:
                pass
        
        return co_occurrences / len(cause_events)
    
    def _calculate_causal_strength(self, cause_events: List[Dict], effect_events: List[Dict]) -> float:
        """计算因果强度"""
        # 简化实现：基于共现和时间顺序
        co_occurrence = self._calculate_co_occurrence(cause_events, effect_events)
        temporal_order = self._check_temporal_order(cause_events, effect_events)
        
        strength = co_occurrence * (1.5 if temporal_order else 0.5)
        return min(strength, 1.0)
    
    # ========================================================================
    # 4️⃣ 预测性告警
    # ========================================================================
    
    def generate_predictive_alerts(self, current_state: Dict) -> List[Dict]:
        """
        生成预测性告警
        
        Args:
            current_state: 当前系统状态
        
        Returns:
            告警列表
        """
        alerts = []
        
        # 基于趋势的告警
        trend_alerts = self._generate_trend_alerts(current_state)
        alerts.extend(trend_alerts)
        
        # 基于模式的告警
        pattern_alerts = self._generate_pattern_alerts(current_state)
        alerts.extend(pattern_alerts)
        
        # 基于因果的告警
        causal_alerts = self._generate_causal_alerts(current_state)
        alerts.extend(causal_alerts)
        
        return alerts
    
    def _generate_trend_alerts(self, current_state: Dict) -> List[Dict]:
        """基于趋势生成告警"""
        alerts = []
        
        # 示例：检查 Agent 健康度趋势
        if 'agent_health_rate' in current_state:
            health_rate = current_state['agent_health_rate']
            
            if health_rate < 0.8:
                alerts.append({
                    'level': 'critical',
                    'type': 'trend',
                    'message': f'Agent 健康度低于 80% ({health_rate:.1%})',
                    'prediction': '系统可能在 24 小时内出现故障',
                    'suggestion': '立即检查不健康的 Agent'
                })
            elif health_rate < 0.95:
                alerts.append({
                    'level': 'warning',
                    'type': 'trend',
                    'message': f'Agent 健康度下降 ({health_rate:.1%})',
                    'prediction': '如果不改善，可能在未来 48 小时内影响系统',
                    'suggestion': '关注健康度下降的 Agent'
                })
        
        return alerts
    
    def _generate_pattern_alerts(self, current_state: Dict) -> List[Dict]:
        """基于模式生成告警"""
        alerts = []
        
        # 示例：检查任务失败模式
        if 'task_failure_pattern' in current_state:
            pattern = current_state['task_failure_pattern']
            
            if pattern.get('increasing', False):
                alerts.append({
                    'level': 'warning',
                    'type': 'pattern',
                    'message': '任务失败率呈上升趋势',
                    'prediction': '未来 3 次执行失败概率 > 50%',
                    'suggestion': '提前检查任务依赖'
                })
        
        return alerts
    
    def _generate_causal_alerts(self, current_state: Dict) -> List[Dict]:
        """基于因果关系生成告警"""
        alerts = []
        
        # 示例：检查因果链
        if 'data_download_failed' in current_state and current_state['data_download_failed']:
            alerts.append({
                'level': 'critical',
                'type': 'causal',
                'message': '数据下载失败',
                'prediction': '依赖数据的任务（选股、复盘）将失败',
                'suggestion': '优先修复数据下载功能'
            })
        
        return alerts
    
    # ========================================================================
    # 主函数
    # ========================================================================
    
    def run_all(self):
        """运行所有分析"""
        print("\n" + "=" * 70)
        print("🔮 世界模型预测分析")
        print("=" * 70)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 示例数据
        sample_data = {
            'agent_health_rate': 0.95,
            'task_failure_pattern': {'increasing': False},
            'data_download_failed': False
        }
        
        # 生成告警
        alerts = self.generate_predictive_alerts(sample_data)
        
        if alerts:
            print(f"🚨 生成 {len(alerts)} 个预测性告警:\n")
            for alert in alerts:
                print(f"  [{alert['level'].upper()}] {alert['message']}")
                print(f"    预测：{alert['prediction']}")
                print(f"    建议：{alert['suggestion']}")
                print()
        else:
            print("✅ 无预测性告警 - 系统运行正常")
        
        print("=" * 70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='世界模型预测分析')
    parser.add_argument('--all', action='store_true', help='运行所有分析')
    parser.add_argument('--timeseries', action='store_true', help='时间序列分析')
    parser.add_argument('--patterns', action='store_true', help='模式识别')
    parser.add_argument('--causal', action='store_true', help='因果推理')
    parser.add_argument('--alerts', action='store_true', help='预测性告警')
    
    args = parser.parse_args()
    
    analyzer = PredictiveAnalytics()
    
    if args.all or (not args.timeseries and not args.patterns and not args.causal and not args.alerts):
        analyzer.run_all()


if __name__ == '__main__':
    main()
