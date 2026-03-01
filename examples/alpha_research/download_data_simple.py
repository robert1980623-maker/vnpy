"""
简化版数据下载脚本

快速下载示例数据用于测试，不需要 RQData 账号
使用 Tushare 或 AKShare 免费数据源
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.dataset import StockPool, FundamentalData, create_pool, create_fundamental_data
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange

try:
    import akshare as ak
except ImportError:
    print("错误：请先安装 akshare")
    print("pip install akshare")
    sys.exit(1)


# ========== 配置 ==========

# 数据保存路径
DATA_PATH = Path("./data")
LAB_PATH = Path("./lab/test_strategy")

# 下载时间范围（最近 1 年）
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)

# 测试用股票池（沪深 300 部分成分股）
TEST_SYMBOLS = [
    "000001.SZSE",  # 平安银行
    "000002.SZSE",  # 万科 A
    "000063.SZSE",  # 中兴通讯
    "000100.SZSE",  # TCL 科技
    "000157.SZSE",  # 中联重科
    "000333.SZSE",  # 美的集团
    "000538.SZSE",  # 云南白药
    "000568.SZSE",  # 泸州老窖
    "000651.SZSE",  # 格力电器
    "000725.SZSE",  # 京东方 A
    "000858.SZSE",  # 五粮液
    "002001.SZSE",  # 新和成
    "002007.SZSE",  # 华兰生物
    "002027.SZSE",  # 分众传媒
    "002049.SZSE",  # 紫光国微
    "002129.SZSE",  # TCL 中环
    "002142.SZSE",  # 宁波银行
    "002230.SZSE",  # 科大讯飞
    "002236.SZSE",  # 大华股份
    "002241.SZSE",  # 歌尔股份
    "002304.SZSE",  # 洋河股份
    "002352.SZSE",  # 顺丰控股
    "002371.SZSE",  # 北方华创
    "002410.SZSE",  # 广联达
    "002415.SZSE",  # 海康威视
    "002459.SZSE",  # 晶澳科技
    "002460.SZSE",  # 赣锋锂业
    "002466.SZSE",  # 天齐锂业
    "002475.SZSE",  # 立讯精密
    "002487.SZSE",  # 大金重工
    "002507.SZSE",  # 涪陵榨菜
    "002594.SZSE",  # 比亚迪
    "002601.SZSE",  # 龙佰集团
    "002648.SZSE",  # 卫星化学
    "002709.SZSE",  # 天赐材料
    "002714.SZSE",  # 牧原股份
    "002812.SZSE",  # 恩捷股份
    "002821.SZSE",  # 凯莱英
    "002850.SZSE",  # 科达利
    "002920.SZSE",  # 德赛西威
    "300014.SZSE",  # 亿纬锂能
    "300059.SZSE",  # 东方财富
    "300122.SZSE",  # 智飞生物
    "300124.SZSE",  # 汇川技术
    "300274.SZSE",  # 阳光电源
    "300316.SZSE",  # 晶盛机电
    "300347.SZSE",  # 泰格医药
    "300413.SZSE",  # 芒果超媒
    "300433.SZSE",  # 蓝思科技
    "300450.SZSE",  # 先导智能
    "300498.SZSE",  # 温氏股份
    "300601.SZSE",  # 康泰生物
    "300628.SZSE",  # 亿联网络
    "300750.SZSE",  # 宁德时代
    "300759.SZSE",  # 康龙化成
    "300760.SZSE",  # 迈瑞医疗
    "300782.SZSE",  # 卓胜微
    "300896.SZSE",  # 爱美客
    "600000.SSE",   # 浦发银行
    "600009.SSE",   # 上海机场
    "600016.SSE",   # 民生银行
    "600028.SSE",   # 中国石化
    "600030.SSE",   # 中信证券
    "600031.SSE",   # 三一重工
    "600036.SSE",   # 招商银行
    "600048.SSE",   # 保利发展
    "600050.SSE",   # 中国联通
    "600104.SSE",   # 上汽集团
    "600111.SSE",   # 北方稀土
    "600132.SSE",   # 重庆啤酒
    "600141.SSE",   # 兴发集团
    "600176.SSE",   # 中国巨石
    "600183.SSE",   # 生益科技
    "600188.SSE",   # 兖矿能源
    "600219.SSE",   # 南山铝业
    "600276.SSE",   # 恒瑞医药
    "600309.SSE",   # 万华化学
    "600346.SSE",   # 恒力石化
    "600352.SSE",   # 浙江龙盛
    "600372.SSE",   # 中航机载
    "600406.SSE",   # 国电南瑞
    "600426.SSE",   # 华鲁恒升
    "600436.SSE",   # 片仔癀
    "600438.SSE",   # 通威股份
    "600459.SSE",   # 贵研铂业
    "600460.SSE",   # 士兰微
    "600486.SSE",   # 扬农化工
    "600489.SSE",   # 中金黄金
    "600519.SSE",   # 贵州茅台
    "600522.SSE",   # 中天科技
    "600547.SSE",   # 山东黄金
    "600570.SSE",   # 恒生电子
    "600584.SSE",   # 长电科技
    "600585.SSE",   # 海螺水泥
    "600588.SSE",   # 用友网络
    "600660.SSE",   # 福耀玻璃
    "600690.SSE",   # 海尔智家
    "600745.SSE",   # 闻泰科技
    "600763.SSE",   # 通策医疗
    "600809.SSE",   # 山西汾酒
    "600803.SSE",   # 新奥股份
    "600887.SSE",   # 伊利股份
    "600893.SSE",   # 航发动力
    "600900.SSE",   # 长江电力
    "600905.SSE",   # 三峡能源
    "600919.SSE",   # 江苏银行
    "600941.SSE",   # 中国移动
    "600989.SSE",   # 宝丰能源
    "601012.SSE",   # 隆基绿能
    "601066.SSE",   # 中信建投
    "601088.SSE",   # 中国神华
    "601117.SSE",   # 中国化学
    "601138.SSE",   # 工业富联
    "601166.SSE",   # 兴业银行
    "601211.SSE",   # 国泰君安
    "601225.SSE",   # 陕西煤业
    "601288.SSE",   # 农业银行
    "601318.SSE",   # 中国平安
    "601328.SSE",   # 交通银行
    "601336.SSE",   # 新华保险
    "601398.SSE",   # 工商银行
    "601601.SSE",   # 中国太保
    "601628.SSE",   # 中国人寿
    "601633.SSE",   # 长城汽车
    "601658.SSE",   # 长城证券
    "601668.SSE",   # 中国建筑
    "601669.SSE",   # 中国电建
    "601688.SSE",   # 华泰证券
    "601728.SSE",   # 中国电信
    "601766.SSE",   # 中国中车
    "601788.SSE",   # 光大证券
    "601816.SSE",   # 京沪高铁
    "601857.SSE",   # 中国石油
    "601865.SSE",   # 福莱特
    "601872.SSE",   # 招商轮船
    "601877.SSE",   # 正泰电器
    "601881.SSE",   # 中国银河
    "601888.SSE",   # 中国中免
    "601899.SSE",   # 紫金矿业
    "601919.SSE",   # 中远海控
    "601939.SSE",   # 建设银行
    "601985.SSE",   # 中国核电
    "601988.SSE",   # 中国银行
    "601995.SSE",   # 中金公司
    "601998.SSE",   # 中信银行
    "603019.SSE",   # 中科曙光
    "603195.SSE",   # 公牛集团
    "603259.SSE",   # 药明康德
    "603260.SSE",   # 合盛硅业
    "603288.SSE",   # 海天味业
    "603290.SSE",   # 斯达半导
    "603369.SSE",   # 今世缘
    "603392.SSE",   # 万泰生物
    "603486.SSE",   # 科沃斯
    "603501.SSE",   # 韦尔股份
    "603517.SSE",   # 绝味食品
    "603596.SSE",   # 伯特利
    "603659.SSE",   # 璞泰来
    "603707.SSE",   # 健友股份
    "603712.SSE",   # 七一二
    "603799.SSE",   # 华友钴业
    "603806.SSE",   # 福斯特
    "603833.SSE",   # 欧派家居
    "603899.SSE",   # 晨光股份
    "603986.SSE",   # 兆易创新
    "688005.SSE",   # 容百科技
    "688008.SSE",   # 澜起科技
    "688009.SSE",   # 中国通号
    "688012.SSE",   # 中微公司
    "688016.SSE",   # 心脉医疗
    "688019.SSE",   # 安集科技
    "688029.SSE",   # 南微医学
    "688032.SSE",   # 禾迈股份
    "688036.SSE",   # 传音控股
    "688037.SSE",   # 芯源微
    "688041.SSE",   # 海光信息
    "688050.SSE",   # 爱博医疗
    "688063.SSE",   # 派能科技
    "688065.SSE",   # 凯赛生物
    "688072.SSE",   # 拓荆科技
    "688082.SSE",   # 盛美上海
    "688083.SSE",   # 中望软件
    "688088.SSE",   # 虹软科技
    "688099.SSE",   # 晶晨股份
    "688105.SSE",   # 诺唯赞
    "688107.SSE",   # 安路科技
    "688111.SSE",   # 金山办公
    "688114.SSE",   # 华大智造
    "688116.SSE",   # 天奈科技
    "688120.SSE",   # 华海清科
    "688122.SSE",   # 西部超导
    "688126.SSE",   # 沪硅产业
    "688169.SSE",   # 石头科技
    "688180.SSE",   # 君实生物
    "688187.SSE",   # 时代电气
    "688188.SSE",   # 柏楚电子
    "688202.SSE",   # 美迪西
    "688208.SSE",   # 道通科技
    "688212.SSE",   # 澳华内镜
    "688223.SSE",   # 晶科能源
    "688234.SSE",   # 天岳先进
    "688235.SSE",   # 百济神州
    "688256.SSE",   # 寒武纪
    "688271.SSE",   # 联影医疗
    "688276.SSE",   # 百克生物
    "688278.SSE",   # 特宝生物
    "688297.SSE",   # 中无人机
    "688301.SSE",   # 奕瑞科技
    "688303.SSE",   # 大全能源
    "688318.SSE",   # 财富趋势
    "688319.SSE",   # 欧林生物
    "688321.SSE",   # 微芯生物
    "688331.SSE",   # 荣昌生物
    "688333.SSE",   # 铂力特
    "688339.SSE",   # 亿华通
    "688348.SSE",   # 昱能科技
    "688356.SSE",   # 键凯科技
    "688357.SSE",   # 建龙微纳
    "688358.SSE",   # 祥生医疗
    "688363.SSE",   # 华熙生物
    "688366.SSE",   # 昊海生科
    "688368.SSE",   # 晶丰明源
    "688369.SSE",   # 致远互联
    "688377.SSE",   # 迪威尔
    "688378.SSE",   # 奥普特
    "688383.SSE",   # 新益昌
    "688385.SSE",   # 复旦微电
    "688390.SSE",   # 固德威
    "688396.SSE",   # 华润微
    "688399.SSE",   # 硕世生物
    "688408.SSE",   # 中信博
    "688425.SSE",   # 铁建重工
    "688432.SSE",   # 有研硅
    "688472.SSE",   # 阿特斯
    "688475.SSE",   # 萤石网络
    "688486.SSE",   # 龙迅股份
    "688498.SSE",   # 源杰科技
    "688505.SSE",   # 复旦张江
    "688506.SSE",   # 百利天恒
    "688508.SSE",   # 芯朋微
    "688516.SSE",   # 奥特维
    "688520.SSE",   # 神州细胞
    "688521.SSE",   # 芯原股份
    "688526.SSE",   # 科前生物
    "688536.SSE",   # 思瑞浦
    "688556.SSE",   # 高测股份
    "688559.SSE",   # 海目星
    "688567.SSE",   # 孚能科技
    "688568.SSE",   # 中科星图
    "688578.SSE",   # 艾力斯
    "688598.SSE",   # 金博股份
    "688599.SSE",   # 天合光能
    "688606.SSE",   # 奥泰生物
    "688608.SSE",   # 恒玄科技
    "688617.SSE",   # 惠泰医疗
    "688619.SSE",   # 罗普特
    "688621.SSE",   # 阳光诺和
    "688636.SSE",   # 智明达
    "688639.SSE",   # 华恒生物
    "688656.SSE",   # 浩欧博
    "688660.SSE",   # 电气风电
    "688661.SSE",   # 和林微纳
    "688663.SSE",   # 新风光
    "688665.SSE",   # 四方光电
    "688667.SSE",   # 菱电电控
    "688668.SSE",   # 鼎通科技
    "688669.SSE",   # 聚石化学
    "688676.SSE",   # 金盘科技
    "688677.SSE",   # 海泰新光
    "688678.SSE",   # 福立旺
    "688680.SSE",   # 海优新材
    "688686.SSE",   # 奥普特
    "688689.SSE",   # 银河微电
    "688690.SSE",   # 纳微科技
    "688696.SSE",   # 极米科技
    "688699.SSE",   # 明微电子
    "688707.SSE",   # 振华新材
    "688711.SSE",   # 宏微科技
    "688728.SSE",   # 格科微
    "688733.SSE",   # 壹石通
    "688737.SSE",   # 中自科技
    "688739.SSE",   # 成大生物
    "688766.SSE",   # 普冉股份
    "688767.SSE",   # 博拓生物
    "688768.SSE",   # 容知日新
    "688772.SSE",   # 珠海冠宇
    "688776.SSE",   # 国光电气
    "688777.SSE",   # 中控技术
    "688778.SSE",   # 厦钨新能
    "688779.SSE",   # 长远锂科
    "688789.SSE",   # 宏华数科
    "688793.SSE",   # 倍轻松
    "688798.SSE",   # 艾为电子
    "688799.SSE",   # 华纳药厂
    "688800.SSE",   # 瑞可达
    "688819.SSE",   # 天能股份
    "688839.SSE",   # 安达智能
    "688981.SSE",   # 中芯国际
]


def download_bar_data(symbol: str, exchange: str) -> list[BarData]:
    """
    使用 AKShare 下载股票日频数据
    
    Args:
        symbol: 股票代码
        exchange: 交易所（SSE/SZSE）
    
    Returns:
        BarData 列表
    """
    try:
        # AKShare 代码格式
        if exchange == "SSE":
            ak_symbol = f"sh{symbol}"
        else:
            ak_symbol = f"sz{symbol}"
        
        # 下载日频数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=START_DATE.strftime("%Y%m%d"),
            end_date=END_DATE.strftime("%Y%m%d"),
            adjust=""  # 不复权
        )
        
        if df is None or df.empty:
            return []
        
        # 转换为 BarData
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.SSE if exchange == "SSE" else Exchange.SZSE,
                datetime=datetime(row["日期"].year, row["日期"].month, row["日期"].day),
                interval=Interval.DAILY,
                open_price=row["开盘"],
                high_price=row["最高"],
                low_price=row["最低"],
                close_price=row["收盘"],
                volume=row["成交量"],
                turnover=row["成交额"],
                open_interest=0,
                gateway_name="AKSHARE"
            )
            bars.append(bar)
        
        return bars
    
    except Exception as e:
        print(f"  ❌ {symbol} 下载失败：{e}")
        return []


def download_test_data() -> None:
    """下载测试数据"""
    print("\n" + "=" * 60)
    print("下载测试数据（使用 AKShare 免费数据源）")
    print("=" * 60)
    print(f"股票数量：{len(TEST_SYMBOLS)}")
    print(f"时间范围：{START_DATE.date()} - {END_DATE.date()}")
    
    lab = AlphaLab(str(LAB_PATH))
    
    success_count = 0
    total_bars = 0
    
    for i, vt_symbol in enumerate(TEST_SYMBOLS):
        symbol = vt_symbol.split(".")[0]
        exchange = vt_symbol.split(".")[1]
        
        print(f"\n[{i+1}/{len(TEST_SYMBOLS)}] {vt_symbol}", end="")
        
        # 下载数据
        bars = download_bar_data(symbol, exchange)
        
        if bars:
            # 保存数据
            lab.save_bar_data(bars)
            success_count += 1
            total_bars += len(bars)
            print(f" ✅ {len(bars)}条记录")
        else:
            print(" ❌ 无数据")
    
    print("\n" + "=" * 60)
    print(f"下载完成")
    print(f"成功：{success_count}/{len(TEST_SYMBOLS)}")
    print(f"总记录数：{total_bars:,}")
    print("=" * 60)


def generate_test_signals() -> None:
    """生成测试信号（随机数据）"""
    print("\n" + "=" * 60)
    print("生成测试信号")
    print("=" * 60)
    
    import random
    
    lab = AlphaLab(str(LAB_PATH))
    
    # 获取所有交易日
    trading_dates = sorted(lab.dts)
    
    if not trading_dates:
        print("❌ 无交易数据，请先下载")
        return
    
    all_signals = []
    
    for dt in trading_dates:
        date_str = dt.strftime("%Y-%m-%d")
        
        # 为每只股票生成随机信号
        signal_data = []
        for vt_symbol in TEST_SYMBOLS:
            signal_data.append({
                "datetime": dt,
                "vt_symbol": vt_symbol,
                "signal": random.uniform(-1, 1),  # 随机信号
                "pe_ratio": random.uniform(5, 50),
                "roe": random.uniform(5, 30),
            })
        
        if signal_data:
            df = pl.DataFrame(signal_data)
            all_signals.append(df)
    
    if all_signals:
        merged = pl.concat(all_signals)
        lab.save_signals(merged)
        print(f"✅ 生成 {len(merged)} 条测试信号")
    else:
        print("❌ 信号生成失败")


def create_sample_pool() -> None:
    """创建示例股票池"""
    print("\n" + "=" * 60)
    print("创建示例股票池")
    print("=" * 60)
    
    pool = create_pool(str(DATA_PATH / "pool"))
    
    # 创建测试股票池
    test_pool = {
        "test_pool": TEST_SYMBOLS
    }
    
    pool.create_custom_pool("test_pool", TEST_SYMBOLS)
    print(f"✅ 创建测试股票池：{len(TEST_SYMBOLS)} 只股票")
    
    # 创建沪深 300 模拟成分股（取前 300 只）
    csi300_symbols = TEST_SYMBOLS[:300]
    pool.create_custom_pool("csi300_sample", csi300_symbols)
    print(f"✅ 创建沪深 300 样本池：{len(csi300_symbols)} 只股票")


def main():
    """主函数"""
    print("=" * 60)
    print("简化版数据下载脚本（AKShare 免费数据源）")
    print("=" * 60)
    print(f"数据保存路径：{DATA_PATH.absolute()}")
    print(f"实验室路径：{LAB_PATH.absolute()}")
    
    # 1. 创建示例股票池
    create_sample_pool()
    
    # 2. 下载测试数据
    download_test_data()
    
    # 3. 生成测试信号
    generate_test_signals()
    
    print("\n" + "=" * 60)
    print("✅ 数据下载完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 运行回测验证")
    print("2. 测试选股策略")
    print("\n示例代码:")
    print("""
from datetime import datetime
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.cross_sectional_engine import create_cross_sectional_engine
from vnpy.alpha.strategy import SimpleScreenerStrategy
from vnpy.trader.constant import Interval

lab = AlphaLab("./lab/test_strategy")
engine = create_cross_sectional_engine(lab)

engine.set_parameters(
    vt_symbols=[],
    interval=Interval.DAILY,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    capital=1_000_000
)

engine.add_strategy(SimpleScreenerStrategy, setting={"top_k": 30})
engine.load_data()
engine.run_backtesting()
engine.calculate_statistics()
engine.show_chart()
    """)


if __name__ == "__main__":
    main()
