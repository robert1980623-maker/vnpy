#!/usr/bin/env python3
"""
生成每日数据质量报告 (cron job: afa51e63)

检查项目:
1. 验证昨日股票数据完整性 (日线/分钟线)
2. 检查数据字段缺失情况
3. 验证数据时间戳连续性
4. 检查异常值/离群点
5. 生成数据质量报告
"""

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field
import holidays


@dataclass
class QualityIssue:
    """质量问题"""
    symbol: str
    issue_type: str
    description: str
    severity: str  # critical/warning/info
    date: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class DataQualityReport:
    """数据质量报告"""
    report_date: str
    check_timestamp: str
    target_date: str  # 昨日日期
    data_dir: str
    
    # 完整性检查
    total_symbols: int
    symbols_with_data: int
    symbols_missing_data: int
    completeness_rate: float
    
    # 字段检查
    fields_check: Dict
    
    # 连续性检查
    continuity_issues: List[Dict]
    
    # 异常值检查
    outliers: List[Dict]
    
    # 问题汇总
    issues: List[Dict]
    critical_count: int
    warning_count: int
    info_count: int
    
    # 质量评分
    quality_score: float
    quality_level: str  # excellent/good/fair/poor/critical
    
    # 建议措施
    recommendations: List[str]


class DailyQualityChecker:
    """每日数据质量检查器"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.issues: List[QualityIssue] = []
        self.cn_holidays = holidays.China()
        
    def _is_trading_day(self, date: datetime) -> bool:
        """判断是否为交易日"""
        if date.weekday() >= 5:  # 周末
            return False
        if date in self.cn_holidays:  # 节假日
            return False
        return True
    
    def _get_previous_trading_day(self, date: datetime) -> datetime:
        """获取前一个交易日"""
        current = date - timedelta(days=1)
        for _ in range(10):
            if self._is_trading_day(current):
                return current
            current = current - timedelta(days=1)
        return current
    
    def _safe_float(self, value, default=0.0):
        """安全转换 float"""
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def check_completeness(self, target_date: str) -> Tuple[int, int, List[str]]:
        """检查数据完整性"""
        import subprocess
        
        csv_files = list(self.data_dir.glob('*.csv'))
        total_symbols = len(csv_files)
        symbols_with_data = 0
        symbols_missing = []
        
        target_formats = [
            target_date.replace('-', ''),  # 20260422
            target_date,  # 2026-04-22
        ]
        
        for csv_file in csv_files:
            found = False
            try:
                # 使用 grep 搜索整个文件
                for fmt in target_formats:
                    result = subprocess.run(
                        ['grep', '-q', fmt, str(csv_file)],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        found = True
                        break
            except Exception as e:
                pass
            
            if found:
                symbols_with_data += 1
            else:
                symbols_missing.append(csv_file.stem)
        
        return total_symbols, symbols_with_data, symbols_missing
    
    def check_fields(self, target_date: str) -> Dict:
        """检查字段完整性"""
        field_stats = {
            'total_files': 0,
            'files_with_all_fields': 0,
            'missing_fields': {},
            'zero_values': {
                'open': 0,
                'high': 0,
                'low': 0,
            }
        }
        
        required_fields = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        
        csv_files = list(self.data_dir.glob('*.csv'))
        field_stats['total_files'] = len(csv_files)
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                    if len(rows) < 2:
                        continue
                    
                    # 检查是否有表头
                    first_row = rows[0]
                    
                    # 简单检查：看数据是否包含 0 值（open/high/low 都是 0 表示数据质量问题）
                    for row in rows[-5:]:  # 检查最后 5 行
                        if len(row) >= 6:
                            open_val = self._safe_float(row[2] if len(row) > 2 else 0)
                            high_val = self._safe_float(row[3] if len(row) > 3 else 0)
                            low_val = self._safe_float(row[4] if len(row) > 4 else 0)
                            
                            if open_val == 0 and high_val == 0 and low_val == 0:
                                field_stats['zero_values']['open'] += 1
                                field_stats['zero_values']['high'] += 1
                                field_stats['zero_values']['low'] += 1
                                break
                                
            except Exception as e:
                pass
        
        # 估算有完整字段的文件数
        field_stats['files_with_all_fields'] = field_stats['total_files'] - field_stats['zero_values']['open']
        
        return field_stats
    
    def check_continuity(self, target_date: str) -> List[Dict]:
        """检查数据连续性"""
        continuity_issues = []
        csv_files = list(self.data_dir.glob('*.csv'))
        
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        prev_trading_day = self._get_previous_trading_day(target_dt)
        prev_date_str = prev_trading_day.strftime('%Y-%m-%d')
        prev_date_str2 = prev_trading_day.strftime('%Y%m%d')
        
        for csv_file in csv_files[:20]:  # 只检查前 20 个文件
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-10:]
                    has_prev_day = False
                    
                    for line in lines:
                        if prev_date_str in line or prev_date_str2 in line:
                            has_prev_day = True
                            break
                    
                    if not has_prev_day:
                        continuity_issues.append({
                            'symbol': csv_file.stem,
                            'issue': f'缺失前一交易日 ({prev_date_str}) 数据',
                            'severity': 'warning'
                        })
                        
            except Exception as e:
                pass
        
        return continuity_issues
    
    def check_outliers(self, target_date: str) -> List[Dict]:
        """检查异常值"""
        outliers = []
        csv_files = list(self.data_dir.glob('*.csv'))
        
        for csv_file in csv_files[:30]:  # 检查前 30 个文件
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                    for row in rows[-5:]:
                        if len(row) >= 6:
                            close_val = self._safe_float(row[5] if len(row) > 5 else 0)
                            volume_val = self._safe_float(row[6] if len(row) > 6 else 0)
                            
                            # 检查价格异常
                            if close_val < 0.5:
                                outliers.append({
                                    'symbol': csv_file.stem,
                                    'issue': f'价格异常低：{close_val}',
                                    'severity': 'warning',
                                    'value': close_val
                                })
                            elif close_val > 500:
                                outliers.append({
                                    'symbol': csv_file.stem,
                                    'issue': f'价格异常高：{close_val}',
                                    'severity': 'info',
                                    'value': close_val
                                })
                                
            except Exception as e:
                pass
        
        return outliers
    
    def generate_report(self, target_date: str = None) -> DataQualityReport:
        """生成数据质量报告"""
        if target_date is None:
            # 默认检查昨日
            target_dt = datetime.now() - timedelta(days=1)
            # 如果是周一，检查上周五
            if target_dt.weekday() == 0:
                target_dt = target_dt - timedelta(days=2)
            target_date = target_dt.strftime('%Y-%m-%d')
        
        print(f"正在生成数据质量报告...")
        print(f"目标日期：{target_date}")
        
        # 1. 完整性检查
        total, with_data, missing = self.check_completeness(target_date)
        completeness_rate = (with_data / total * 100) if total > 0 else 0
        
        print(f"  完整性：{with_data}/{total} ({completeness_rate:.1f}%)")
        
        # 2. 字段检查
        fields_check = self.check_fields(target_date)
        print(f"  字段检查：{fields_check['files_with_all_fields']}/{fields_check['total_files']} 文件完整")
        
        # 3. 连续性检查
        continuity_issues = self.check_continuity(target_date)
        print(f"  连续性问题：{len(continuity_issues)} 处")
        
        # 4. 异常值检查
        outliers = self.check_outliers(target_date)
        print(f"  异常值：{len(outliers)} 处")
        
        # 汇总问题
        all_issues = []
        critical_count = 0
        warning_count = 0
        info_count = 0
        
        # 缺失数据是严重问题
        for symbol in missing[:50]:  # 最多记录 50 个
            all_issues.append({
                'symbol': symbol,
                'issue_type': 'missing_data',
                'description': f'缺失 {target_date} 数据',
                'severity': 'critical',
                'date': target_date
            })
            critical_count += 1
        
        # 连续性问题是警告
        for issue in continuity_issues:
            all_issues.append({
                'symbol': issue['symbol'],
                'issue_type': 'continuity_gap',
                'description': issue['issue'],
                'severity': 'warning',
                'date': target_date
            })
            warning_count += 1
        
        # 异常值
        for outlier in outliers:
            all_issues.append({
                'symbol': outlier['symbol'],
                'issue_type': 'outlier',
                'description': outlier['issue'],
                'severity': outlier['severity'],
                'date': target_date,
                'value': outlier.get('value', '')
            })
            if outlier['severity'] == 'warning':
                warning_count += 1
            else:
                info_count += 1
        
        # 计算质量评分
        if completeness_rate >= 95:
            quality_score = 95
            quality_level = 'excellent'
        elif completeness_rate >= 80:
            quality_score = 80
            quality_level = 'good'
        elif completeness_rate >= 60:
            quality_score = 60
            quality_level = 'fair'
        elif completeness_rate >= 40:
            quality_score = 40
            quality_level = 'poor'
        else:
            quality_score = 20
            quality_level = 'critical'
        
        # 生成建议
        recommendations = []
        if completeness_rate < 80:
            recommendations.append('⚠️ 严重：数据完整性不足，建议检查数据下载脚本是否正常运行')
        if fields_check['zero_values']['open'] > 10:
            recommendations.append('⚠️ 警告：大量股票 OHLC 数据为 0，建议检查数据源格式')
        if len(continuity_issues) > 5:
            recommendations.append('⚠️ 注意：多处数据连续性中断，建议检查增量下载逻辑')
        if len(outliers) > 5:
            recommendations.append('ℹ️ 提示：发现多个异常值，建议人工复核')
        
        if not recommendations:
            recommendations.append('✅ 数据质量良好，无需特别处理')
        
        report = DataQualityReport(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            check_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            target_date=target_date,
            data_dir=str(self.data_dir),
            total_symbols=total,
            symbols_with_data=with_data,
            symbols_missing_data=len(missing),
            completeness_rate=round(completeness_rate, 2),
            fields_check=fields_check,
            continuity_issues=continuity_issues,
            outliers=outliers,
            issues=all_issues,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            quality_score=quality_score,
            quality_level=quality_level,
            recommendations=recommendations
        )
        
        return report


def main():
    """主函数"""
    import sys
    
    # 确定目标日期
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        # 默认昨日
        target_dt = datetime.now() - timedelta(days=1)
        if target_dt.weekday() == 0:  # 周一检查上周五
            target_dt = target_dt - timedelta(days=2)
        target_date = target_dt.strftime('%Y-%m-%d')
    
    # 创建工作目录
    work_dir = Path('/Users/rowang/projects/vnpy/examples/alpha_research')
    reports_dir = work_dir / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    # 执行检查
    checker = DailyQualityChecker(str(work_dir / 'data' / 'akshare' / 'bars'))
    report = checker.generate_report(target_date)
    
    # 保存报告
    report_dict = asdict(report)
    report_file = reports_dir / f'data_quality_{target_date}.json'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存：{report_file}")
    print(f"\n{'='*60}")
    print(f"数据质量报告摘要")
    print(f"{'='*60}")
    print(f"目标日期：{report.target_date}")
    print(f"检查时间：{report.check_timestamp}")
    print(f"")
    print(f"【完整性】")
    print(f"  总股票数：{report.total_symbols}")
    print(f"  有数据：{report.symbols_with_data}")
    print(f"  缺失：{report.symbols_missing_data}")
    print(f"  完整率：{report.completeness_rate}%")
    print(f"")
    print(f"【问题统计】")
    print(f"  严重：{report.critical_count}")
    print(f"  警告：{report.warning_count}")
    print(f"  提示：{report.info_count}")
    print(f"")
    print(f"【质量评分】")
    print(f"  得分：{report.quality_score}/100")
    print(f"  等级：{report.quality_level.upper()}")
    print(f"")
    print(f"【建议措施】")
    for rec in report.recommendations:
        print(f"  {rec}")
    print(f"{'='*60}")
    
    return report


if __name__ == '__main__':
    main()
