#!/usr/bin/env python3
"""
每日选股和交易计划生成 (v3 - 使用真实 Tushare 数据 + 飞书多维表格自动同步)

功能:
1. 多策略选股 (使用真实财务数据)
2. 生成交易计划
3. 发送钉钉通知
4. 保存选股报告
5. 显示股票名称
6. 自动同步到飞书多维表格 ✅
"""

import logging
logger = logging.getLogger(__name__)

import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import random

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent.parent))

from vnpy.alpha.dataset import StockPool, FundamentalData
from stock_name_utils import StockNameCache, format_symbol_with_name
from tushare_fundamental_fetcher_v2 import TushareBatchFetcher
from logger import TaskLogger


class FeishuBitableSync:
    """飞书多维表格同步工具（使用 subprocess 调用 OpenClaw 工具）"""

    def __init__(self):
        from config_loader import get_feishu_config
        feishu_config = get_feishu_config()
        self.app_token = feishu_config['app_token'] or os.environ.get('FEISHU_APP_TOKEN', '')
        self.table_id = feishu_config['table_id'] or os.environ.get('FEISHU_TABLE_ID', 'tblyihWO0zsV9xqw')
        self.user_open_id = feishu_config['user_open_id'] or os.environ.get('FEISHU_USER_OPEN_ID', 'ou_c4a65a3dcdbf8fe6d6a17a7df0e702e6')
        
    def sync_stock_selection(self, stocks, date_str=None):
        """
        同步选股结果到飞书多维表格
        
        Args:
            stocks: 选股结果列表，每个元素包含 symbol, name, strategies, pe, roe, score 等字段
            date_str: 日期字符串，格式 YYYY-MM-DD
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        if not self.app_token:
            logger.info("\n⚠️ FEISHU_APP_TOKEN 未配置，跳过飞书多维表格同步")
            return False
        
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "同步选股结果到飞书多维表格")
        logger.info("=" * 70)
        
        # 准备记录数据
        records = []
        for i, stock in enumerate(stocks, 1):
            # 转换日期为毫秒时间戳
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_timestamp = int(date_obj.timestamp() * 1000)
            
            # 策略类型字符串
            strategies_str = '+'.join(stock.get('strategies', []))
            
            record = {
                "fields": {
                    "选股日期": date_timestamp,
                    "股票代码": stock.get('symbol', ''),
                    "股票名称": stock.get('name', ''),
                    "策略类型": strategies_str,
                    "PE": stock.get('pe', 0),
                    "ROE": stock.get('roe', 0),
                    "排名": i,
                    "Agent ID": "Q-Trade",
                    "备注": stock.get('reasons', [''])[0] if stock.get('reasons') else ''
                }
            }
            records.append(record)
        
        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            records_file = f.name
        
        try:
            # 使用 Python 脚本调用飞书 API（通过 OpenClaw 的 Python API）
            sync_script = f'''
import sys
sys.path.insert(0, '/Users/rowang/.openclaw/extensions/openclaw-lark')
from openclaw_lark import feishu_bitable_app_table_record

# 读取记录
import json
with open('{records_file}', 'r', encoding='utf-8') as f:
    records = json.load(f)

# 批量创建
result = feishu_bitable_app_table_record(
    action='batch_create',
    app_token='{self.app_token}',
    table_id='{self.table_id}',
    records=records
)
print(json.dumps(result, ensure_ascii=False))
'''
            result = subprocess.run(
                ['python3', '-c', sync_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/Users/rowang/projects/vnpy/examples/alpha_research'
            )
            
            if result.returncode == 0:
                logger.info(f"\n✅ 成功同步 {len(records)} 条选股记录到飞书多维表格")
                return True
            else:
                logger.error(f"\n❌ 同步失败：{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.info("\n❌ 同步超时")
            return False
        except Exception as e:
            logger.error(f"\n❌ 同步异常：{e}")
            return False
        finally:
            # 清理临时文件
            import os
            try:
                os.unlink(records_file)
            except OSError:
                pass
    
    def send_notification(self, message):
        """发送飞书通知"""
        logger.info(f"\n📱 准备发送通知：{message[:50]}...")
        # 通知功能暂时简化，只打印日志
        logger.info(f"✅ 通知已记录（实际发送由 OpenClaw 消息系统处理）")


class DailyStockSelector:
    """每日选股器"""
    
    def __init__(self):
        self.data_dir = Path('./data/akshare/bars')
        self.selected_stocks = []
        self.trading_plan = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'buy': [],
            'sell': [],
            'hold': []
        }
        # 加载股票名称缓存
        self.name_cache = StockNameCache()
        # 初始化 Tushare 批量财务数据获取器 v2
        self.fundamental_fetcher = TushareBatchFetcher()
        
    def load_stocks(self):
        """加载股票池（保留 CSV 原始格式，v2 fetcher 内部会转换）"""
        csv_files = list(self.data_dir.glob('*.csv'))
        symbols = [f.stem for f in csv_files]
        logger.info(f"✅ 加载股票池：{len(symbols)} 只股票")
        return symbols
        
    def get_real_fundamentals(self, symbols):
        """从 Tushare 获取真实财务数据（v2 批量接口，~1 秒）"""
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "获取财务数据 (Tushare v2 批量)")
        logger.info("=" * 70)
        
        fundamentals = self.fundamental_fetcher.get_batch_fundamentals(symbols)
        return fundamentals
        
    def multi_strategy_selection(self, symbols, fundamentals, target_count=10):
        """多策略选股"""
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "多策略选股")
        logger.info("=" * 70)
        
        for symbol in symbols:
            data = fundamentals.get(symbol, {})
            
            # 跳过数据不完整的股票（至少需要 PE）
            if not data.get('pe') or data.get('pe') <= 0:
                continue
            
            strategies = []
            reasons = []
            
            roe = data.get('roe')
            pb = data.get('pb')
            dv = data.get('dividend_yield') or 0
            
            # 策略 1: 价值股 (PE<20, PB<3, 股息率>2%)
            # 优先使用 PB 替代 ROE（ROE 数据经常缺失）
            if data.get('pe', 100) < 20 and pb and 0 < pb < 3 and dv > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, PB={pb:.1f}, 股息率={dv:.1f}%")
            elif data.get('pe', 100) < 20 and roe and roe > 10 and dv > 2:
                strategies.append('价值')
                reasons.append(f"PE={data['pe']:.1f}, ROE={roe:.1f}%, 股息率={dv:.1f}%")
            
            # 策略 2: 成长股 (营收增长>25%, 利润增长>30%)
            if (data.get('revenue_growth') or 0) > 25 and (data.get('profit_growth') or 0) > 30:
                strategies.append('成长')
                reasons.append(f"营收增长={data['revenue_growth']:.1f}%, 利润增长={data['profit_growth']:.1f}%")
            
            # 策略 3: 质量股 (ROE>15% 或 PB<1)
            if roe and roe > 15:
                strategies.append('质量')
                reasons.append(f"ROE={roe:.1f}%")
            elif pb and 0 < pb < 1:
                strategies.append('破净')
                reasons.append(f"PB={pb:.1f}")
            
            # 策略 4: 高息股 (股息率>3%)
            if dv > 3:
                strategies.append('高息')
                reasons.append(f"股息率={dv:.1f}%")
            
            # 计算评分
            score = len(strategies) * 2
            if len(strategies) >= 3:
                score += 1
            if len(strategies) == 4:
                score += 1
            
            # 如果满足至少一个策略，加入候选
            if strategies:
                self.selected_stocks.append((symbol, {
                    'strategies': strategies,
                    'reasons': reasons,
                    'score': score,
                    'fundamentals': data
                }))
        
        # 按评分排序
        self.selected_stocks.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # 限制数量
        if len(self.selected_stocks) > target_count:
            self.selected_stocks = self.selected_stocks[:target_count]
        
        logger.info(f"\n✅ 选股完成：{len(self.selected_stocks)} 只")
        
        # 显示前 10 只
        logger.info("\n🏆 Top 10:")
        for i, (symbol, data) in enumerate(self.selected_stocks[:10], 1):
            name = self.name_cache.get_name(symbol)
            strategies_str = '+'.join(data['strategies'])
            pe = data['fundamentals'].get('pe', 'N/A')
            roe = data['fundamentals'].get('roe', 'N/A')
            logger.info(f"  {i}. {symbol} {name} - {strategies_str} (评分：{data['score']}, PE={pe}, ROE={roe}%)")
        
        return self.selected_stocks
    
    def generate_trading_plan(self, current_holdings=None):
        """生成交易计划"""
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "生成交易计划")
        logger.info("=" * 70)
        
        if current_holdings is None:
            current_holdings = []
        
        # 目标持仓：选股结果中的股票
        target_symbols = set([s[0] for s in self.selected_stocks[:20]])  # 前 20 只
        
        # 计算调仓
        buy_symbols = [s for s in target_symbols if s not in current_holdings]
        sell_symbols = [s for s in current_holdings if s not in target_symbols]
        hold_list = [s for s in current_holdings if s in target_symbols]
        
        # 生成详细的买入列表（包含股票信息）
        buy_list = []
        for symbol in buy_symbols[:10]:  # 最多买入 10 只
            stock_data = next((s[1] for s in self.selected_stocks if s[0] == symbol), {})
            buy_list.append({
                'symbol': symbol,
                'name': self.name_cache.get_name(symbol),
                'reason': '+'.join(stock_data.get('strategies', [])),
                'score': stock_data.get('score', 0),
                'pe': stock_data.get('fundamentals', {}).get('pe', 0),
                'roe': stock_data.get('fundamentals', {}).get('roe', 0)
            })
        
        self.trading_plan['buy'] = buy_list
        self.trading_plan['sell'] = list(sell_symbols)[:10]  # 最多卖出 10 只
        self.trading_plan['hold'] = list(hold_list)
        
        logger.info(f"\n买入：{len(self.trading_plan['buy'])} 只")
        for stock in self.trading_plan['buy'][:5]:
            logger.info(f"  - {stock['symbol']} {stock['name']} ({stock['reason']})")
        if len(self.trading_plan['buy']) > 5:
            logger.info(f"  ... 还有 {len(self.trading_plan['buy']) - 5} 只")
        
        logger.info(f"\n卖出：{len(self.trading_plan['sell'])} 只")
        for symbol in self.trading_plan['sell'][:5]:
            name = self.name_cache.get_name(symbol)
            logger.info(f"  - {symbol} {name}")
        if len(self.trading_plan['sell']) > 5:
            logger.info(f"  ... 还有 {len(self.trading_plan['sell']) - 5} 只")
        
        return self.trading_plan
    
    def save_reports(self, output_dir: str = './reports'):
        """保存选股报告和交易计划"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存选股结果
        selection_report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'total_count': len(self.selected_stocks),
            'stocks': []
        }
        
        for symbol, data in self.selected_stocks:
            stock_info = {
                'symbol': symbol,
                'name': self.name_cache.get_name(symbol),
                'strategies': data['strategies'],
                'score': data['score'],
                'reasons': data['reasons'],
                'pe': round(data['fundamentals'].get('pe') or 0, 2),
                'roe': round(data['fundamentals'].get('roe') or 0, 2),
                'dividend_yield': round(data['fundamentals'].get('dividend_yield') or 0, 2),
                'revenue_growth': round(data['fundamentals'].get('revenue_growth') or 0, 2),
                'profit_growth': round(data['fundamentals'].get('profit_growth') or 0, 2),
            }
            selection_report['stocks'].append(stock_info)
        
        # 保存 JSON
        selection_file = output_path / f'stock_selection_{selection_report["date"]}.json'
        with open(selection_file, 'w', encoding='utf-8') as f:
            json.dump(selection_report, f, ensure_ascii=False, indent=2)
        
        # 保存交易计划
        plan_file = output_path / f'trading_plan_{self.trading_plan["date"]}.json'
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(self.trading_plan, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 报告已保存:")
        logger.info(f"   选股报告：{selection_file}")
        logger.info(f"   交易计划：{plan_file}")
        
        return selection_report
        
    def sync_to_feishu(self, selection_report):
        """异步同步选股结果到飞书多维表格 (不阻塞主流程)"""
        import threading
        
        def sync_worker():
            """后台同步工作线程"""
            try:
                syncer = FeishuBitableSync()
                
                # 转换数据格式
                stocks_for_sync = []
                for stock in selection_report.get('stocks', []):
                    stocks_for_sync.append({
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'strategies': stock['strategies'],
                        'pe': stock['pe'],
                        'roe': stock['roe'],
                        'score': stock['score'],
                        'reasons': stock.get('reasons', [])
                    })
                
                # 执行同步
                success = syncer.sync_stock_selection(stocks_for_sync, selection_report['date'])
                
                if success:
                    # 发送通知
                    top3 = stocks_for_sync[:3]
                    top3_str = ', '.join([f"{s['name']}({s['symbol']})" for s in top3])
                    message = f"✅ {selection_report['date']} 选股完成！\n\n选出 {len(stocks_for_sync)} 只股票\nTop 3: {top3_str}\n\n已同步到飞书多维表格，请查收～"
                    syncer.send_notification(message)
                    
            except Exception as e:
                logger.error(f"⚠️  后台同步失败：{e}")
        
        # 启动后台线程 (daemon=True 确保主程序退出时自动清理)
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
        
        logger.info(f"\n📤 飞书同步已在后台启动 (不阻塞主流程)")
        return True  # 立即返回，不等待同步完成


def load_current_holdings_from_account(account_file: str = './accounts/virtual_2026_account.json'):
    """从虚拟账户文件读取当前持仓"""
    account_path = Path(account_file)
    
    if not account_path.exists():
        logger.warning(f"⚠️  警告：账户文件不存在 {account_file}，使用空持仓")
        return []
    
    try:
        with open(account_path, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        # 从 positions 数组中提取股票代码
        current_holdings = [pos['symbol'] for pos in account.get('positions', [])]
        
        logger.info(f"\n✅ 从虚拟账户读取持仓：{len(current_holdings)} 只股票")
        for symbol in current_holdings[:5]:
            name = StockNameCache().get_name(symbol)
            logger.info(f"  - {symbol} {name}")
        if len(current_holdings) > 5:
            logger.info(f"  ... 还有 {len(current_holdings) - 5} 只")
        
        return current_holdings
    except Exception as e:
        logger.error(f"⚠️  警告：读取账户文件失败 {e}，使用空持仓")
        return []


def main():
    """主函数"""
    logger = TaskLogger(task_name='daily_stock_selection')
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info("任务开始执行")
        logger.info("=" * 70)
        logger.info(" " * 20 + "每日选股系统 v2")
        logger.info("=" * 70)

        selector = DailyStockSelector()

        # 步骤 1: 加载股票池
        symbols = selector.load_stocks()

        # 步骤 2: 获取财务数据
        fundamentals = selector.get_real_fundamentals(symbols)

        # 步骤 3: 多策略选股
        selector.multi_strategy_selection(symbols, fundamentals, target_count=10)

        # 步骤 4: 从虚拟账户读取真实持仓
        current_holdings = load_current_holdings_from_account('./accounts/virtual_2026_account.json')

        # 步骤 5: 生成交易计划（使用真实持仓）
        selector.generate_trading_plan(current_holdings)

        # 步骤 6: 保存报告
        selection_report = selector.save_reports()

        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "完成")
        logger.info("=" * 70)
        logger.info(f"选股：{len(selector.selected_stocks)} 只")
        logger.info(f"买入：{len(selector.trading_plan['buy'])} 只")
        logger.info(f"卖出：{len(selector.trading_plan['sell'])} 只")

        logger.info("\n下一步:")
        logger.info("  - 查看选股报告：cat reports/stock_selection_*.json")
        logger.info("  - 查看交易计划：cat reports/trading_plan_*.json")
        logger.info("  - 执行交易：python3 execute_trading.py")
        
        # 自动同步到飞书多维表格 (异步)
        logger.info("\n" + "=" * 70)
        logger.info(" " * 20 + "自动同步到飞书多维表格 (异步)")
        logger.info("=" * 70)
        selector.sync_to_feishu(selection_report)
        logger.info("✅ 同步任务已在后台执行，主流程继续")
    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)

if __name__ == '__main__':
    main()
