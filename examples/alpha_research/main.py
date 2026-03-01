#!/usr/bin/env python3
"""
量化交易系统主入口

功能:
1. 数据下载
2. 选股策略
3. 回测验证
4. 模拟交易

使用示例:
    # 完整流程：下载数据 → 选股 → 回测 → 模拟交易
    python main.py --strategy value --stocks 10
    
    # 仅选股和模拟交易
    python main.py --strategy value --stocks 10 --skip-download --skip-backtest
    
    # 仅下载数据
    python main.py --only-download --max 20
    
    # 使用自定义配置
    python main.py --config config.yaml --strategy momentum
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 尝试导入 YAML 支持
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "vnpy"))

# 导入 vnpy 模块
try:
    from vnpy.alpha.lab import AlphaLab
    from vnpy.alpha.dataset import StockPool
    from vnpy.alpha.strategy.strategies.preset_strategies import (
        ValueStrategy, GrowthStrategy, MomentumStrategy,
        QualityStrategy, IndustryRotationStrategy
    )
    VNPY_AVAILABLE = True
except ImportError as e:
    print(f"警告：vnpy 模块导入失败：{e}")
    print("将使用简化模式运行")
    VNPY_AVAILABLE = False


def load_config(config_path: Optional[str] = None) -> dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        配置字典
    """
    if not YAML_AVAILABLE:
        logging.warning("PyYAML 未安装，使用默认配置")
        return {}
    
    # 默认配置文件路径
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logging.warning(f"配置文件不存在：{config_path}，使用默认配置")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info(f"配置文件已加载：{config_path}")
        return config
    except Exception as e:
        logging.error(f"加载配置文件失败：{e}")
        return {}


def setup_logging(log_dir: str = "./logs", log_level: str = "INFO", config: dict = None) -> logging.Logger:
    """
    设置日志系统
    
    Args:
        log_dir: 日志目录
        log_level: 日志级别
        config: 配置字典（可选）
    """
    # 如果提供了配置文件，优先使用配置
    if config and 'logging' in config:
        log_config = config['logging']
        log_dir = log_config.get('directory', log_dir)
        log_level = log_config.get('level', log_level)
    
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(
        log_path / f"quant_trading_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger("QuantTrading")


def download_data(max_stocks: int = 20, force: bool = False, data_dir: str = "./data/akshare/bars") -> bool:
    """
    下载股票数据
    
    Args:
        max_stocks: 最大下载股票数量
        force: 是否强制重新下载
        data_dir: 数据保存目录
        
    Returns:
        是否成功
    """
    logger = logging.getLogger("QuantTrading.Download")
    logger.info(f"开始下载数据，最大股票数：{max_stocks}")
    
    try:
        # 检查依赖
        try:
            import akshare
        except ImportError:
            logger.error("缺少 akshare 依赖，请运行：pip3 install akshare")
            logger.error("或使用备选数据源：python3 test_baostock.py")
            logger.error("或生成模拟数据：python3 generate_mock_data.py")
            return False
        
        # 导入下载脚本
        from download_data_akshare import download_stocks
        
        # 执行下载
        downloaded = download_stocks(
            max_stocks=max_stocks,
            output_dir=data_dir,
            force=force
        )
        
        logger.info(f"数据下载完成，共下载 {downloaded} 只股票")
        return True
        
    except Exception as e:
        logger.error(f"数据下载失败：{e}", exc_info=True)
        return False


def screen_stocks(
    strategy: str = "value",
    max_stocks: int = 10,
    data_dir: str = "./data/akshare/bars",
    lab_dir: str = "./lab/test"
) -> List[str]:
    """
    选股
    
    Args:
        strategy: 策略名称 (value|growth|momentum|quality|industry)
        max_stocks: 最大选股数量
        data_dir: 数据目录
        lab_dir: Lab 工作目录
        
    Returns:
        选中的股票代码列表
    """
    logger = logging.getLogger("QuantTrading.Screener")
    logger.info(f"开始选股，策略：{strategy}, 数量：{max_stocks}")
    
    # 简化版股票池（实际应该从股票池管理获取）
    stock_pool = [
        "000001.SZ", "000002.SZ", "000063.SZ", "000858.SZ",
        "002230.SZ", "002415.SZ", "002594.SZ", "300059.SZ", "300750.SZ",
        "600000.SH", "600016.SH", "600036.SH", "600519.SH", "600570.SH",
        "600690.SH", "601012.SH", "601166.SH", "601288.SH"
    ]
    
    if not VNPY_AVAILABLE:
        # 简化模式：直接返回前 N 只股票
        logger.warning("vnpy 模块不可用，使用简化选股模式")
        selected = stock_pool[:max_stocks]
        logger.info(f"选股完成（简化模式），选中 {len(selected)} 只股票：{selected}")
        return selected
    
    try:
        # 创建 Lab
        lab = AlphaLab(lab_dir)
        
        # 选择策略
        strategies = {
            "value": ValueStrategy,
            "growth": GrowthStrategy,
            "momentum": MomentumStrategy,
            "quality": QualityStrategy,
            "industry": IndustryRotationStrategy
        }
        
        if strategy not in strategies:
            logger.error(f"未知策略：{strategy}，可用策略：{list(strategies.keys())}")
            return stock_pool[:max_stocks]
        
        strategy_cls = strategies[strategy]
        strategy_instance = strategy_cls()
        
        logger.info(f"股票池大小：{len(stock_pool)}")
        
        # 执行选股
        selected = []
        for stock in stock_pool:
            if len(selected) >= max_stocks:
                break
            
            try:
                # 加载数据
                bars = lab.load_bar_data(stock, "daily")
                if bars is None or len(bars) == 0:
                    continue
                
                # 计算指标
                df = bars.to_pandas()
                if len(df) < 60:  # 至少需要 60 天数据
                    continue
                
                # 应用策略筛选
                if strategy == "value":
                    # 简化版：使用市盈率筛选（实际应该从财务数据获取）
                    selected.append(stock)
                elif strategy == "momentum":
                    # 动量策略：选择近期涨幅靠前的
                    recent_return = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
                    if recent_return > 0:  # 近期上涨
                        selected.append(stock)
                else:
                    # 其他策略：简单选择
                    selected.append(stock)
                    
            except Exception as e:
                logger.debug(f"处理 {stock} 失败：{e}")
                continue
        
        logger.info(f"选股完成，选中 {len(selected)} 只股票：{selected}")
        return selected
        
    except Exception as e:
        logger.error(f"选股失败：{e}", exc_info=True)
        return stock_pool[:max_stocks]


def run_backtest(
    stocks: List[str],
    start_date: str = "20250101",
    end_date: str = "20260301",
    data_dir: str = "./data/akshare/bars"
) -> dict:
    """
    回测
    
    Args:
        stocks: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        data_dir: 数据目录
        
    Returns:
        回测结果
    """
    logger = logging.getLogger("QuantTrading.Backtest")
    logger.info(f"开始回测，股票数：{len(stocks)}, 区间：{start_date}-{end_date}")
    
    try:
        # 简化版回测（实际应该使用完整的回测引擎）
        results = {
            "total_return": 0.0,
            "annual_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0
        }
        
        # TODO: 实现完整回测
        logger.warning("回测功能待完善，使用简化结果")
        
        logger.info(f"回测完成，总收益：{results['total_return']:.2%}")
        return results
        
    except Exception as e:
        logger.error(f"回测失败：{e}", exc_info=True)
        return {}


def run_paper_trading(
    stocks: List[str],
    initial_capital: float = 1_000_000.0,
    volume_per_stock: int = 1000,
    data_dir: str = "./data/akshare/bars"
) -> dict:
    """
    模拟交易
    
    Args:
        stocks: 股票代码列表
        initial_capital: 初始资金
        volume_per_stock: 每只股票买入数量
        data_dir: 数据目录
        
    Returns:
        交易结果
    """
    logger = logging.getLogger("QuantTrading.PaperTrading")
    logger.info(f"开始模拟交易，股票数：{len(stocks)}, 初始资金：{initial_capital:,.0f}")
    
    try:
        # 检查依赖
        try:
            import pandas
        except ImportError:
            logger.error("缺少 pandas 依赖，请运行：pip3 install pandas numpy")
            logger.error("或查看 QUICKSTART.md 获取详细安装指南")
            return {}
        
        # 导入模拟交易模块
        from paper_trading import PaperTradingAccount
        
        # 创建账户
        account = PaperTradingAccount(
            initial_capital=initial_capital,
            data_dir=data_dir
        )
        
        # 买入股票
        bought_stocks = []
        for stock in stocks:
            try:
                order_id = account.buy(stock, volume=volume_per_stock)
                if order_id:
                    bought_stocks.append(stock)
                    logger.info(f"买入 {stock}，数量：{volume_per_stock}")
            except Exception as e:
                logger.warning(f"买入 {stock} 失败：{e}")
                continue
        
        # 打印组合概览
        logger.info("=" * 60)
        logger.info("模拟交易完成，组合概览:")
        
        summary = account.get_portfolio_summary()
        logger.info(f"总资产：¥{summary['total_value']:,.2f}")
        logger.info(f"可用资金：¥{summary['capital']:,.2f}")
        logger.info(f"总盈亏：¥{summary['total_profit']:,.2f} ({summary['total_return_pct']:.2%})")
        logger.info(f"持仓数量：{summary['position_count']}")
        
        # 保存结果（统一路径）
        output_dir = Path("./paper_trading")
        output_dir.mkdir(exist_ok=True)
        account.save_to_file(str(output_dir))
        logger.info(f"交易记录已保存到：{output_dir.absolute()}")
        logger.info(f"  - 持仓：{output_dir}/positions.json")
        logger.info(f"  - 成交：{output_dir}/trades.csv")
        logger.info(f"  - 概览：{output_dir}/portfolio_summary.json")
        
        return summary
        
    except Exception as e:
        logger.error(f"模拟交易失败：{e}", exc_info=True)
        return {}


def main():
    """主函数"""
    # 先加载配置文件
    # 注意：此时 logger 还未初始化，使用 print 输出
    config_path = None
    for i, arg in enumerate(sys.argv):
        if arg in ['--config', '-c'] and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
            break
    
    config = load_config(config_path)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="量化交易系统主入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
    # 完整流程
    python main.py --strategy value --stocks 10
    
    # 仅选股和模拟交易
    python main.py --strategy value --stocks 10 --skip-download --skip-backtest
    
    # 仅下载数据
    python main.py --only-download --max 20
    
    # 使用配置文件
    python main.py --config config.yaml
        """
    )
    
    # 策略参数（从配置文件读取默认值）
    default_strategy = config.get('strategy', {}).get('default_strategy', 'value')
    default_stocks = config.get('strategy', {}).get('max_stocks', 10)
    
    parser.add_argument(
        "--strategy", "-s",
        type=str,
        default=default_strategy,
        choices=["value", "growth", "momentum", "quality", "industry"],
        help=f"选股策略 (默认：{default_strategy})"
    )
    
    parser.add_argument(
        "--stocks", "-n",
        type=int,
        default=default_stocks,
        help=f"选股数量 (默认：{default_stocks})"
    )
    
    # 流程控制
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="跳过数据下载"
    )
    
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="跳过回测"
    )
    
    parser.add_argument(
        "--skip-trading",
        action="store_true",
        help="跳过模拟交易"
    )
    
    parser.add_argument(
        "--only-download",
        action="store_true",
        help="仅下载数据"
    )
    
    # 配置参数
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径 (YAML)"
    )
    
    # 数据参数
    default_data_dir = config.get('data', {}).get('directory', './data/akshare/bars')
    default_max_download = config.get('data', {}).get('max_stocks', 20)
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default=default_data_dir,
        help=f"数据目录 (默认：{default_data_dir})"
    )
    
    parser.add_argument(
        "--lab-dir",
        type=str,
        default=config.get('advanced', {}).get('lab_directory', './lab/test'),
        help="Lab 工作目录 (默认：./lab/test)"
    )
    
    parser.add_argument(
        "--max-download",
        type=int,
        default=default_max_download,
        help=f"最大下载股票数 (默认：{default_max_download})"
    )
    
    # 交易参数
    default_capital = config.get('trading', {}).get('initial_capital', 1_000_000.0)
    default_volume = config.get('trading', {}).get('default_volume', 1000)
    
    parser.add_argument(
        "--capital",
        type=float,
        default=default_capital,
        help=f"初始资金 (默认：{default_capital:,.0f})"
    )
    
    parser.add_argument(
        "--volume",
        type=int,
        default=default_volume,
        help=f"每只股票买入数量 (默认：{default_volume})"
    )
    
    # 日志参数
    default_log_level = config.get('logging', {}).get('level', 'INFO')
    default_log_dir = config.get('logging', {}).get('directory', './logs')
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=default_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help=f"日志级别 (默认：{default_log_level})"
    )
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default=default_log_dir,
        help=f"日志目录 (默认：{default_log_dir})"
    )
    
    args = parser.parse_args()
    
    # 设置日志（传入配置）
    global logger
    logger = setup_logging(args.log_dir, args.log_level, config)
    
    # 打印欢迎信息
    logger.info("=" * 60)
    logger.info("量化交易系统 v1.0")
    logger.info("=" * 60)
    logger.info(f"策略：{args.strategy}")
    logger.info(f"选股数量：{args.stocks}")
    logger.info(f"初始资金：¥{args.capital:,.0f}")
    logger.info(f"数据目录：{args.data_dir}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # 1. 下载数据
        if args.only_download:
            logger.info("模式：仅下载数据")
            success = download_data(
                max_stocks=args.max_download,
                data_dir=args.data_dir
            )
            sys.exit(0 if success else 1)
        
        if not args.skip_download:
            logger.info("步骤 1/4: 下载数据...")
            download_data(
                max_stocks=args.max_download,
                data_dir=args.data_dir
            )
        else:
            logger.info("步骤 1/4: 跳过数据下载")
        
        # 2. 选股
        logger.info("步骤 2/4: 选股...")
        selected_stocks = screen_stocks(
            strategy=args.strategy,
            max_stocks=args.stocks,
            data_dir=args.data_dir,
            lab_dir=args.lab_dir
        )
        
        if not selected_stocks:
            logger.warning("未选中任何股票，程序终止")
            sys.exit(1)
        
        logger.info(f"选中 {len(selected_stocks)} 只股票：{', '.join(selected_stocks)}")
        
        # 3. 回测
        if not args.skip_backtest:
            logger.info("步骤 3/4: 回测...")
            backtest_result = run_backtest(
                stocks=selected_stocks,
                data_dir=args.data_dir
            )
            
            if backtest_result:
                logger.info(f"回测结果：总收益 {backtest_result.get('total_return', 0):.2%}")
        else:
            logger.info("步骤 3/4: 跳过回测")
        
        # 4. 模拟交易
        if not args.skip_trading:
            logger.info("步骤 4/4: 模拟交易...")
            trading_result = run_paper_trading(
                stocks=selected_stocks,
                initial_capital=args.capital,
                volume_per_stock=args.volume,
                data_dir=args.data_dir
            )
            
            if trading_result:
                logger.info("=" * 60)
                logger.info("交易完成！")
                logger.info(f"总资产：¥{trading_result.get('total_value', 0):,.2f}")
                logger.info(f"总盈亏：¥{trading_result.get('total_profit', 0):,.2f} "
                           f"({trading_result.get('total_return_pct', 0):.2%})")
                logger.info("=" * 60)
        else:
            logger.info("步骤 4/4: 跳过模拟交易")
        
        # 完成
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("系统运行完成！")
        logger.info(f"总耗时：{duration}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("用户中断程序")
        sys.exit(1)
    except Exception as e:
        logger.error(f"系统异常：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
