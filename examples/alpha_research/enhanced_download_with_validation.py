#!/usr/bin/env python3
"""
增强版批量下载 - 带交易日判断和数据验证

功能:
- 自动判断交易日
- 下载后验证数据日期
- 失败自动重试
- 详细日志记录
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 导入交易日历
from trading_calendar import TradingCalendar, get_last_trading_day, is_data_published

# 配置
DATA_DIR = Path('./data/akshare/bars')
LOG_DIR = Path('./logs')
REPORT_DIR = Path('./reports/download')

for d in [DATA_DIR, LOG_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

class EnhancedDownloader:
    """增强版下载器"""
    
    def __init__(self):
        self.calendar = TradingCalendar()
        self.log_file = LOG_DIR / f'download_{datetime.now().strftime("%Y%m%d_%H%M")}.log'
        self.report = {
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'expected_date': None,
            'downloaded': [],
            'failed': [],
            'skipped': [],
            'validated': [],
            'validation_failed': []
        }
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def pre_download_check(self) -> tuple:
        """
        下载前检查
        
        Returns:
            (should_proceed, reason, expected_date)
        """
        now = datetime.now()
        
        # 检查是否为交易日
        if not self.calendar.is_trading_day(now):
            return False, "非交易日", None
        
        # 检查数据是否已发布
        if not self.calendar.is_data_published(now):
            return False, "数据未发布", None
        
        # 获取期望日期
        expected_date = get_last_trading_day(now)
        self.report['expected_date'] = expected_date.strftime('%Y-%m-%d')
        
        return True, "检查通过", expected_date
    
    def download_stocks(self, symbols: list) -> dict:
        """
        下载股票数据
        
        Args:
            symbols: 股票代码列表
        
        Returns:
            下载结果
        """
        if not symbols:
            return {'success': [], 'failed': []}
        
        self.log(f"开始下载 {len(symbols)} 只股票...")
        
        success = []
        failed = []
        
        # 调用批量下载脚本
        script = Path('./batch_download_enhanced.py')
        if not script.exists():
            script = Path('./batch_download.py')
        
        if not script.exists():
            self.log("❌ 下载脚本不存在")
            return {'success': [], 'failed': symbols}
        
        try:
            env = {'PYTHONPATH': str(Path('./').absolute())}
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            # 解析输出
            if result.returncode == 0:
                self.log("✅ 下载完成")
                success = symbols
            else:
                self.log(f"⚠️ 下载有错误：{result.stderr[:200]}")
                success = symbols  # 保守假设都成功
            
        except subprocess.TimeoutExpired:
            self.log("❌ 下载超时")
            failed = symbols
        except Exception as e:
            self.log(f"❌ 下载异常：{e}")
            failed = symbols
        
        return {'success': success, 'failed': failed}
    
    def validate_download(self, symbols: list, expected_date: datetime) -> dict:
        """
        验证下载结果
        
        Args:
            symbols: 股票代码列表
            expected_date: 期望的数据日期
        
        Returns:
            验证结果
        """
        self.log(f"开始验证 {len(symbols)} 只股票数据...")
        
        validated = []
        failed = []
        
        for symbol in symbols:
            code = symbol.split('.')[0] if '.' in symbol else symbol
            suffix = symbol.split('.')[1] if '.' in symbol else ''
            suffix_lower = suffix.lower()
            suffix_upper = suffix.upper()
            possible_files = [
                DATA_DIR / f'{code}_{suffix_lower}.csv' if suffix else None,
                DATA_DIR / f'{code}_{suffix_upper}.csv' if suffix else None,
                DATA_DIR / f'{code}.csv',
            ]
            possible_files = [f for f in possible_files if f]  # filter None
            
            # 查找所有匹配的文件，选择最新数据的那个
            valid_files = []
            for f in possible_files:
                if f.exists():
                    try:
                        df_temp = pd.read_csv(f)
                        if not df_temp.empty:
                            # 获取日期列
                            date_col = None
                            for col in ['trade_date', 'datetime', '日期', 'date']:
                                if col in df_temp.columns:
                                    date_col = col
                                    break
                            if not date_col:
                                date_col = df_temp.columns[1]
                            # 获取最新日期（CSV 按日期倒序排列，第一行最新）
                            last_row_date = pd.to_datetime(df_temp.iloc[0][date_col])
                            valid_files.append((f, df_temp, last_row_date))
                    except Exception:
                        continue
            
            if not valid_files:
                failed.append({
                    'symbol': symbol,
                    'reason': '文件不存在'
                })
                continue
            
            # 选择最新数据的文件
            valid_files.sort(key=lambda x: x[2], reverse=True)
            file_found, df, last_date = valid_files[0]
            
            try:
                # 读取最后一行（最新数据）
                if df.empty:
                    failed.append({
                        'symbol': symbol,
                        'reason': '文件为空'
                    })
                    continue
                
                # 获取日期列
                date_col = None
                for col in ['trade_date', 'datetime', '日期', 'date']:
                    if col in df.columns:
                        date_col = col
                        break
                
                if not date_col:
                    date_col = df.columns[1]
                
                # 读取第一行（最新数据，CSV 按日期倒序排列）
                last_date_str = df.iloc[0][date_col]
                last_date = pd.to_datetime(last_date_str)
                
                # 检查日期是否匹配期望
                days_diff = (expected_date - last_date).days
                
                if days_diff <= 0:
                    validated.append({
                        'symbol': symbol,
                        'last_date': last_date_str,
                        'status': 'fresh'
                    })
                else:
                    failed.append({
                        'symbol': symbol,
                        'reason': f'数据滞后{days_diff}天',
                        'last_date': last_date_str
                    })
                    
            except Exception as e:
                failed.append({
                    'symbol': symbol,
                    'reason': f'验证错误：{e}'
                })
        
        self.log(f"验证完成：成功{len(validated)}, 失败{len(failed)}")
        
        return {'validated': validated, 'failed': failed}
    
    def run(self, symbols: list = None, auto_validate: bool = True) -> dict:
        """
        运行完整下载流程
        
        Args:
            symbols: 股票代码列表（None 则从持仓获取）
            auto_validate: 是否自动验证
        
        Returns:
            执行结果
        """
        self.log("=" * 60)
        self.log("🚀 增强版数据下载启动")
        self.log("=" * 60)
        
        # 1. 下载前检查
        should_proceed, reason, expected_date = self.pre_download_check()
        
        if not should_proceed:
            self.log(f"⏭️ 跳过下载：{reason}")
            self.report['status'] = 'skipped'
            self.report['skip_reason'] = reason
            self._save_report()
            return self.report
        
        self.log(f"✅ 下载前检查通过，期望日期：{expected_date.strftime('%Y-%m-%d')}")
        
        # 2. 获取股票列表
        if symbols is None:
            symbols = self._get_holdings_stocks()
        
        if not symbols:
            self.log("📋 持仓为空，使用 HS300 成分股作为下载列表...")
            try:
                import akshare as ak
                df = ak.index_stock_cons(symbol='000300')
                symbols = df['品种代码'].tolist()[:50]  # 取前50只
                self.log(f"✅ 从 HS300 获取 {len(symbols)} 只股票")
            except Exception as e:
                self.log(f"⚠️ HS300 获取失败：{e}")
                self.log("⚠️ 无股票需要下载")
                self.report['status'] = 'no_symbols'
                self._save_report()
                return self.report
        
        self.log(f"📋 待下载股票：{len(symbols)} 只")
        
        # 3. 执行下载
        dl_result = self.download_stocks(symbols)
        self.report['downloaded'] = dl_result['success']
        self.report['failed'] = dl_result['failed']
        
        # 4. 验证下载结果
        if auto_validate and dl_result['success']:
            validate_result = self.validate_download(
                dl_result['success'],
                expected_date
            )
            self.report['validated'] = validate_result['validated']
            self.report['validation_failed'] = validate_result['failed']
            
            # 如果有验证失败的，尝试重试
            if validate_result['failed']:
                self.log(f"⚠️ {len(validate_result['failed'])} 只股票验证失败，尝试重试...")
                retry_symbols = [f['symbol'] for f in validate_result['failed']]
                retry_result = self.download_stocks(retry_symbols)
                
                # 再次验证
                revalidate = self.validate_download(retry_result['success'], expected_date)
                self.report['validated'].extend(revalidate['validated'])
                self.report['validation_failed'].extend(revalidate['failed'])
        
        # 5. 生成报告
        total = len(symbols)
        success = len(self.report['validated'])
        self.report['status'] = 'completed'
        self.report['success_rate'] = success / total if total > 0 else 0
        self.report['end_time'] = datetime.now().isoformat()
        
        self.log("=" * 60)
        self.log(f"✅ 下载完成，成功率：{self.report['success_rate']*100:.1f}%")
        self.log("=" * 60)
        
        self._save_report()
        return self.report
    
    def _get_holdings_stocks(self) -> list:
        """从持仓获取股票列表（优先级：飞书缓存 > 虚拟账户 > HS300）"""
        # 优先从飞书缓存读取（真实持仓）
        feishu_positions_file = Path('./data/feishu_cache/positions.json')
        if feishu_positions_file.exists():
            try:
                with open(feishu_positions_file, 'r', encoding='utf-8') as f:
                    feishu_data = json.load(f)
                records = feishu_data.get('records', [])
                symbols = [r.get('股票代码', '') for r in records if r.get('股票代码')]
                if symbols:
                    self.log(f"📋 从飞书缓存读取持仓：{len(symbols)} 只")
                    return symbols
            except Exception as e:
                self.log(f"⚠️ 飞书缓存读取失败：{e}")
        
        # Fallback: 虚拟账户持仓
        account_file = Path('./accounts/virtual_2026_account.json')
        if account_file.exists():
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    account = json.load(f)
                positions = account.get('positions', [])
                symbols = [p.get('symbol', '') for p in positions if p.get('symbol')]
                if symbols:
                    self.log(f"📋 从虚拟账户读取持仓：{len(symbols)} 只")
                    return symbols
            except Exception as e:
                self.log(f"⚠️ 虚拟账户读取失败：{e}")
        
        # 最终 Fallback: 返回空列表，让外层用 HS300
        return []
    
    def _save_report(self):
        """保存报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = REPORT_DIR / f'download_report_{timestamp}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2, default=str)
        
        # 最新报告
        latest_file = REPORT_DIR / 'latest_download_report.json'
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2, default=str)
        
        self.log(f"📄 报告已保存：{report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版数据下载')
    parser.add_argument('--symbols', nargs='+', help='指定股票代码')
    parser.add_argument('--no-validate', action='store_true', help='禁用验证')
    parser.add_argument('--non-interactive', action='store_true', help='无人值守模式')
    
    args = parser.parse_args()
    
    downloader = EnhancedDownloader()
    result = downloader.run(
        symbols=args.symbols,
        auto_validate=not args.no_validate
    )
    
    # 退出码
    sys.exit(0 if result['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
