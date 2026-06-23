#!/usr/bin/env python3
"""
每日 17:00 股票数据下载任务

功能:
1. 下载当日 A 股全市场股票行情数据
2. 抓取消息面数据：新闻、公司公告、券商研报
3. 更新宏观政策数据（央行、财政部、发改委等）
4. 同步国际形势数据（美股、港股、汇率、大宗商品）
5. 数据保存到 /Users/rowang/projects/vnpy/examples/alpha_research/data/
6. 完成后记录日志，确认数据完整性

用法:
    python3 daily_data_download_1700.py

Cron 配置 (17:00 执行):
    0 17 * * * cd /Users/rowang/projects/vnpy/examples/alpha_research && /usr/bin/python3 daily_data_download_1700.py >> logs/daily_download_1700.log 2>&1
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# 通知工具
from notification_utils import notify_task_start, notify_task_complete

# Tushare Token（用于宏观政策下载）
TUSHARE_TOKEN = '612016803bce9d11dda0846c5352ad7e4077ead71657cd6ee50b8bf5'

# 日志配置
log_dir = project_dir / 'logs' / 'daily_download_1700'
log_dir.mkdir(parents=True, exist_ok=True)

class DailyDataDownloader:
    """每日 17:00 数据下载器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.data_dir = project_dir / 'data'
        self.results = {
            'start_time': self.start_time.isoformat(),
            'end_time': None,
            'duration_seconds': None,
            'tasks': {},
            'status': 'running',
            'errors': []
        }
        
        print("=" * 80)
        print(" " * 25 + "每日 17:00 数据下载任务")
        print("=" * 80)
        print(f"开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据目录：{self.data_dir}")
        print("=" * 80)
        print()
    
    def _log_task(self, task_name: str, status: str, details: Dict = None):
        """记录任务状态"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
        print(f"[{timestamp}] {icon} {task_name}: {status}")
        
        self.results['tasks'][task_name] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
    
    def download_stock_market_data(self) -> Dict:
        """
        任务 1: 下载当日 A 股全市场股票行情数据
        使用 Tushare Pro 下载沪深 300 成分股日线数据
        """
        task_name = "A 股行情数据"
        self._log_task(task_name, "进行中")
        
        try:
            # 导入 batch_download_enhanced 模块
            import batch_download_enhanced as batch_downloader
            
            # 获取股票列表
            stocks = batch_downloader.get_stock_list()
            
            # 分批下载
            total_success = 0
            total_failed = 0
            
            for i in range(0, len(stocks), batch_downloader.BATCH_SIZE):
                batch_stocks = stocks[i:i + batch_downloader.BATCH_SIZE]
                batch_num = (i // batch_downloader.BATCH_SIZE) + 1
                
                # 下载批次
                success = batch_downloader.download_batch(batch_num, batch_stocks)
                if success:
                    total_success += len(batch_stocks)
                else:
                    total_failed += len(batch_stocks)
                
                # 批次间隔 (缩短间隔以加快下载)
                if i + batch_downloader.BATCH_SIZE < len(stocks):
                    time.sleep(5)
            
            stats = {
                'downloaded': total_success,
                'failed': total_failed,
                'total_stocks': len(stocks),
                'data_dir': str(self.data_dir / 'akshare')
            }
            
            self._log_task(task_name, "success", stats)
            return {'status': 'success', 'stats': stats}
            
        except Exception as e:
            error_msg = f"A 股行情数据下载失败：{str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            self.results['errors'].append(error_msg)
            self._log_task(task_name, "error", {'error': str(e)})
            return {'status': 'error', 'error': str(e)}
    
    def download_news_data(self) -> Dict:
        """
        任务 2: 抓取消息面数据
        - 个股新闻
        - 公司公告
        - 券商研报
        """
        task_name = "消息面数据"
        self._log_task(task_name, "进行中")
        
        try:
            # 导入新闻下载模块
            from download_news_data import download_all_news
            
            result = download_all_news()
            
            stats = {
                'stocks_count': result.get('stocks_count', 0),
                'news_count': result.get('news_count', 0),
                'use_tushare': result.get('use_tushare', False),
                'data_dir': str(self.data_dir / 'news')
            }
            
            self._log_task(task_name, "success", stats)
            return {'status': 'success', 'stats': stats}
            
        except Exception as e:
            error_msg = f"消息面数据下载失败：{str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            self.results['errors'].append(error_msg)
            self._log_task(task_name, "error", {'error': str(e)})
            return {'status': 'error', 'error': str(e)}
    
    def download_policy_data(self) -> Dict:
        """
        任务 3: 更新宏观政策数据
        - 央行公开市场操作
        - 存款准备金率
        - 存贷款基准利率
        - 货币供应量 (M0/M1/M2)
        - 社会融资规模
        - CPI/PPI 数据
        - PMI 数据
        """
        task_name = "宏观政策数据"
        self._log_task(task_name, "进行中")
        
        try:
            from download_daily_policy_data import DailyPolicyDataDownloader
            
            # 设置 TUSHARE_TOKEN 环境变量
            os.environ.setdefault('TUSHARE_TOKEN', TUSHARE_TOKEN)
            
            downloader = DailyPolicyDataDownloader()
            result = downloader.download_all()
            
            stats = {
                'status': result.get('status', 'unknown'),
                'data_types': list(result.get('data', {}).keys()) if isinstance(result, dict) else [],
                'data_dir': str(self.data_dir / 'policy')
            }
            
            self._log_task(task_name, "success", stats)
            return {'status': 'success', 'stats': stats}
            
        except Exception as e:
            error_msg = f"宏观政策数据下载失败：{str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            self.results['errors'].append(error_msg)
            self._log_task(task_name, "error", {'error': str(e)})
            return {'status': 'error', 'error': str(e)}
    
    def download_global_data(self) -> Dict:
        """
        任务 4: 同步国际形势数据
        - 美股数据
        - 港股数据
        - 汇率数据
        - 大宗商品
        - 地缘政治新闻
        """
        task_name = "国际形势数据"
        self._log_task(task_name, "进行中")
        
        try:
            from download_global_data_tushare import GlobalDataDownloader
            from download_geopolitics_data import GeopoliticsDataDownloader
            
            # 下载全球经济数据
            global_downloader = GlobalDataDownloader()
            global_result = global_downloader.download_all()
            
            # 下载地缘政治新闻
            geo_downloader = GeopoliticsDataDownloader()
            geo_result = geo_downloader.download_all()
            
            stats = {
                'global_economy': 'success' if global_result else 'partial',
                'international_news_count': global_result.get('international_news_count', 0) if global_result else 0,
                'geopolitics': 'success' if geo_result else 'partial',
                'geopolitics_summary': geo_result.get('summary', {}) if geo_result else {},
                'data_dir': str(self.data_dir / 'geopolitics')
            }
            
            self._log_task(task_name, "success", stats)
            return {'status': 'success', 'stats': stats}
            
        except Exception as e:
            error_msg = f"国际形势数据下载失败：{str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            self.results['errors'].append(error_msg)
            self._log_task(task_name, "error", {'error': str(e)})
            return {'status': 'error', 'error': str(e)}
    
    def verify_data_integrity(self) -> Dict:
        """
        任务 5: 验证数据完整性
        检查各数据目录的文件数量和最新修改时间
        """
        task_name = "数据完整性验证"
        self._log_task(task_name, "进行中")
        
        try:
            verification = {}
            
            # 检查各数据目录
            data_subdirs = ['stock_data', 'news', 'policy', 'geopolitics']
            
            for subdir in data_subdirs:
                dir_path = self.data_dir / subdir
                if dir_path.exists():
                    files = list(dir_path.glob('*'))
                    if files:
                        latest = max(files, key=lambda f: f.stat().st_mtime)
                        latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
                        verification[subdir] = {
                            'file_count': len(files),
                            'latest_file': latest.name,
                            'latest_time': latest_time.isoformat(),
                            'is_fresh': (datetime.now() - latest_time).total_seconds() < 86400  # 24 小时内
                        }
                    else:
                        verification[subdir] = {'file_count': 0, 'status': 'empty'}
                else:
                    verification[subdir] = {'status': 'dir_not_found'}
            
            # 总体评估
            all_fresh = all(
                v.get('is_fresh', False) 
                for v in verification.values() 
                if isinstance(v, dict) and 'is_fresh' in v
            )
            
            stats = {
                'verification': verification,
                'all_fresh': all_fresh,
                'checked_dirs': len(data_subdirs)
            }
            
            status = "success" if all_fresh else "warning"
            self._log_task(task_name, status, stats)
            return {'status': status, 'stats': stats}
            
        except Exception as e:
            error_msg = f"数据完整性验证失败：{str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            self.results['errors'].append(error_msg)
            self._log_task(task_name, "error", {'error': str(e)})
            return {'status': 'error', 'error': str(e)}
    
    def save_log(self):
        """保存下载日志"""
        self.results['end_time'] = datetime.now().isoformat()
        self.results['duration_seconds'] = (
            datetime.now() - self.start_time
        ).total_seconds()
        
        # 确定总体状态
        failed_tasks = [
            name for name, info in self.results['tasks'].items()
            if info['status'] == 'error'
        ]
        
        if failed_tasks:
            self.results['status'] = 'partial_success'
            self.results['failed_tasks'] = failed_tasks
        elif self.results['errors']:
            self.results['status'] = 'completed_with_errors'
        else:
            self.results['status'] = 'success'
        
        # 保存日志文件
        log_filename = f"download_log_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        log_path = log_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 日志已保存：{log_path}")
        
        # 同时保存一份最新日志的快捷方式
        latest_log_path = log_dir / 'latest_download_log.json'
        with open(latest_log_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📄 最新日志：{latest_log_path}")
        
        return log_path
    
    def print_summary(self):
        """打印下载摘要"""
        print("\n" + "=" * 80)
        print(" " * 30 + "下载任务摘要")
        print("=" * 80)
        
        # 任务状态
        print("\n📊 任务执行情况:")
        for task_name, info in self.results['tasks'].items():
            icon = "✅" if info['status'] == 'success' else "⚠️" if info['status'] == 'warning' else "❌"
            print(f"  {icon} {task_name}: {info['status']}")
        
        # 总体状态
        print(f"\n📈 总体状态: {self.results['status']}")
        print(f"⏱️  总耗时：{self.results['duration_seconds']:.1f} 秒")
        
        # 错误信息
        if self.results['errors']:
            print(f"\n⚠️  错误数量：{len(self.results['errors'])}")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"  {i}. {error}")
        
        # 数据完整性
        if '数据完整性验证' in self.results['tasks']:
            verification = self.results['tasks']['数据完整性验证'].get('details', {})
            if verification.get('all_fresh'):
                print("\n✅ 所有数据均为最新 (24 小时内)")
            else:
                print("\n⚠️  部分数据可能过期")
        
        print("=" * 80)
    
    def run(self):
        """执行所有下载任务"""
        # 全局设置 TUSHARE_TOKEN
        os.environ.setdefault('TUSHARE_TOKEN', TUSHARE_TOKEN)
        
        try:
            # 发送开始通知
            notify_task_start(
                task_name="每日 17:00 数据下载",
                details={
                    'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'tasks': ['A 股行情', '消息面', '宏观政策', '国际形势', '数据验证']
                }
            )
            
            # 依次执行各任务
            self.download_stock_market_data()
            time.sleep(2)  # 短暂休息，避免 API 限流
            
            self.download_news_data()
            time.sleep(2)
            
            self.download_policy_data()
            time.sleep(2)
            
            self.download_global_data()
            time.sleep(2)
            
            self.verify_data_integrity()
            
            # 保存日志（必须在 print_summary 之前，设置 duration_seconds）
            self.save_log()
            
            # 打印摘要
            self.print_summary()
            
            # 发送完成通知
            notify_task_complete(
                task_name="每日 17:00 数据下载",
                details={
                    'status': self.results['status'],
                    'duration_seconds': self.results['duration_seconds'],
                    'tasks_completed': len([t for t, i in self.results['tasks'].items() if i['status'] == 'success']),
                    'tasks_total': len(self.results['tasks'])
                }
            )
            
            print(f"\n✅ 每日 17:00 数据下载任务完成!")
            return self.results
            
        except Exception as e:
            error_msg = f"下载任务执行失败：{str(e)}"
            print(f"\n❌ {error_msg}")
            traceback.print_exc()
            
            self.results['status'] = 'failed'
            self.results['errors'].append(error_msg)
            
            # 先保存日志（设置 duration_seconds）
            self.save_log()
            
            # 打印摘要
            try:
                self.print_summary()
            except Exception:
                pass  # 避免二次崩溃
            
            return self.results


def main():
    """主函数"""
    downloader = DailyDataDownloader()
    results = downloader.run()
    
    # 返回退出码
    if results['status'] == 'success':
        sys.exit(0)
    elif results['status'] in ['partial_success', 'completed_with_errors']:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()
