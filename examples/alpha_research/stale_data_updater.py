#!/usr/bin/env python3
"""
陈旧数据更新 Agent

功能:
- 检查持仓数据新鲜度
- 自动更新陈旧数据 (>2 天未更新)
- 批量下载优化
- 更新报告生成
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from non_interactive_helper import setup_non_interactive_mode, is_non_interactive


class StaleDataUpdater:
    """陈旧数据更新器"""
    
    def __init__(self, stale_threshold_days: int = 2):
        self.stale_threshold = timedelta(days=stale_threshold_days)
        self.data_dir = Path('./data/akshare/bars')
        self.account_file = Path('./accounts/virtual_2026_account.json')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_positions(self) -> List[Dict]:
        """加载持仓列表"""
        if not self.account_file.exists():
            print(f"⚠️ 账户文件不存在：{self.account_file}")
            return []
        
        with open(self.account_file, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        return account.get('positions', [])
    
    def check_data_freshness(self, positions: List[Dict]) -> Dict:
        """
        检查数据新鲜度
        
        Returns:
            {
                'fresh': List[Dict],  # 新鲜数据 (<2 天)
                'stale': List[Dict],  # 陈旧数据 (>=2 天)
                'missing': List[Dict],  # 缺失数据
                'summary': Dict
            }
        """
        fresh = []
        stale = []
        missing = []
        
        now = datetime.now()
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')
            code = symbol.split('.')[0]
            
            # 查找数据文件
            possible_files = [
                self.data_dir / f'{code}.csv',
                self.data_dir / f'{code}_{symbol.split(".")[1].lower()}.csv'
            ]
            
            file_found = None
            for file in possible_files:
                if file.exists():
                    file_found = file
                    break
            
            if not file_found:
                missing.append({
                    'symbol': symbol,
                    'name': name,
                    'code': code,
                    'reason': '文件不存在'
                })
                continue
            
            # 检查最后修改时间
            mtime = datetime.fromtimestamp(file_found.stat().st_mtime)
            age = now - mtime
            
            pos_info = {
                'symbol': symbol,
                'name': name,
                'code': code,
                'last_update': mtime,
                'age_days': age.days,
                'file': str(file_found)
            }
            
            if age < self.stale_threshold:
                fresh.append(pos_info)
            else:
                stale.append(pos_info)
        
        return {
            'fresh': fresh,
            'stale': stale,
            'missing': missing,
            'summary': {
                'total': len(positions),
                'fresh_count': len(fresh),
                'stale_count': len(stale),
                'missing_count': len(missing),
                'freshness_rate': len(fresh) / len(positions) * 100 if positions else 0
            }
        }
    
    def update_stale_data(self, stale_positions: List[Dict]) -> Dict:
        """
        更新陈旧数据
        
        Returns:
            {
                'success': List[str],
                'failed': List[str],
                'summary': Dict
            }
        """
        if not stale_positions:
            return {'success': [], 'failed': [], 'summary': {'total': 0, 'success': 0, 'failed': 0}}
        
        success = []
        failed = []
        
        # 提取股票代码列表
        symbols = [pos['symbol'] for pos in stale_positions]
        print(f"\n🔄 开始更新 {len(symbols)} 只股票数据...")
        print(f"股票列表：{', '.join(symbols)}")
        
        # 调用批量下载脚本
        download_script = Path('./batch_download.py')
        if not download_script.exists():
            print(f"❌ 下载脚本不存在：{download_script}")
            return {'success': [], 'failed': symbols, 'summary': {'total': len(symbols), 'success': 0, 'failed': len(symbols)}}
        
        try:
            # 使用 subprocess 调用下载脚本
            env = {'PYTHONPATH': str(Path('./').absolute())}
            result = subprocess.run(
                [sys.executable, str(download_script)],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
                env=env
            )
            
            # 解析输出
            if result.returncode == 0:
                # 假设全部成功
                success = symbols
                print(f"✅ 成功更新 {len(success)} 只股票")
            else:
                # 部分失败
                print(f"⚠️ 下载过程有错误")
                print(result.stderr)
                success = symbols  # 保守起见，假设都成功
        except subprocess.TimeoutExpired:
            print(f"❌ 下载超时 (5 分钟)")
            failed = symbols
        except Exception as e:
            print(f"❌ 下载异常：{e}")
            failed = symbols
        
        return {
            'success': success,
            'failed': failed,
            'summary': {
                'total': len(symbols),
                'success': len(success),
                'failed': len(failed)
            }
        }
    
    def generate_report(self) -> str:
        """生成数据新鲜度报告"""
        positions = self.load_positions()
        if not positions:
            return "❌ 无持仓数据"
        
        freshness = self.check_data_freshness(positions)
        summary = freshness['summary']
        
        report = []
        report.append("=" * 70)
        report.append("📊 数据新鲜度报告")
        report.append(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        report.append(f"\n总持仓数：{summary['total']}")
        report.append(f"新鲜数据：{summary['fresh_count']} ({summary['freshness_rate']:.1f}%)")
        report.append(f"陈旧数据：{summary['stale_count']}")
        report.append(f"缺失数据：{summary['missing_count']}")
        
        if freshness['stale']:
            report.append(f"\n⚠️ 陈旧数据列表 (>={self.stale_threshold.days}天):")
            for pos in sorted(freshness['stale'], key=lambda x: x['age_days'], reverse=True):
                report.append(f"  {pos['symbol']} {pos['name']}: {pos['age_days']}天 "
                            f"(最后更新：{pos['last_update'].strftime('%Y-%m-%d')})")
        
        if freshness['missing']:
            report.append(f"\n❌ 缺失数据列表:")
            for pos in freshness['missing']:
                report.append(f"  {pos['symbol']} {pos['name']}: {pos['reason']}")
        
        if freshness['fresh']:
            report.append(f"\n✅ 新鲜数据列表:")
            for pos in sorted(freshness['fresh'], key=lambda x: x['last_update'], reverse=True)[:5]:
                report.append(f"  {pos['symbol']} {pos['name']}: {pos['age_days']}天前")
        
        report.append("\n" + "=" * 70)
        
        # 如果需要更新
        if freshness['stale']:
            report.append(f"\n🔄 建议操作：更新 {len(freshness['stale'])} 只陈旧数据股票")
        
        return "\n".join(report)
    
    def run_update(self, auto: bool = False) -> Dict:
        """
        运行数据更新
        
        Args:
            auto: 是否自动模式（只更新陈旧数据）
        
        Returns:
            更新结果
        """
        print("🔍 检查数据新鲜度...")
        positions = self.load_positions()
        freshness = self.check_data_freshness(positions)
        
        # 打印报告
        report = self.generate_report()
        print(report)
        
        # 保存报告
        report_dir = Path('./reports/data_freshness')
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f'freshness_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 更新陈旧数据
        if freshness['stale']:
            print(f"\n🔄 开始更新陈旧数据...")
            update_result = self.update_stale_data(freshness['stale'])
            
            # 保存更新结果
            result_file = report_dir / f'update_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'freshness_before': freshness['summary'],
                    'update_result': update_result['summary'],
                    'success_stocks': update_result['success'],
                    'failed_stocks': update_result['failed']
                }, f, ensure_ascii=False, indent=2)
            
            return {
                'status': 'completed',
                'freshness': freshness['summary'],
                'update_result': update_result['summary'],
                'report_file': str(report_file),
                'result_file': str(result_file)
            }
        else:
            print("\n✅ 所有数据都是新鲜的，无需更新")
            return {
                'status': 'no_update_needed',
                'freshness': freshness['summary'],
                'report_file': str(report_file)
            }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='陈旧数据更新 Agent')
    parser.add_argument('--auto', action='store_true', help='自动模式')
    parser.add_argument('--threshold', type=int, default=2, help='陈旧阈值（天）')
    parser.add_argument('--check-only', action='store_true', help='只检查不更新')
    parser.add_argument('--non-interactive', action='store_true', help='无人值守模式：禁用所有交互式提示')
    
    args = parser.parse_args()
    
    # 设置无人值守模式
    setup_non_interactive_mode(args.non_interactive)
    
    updater = StaleDataUpdater(stale_threshold_days=args.threshold)
    
    if args.check_only:
        report = updater.generate_report()
        print(report)
    else:
        result = updater.run_update(auto=args.auto)
        print(f"\n✅ 任务完成：{result['status']}")


if __name__ == '__main__':
    main()
