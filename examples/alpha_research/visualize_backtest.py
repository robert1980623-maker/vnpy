"""
回测结果可视化

生成资金曲线、回撤图等
"""

import sys
from pathlib import Path

import polars as pl
import numpy as np

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("⚠️  未安装 plotly，无法显示图表")
    print("安装：pip install plotly")


def load_backtest_results() -> pl.DataFrame:
    """
    运行回测并获取结果
    
    复用简化回测引擎
    """
    from test_backtest_simple import run_backtest
    
    engine = run_backtest()
    
    # 转换为 DataFrame
    df = pl.DataFrame(engine.daily_values)
    
    return df, engine


def create_charts(df: pl.DataFrame) -> None:
    """创建图表"""
    
    if not HAS_PLOTLY:
        print("\n⚠️  跳过图表生成（需要 plotly）")
        return
    
    print("\n📊 生成图表...")
    
    # 计算指标
    df = df.with_columns([
        pl.col("total_value").alias("value"),
        (pl.col("total_value") / pl.col("total_value").cum_max()).alias("drawdown_ratio")
    ])
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("资金曲线", "回撤")
    )
    
    # 1. 资金曲线
    fig.add_trace(
        go.Scatter(
            x=df["datetime"].to_list(),
            y=df["total_value"].to_list(),
            name="组合价值",
            line=dict(color="blue", width=2)
        ),
        row=1, col=1
    )
    
    # 添加基准线（初始资金）
    fig.add_trace(
        go.Scatter(
            x=df["datetime"].to_list(),
            y=[1_000_000] * len(df),
            name="初始资金",
            line=dict(color="gray", width=1, dash="dash")
        ),
        row=1, col=1
    )
    
    # 2. 回撤
    drawdown = []
    peak = df["total_value"][0]
    
    for value in df["total_value"]:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        drawdown.append(dd)
    
    fig.add_trace(
        go.Scatter(
            x=df["datetime"].to_list(),
            y=drawdown,
            name="回撤 %",
            line=dict(color="red", width=1),
            fill="tozeroy"
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        title="回测结果可视化",
        height=800,
        showlegend=True,
        hovermode="x unified"
    )
    
    fig.update_xaxes(title="日期", row=2, col=1)
    fig.update_yaxes(title="组合价值", row=1, col=1)
    fig.update_yaxes(title="回撤 %", row=2, col=1)
    
    # 保存图表
    output_path = Path("./backtest_result.html")
    fig.write_html(str(output_path))
    
    print(f"  ✅ 图表已保存：{output_path.absolute()}")
    print("  用浏览器打开查看交互式图表")


def print_statistics(df: pl.DataFrame) -> None:
    """打印统计信息"""
    
    print("\n" + "=" * 60)
    print("详细统计")
    print("=" * 60)
    
    # 基础统计
    initial = df["total_value"][0]
    final = df["total_value"][-1]
    total_return = (final - initial) / initial * 100
    
    print(f"\n📈 收益指标:")
    print(f"  总收益率：{total_return:.2f}%")
    print(f"  绝对收益：{final - initial:,.0f}")
    
    # 年化收益（假设 240 个交易日/年）
    trading_days = len(df)
    years = trading_days / 240
    if years > 0:
        annual_return = ((final / initial) ** (1 / years) - 1) * 100
        print(f"  年化收益率：{annual_return:.2f}%")
    
    # 波动率
    daily_returns = df["total_value"].pct_change().drop_nulls()
    if len(daily_returns) > 0:
        volatility = daily_returns.std() * 100
        print(f"  日波动率：{volatility:.2f}%")
        print(f"  年化波动率：{volatility * np.sqrt(240):.2f}%")
    
    # 夏普比率（假设无风险利率 3%）
    risk_free = 0.03
    if years > 0 and len(daily_returns) > 0:
        excess_return = (final / initial) ** (1 / years) - 1 - risk_free
        sharpe = excess_return / (daily_returns.std() * np.sqrt(240))
        print(f"  夏普比率：{sharpe:.2f}")
    
    # 最大回撤
    max_dd = 0.0
    peak = initial
    
    for value in df["total_value"]:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    print(f"\n📉 风险指标:")
    print(f"  最大回撤：{max_dd:.2f}%")
    
    # 胜率（上涨天数比例）
    up_days = len(daily_returns.filter(daily_returns > 0))
    total_days = len(daily_returns)
    win_rate = up_days / total_days * 100 if total_days > 0 else 0
    
    print(f"\n📊 交易统计:")
    print(f"  交易天数：{total_days}")
    print(f"  上涨天数：{up_days}")
    print(f"  胜率：{win_rate:.1f}%")
    
    print("=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("回测结果可视化")
    print("=" * 60)
    
    # 1. 加载回测结果
    df, engine = load_backtest_results()
    
    # 2. 打印统计
    print_statistics(df)
    
    # 3. 生成图表
    create_charts(df)
    
    print("\n✅ 可视化完成！")


if __name__ == "__main__":
    main()
