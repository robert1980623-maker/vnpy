"""
选股策略真实数据回测

使用模拟数据进行回测测试
"""

from datetime import datetime
from pathlib import Path
import pandas as pd
import json
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.strategy import ValueStockStrategy
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.dataset import FundamentalData, FinancialIndicator

# 创建兼容的 Interval
class Interval:
    DAILY = "daily"


class SimpleBar:
    """简单的 K 线数据类"""
    def __init__(self, vt_symbol, datetime, open_price, high_price, low_price, 
                 close_price, volume, turnover=0):
        self.vt_symbol = vt_symbol
        self.datetime = datetime
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.volume = volume
        self.turnover = turnover
        self.interval = "daily"


class SimpleLab:
    """简单的实验室，用于加载本地数据"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self._bars_cache = {}
        self._fundamental = FundamentalData()
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        # 加载 K 线数据
        bars_path = self.data_dir / "bars"
        if bars_path.exists():
            for filepath in bars_path.glob("*.csv"):
                filename = filepath.stem
                parts = filename.split("_")
                if len(parts) != 2:
                    continue
                
                vt_symbol = f"{parts[0]}.{parts[1]}"
                df = pd.read_csv(filepath)
                df["datetime"] = pd.to_datetime(df["datetime"])
                
                bars = []
                for _, row in df.iterrows():
                    bar = SimpleBar(
                        vt_symbol=vt_symbol,
                        datetime=row["datetime"],
                        open_price=row["open_price"],
                        high_price=row["high_price"],
                        low_price=row["low_price"],
                        close_price=row["close_price"],
                        volume=row["volume"],
                        turnover=row.get("turnover", 0)
                    )
                    bars.append(bar)
                
                if bars:
                    self._bars_cache[vt_symbol] = bars
                    print(f"加载 {vt_symbol}: {len(bars)} 条 K 线")
        
        # 加载财务数据
        fundamental_path = self.data_dir / "fundamental.json"
        if fundamental_path.exists():
            with open(fundamental_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for vt_symbol, reports in data.items():
                for report_date, ind in reports.items():
                    indicator = FinancialIndicator(
                        vt_symbol=vt_symbol,
                        report_date=ind.get("report_date", report_date),
                        pe_ratio=ind.get("pe_ratio"),
                        pb_ratio=ind.get("pb_ratio"),
                        dividend_yield=ind.get("dividend_yield"),
                        roe=ind.get("roe"),
                        revenue_growth=ind.get("revenue_growth"),
                        net_profit_growth=ind.get("net_profit_growth")
                    )
                    self._fundamental.add(indicator)
            
            print(f"加载财务数据：{self._fundamental.get_stock_count()} 只股票")
    
    def get_bars(self, vt_symbol: str, interval, start: datetime, end: datetime) -> list:
        """获取 K 线数据"""
        bars = self._bars_cache.get(vt_symbol, [])
        return [bar for bar in bars if start <= bar.datetime <= end]
    
    def get_fundamental(self, vt_symbol: str, date: datetime) -> FinancialIndicator:
        """获取财务数据"""
        return self._fundamental.get_latest(vt_symbol)


def run_backtest(data_dir: str = "./data/mock"):
    """运行回测"""
    print("\n" + "=" * 60)
    print("选股策略回测")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n1. 加载数据...")
    lab = SimpleLab(data_dir)
    
    vt_symbols = list(lab._bars_cache.keys())
    if not vt_symbols:
        print("没有可用的股票数据！")
        return
    
    print(f"\n可用股票：{len(vt_symbols)} 只")
    
    # 2. 设置回测参数
    print("\n2. 设置回测参数...")
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    initial_capital = 1_000_000
    
    print(f"  开始日期：{start.strftime('%Y-%m-%d')}")
    print(f"  结束日期：{end.strftime('%Y-%m-%d')}")
    print(f"  初始资金：{initial_capital:,}")
    
    # 3. 创建回测引擎
    print("\n3. 创建回测引擎...")
    engine = create_cross_sectional_engine(
        lab,
        initial_capital=initial_capital,
        commission_rate=0.0003,
        slippage=0.001,
        max_positions=5,
        position_size=0.2
    )
    
    engine.set_parameters(
        vt_symbols=vt_symbols,
        interval="daily",
        start=start,
        end=end,
        capital=initial_capital
    )
    
    # 4. 添加策略
    print("\n4. 添加策略...")
    engine.add_strategy(
        ValueStockStrategy,
        setting={
            'max_pe': 20,
            'max_pb': 3,
            'min_dividend_yield': 2,
            'min_roe': 8,
            'max_positions': 5
        }
    )
    print("  价值股策略 (PE<20, PB<3, 股息率>2%, ROE>8%)")
    
    # 5. 运行回测
    print("\n5. 运行回测...")
    try:
        engine.load_data()
        print("  ✓ 数据加载完成")
        
        engine.run_backtesting()
        print("  ✓ 回测运行完成")
        
        # 6. 计算统计
        print("\n6. 回测结果...")
        stats = engine.calculate_statistics()
        
        if stats:
            print(f"\n{'='*60}")
            print("回测统计")
            print(f"{'='*60}")
            print(f"总收益：     {stats.get('total_return_pct', 0):>10.2f}%")
            print(f"年化收益：   {stats.get('annual_return_pct', 0):>10.2f}%")
            print(f"波动率：     {stats.get('volatility_pct', 0):>10.2f}%")
            print(f"夏普比率：   {stats.get('sharpe_ratio', 0):>10.2f}")
            print(f"最大回撤：   {stats.get('max_drawdown_pct', 0):>10.2f}%")
            print(f"交易次数：   {stats.get('total_trades', 0):>10d}")
            print(f"手续费：     {stats.get('total_commission', 0):>10.2f}")
            print(f"最终净值：   {stats.get('final_value', 0):>10.2f}")
            print(f"{'='*60}")
        else:
            print("无法计算统计信息")
        
        # 7. 显示图表
        print("\n7. 生成图表...")
        try:
            engine.show_chart()
            print("  ✓ 图表已显示")
        except Exception as e:
            print(f"  提示：安装 matplotlib 以显示图表 (pip install matplotlib)")
        
    except Exception as e:
        print(f"\n回测失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="选股策略回测")
    parser.add_argument("--data", type=str, default="./data/mock", 
                       help="数据目录")
    
    args = parser.parse_args()
    run_backtest(args.data)
