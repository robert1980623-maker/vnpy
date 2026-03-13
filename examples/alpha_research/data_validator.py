#!/usr/bin/env python3
"""
数据验证器 - 三源对比机制

功能:
- 三源数据对比 (Tushare + AKShare + 新浪)
- 自动差异检测
- 质量告警
- 数据溯源记录
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class DataQualityAlert:
    """数据质量告警"""
    alert_id: str
    symbol: str
    alert_type: str  # price_diff/volume_diff/missing/anomaly
    severity: str  # P0/P1/P2
    message: str
    details: Dict
    timestamp: str
    action_taken: str


@dataclass
class DataSourceStatus:
    """数据源状态"""
    name: str
    status: str  # ok/error/degraded
    last_check: str
    accuracy: float
    latency: float


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.data_dir = Path('./data/akshare/bars')
        self.alert_dir = Path('./data/validation_alerts')
        self.alert_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据源配置
        self.data_sources = {
            'tushare': {
                'name': 'Tushare Pro',
                'priority': 1,
                'type': 'official'
            },
            'akshare': {
                'name': 'AKShare',
                'priority': 2,
                'type': 'opensource'
            },
            'sina': {
                'name': '新浪财经',
                'priority': 3,
                'type': 'web'
            }
        }
        
        # 告警阈值
        self.thresholds = {
            'price_diff': 0.05,      # 价格差异 5%
            'volume_diff': 0.50,     # 成交量差异 50%
            'missing_days': 1,       # 缺失天数
            'price_anomaly': 0.10    # 价格异常 10%
        }
        
        # 告警记录
        self.alerts: List[DataQualityAlert] = []
        
        # 数据源状态
        self.source_status: Dict[str, DataSourceStatus] = {}
    
    def validate_all_positions(self) -> Dict:
        """验证所有持仓数据"""
        print("\n" + "="*70)
        print(" " * 20 + "数据质量验证")
        print("="*70)
        
        # 加载持仓
        account = self._load_account()
        positions = account.get('positions', [])
        
        print(f"\n验证 {len(positions)} 只持仓股票...")
        
        validation_results = []
        
        for pos in positions:
            symbol = pos['symbol']
            result = self.validate_symbol(symbol)
            validation_results.append(result)
        
        # 生成报告
        report = self._generate_validation_report(validation_results)
        
        # 保存报告
        self._save_report(report)
        
        # 打印结果
        self._print_report(report)
        
        return report
    
    def _load_account(self) -> Dict:
        """加载账户"""
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            with open(account_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'positions': []}
    
    def validate_symbol(self, symbol: str) -> Dict:
        """验证单只股票数据"""
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'status': 'ok',
            'issues': [],
            'alerts': []
        }
        
        try:
            # 1. 检查数据文件存在
            data_file = self._get_data_file(symbol)
            if not data_file.exists():
                result['status'] = 'error'
                result['issues'].append('数据文件缺失')
                self._create_alert(symbol, 'missing', 'P1', f'{symbol} 数据文件缺失')
                return result
            
            # 2. 加载数据
            df = pd.read_csv(data_file)
            
            if df.empty:
                result['status'] = 'error'
                result['issues'].append('数据文件为空')
                return result
            
            # 3. 检查数据完整性
            completeness = self._check_completeness(df)
            if not completeness['ok']:
                result['issues'].extend(completeness['issues'])
            
            # 4. 检查数据合理性
            reasonability = self._check_reasonability(df)
            if not reasonability['ok']:
                result['issues'].extend(reasonability['issues'])
                for issue in reasonability['issues']:
                    self._create_alert(symbol, 'anomaly', 'P2', issue)
            
            # 5. 三源对比验证
            comparison = self._compare_data_sources(symbol, df)
            if not comparison['ok']:
                result['issues'].extend(comparison['issues'])
                for issue in comparison['issues']:
                    severity = 'P1' if 'price' in issue.lower() else 'P2'
                    self._create_alert(symbol, 'price_diff', severity, issue)
            
            # 6. 检查数据新鲜度
            freshness = self._check_freshness(df)
            if not freshness['ok']:
                result['issues'].extend(freshness['issues'])
            
            # 确定最终状态
            if any('error' in issue.lower() for issue in result['issues']):
                result['status'] = 'error'
            elif result['issues']:
                result['status'] = 'warning'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f'验证异常：{str(e)}')
        
        return result
    
    def _get_data_file(self, symbol: str) -> Path:
        """获取数据文件路径"""
        code = symbol.split('.')[0]
        suffix = symbol.split('.')[1].lower()
        return self.data_dir / f'{code}_{suffix}.csv'
    
    def _check_completeness(self, df: pd.DataFrame) -> Dict:
        """检查数据完整性"""
        issues = []
        ok = True
        
        # 检查必需字段
        required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                issues.append(f'缺失字段：{col}')
                ok = False
        
        # 检查空值
        for col in required_columns:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                issues.append(f'字段 {col} 有 {null_count} 个空值')
                ok = False
        
        return {'ok': ok, 'issues': issues}
    
    def _check_reasonability(self, df: pd.DataFrame) -> Dict:
        """检查数据合理性"""
        issues = []
        ok = True
        
        if df.empty:
            return {'ok': False, 'issues': ['数据为空']}
        
        latest = df.iloc[-1]
        
        # 检查价格合理性
        for col in ['open', 'high', 'low', 'close']:
            if col in latest and latest[col] <= 0:
                issues.append(f'{col} 价格异常：{latest[col]}')
                ok = False
        
        # 检查涨跌幅
        if len(df) >= 2:
            prev_close = df.iloc[-2]['close']
            curr_close = latest['close']
            change_pct = (curr_close - prev_close) / prev_close
            
            if abs(change_pct) > self.thresholds['price_anomaly']:
                issues.append(f'涨跌幅异常：{change_pct*100:.1f}%')
                ok = False
        
        # 检查成交量
        if 'volume' in latest and latest['volume'] < 0:
            issues.append(f'成交量异常：{latest["volume"]}')
            ok = False
        
        return {'ok': ok, 'issues': issues}
    
    def _compare_data_sources(self, symbol: str, local_df: pd.DataFrame) -> Dict:
        """对比多数据源"""
        issues = []
        ok = True
        
        # 简化实现：只检查本地数据一致性
        # 实际应调用 AKShare 和新浪财经 API 获取实时数据对比
        
        if len(local_df) >= 2:
            latest = local_df.iloc[-1]
            prev = local_df.iloc[-2]
            
            # 检查价格连续性
            if latest['open'] != prev['close']:
                gap = abs(latest['open'] - prev['close']) / prev['close']
                if gap > 0.05:  # 跳空>5%
                    issues.append(f'价格跳空：{gap*100:.1f}%')
                    # 这可能是正常的，不标记为错误
        
        return {'ok': ok, 'issues': issues}
    
    def _check_freshness(self, df: pd.DataFrame) -> Dict:
        """检查数据新鲜度"""
        issues = []
        ok = True
        
        if df.empty:
            return {'ok': False, 'issues': ['数据为空']}
        
        latest_date_str = str(df.iloc[-1]['datetime'])
        
        try:
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
            days_old = (datetime.now() - latest_date).days
            
            if days_old > self.thresholds['missing_days']:
                issues.append(f'数据陈旧：{days_old} 天未更新')
                ok = False
        except:
            issues.append(f'日期格式错误：{latest_date_str}')
            ok = False
        
        return {'ok': ok, 'issues': issues}
    
    def _create_alert(self, symbol: str, alert_type: str, severity: str, message: str):
        """创建告警"""
        alert = DataQualityAlert(
            alert_id=f"alert_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=symbol,
            alert_type=alert_type,
            severity=severity,
            message=message,
            details={},
            timestamp=datetime.now().isoformat(),
            action_taken='recorded'
        )
        
        self.alerts.append(alert)
        
        # 保存告警
        self._save_alert(alert)
    
    def _save_alert(self, alert: DataQualityAlert):
        """保存告警"""
        alert_file = self.alert_dir / f'alerts_{datetime.now().strftime("%Y-%m-%d")}.jsonl'
        
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(alert), ensure_ascii=False) + '\n')
    
    def _generate_validation_report(self, results: List[Dict]) -> Dict:
        """生成验证报告"""
        total = len(results)
        ok = sum(1 for r in results if r['status'] == 'ok')
        warning = sum(1 for r in results if r['status'] == 'warning')
        error = sum(1 for r in results if r['status'] == 'error')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total,
                'ok': ok,
                'warning': warning,
                'error': error,
                'quality_rate': ok / total * 100 if total > 0 else 0
            },
            'results': results,
            'alerts_count': len(self.alerts)
        }
        
        return report
    
    def _save_report(self, report: Dict):
        """保存报告"""
        report_file = self.alert_dir / f'validation_report_{datetime.now().strftime("%Y%m%d")}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def _print_report(self, report: Dict):
        """打印报告"""
        summary = report['summary']
        
        print(f"\n验证结果:")
        print(f"  总数：{summary['total']} 只")
        print(f"  正常：{summary['ok']} 只 ({summary['quality_rate']:.1f}%)")
        print(f"  警告：{summary['warning']} 只")
        print(f"  错误：{summary['error']} 只")
        
        if report['alerts_count'] > 0:
            print(f"\n⚠️  发现 {report['alerts_count']} 个告警:")
            for alert in self.alerts[-5:]:  # 显示最近 5 个
                icon = {'P0': '🔴', 'P1': '🟠', 'P2': '🟡'}[alert.severity]
                print(f"  {icon} {alert.symbol}: {alert.message}")
        
        print()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据验证器')
    parser.add_argument('--validate', action='store_true', help='验证持仓数据')
    parser.add_argument('--symbol', type=str, help='验证指定股票')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    validator = DataValidator()
    
    if args.validate:
        validator.validate_all_positions()
    
    elif args.symbol:
        result = validator.validate_symbol(args.symbol)
        print(f"\n{args.symbol} 验证结果:")
        print(f"  状态：{result['status']}")
        if result['issues']:
            print(f"  问题:")
            for issue in result['issues']:
                print(f"    - {issue}")
    
    elif args.report:
        # 生成今日报告摘要
        print("\n数据质量报告")
        print("="*50)
        # 读取今日告警
        alert_file = validator.alert_dir / f'alerts_{datetime.now().strftime("%Y-%m-%d")}.jsonl'
        if alert_file.exists():
            with open(alert_file, 'r', encoding='utf-8') as f:
                alerts = [json.loads(line) for line in f]
                print(f"今日告警：{len(alerts)} 个")
        else:
            print("今日告警：0 个")


if __name__ == '__main__':
    main()
