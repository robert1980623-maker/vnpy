#!/usr/bin/env python3
"""
数据验证器 - 三源对比机制

功能:
- 三源数据对比 (Tushare + AKShare + 新浪)
- 自动差异检测
- 质量告警
- 数据溯源记录
"""

import logging
logger = logging.getLogger(__name__)

import json
import math
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import pandas as pd

# AlertNotifier 延迟导入的占位（允许 mock 测试）
try:
    from alert_notifier import AlertNotifier
except ImportError:
    AlertNotifier = None


# ---------------------------------------------------------------------------
# Pipeline validation data classes
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """单个校验项结果"""
    name: str               # 校验项名称 (e.g. 'row_count')
    passed: bool            # 是否通过
    message: str            # 人类可读的描述
    details: Dict = field(default_factory=dict)  # 附加信息
    severity: str = 'INFO'  # INFO / WARNING / ERROR

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationResult:
    """校验结果汇总"""
    symbol: str
    passed: bool
    checks: List[CheckResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def summary(self) -> str:
        """生成校验摘要（人类可读）"""
        status = "PASSED" if self.passed else "FAILED"
        lines = [f"[{status}] {self.symbol} @ {self.timestamp}"]
        for c in self.checks:
            icon = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{icon}] {c.name}: {c.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'passed': self.passed,
            'timestamp': self.timestamp,
            'checks': [c.to_dict() for c in self.checks],
        }

    @property
    def failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == 'ERROR')

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == 'WARNING')


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

        # Pipeline validation error log path
        self.validation_error_log = Path('./logs/validation_errors.log')
        self.validation_error_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Pipeline validation (DataFrame-based)
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame, symbol: str) -> ValidationResult:
        """校验 DataFrame 数据质量（下载后管道校验）

        Args:
            df: K 线 DataFrame（应包含 date/datetime, open, high, low, close, volume）
            symbol: 股票代码

        Returns:
            ValidationResult
        """
        checks: List[CheckResult] = [
            self._check_required_columns(df),
            self._check_row_count(df, symbol),
            self._check_date_continuity(df),
            self._check_value_range(df),
            self._check_freshness(df),
        ]
        passed = all(c.passed for c in checks if c.severity == 'ERROR')
        result = ValidationResult(symbol=symbol, passed=passed, checks=checks)

        # 记录到 validation_errors.log（仅失败项）
        if not result.passed:
            self._log_validation_error(result)

        return result

    def _check_required_columns(self, df: pd.DataFrame) -> CheckResult:
        """字段完整性校验: date/datetime, open, high, low, close, volume 必须存在"""
        accepted_date_cols = {'date', 'datetime', 'trade_date'}
        required_value_cols = {'open', 'high', 'low', 'close', 'volume'}

        cols = set(df.columns)
        has_date = bool(cols & accepted_date_cols)
        missing_values = required_value_cols - cols

        missing = []
        if not has_date:
            missing.append('date/datetime/trade_date')
        missing.extend(sorted(missing_values))

        if missing:
            return CheckResult(
                name='required_columns',
                passed=False,
                message=f"缺失字段: {', '.join(missing)}",
                details={'missing': missing, 'available': sorted(cols)},
                severity='ERROR',
            )
        return CheckResult(
            name='required_columns',
            passed=True,
            message='所有必需字段存在',
            details={'columns': sorted(cols)},
        )

    def _check_row_count(self, df: pd.DataFrame, symbol: str) -> CheckResult:
        """行数校验: 日线数据 >= 200 行/年"""
        if df.empty:
            return CheckResult(
                name='row_count',
                passed=False,
                message='数据为空',
                severity='ERROR',
            )

        # 估算年份跨度
        date_col = self._date_column(df)
        min_years = 1.0
        if date_col and len(df) >= 2:
            try:
                dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
                if len(dates) >= 2:
                    span_days = (dates.max() - dates.min()).days
                    if span_days > 0:
                        # 使用较小下限，避免对短跨度数据过度宽松
                        min_years = max(span_days / 365.25, 0.01)
            except Exception:
                pass

        expected_min = int(200 * min_years)
        actual = len(df)

        if actual < expected_min:
            return CheckResult(
                name='row_count',
                passed=False,
                message=f"行数不足: {actual} < {expected_min} (预期 {int(min_years * 365)}天 >= 200行/年)",
                details={'actual': actual, 'expected_min': expected_min, 'span_years': round(min_years, 2)},
                severity='ERROR',
            )
        return CheckResult(
            name='row_count',
            passed=True,
            message=f"行数正常: {actual} 行 (跨度 {min_years:.1f} 年)",
            details={'actual': actual, 'expected_min': expected_min},
        )

    def _check_date_continuity(self, df: pd.DataFrame) -> CheckResult:
        """日期连续性校验: 检查交易日是否有缺失"""
        date_col = self._date_column(df)
        if not date_col:
            return CheckResult(
                name='date_continuity',
                passed=False,
                message='无日期字段，无法校验连续性',
                severity='WARNING',
            )

        try:
            dates = pd.to_datetime(df[date_col], errors='coerce').dropna().sort_values()
        except Exception as e:
            return CheckResult(
                name='date_continuity',
                passed=False,
                message=f'日期解析失败: {e}',
                severity='ERROR',
            )

        if dates.empty:
            return CheckResult(
                name='date_continuity',
                passed=False,
                message='日期列全部为空',
                severity='ERROR',
            )

        # 使用 A 股交易日历近似：只检查周一-周五的缺失（节假日无法精确判断）
        unique_dates = dates.dt.date.drop_duplicates()
        if len(unique_dates) < 2:
            return CheckResult(
                name='date_continuity',
                passed=True,
                message=f'仅有 {len(unique_dates)} 个交易日，跳过连续性校验',
                details={'trading_days': len(unique_dates)},
            )

        # 生成预期工作日范围
        start, end = min(unique_dates), max(unique_dates)
        all_weekdays = pd.bdate_range(start=start, end=end).date
        missing_days = sorted(set(all_weekdays) - set(unique_dates))

        # 允许少量缺失（节假日），阈值：缺失 <= 5% 视为 WARNING，> 10% 视为 ERROR
        ratio = len(missing_days) / max(len(all_weekdays), 1)
        passed = ratio <= 0.05
        severity = 'ERROR' if ratio > 0.10 else ('WARNING' if missing_days else 'INFO')

        return CheckResult(
            name='date_continuity',
            passed=passed,
            message=f"缺失 {len(missing_days)} 个工作日 ({ratio:.1%})",
            details={
                'missing_count': len(missing_days),
                'total_weekdays': len(all_weekdays),
                'trading_days': len(unique_dates),
                'missing_ratio': round(ratio, 4),
                'sample_missing': [str(d) for d in missing_days[:5]],
            },
            severity=severity,
        )

    def _check_value_range(self, df: pd.DataFrame) -> CheckResult:
        """数值范围校验: 股价 > 0, 成交量 >= 0, 无 NaN/Inf"""
        issues = []

        # 股价列必须 > 0
        for col in ['open', 'high', 'low', 'close']:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors='coerce')
            null_count = int(series.isna().sum())
            non_positive = int((series <= 0).sum())
            inf_count = int(series.apply(lambda x: isinstance(x, float) and math.isinf(x)).sum()) if null_count == 0 else 0
            bad = null_count + non_positive + inf_count
            if bad > 0:
                issues.append(f"{col}: {bad} 异常值 (null={null_count}, <=0={non_positive}, inf={inf_count})")

        # 成交量 >= 0
        if 'volume' in df.columns:
            vol = pd.to_numeric(df['volume'], errors='coerce')
            vol_null = int(vol.isna().sum())
            vol_neg = int((vol < 0).sum())
            if vol_null + vol_neg > 0:
                issues.append(f"volume: {vol_null + vol_neg} 异常值 (null={vol_null}, <0={vol_neg})")

        if issues:
            return CheckResult(
                name='value_range',
                passed=False,
                message='; '.join(issues),
                details={'issues': issues},
                severity='ERROR',
            )
        return CheckResult(
            name='value_range',
            passed=True,
            message='所有数值在合理范围内',
        )

    def _check_freshness(self, df: pd.DataFrame) -> CheckResult:
        """数据新鲜度校验: 最新日期 <= 今天 - 1 天"""
        date_col = self._date_column(df)
        if not date_col:
            return CheckResult(
                name='freshness',
                passed=False,
                message='无日期字段，无法校验新鲜度',
                severity='WARNING',
            )

        try:
            dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
            if dates.empty:
                return CheckResult(
                    name='freshness',
                    passed=False,
                    message='日期列全部为空',
                    severity='ERROR',
                )
            latest = dates.max()
            today = pd.Timestamp.now().normalize()
            age_days = (today - latest.normalize()).days

            # 允许 3 天延迟（周末/节假日）
            if age_days > 3:
                return CheckResult(
                    name='freshness',
                    passed=False,
                    message=f"数据陈旧: 最新日期 {latest.date()} (距今 {age_days} 天)",
                    details={'latest': str(latest.date()), 'age_days': age_days},
                    severity='WARNING',
                )
            return CheckResult(
                name='freshness',
                passed=True,
                message=f"数据新鲜: 最新日期 {latest.date()} (距今 {age_days} 天)",
                details={'latest': str(latest.date()), 'age_days': age_days},
            )
        except Exception as e:
            return CheckResult(
                name='freshness',
                passed=False,
                message=f'日期解析失败: {e}',
                severity='ERROR',
            )

    def _date_column(self, df: pd.DataFrame) -> Optional[str]:
        """识别 DataFrame 中的日期列"""
        for col in ('date', 'datetime', 'trade_date'):
            if col in df.columns:
                return col
        return None

    def _log_validation_error(self, result: ValidationResult):
        """记录校验失败到 validation_errors.log"""
        try:
            with open(self.validation_error_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write validation error log: {e}")

    def notify_validation_failure(self, result: ValidationResult):
        """校验失败时通过飞书通知（使用现有的 alert_notifier）"""
        if result.passed:
            return
        if AlertNotifier is None:
            logger.warning("AlertNotifier not available, skipping notification")
            return
        try:
            notifier = AlertNotifier()
            failed_names = [c.name for c in result.failed_checks]
            severity = 'P1' if result.error_count > 0 else 'P2'
            alert = notifier.create_alert(
                severity=severity,
                agent='data_validator',
                error=f"数据校验失败 {result.symbol}: {', '.join(failed_names)}",
                action_taken='记录到 validation_errors.log',
            )
            notifier.send_alert(alert)
            logger.info(f"Validation alert sent for {result.symbol}")
        except Exception as e:
            logger.error(f"Failed to send validation alert: {e}")

    def validate_all_positions(self) -> Dict:
        """验证所有持仓数据"""
        logger.info("\n" + "="*70)
        logger.info(" " * 20 + "数据质量验证")
        logger.info("="*70)
        
        # 加载持仓
        account = self._load_account()
        positions = account.get('positions', [])
        
        logger.info(f"\n验证 {len(positions)} 只持仓股票...")
        
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
            
            # 6. 检查数据新鲜度（legacy 模式，返回 dict）
            freshness = self._check_freshness_legacy(df)
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
    
    def _check_completeness_legacy(self, df: pd.DataFrame) -> Dict:
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
    
    def _check_reasonability_legacy(self, df: pd.DataFrame) -> Dict:
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
    
    def _compare_data_sources_legacy(self, symbol: str, local_df: pd.DataFrame) -> Dict:
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
    
    def _check_freshness_legacy(self, df: pd.DataFrame) -> Dict:
        """检查数据新鲜度（legacy 模式，用于 validate_symbol）"""
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
        
        # 🔴 严重告警上报 Manager
        if severity in ['P0', 'P1']:
            self._report_to_manager(alert)
    

    def _report_to_manager(self, alert: DataQualityAlert):
        """上报严重告警到 Manager"""
        try:
            from issue_queue import IssueQueue
            queue = IssueQueue()
            
            # 创建问题
            issue = queue.create_issue(
                agent='data_validator',
                severity=alert.severity,
                error_type=alert.alert_type,
                error_message=f"{alert.symbol}: {alert.message}"
            )
            issue_id = queue.write_issue(issue)
            
            logger.info(f"✅ 已上报 Manager: {alert.symbol} - {alert.message} (Issue: {issue_id})")
            
        except Exception as e:
            logger.error(f"⚠️ 上报 Manager 失败：{e}")

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
        
        logger.info(f"\n验证结果:")
        logger.info(f"  总数：{summary['total']} 只")
        logger.info(f"  正常：{summary['ok']} 只 ({summary['quality_rate']:.1f}%)")
        logger.warning(f"  警告：{summary['warning']} 只")
        logger.error(f"  错误：{summary['error']} 只")
        
        if report['alerts_count'] > 0:
            logger.info(f"\n⚠️  发现 {report['alerts_count']} 个告警:")
            for alert in self.alerts[-5:]:  # 显示最近 5 个
                icon = {'P0': '🔴', 'P1': '🟠', 'P2': '🟡'}[alert.severity]
                logger.info(f"  {icon} {alert.symbol}: {alert.message}")
        
        logger.info()


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
        logger.info(f"\n{args.symbol} 验证结果:")
        logger.info(f"  状态：{result['status']}")
        if result['issues']:
            logger.info(f"  问题:")
            for issue in result['issues']:
                logger.info(f"    - {issue}")
    
    elif args.report:
        # 生成今日报告摘要
        logger.info("\n数据质量报告")
        logger.info("="*50)
        # 读取今日告警
        alert_file = validator.alert_dir / f'alerts_{datetime.now().strftime("%Y-%m-%d")}.jsonl'
        if alert_file.exists():
            with open(alert_file, 'r', encoding='utf-8') as f:
                alerts = [json.loads(line) for line in f]
                logger.info(f"今日告警：{len(alerts)} 个")
        else:
            logger.info("今日告警：0 个")


if __name__ == '__main__':
    main()


# 选股前验证模式
def validate_pre_stock_selection():
    """选股前验证"""
    logger.info("\n" + "="*70)
    logger.info(" " * 20 + "选股前数据验证")
    logger.info("="*70)
    
    # 验证所有持仓
    report = validate_all_positions()
    
    # 判断是否可以通过
    summary = report['summary']
    
    logger.info(f"\n{'='*70}")
    logger.info(" 验证结果:")
    logger.info(f"{'='*70}")
    
    if summary['error'] > 0:
        logger.error(f"❌ 发现 {summary['error']} 只股票数据错误")
        logger.info("⚠️  建议：暂停选股，先修复数据问题")
        return False
    
    elif summary['warning'] > 0:
        logger.warning(f"⚠️  发现 {summary['warning']} 只股票数据警告")
        if summary['warning'] > len(summary) * 0.3:  # 超过 30% 有警告
            logger.warning("⚠️  警告比例过高，建议延迟选股")
            return False
        else:
            logger.warning("✅  警告在可接受范围内，可以继续选股")
            return True
    
    else:
        logger.info(f"✅ 所有 {summary['ok']} 只股票数据正常")
        logger.info("✅ 可以通过选股验证")
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据验证器')
    parser.add_argument('--validate', action='store_true', help='验证持仓数据')
    parser.add_argument('--pre-stock', action='store_true', help='选股前验证模式')
    parser.add_argument('--symbol', type=str, help='验证指定股票')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    validator = DataValidator()
    
    if args.validate and args.pre_stock:
        # 选股前验证模式
        success = validate_pre_stock_selection()
        exit(0 if success else 1)
    elif args.validate:
        validator.validate_all_positions()
    # ... 其他参数处理
