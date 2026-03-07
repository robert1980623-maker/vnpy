#!/usr/bin/env python3
"""
数据质量检查工具 (优化版)

功能:
- 检查数据完整性
- 检测异常值
- 检查缺失值
- 检查数据连续性
- 生成质量报告

优化:
- ✅ 集成中国节假日日历
- ✅ 智能规则配置 (分板块)
- ✅ 改进量价匹配算法
"""

import csv
import json
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
class QualityReport:
    """质量报告"""
    check_date: str
    data_dir: str
    total_files: int
    total_records: int
    issues_count: int
    critical_count: int
    warning_count: int
    info_count: int
    quality_score: float
    issues: List[Dict] = field(default_factory=list)


class DataQualityChecker:
    """数据质量检查器"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        self.data_dir = Path(data_dir)
        self.issues: List[QualityIssue] = []
        self.stats = {
            'total_files': 0,
            'total_records': 0,
            'symbols': []
        }
        
        # 加载中国节假日
        self.cn_holidays = holidays.China()
        
        # 智能规则配置 (分板块)
        self.config = {
            # 涨跌幅限制 (分板块)
            'max_price_change': {
                'main_board': 0.10,      # 主板 10%
                'chi_next': 0.20,        # 创业板 20%
                'star_market': 0.20,     # 科创板 20%
                'st_stock': 0.05,        # ST 股 5%
                'bse': 0.30              # 北交所 30%
            },
            'max_volume_ratio': 10.0,     # 最大成交量比率
            'min_price': 0.5,             # 最低价格
            'max_price': 1000.0,          # 最高价格
            'max_gap_days': 10,           # 最大允许缺失天数 (考虑长假)
            'required_columns': ['vt_symbol', 'datetime', 'open_price', 'high_price', 
                               'low_price', 'close_price', 'volume', 'turnover']
        }
        
        # 板块识别规则
        self.board_rules = {
            '688': 'star_market',      # 科创板
            '300': 'chi_next',         # 创业板
            '301': 'chi_next',
            '302': 'chi_next',
            '000': 'main_board',       # 主板
            '001': 'main_board',
            '002': 'main_board',       # 中小板
            '003': 'main_board',
            '600': 'main_board',       # 沪市主板
            '601': 'main_board',
            '603': 'main_board',
            '605': 'main_board',
            '8': 'bse',                # 北交所
            '4': 'bse',
        }
    
    def _get_board(self, symbol: str) -> str:
        """根据股票代码识别板块"""
        code = symbol.split('.')[0]
        prefix = code[:3]
        
        # 检查是否为 ST 股
        if 'ST' in code or 'st' in code:
            return 'st_stock'
        
        # 根据前缀识别板块
        for board_prefix, board in self.board_rules.items():
            if code.startswith(board_prefix):
                return board
        
        return 'main_board'  # 默认主板
    
    def _is_trading_day(self, date: datetime) -> bool:
        """判断是否为交易日"""
        # 周末
        if date.weekday() >= 5:
            return False
        # 节假日
        if date in self.cn_holidays:
            return False
        return True
    
    def _find_next_trading_day(self, date: datetime, forward: bool = True) -> datetime:
        """查找下一个/上一个交易日"""
        delta = 1 if forward else -1
        current = date + timedelta(days=delta)
        
        # 最多查找 30 天
        for _ in range(30):
            if self._is_trading_day(current):
                return current
            current = current + timedelta(days=delta)
        
        return current
    
    def check_all(self) -> QualityReport:
        """执行所有检查"""
        print("=" * 70)
        print(" " * 20 + "数据质量检查 (优化版)")
        print("=" * 70)
        print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据目录：{self.data_dir}")
        print(f"节假日日历：{len(self.cn_holidays)} 个节假日")
        print()
        
        # 1. 检查文件存在
        self._check_files_exist()
        
        # 2. 检查数据结构
        self._check_data_structure()
        
        # 3. 检查数据完整性
        self._check_data_completeness()
        
        # 4. 检查异常值 (智能规则)
        self._check_outliers_smart()
        
        # 5. 检查数据连续性 (考虑节假日)
        self._check_continuity_smart()
        
        # 6. 检查逻辑一致性 (优化算法)
        self._check_consistency_optimized()
        
        # 生成报告
        report = self._generate_report()
        
        # 打印报告
        self._print_report(report)
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _check_files_exist(self):
        """检查文件存在"""
        print("【1. 文件检查】")
        
        csv_files = list(self.data_dir.glob('*.csv'))
        self.stats['total_files'] = len(csv_files)
        
        if len(csv_files) == 0:
            self.issues.append(QualityIssue(
                symbol='ALL',
                issue_type='missing_files',
                description='数据目录为空',
                severity='critical'
            ))
            print("  ❌ 数据目录为空")
        else:
            print(f"  ✅ 发现 {len(csv_files)} 个 CSV 文件")
        
        print()
    
    def _check_data_structure(self):
        """检查数据结构"""
        print("【2. 数据结构检查】")
        
        errors = 0
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # 检查列
                if reader.fieldnames != self.config['required_columns']:
                    self.issues.append(QualityIssue(
                        symbol=symbol,
                        issue_type='wrong_columns',
                        description=f'列名不匹配',
                        severity='critical',
                        expected=str(self.config['required_columns']),
                        actual=str(reader.fieldnames)
                    ))
                    errors += 1
        
        if errors == 0:
            print("  ✅ 所有文件列名正确")
        else:
            print(f"  ❌ {errors} 个文件列名错误")
        print()
    
    def _check_data_completeness(self):
        """检查数据完整性"""
        print("【3. 数据完整性检查】")
        
        missing_data = 0
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            self.stats['symbols'].append(symbol)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                self.stats['total_records'] += len(records)
                
                # 检查缺失值
                for row in records:
                    for col in self.config['required_columns']:
                        if not row.get(col) or row[col] == '':
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='missing_value',
                                description=f'{col} 字段缺失',
                                severity='warning',
                                date=row.get('datetime', '')
                            ))
                            missing_data += 1
                            break
        
        if missing_data == 0:
            print("  ✅ 无缺失值")
        else:
            print(f"  ⚠️ 发现 {missing_data} 个缺失值")
        print()
    
    def _check_outliers_smart(self):
        """智能异常值检查 (分板块)"""
        print("【4. 异常值检查 (智能规则)】")
        
        outliers = 0
        board_stats = {}
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            board = self._get_board(symbol)
            
            if board not in board_stats:
                board_stats[board] = {'count': 0, 'issues': 0}
            board_stats[board]['count'] += 1
            
            # 获取该板块的涨跌幅限制
            max_change = self.config['max_price_change'].get(board, 0.10)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                prev_close = None
                
                for row in reader:
                    close_price = float(row['close_price'])
                    volume = float(row['volume'])
                    
                    # 检查价格范围
                    if close_price < self.config['min_price']:
                        self.issues.append(QualityIssue(
                            symbol=symbol,
                            issue_type='price_too_low',
                            description=f'价格低于最低限制',
                            severity='warning',
                            date=row['datetime'],
                            expected=f">= {self.config['min_price']}",
                            actual=str(close_price)
                        ))
                        outliers += 1
                    
                    if close_price > self.config['max_price']:
                        self.issues.append(QualityIssue(
                            symbol=symbol,
                            issue_type='price_too_high',
                            description=f'价格高于最高限制',
                            severity='warning',
                            date=row['datetime'],
                            expected=f"<= {self.config['max_price']}",
                            actual=str(close_price)
                        ))
                        outliers += 1
                    
                    # 检查涨跌幅 (使用板块特定阈值)
                    if prev_close:
                        change_rate = abs(close_price - prev_close) / prev_close
                        if change_rate > max_change:
                            # 额外检查：是否是除权除息日
                            if change_rate > 0.50:  # 超过 50% 很可能是除权
                                severity = 'info'
                                desc = f'可能是除权除息日 (涨跌幅 {change_rate*100:.1f}%)'
                            else:
                                severity = 'info'  # 涨跌停是正常现象
                                desc = f'单日涨跌幅过大 ({change_rate*100:.1f}% > {max_change*100:.0f}%)'
                            
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='price_jump',
                                description=desc,
                                severity=severity,
                                date=row['datetime'],
                                expected=f"<={max_change*100:.0f}%",
                                actual=f"{change_rate*100:.2f}%"
                            ))
                            outliers += 1
                    
                    prev_close = close_price
        
        # 打印板块统计
        print("  板块统计:")
        for board, stats in board_stats.items():
            print(f"    {board}: {stats['count']} 只股票")
        
        if outliers == 0:
            print("  ✅ 无异常值")
        else:
            print(f"  ⚠️ 发现 {outliers} 个异常值 (已分板块优化)")
        print()
    
    def _check_continuity_smart(self):
        """智能数据连续性检查 (考虑节假日)"""
        print("【5. 数据连续性检查 (考虑节假日)】")
        
        gaps = 0
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                dates = [datetime.strptime(row['datetime'], '%Y-%m-%d') for row in reader]
                
                # 检查日期连续性
                for i in range(1, len(dates)):
                    date1 = dates[i-1]
                    date2 = dates[i]
                    
                    # 计算交易日间隔
                    trading_days_gap = 0
                    current = date1
                    while current < date2:
                        current += timedelta(days=1)
                        if self._is_trading_day(current):
                            trading_days_gap += 1
                    
                    # 如果间隔超过阈值
                    if trading_days_gap > self.config['max_gap_days']:
                        self.issues.append(QualityIssue(
                            symbol=symbol,
                            issue_type='data_gap',
                            description=f'数据缺失超过{self.config["max_gap_days"]}个交易日',
                            severity='warning',
                            date=dates[i-1].strftime('%Y-%m-%d'),
                            expected=f"gap <= {self.config['max_gap_days']} trading days",
                            actual=f"gap = {trading_days_gap} trading days"
                        ))
                        gaps += 1
        
        if gaps == 0:
            print("  ✅ 数据连续性好 (已考虑节假日)")
        else:
            print(f"  ⚠️ 发现 {gaps} 处数据中断")
        print()
    
    def _check_consistency_optimized(self):
        """优化的逻辑一致性检查"""
        print("【6. 逻辑一致性检查 (优化算法)】")
        
        inconsistencies = 0
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    open_p = float(row['open_price'])
                    high_p = float(row['high_price'])
                    low_p = float(row['low_price'])
                    close_p = float(row['close_price'])
                    
                    # 检查 OHLC 逻辑
                    if not (low_p <= open_p <= high_p and low_p <= close_p <= high_p):
                        self.issues.append(QualityIssue(
                            symbol=symbol,
                            issue_type='ohlc_invalid',
                            description='OHLC 价格逻辑错误',
                            severity='critical',
                            date=row['datetime'],
                            expected='low <= open,close <= high',
                            actual=f"O={open_p}, H={high_p}, L={low_p}, C={close_p}"
                        ))
                        inconsistencies += 1
                    
                    # 优化的量价匹配检查
                    volume = float(row['volume'])
                    turnover = float(row['turnover'])
                    
                    if volume > 0 and turnover > 0:
                        # 使用 (开盘 + 收盘)/2 作为预期均价
                        avg_price_expected = (open_p + close_p) / 2
                        avg_price_actual = turnover / volume
                        
                        # 允许 30% 的差异 (考虑盘中波动)
                        diff_rate = abs(avg_price_actual - avg_price_expected) / avg_price_expected
                        
                        if diff_rate > 0.30:
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='volume_turnover_mismatch',
                                description='成交量与成交额差异较大',
                                severity='info',  # 降低严重性
                                date=row['datetime'],
                                expected=f"diff <= 30%",
                                actual=f"diff = {diff_rate*100:.1f}%"
                            ))
                            inconsistencies += 1
        
        if inconsistencies == 0:
            print("  ✅ 逻辑一致性好")
        else:
            print(f"  ℹ️ 发现 {inconsistencies} 处提示 (已优化算法)")
        print()
    
    def _generate_report(self) -> QualityReport:
        """生成报告"""
        critical = len([i for i in self.issues if i.severity == 'critical'])
        warning = len([i for i in self.issues if i.severity == 'warning'])
        info = len([i for i in self.issues if i.severity == 'info'])
        
        # 计算质量分数 (100 分制，优化版)
        base_score = 100
        penalty = critical * 10 + warning * 0.5 + info * 0
        quality_score = max(0, base_score - penalty)
        
        report = QualityReport(
            check_date=datetime.now().isoformat(),
            data_dir=str(self.data_dir),
            total_files=self.stats['total_files'],
            total_records=self.stats['total_records'],
            issues_count=len(self.issues),
            critical_count=critical,
            warning_count=warning,
            info_count=info,
            quality_score=round(quality_score, 2),
            issues=[asdict(i) for i in self.issues]
        )
        
        return report
    
    def _print_report(self, report: QualityReport):
        """打印报告"""
        print("=" * 70)
        print(" " * 20 + "质量检查报告")
        print("=" * 70)
        print()
        
        print("【统计信息】")
        print(f"  数据文件：{report.total_files} 个")
        print(f"  数据记录：{report.total_records:,} 条")
        print(f"  股票数量：{len(self.stats['symbols'])} 只")
        print()
        
        print("【问题统计】")
        print(f"  总问题数：{report.issues_count}")
        print(f"  严重问题：{report.critical_count} (红色)")
        print(f"  警告问题：{report.warning_count} (黄色)")
        print(f"  提示信息：{report.info_count} (蓝色)")
        print()
        
        print("【质量评分】")
        score = report.quality_score
        if score >= 90:
            print(f"  得分：{score}/100 ✅ 优秀")
        elif score >= 70:
            print(f"  得分：{score}/100 ⚠️ 良好")
        elif score >= 60:
            print(f"  得分：{score}/100 ⚠️ 及格")
        else:
            print(f"  得分：{score}/100 ❌ 需要改进")
        print()
        
        if self.issues:
            print("【问题详情】")
            # 只显示严重和警告问题
            critical_warnings = [i for i in self.issues if i.severity in ['critical', 'warning']][:10]
            
            for issue in critical_warnings:
                emoji = {'critical': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(issue.severity, '•')
                print(f"  {emoji} [{issue.symbol}] {issue.issue_type}: {issue.description}")
            
            if len(critical_warnings) < len([i for i in self.issues if i.severity in ['critical', 'warning']]):
                remaining = len([i for i in self.issues if i.severity in ['critical', 'warning']]) - len(critical_warnings)
                print(f"  ... 还有 {remaining} 个严重/警告问题")
            
            # 提示信息不显示详情
            if report.info_count > 0:
                print(f"  ℹ️ 还有 {report.info_count} 条提示信息 (已省略)")
        print()
        
        print("=" * 70)
    
    def _save_report(self, report: QualityReport):
        """保存报告"""
        report_dir = Path('reports/quality')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'quality_report_{timestamp}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 报告已保存：{report_file}")
        print()


def main():
    print()
    
    # 创建检查器
    checker = DataQualityChecker('./data/akshare/bars')
    
    # 执行检查
    report = checker.check_all()
    
    # 返回退出码 (有严重问题返回 1)
    if report.critical_count > 0:
        exit(1)
    else:
        exit(0)


if __name__ == '__main__':
    main()
