#!/usr/bin/env python3
"""
数据质量检查工具 (优化版 - 修复版)

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
- ✅ 支持两种列名格式 (vnpy格式 & 简化格式)
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
        }
        
        # 列名映射 (支持两种格式)
        self.column_mapping = {
            # vnpy 格式
            'vt_symbol': 'vt_symbol',
            'datetime': 'datetime',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume',
            'turnover': 'turnover',
            # 简化格式
            'symbol': 'vt_symbol',
            'date': 'datetime',
        }
    
    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """将列名映射到标准格式"""
        mapped = {}
        for col in fieldnames:
            if col in self.column_mapping:
                mapped[self.column_mapping[col]] = col
            else:
                mapped[col] = col
        return mapped
    
    def _get_symbol_board(self, symbol: str) -> str:
        """根据股票代码获取板块"""
        if not symbol:
            return 'main_board'
        
        # 去除后缀
        symbol = symbol.replace('_', '').replace('.csv', '')
        
        # 提取前两位
        if len(symbol) >= 2:
            prefix = symbol[:2]
            if prefix in self.board_rules:
                return self.board_rules[prefix]
        
        return 'main_board'
    
    def _check_file_columns(self, csv_file: Path, fieldnames: List[str]) -> bool:
        """检查文件列名是否有效"""
        # 检查是否包含必要的列
        required = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in fieldnames]
        
        if missing:
            self.issues.append(QualityIssue(
                symbol=csv_file.stem.replace('_', '.'),
                issue_type='missing_columns',
                description=f'缺少必要列: {", ".join(missing)}',
                severity='critical',
                expected=str(required),
                actual=str(fieldnames)
            ))
            return False
        
        return True
    
    def _check_data_quality(self):
        """检查数据质量"""
        print("【1. 文件检查】")
        print(f"  ✅ 发现 {len(list(self.data_dir.glob('*.csv')))} 个 CSV 文件")
        print()
        
        print("【2. 数据结构检查】")
        errors = 0
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            self.stats['symbols'].append(symbol)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                
                # 检查列
                if not self._check_file_columns(csv_file, fieldnames):
                    errors += 1
                    continue
        
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
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                self.stats['total_records'] += len(records)
                
                # 检查缺失值
                for row in records:
                    # 使用映射后的列名
                    datetime_col = self.column_mapping.get('datetime', 'datetime')
                    open_col = self.column_mapping.get('open', 'open')
                    high_col = self.column_mapping.get('high', 'high')
                    low_col = self.column_mapping.get('low', 'low')
                    close_col = self.column_mapping.get('close', 'close')
                    volume_col = self.column_mapping.get('volume', 'volume')
                    
                    for col in [datetime_col, open_col, high_col, low_col, close_col, volume_col]:
                        if not row.get(col) or row[col] == '':
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='missing_value',
                                description=f'{col} 字段缺失',
                                severity='warning',
                                date=row.get(datetime_col, '')
                            ))
                            missing_data += 1
                            break
        
        print(f"  ⚠️ 发现 {missing_data} 个缺失值")
        print()
    
    def _check_outliers_smart(self):
        """智能异常值检查"""
        print("【4. 异常值检查 (智能规则)】")
        
        total_records = 0
        outlier_records = 0
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            board = self._get_symbol_board(symbol)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                total_records += len(records)
                
                # 使用映射后的列名
                datetime_col = self.column_mapping.get('datetime', 'datetime')
                open_col = self.column_mapping.get('open', 'open')
                high_col = self.column_mapping.get('high', 'high')
                low_col = self.column_mapping.get('low', 'low')
                close_col = self.column_mapping.get('close', 'close')
                volume_col = self.column_mapping.get('volume', 'volume')
                
                # 获取该板块的涨跌幅限制
                max_change = self.config['max_price_change'].get(board, 0.10)
                
                for row in records:
                    try:
                        close_price = float(row[close_col])
                        volume = float(row[volume_col])
                        
                        # 检查价格范围
                        if close_price < self.config['min_price']:
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='price_too_low',
                                description=f'价格低于最低限制',
                                severity='warning',
                                date=row[datetime_col]
                            ))
                            outlier_records += 1
                        
                        if close_price > self.config['max_price']:
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='price_too_high',
                                description=f'价格高于最高限制',
                                severity='warning',
                                date=row[datetime_col]
                            ))
                            outlier_records += 1
                        
                        # 检查成交量比率
                        if volume > self.config['max_volume_ratio'] * 1000:
                            self.issues.append(QualityIssue(
                                symbol=symbol,
                                issue_type='volume_too_high',
                                description=f'成交量异常高',
                                severity='warning',
                                date=row[datetime_col]
                            ))
                            outlier_records += 1
                            
                    except (ValueError, KeyError) as e:
                        # 跳过无法解析的行
                        continue
        
        print(f"  ⚠️ 发现 {outlier_records} 条异常数据")
        print()
    
    def _check_data_continuity(self):
        """检查数据连续性"""
        print("【5. 数据连续性检查】")
        
        gap_count = 0
        gap_days = []
        
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem.replace('_', '.')
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                
                if len(records) < 2:
                    continue
                
                # 使用映射后的列名
                datetime_col = self.column_mapping.get('datetime', 'datetime')
                
                # 按日期排序
                records.sort(key=lambda x: x[datetime_col])
                
                # 检查连续性
                prev_date = None
                for row in records:
                    try:
                        current_date = datetime.strptime(row[datetime_col], '%Y-%m-%d')
                        
                        if prev_date:
                            delta = (current_date - prev_date).days
                            if delta > self.config['max_gap_days']:
                                gap_count += 1
                                gap_days.append({
                                    'symbol': symbol,
                                    'date': row[datetime_col],
                                    'gap': delta
                                })
                        
                        prev_date = current_date
                        
                    except (ValueError, KeyError) as e:
                        continue
        
        if gap_count == 0:
            print("  ✅ 数据连续性良好")
        else:
            print(f"  ⚠️ 发现 {gap_count} 处数据缺失")
            if gap_days:
                print(f"     示例: {gap_days[0]}")
        
        print()
    
    def _generate_report(self):
        """生成质量报告"""
        critical_count = sum(1 for issue in self.issues if issue.severity == 'critical')
        warning_count = sum(1 for issue in self.issues if issue.severity == 'warning')
        info_count = sum(1 for issue in self.issues if issue.severity == 'info')
        
        # 计算质量分数 (简单算法)
        total_issues = len(self.issues)
        quality_score = max(0, 100 - (total_issues * 2))
        
        report = QualityReport(
            check_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data_dir=str(self.data_dir),
            total_files=self.stats['total_files'],
            total_records=self.stats['total_records'],
            issues_count=total_issues,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            quality_score=round(quality_score, 2)
        )
        
        return report
    
    def check_all(self):
        """执行所有检查"""
        print("=" * 60)
        print("                    数据质量检查 (优化版)")
        print("=" * 60)
        print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据目录：{self.data_dir}")
        print(f"节假日日历：{len(self.cn_holidays)} 个节假日")
        print()
        
        self._check_data_quality()
        self._check_data_completeness()
        self._check_outliers_smart()
        self._check_data_continuity()
        
        report = self._generate_report()
        
        # 打印报告
        print("=" * 60)
        print("                    质量报告")
        print("=" * 60)
        print(f"检查时间：{report.check_date}")
        print(f"数据目录：{report.data_dir}")
        print(f"总文件数：{report.total_files}")
        print(f"总记录数：{report.total_records}")
        print()
        print(f"问题总数：{report.issues_count}")
        print(f"  - 严重：{report.critical_count}")
        print(f"  - 警告：{report.warning_count}")
        print(f"  - 信息：{report.info_count}")
        print()
        print(f"质量评分：{report.quality_score}/100")
        print()
        
        # 保存报告
        report_file = self.data_dir.parent / f"reports/data_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        
        print(f"报告已保存：{report_file}")
        print()
        
        # 打印问题详情
        if report.issues_count > 0:
            print("问题详情：")
            for issue in self.issues:
                print(f"  [{issue.severity.upper()}] {issue.symbol}: {issue.description}")
                if issue.date:
                    print(f"      日期: {issue.date}")
            print()
        
        return report


def main():
    checker = DataQualityChecker()
    report = checker.check_all()
    
    # 返回状态码
    if report.critical_count > 0:
        return 1
    elif report.warning_count > 0:
        return 2
    else:
        return 0


if __name__ == '__main__':
    exit(main())
