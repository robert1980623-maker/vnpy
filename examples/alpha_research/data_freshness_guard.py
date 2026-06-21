#!/usr/bin/env python3
"""
数据新鲜度守护者

功能:
- 智能判断是否需要下载（交易日 + 数据已发布）
- 下载后自动验证数据日期
- 自动触发补充下载
- 生成新鲜度报告
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd

from trading_calendar import TradingCalendar, is_trading_day, get_last_trading_day, is_data_published
from notification_utils import notify_task_start, notify_task_complete, notify_task_error

class DataFreshnessGuard:
    """数据新鲜度守护者"""
    
    def __init__(self, data_dir: str = './data/akshare/bars'):
        # 基于脚本位置计算项目根目录，确保路径始终正确解析
        self.script_root = Path(__file__).resolve().parent  # examples/alpha_research/
        self.project_root = self.script_root.parent.parent   # /Users/rowang/projects/vnpy/
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.calendar = TradingCalendar()
        self.report_dir = self.script_root / 'reports' / 'data_freshness'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.report = {
            'check_time': datetime.now().isoformat(),
            'status': 'unknown',
            'expected_date': None,
            'actual_date': None,
            'fresh_stocks': [],
            'stale_stocks': [],
            'missing_stocks': [],
            'actions': []
        }
    
    def get_expected_date(self) -> datetime:
        """获取期望的数据日期（最近交易日）"""
        return get_last_trading_day()
    
    def should_download(self) -> Tuple[bool, str]:
        """
        判断是否应该执行下载
        
        Returns:
            (should_download, reason)
        """
        now = datetime.now()
        
        # 1. 检查是否为交易日
        if not self.calendar.is_trading_day(now):
            return False, "今日非交易日"
        
        # 2. 检查数据是否已发布
        if not self.calendar.is_data_published(now):
            return False, "数据尚未发布（需 16:30 后）"
        
        # 3. 检查是否需要更新
        expected_date = self.get_expected_date()
        freshness = self.check_all_freshness(expected_date)
        
        # 检查是否有错误（账户文件不存在/无持仓等）
        if 'error' in freshness:
            return False, f"无法检查新鲜度：{freshness['error']}"
        
        # 安全检查：确保 stale_rate 存在
        stale_rate = freshness.get('stale_rate', 0)
        if stale_rate > 0.2:  # 超过 20% 滞后
            return True, f"{stale_rate*100:.1f}% 数据滞后"
        
        return False, f"数据新鲜度良好 ({(1-stale_rate)*100:.1f}%)"
    
    def check_single_stock(self, symbol: str, expected_date: datetime) -> Dict:
        """检查单只股票数据新鲜度"""
        # 处理 symbol 格式：可能是 "600522" 或 "600522.SH" 或 "000651.SZ"
        if '.' in symbol:
            code = symbol.split('.')[0]
            exchange = symbol.split('.')[1].lower()
        else:
            code = symbol
            # 根据代码前缀推断交易所
            if code.startswith('6') or code.startswith('5'):
                exchange = 'sh'
            else:
                exchange = 'sz'
        
        possible_files = [
            self.data_dir / f'{code}.csv',
            self.data_dir / f'{code}_{exchange}.csv',
            self.data_dir / f'{code.upper()}.csv'
        ]
        
        # 查找文件
        file_found = None
        for f in possible_files:
            if f.exists():
                file_found = f
                break
        
        if not file_found:
            return {
                'symbol': symbol,
                'status': 'missing',
                'last_date': None,
                'days_stale': None
            }
        
        # 读取最后一行
        try:
            # 读取最后几行，确保获取到有效数据
            df = pd.read_csv(file_found, nrows=5)
            if df.empty:
                return {
                    'symbol': symbol,
                    'status': 'empty',
                    'last_date': None,
                    'days_stale': None
                }
            
            # 获取日期列
            date_col = None
            for col in ['trade_date', 'datetime', '日期', 'date']:
                if col in df.columns:
                    date_col = col
                    break
            
            if not date_col:
                # 尝试第一列（通常是代码）或第二列
                date_col = df.columns[0] if len(df.columns) > 0 else None
                if date_col and 'date' not in date_col.lower():
                    date_col = df.columns[1] if len(df.columns) > 1 else None
            
            if not date_col:
                return {
                    'symbol': symbol,
                    'status': 'error',
                    'error': '无法识别日期列',
                    'last_date': None,
                    'days_stale': None
                }
            
            # 从最后一行开始向前查找有效日期
            last_date_str = None
            last_date = None
            for i in range(len(df) - 1, -1, -1):
                candidate = df.iloc[i][date_col]
                if pd.notna(candidate) and candidate != '':
                    last_date_str = str(candidate)
                    try:
                        last_date = pd.to_datetime(last_date_str)
                        break
                    except:
                        continue
            
            if last_date is None:
                return {
                    'symbol': symbol,
                    'status': 'error',
                    'error': '无法解析日期',
                    'last_date': None,
                    'days_stale': None
                }
            
            days_stale = (expected_date - last_date).days
            
            return {
                'symbol': symbol,
                'status': 'fresh' if days_stale <= 0 else 'stale',
                'last_date': last_date_str,
                'days_stale': days_stale
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'status': 'error',
                'error': str(e),
                'last_date': None,
                'days_stale': None
            }
    
    def check_all_freshness(self, expected_date: datetime = None) -> Dict:
        """检查所有持仓数据新鲜度"""
        if expected_date is None:
            expected_date = self.get_expected_date()
        
        # 加载持仓（使用项目根目录下的 accounts 目录）
        account_file = self.project_root / 'accounts' / 'virtual_2026_account.json'
        if not account_file.exists():
            return {'error': f'账户文件不存在: {account_file}'}
        
        with open(account_file, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        positions = account.get('positions', [])
        if not positions:
            return {'error': '无持仓数据'}
        
        results = []
        fresh = []
        stale = []
        missing = []
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            result = self.check_single_stock(symbol, expected_date)
            results.append(result)
            
            if result['status'] == 'fresh':
                fresh.append(symbol)
            elif result['status'] in ['missing', 'empty']:
                missing.append(symbol)
            else:
                stale.append({
                    'symbol': symbol,
                    'days_stale': result.get('days_stale', 0),
                    'last_date': result.get('last_date', 'unknown')
                })
        
        total = len(positions)
        stale_rate = len(stale) / total if total > 0 else 0
        
        return {
            'expected_date': expected_date.strftime('%Y-%m-%d'),
            'total': total,
            'fresh_count': len(fresh),
            'stale_count': len(stale),
            'missing_count': len(missing),
            'fresh_rate': len(fresh) / total if total > 0 else 0,
            'stale_rate': stale_rate,
            'fresh': fresh,
            'stale': sorted(stale, key=lambda x: x['days_stale'], reverse=True),
            'missing': missing
        }
    
    def trigger_download(self, symbols: List[str] = None) -> Dict:
        """触发数据下载"""
        if symbols is None:
            # 下载所有滞后数据
            freshness = self.check_all_freshness()
            
            # 检查是否有错误
            if 'error' in freshness:
                return {'status': 'error', 'downloaded': 0, 'error': freshness['error']}
            
            symbols = [s['symbol'] for s in freshness.get('stale', [])]
            symbols.extend(freshness.get('missing', []))
        
        if not symbols:
            return {'status': 'no_symbols', 'downloaded': 0}
        
        print(f"🔄 开始下载 {len(symbols)} 只股票数据...")
        self.report['actions'].append({
            'action': 'download',
            'symbols': symbols,
            'count': len(symbols),
            'time': datetime.now().isoformat()
        })
        
        try:
            # 调用批量下载脚本（基于项目根目录查找）
            script = self.project_root / 'examples' / 'alpha_research' / 'batch_download_enhanced.py'
            if not script.exists():
                script = self.project_root / 'examples' / 'alpha_research' / 'batch_download.py'
            
            env = {'PYTHONPATH': str(self.project_root)}
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'downloaded': len(symbols),
                    'output': result.stdout[-500:] if result.stdout else ''
                }
            else:
                return {
                    'status': 'partial',
                    'downloaded': len(symbols),
                    'error': result.stderr[-500:] if result.stderr else 'Unknown error'
                }
                
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'downloaded': 0, 'error': '下载超时'}
        except Exception as e:
            return {'status': 'error', 'downloaded': 0, 'error': str(e)}
    
    def verify_after_download(self, symbols: List[str]) -> Dict:
        """下载后验证"""
        expected_date = self.get_expected_date()
        verified = []
        failed = []
        
        for symbol in symbols:
            result = self.check_single_stock(symbol, expected_date)
            
            # 检查是否有错误（如文件读取失败）
            if 'error' in result:
                failed.append({
                    'symbol': symbol,
                    'reason': f"error: {result.get('error', 'unknown')}",
                    'last_date': None
                })
                continue
            
            # 检查日期是否有效
            last_date = result.get('last_date')
            if last_date is None or (isinstance(last_date, float) and last_date != last_date):  # NaN check
                failed.append({
                    'symbol': symbol,
                    'reason': 'no_data',
                    'last_date': None
                })
                continue
            
            if result['status'] == 'fresh':
                verified.append(symbol)
            else:
                failed.append({
                    'symbol': symbol,
                    'reason': result['status'],
                    'last_date': last_date
                })
        
        return {
            'verified': verified,
            'failed': failed,
            'success_rate': len(verified) / len(symbols) if symbols else 0
        }
    
    def run_guard_cycle(self, auto_fix: bool = True) -> Dict:
        """
        运行一个完整的新鲜度守护周期
        
        Args:
            auto_fix: 是否自动修复滞后数据
        
        Returns:
            执行结果
        """
        print("=" * 70)
        print("🛡️ 数据新鲜度守护检查")
        print("=" * 70)
        
        now = datetime.now()
        expected_date = self.get_expected_date()
        
        self.report['expected_date'] = expected_date.strftime('%Y-%m-%d')
        
        print(f"检查时间：{now.strftime('%Y-%m-%d %H:%M')}")
        print(f"期望数据日期：{expected_date.strftime('%Y-%m-%d')}")
        print()
        
        # 1. 判断是否需要下载
        should_dl, reason = self.should_download()
        print(f"下载判断：{'需要' if should_dl else '不需要'} - {reason}")
        
        if not should_dl:
            self.report['status'] = 'fresh'
            self._save_report()
            return {'status': 'fresh', 'reason': reason}
        
        # 2. 检查新鲜度详情
        print("\n📊 新鲜度详情:")
        freshness = self.check_all_freshness(expected_date)
        
        # 检查是否有错误
        if 'error' in freshness:
            print(f"  ❌ 错误：{freshness['error']}")
            self.report['status'] = 'error'
            self.report['actions'].append({
                'action': 'freshness_check_error',
                'error': freshness['error'],
                'time': datetime.now().isoformat()
            })
            self._save_report()
            return {'status': 'error', 'error': freshness['error']}
        
        print(f"  总持仓：{freshness['total']}")
        print(f"  新鲜：{freshness['fresh_count']} ({freshness['fresh_rate']*100:.1f}%)")
        print(f"  滞后：{freshness['stale_count']} ({freshness['stale_rate']*100:.1f}%)")
        print(f"  缺失：{freshness['missing_count']}")
        
        self.report['actual_date'] = freshness.get('expected_date')
        self.report['fresh_stocks'] = freshness['fresh']
        self.report['stale_stocks'] = freshness['stale']
        self.report['missing_stocks'] = freshness['missing']
        
        if freshness['stale_rate'] < 0.2:
            self.report['status'] = 'acceptable'
            self._save_report()
            return {'status': 'acceptable', 'freshness': freshness}
        
        # 3. 自动修复
        if auto_fix:
            print(f"\n🔄 自动修复启动...")
            stale_symbols = [s['symbol'] for s in freshness['stale']]
            stale_symbols.extend(freshness['missing'])
            
            dl_result = self.trigger_download(stale_symbols)
            print(f"下载结果：{dl_result['status']}")
            
            if dl_result['status'] in ['success', 'partial']:
                # 验证下载结果
                verify_result = self.verify_after_download(stale_symbols)
                print(f"验证成功率：{verify_result['success_rate']*100:.1f}%")
                
                self.report['actions'].append({
                    'action': 'verify',
                    'result': verify_result,
                    'time': datetime.now().isoformat()
                })
                
                if verify_result['success_rate'] >= 0.9:
                    self.report['status'] = 'fixed'
                else:
                    self.report['status'] = 'partial_fix'
            else:
                self.report['status'] = 'fix_failed'
                self.report['actions'].append({
                    'action': 'download_failed',
                    'error': dl_result.get('error'),
                    'time': datetime.now().isoformat()
                })
        else:
            self.report['status'] = 'needs_fix'
        
        # 保存报告
        self._save_report()
        
        return {
            'status': self.report['status'],
            'freshness': freshness,
            'actions': self.report['actions']
        }
    
    def _save_report(self):
        """保存报告"""
        import math
        
        def clean_for_json(obj):
            """清理 NaN/Inf 等无法序列化的值"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            elif isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            else:
                return obj
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.report_dir / f'guard_report_{timestamp}.json'
        
        # 清理报告中的 NaN 值
        clean_report = clean_for_json(self.report)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(clean_report, f, ensure_ascii=False, indent=2, default=str)
        
        # 也保存最新报告
        latest_file = self.report_dir / 'latest_report.json'
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(clean_report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 报告已保存：{report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据新鲜度守护者')
    parser.add_argument('--check-only', action='store_true', help='只检查不修复')
    parser.add_argument('--no-auto-fix', action='store_true', help='禁用自动修复')
    parser.add_argument('--non-interactive', action='store_true', help='无人值守模式')
    
    args = parser.parse_args()
    
    # 发送开始通知
    notify_task_start("数据新鲜度守护", {
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    try:
        guard = DataFreshnessGuard()
        auto_fix = not args.no_auto_fix and not args.check_only
        
        result = guard.run_guard_cycle(auto_fix=auto_fix)
        
        # 发送完成通知
        notify_task_complete("数据新鲜度守护", {
            "状态": result.get('status', 'unknown'),
            "结果": json.dumps(result, ensure_ascii=False)[:200]
        })
        
        print(f"\n✅ 守护周期完成，状态：{result.get('status')}")
        
    except Exception as e:
        notify_task_error("数据新鲜度守护", str(e))
        raise


if __name__ == '__main__':
    main()
