#!/usr/bin/env python3
"""
daily_stock_selection.py 单元测试

覆盖:
- test_feishu_config_loading:         飞书配置加载（config_loader / 环境变量 / 缺失字段）
- test_stock_filtering:               多策略选股过滤逻辑（价值/成长/质量/高息/破净）
- test_industry_rotation_calculation: 行业轮动计算（评分排序、target_count 截断）

外部依赖全部通过 unittest.mock 隔离：
- config_loader.get_feishu_config
- stock_name_utils.StockNameCache
- tushare_fundamental_fetcher_v2.TushareBatchFetcher
- vnpy.alpha.dataset.StockPool / FundamentalData
"""

import os
import sys
import types
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# 路径设置 & 外部依赖 stub
# ---------------------------------------------------------------------------
# 目标模块位于 examples/alpha_research/，需要把该目录加入 sys.path
_alpha_research_dir = Path(__file__).resolve().parents[2] / "examples" / "alpha_research"
if str(_alpha_research_dir) not in sys.path:
    sys.path.insert(0, str(_alpha_research_dir))

# 在导入目标模块前，先把所有外部依赖注册到 sys.modules，避免触发真实 I/O
_STUBS = {
    "vnpy": types.ModuleType("vnpy"),
    "vnpy.alpha": types.ModuleType("vnpy.alpha"),
    "vnpy.alpha.dataset": types.ModuleType("vnpy.alpha.dataset"),
    "stock_name_utils": types.ModuleType("stock_name_utils"),
    "tushare_fundamental_fetcher_v2": types.ModuleType("tushare_fundamental_fetcher_v2"),
    "logger": types.ModuleType("logger"),
    "config_loader": types.ModuleType("config_loader"),
}
_STUBS["vnpy.alpha"].dataset = _STUBS["vnpy.alpha.dataset"]
_STUBS["vnpy"].alpha = _STUBS["vnpy.alpha"]

# StockPool / FundamentalData —— 仅在模块顶层 import 时引用，给占位类即可
_STUBS["vnpy.alpha.dataset"].StockPool = MagicMock(name="StockPool")
_STUBS["vnpy.alpha.dataset"].FundamentalData = MagicMock(name="FundamentalData")

# StockNameCache 实例需要 get_name() 方法
_mock_name_cache_cls = MagicMock(name="StockNameCache")
_mock_name_cache_cls.return_value.get_name.side_effect = lambda sym: f"Name_{sym}"
_STUBS["stock_name_utils"].StockNameCache = _mock_name_cache_cls
_STUBS["stock_name_utils"].format_symbol_with_name = lambda sym: sym

# TushareBatchFetcher 实例化时不应产生副作用
_STUBS["tushare_fundamental_fetcher_v2"].TushareBatchFetcher = MagicMock(name="TushareBatchFetcher")

# TaskLogger
_mock_logger_cls = MagicMock(name="TaskLogger")
_STUBS["logger"].TaskLogger = _mock_logger_cls

# config_loader —— 默认返回空配置（由各测试用例自行 patch）
_STUBS["config_loader"].get_feishu_config = lambda: {
    "app_token": "",
    "table_id": "",
    "user_open_id": "",
}

for mod_name, mod_obj in _STUBS.items():
    sys.modules.setdefault(mod_name, mod_obj)

# 现在可以安全导入目标模块
from daily_stock_selection import (  # noqa: E402
    FeishuBitableSync,
    DailyStockSelector,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def feishu_env(monkeypatch):
    """清除所有飞书相关环境变量，保证测试隔离"""
    for key in ("FEISHU_APP_TOKEN", "FEISHU_TABLE_ID", "FEISHU_USER_OPEN_ID"):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture()
def selector():
    """
    创建 DailyStockSelector 实例，所有外部依赖已被 stub 替换。
    每个测试获得独立实例，selected_stocks 互不影响。
    """
    return DailyStockSelector()


# ===========================================================================
# test_feishu_config_loading — 飞书配置加载
# ===========================================================================

class TestFeishuConfigLoading:
    """飞书配置加载逻辑"""

    def test_feishu_config_loading_all_from_config(self, feishu_env):
        """
        场景 1: config_loader.get_feishu_config() 返回完整配置
        期望:   FeishuBitableSync 优先使用 config_loader 的返回值
        """
        fake_config = {
            "app_token": "cli_a1b2c3",
            "table_id": "tblXyZ123",
            "user_open_id": "ou_abc",
        }
        with patch("config_loader.get_feishu_config", return_value=fake_config):
            sync = FeishuBitableSync()

        assert sync.app_token == "cli_a1b2c3"
        assert sync.table_id == "tblXyZ123"
        assert sync.user_open_id == "ou_abc"

    def test_feishu_config_loading_env_fallback(self, feishu_env):
        """
        场景 2: config_loader 返回空值，回退到环境变量
        期望:   从 FEISHU_APP_TOKEN / FEISHU_TABLE_ID / FEISHU_USER_OPEN_ID 加载
        """
        feishu_env.setenv("FEISHU_APP_TOKEN", "cli_env_token")
        feishu_env.setenv("FEISHU_TABLE_ID", "tbl_env_table")
        feishu_env.setenv("FEISHU_USER_OPEN_ID", "ou_env_user")

        empty_config = {"app_token": "", "table_id": "", "user_open_id": ""}
        with patch("config_loader.get_feishu_config", return_value=empty_config):
            sync = FeishuBitableSync()

        assert sync.app_token == "cli_env_token"
        assert sync.table_id == "tbl_env_table"
        assert sync.user_open_id == "ou_env_user"

    def test_feishu_config_loading_partial_env(self, feishu_env):
        """
        场景 3: config_loader 部分有值，其余从环境变量补齐
        期望:   config_loader 优先；缺失字段才查环境变量；再缺失则用硬编码默认
        """
        feishu_env.setenv("FEISHU_TABLE_ID", "tbl_from_env")
        # 不设置 FEISHU_APP_TOKEN → 应该走到硬编码默认值 ''

        partial_config = {
            "app_token": "cli_from_loader",
            "table_id": "",             # 缺失 → 环境变量
            "user_open_id": "",          # 缺失 → 环境变量 → 未设置 → 硬编码默认
        }
        with patch("config_loader.get_feishu_config", return_value=partial_config):
            sync = FeishuBitableSync()

        assert sync.app_token == "cli_from_loader"           # config_loader 优先
        assert sync.table_id == "tbl_from_env"               # 环境变量补齐
        # user_open_id 环境变量未设 → 使用源码中的硬编码默认值
        assert sync.user_open_id == "ou_c4a65a3dcdbf8fe6d6a17a7df0e702e6"

    def test_feishu_sync_returns_false_without_app_token(self, feishu_env, caplog):
        """
        场景 4: app_token 为空时，sync_stock_selection 应返回 False 且不发起请求
        """
        import logging
        empty_config = {"app_token": "", "table_id": "", "user_open_id": ""}
        with patch("config_loader.get_feishu_config", return_value=empty_config):
            sync = FeishuBitableSync()

        with caplog.at_level(logging.INFO):
            result = sync.sync_stock_selection(
                [{"symbol": "000001", "name": "测试", "strategies": ["价值"]}]
            )
        assert result is False
        assert "FEISHU_APP_TOKEN" in caplog.text


# ===========================================================================
# test_stock_filtering — 股票筛选逻辑
# ===========================================================================

class TestStockFiltering:
    """multi_strategy_selection 多策略选股"""

    def test_stock_filtering_value_strategy_pb(self, selector):
        """
        价值策略（PB 路径）: PE<20, 0<PB<3, 股息率>2%
        """
        fundamentals = {
            "600036": {"pe": 8.0, "pb": 1.2, "roe": None, "dividend_yield": 4.0,
                        "revenue_growth": 0, "profit_growth": 0},
        }
        result = selector.multi_strategy_selection(["600036"], fundamentals)

        assert len(result) == 1
        symbol, data = result[0]
        assert symbol == "600036"
        assert "价值" in data["strategies"]

    def test_stock_filtering_value_strategy_roe_fallback(self, selector):
        """
        价值策略（ROE 回退路径）: PE<20, ROE>10, 股息率>2%（PB 不满足时）
        """
        fundamentals = {
            "601318": {"pe": 10.0, "pb": 5.0, "roe": 18.0, "dividend_yield": 3.0,
                        "revenue_growth": 0, "profit_growth": 0},
        }
        result = selector.multi_strategy_selection(["601318"], fundamentals)

        assert len(result) == 1
        _, data = result[0]
        assert "价值" in data["strategies"]

    def test_stock_filtering_growth_strategy(self, selector):
        """
        成长策略: 营收增长>25%, 利润增长>30%
        """
        fundamentals = {
            "300750": {"pe": 50.0, "pb": 10.0, "roe": 12.0, "dividend_yield": 0.5,
                        "revenue_growth": 40.0, "profit_growth": 50.0},
        }
        result = selector.multi_strategy_selection(["300750"], fundamentals)

        assert len(result) == 1
        _, data = result[0]
        assert "成长" in data["strategies"]

    def test_stock_filtering_quality_strategy(self, selector):
        """
        质量策略: ROE>15%
        """
        fundamentals = {
            "000858": {"pe": 35.0, "pb": 8.0, "roe": 22.0, "dividend_yield": 1.0,
                        "revenue_growth": 10.0, "profit_growth": 15.0},
        }
        result = selector.multi_strategy_selection(["000858"], fundamentals)

        assert len(result) == 1
        _, data = result[0]
        assert "质量" in data["strategies"]

    def test_stock_filtering_break_net_asset(self, selector):
        """
        破净策略: 0<PB<1（ROE 不满足时走 elif 分支）
        """
        fundamentals = {
            "601398": {"pe": 6.0, "pb": 0.7, "roe": 5.0, "dividend_yield": 1.0,
                        "revenue_growth": 2.0, "profit_growth": 3.0},
        }
        result = selector.multi_strategy_selection(["601398"], fundamentals)

        assert len(result) == 1
        _, data = result[0]
        assert "破净" in data["strategies"]

    def test_stock_filtering_high_dividend_strategy(self, selector):
        """
        高息策略: 股息率>3%
        """
        fundamentals = {
            "601006": {"pe": 12.0, "pb": 1.5, "roe": 8.0, "dividend_yield": 5.0,
                        "revenue_growth": 3.0, "profit_growth": 2.0},
        }
        result = selector.multi_strategy_selection(["601006"], fundamentals)

        assert len(result) == 1
        _, data = result[0]
        assert "高息" in data["strategies"]

    def test_stock_filtering_skip_invalid_pe(self, selector):
        """
        PE 为 None / 0 / 负数 的股票应被跳过
        """
        fundamentals = {
            "BAD1": {"pe": None, "pb": 1.0, "roe": 20.0},
            "BAD2": {"pe": 0, "pb": 1.0, "roe": 20.0},
            "BAD3": {"pe": -5, "pb": 1.0, "roe": 20.0},
        }
        result = selector.multi_strategy_selection(
            ["BAD1", "BAD2", "BAD3"], fundamentals
        )
        assert result == []

    def test_stock_filtering_no_matching_strategy(self, selector):
        """
        数据完整但不满足任何策略条件 → 不加入候选
        """
        fundamentals = {
            "MEDI": {"pe": 25.0, "pb": 4.0, "roe": 8.0, "dividend_yield": 1.0,
                      "revenue_growth": 10.0, "profit_growth": 10.0},
        }
        result = selector.multi_strategy_selection(["MEDI"], fundamentals)
        assert result == []

    def test_stock_filtering_multi_strategy_bonus(self, selector):
        """
        同时满足 ≥3 个策略时，评分应包含额外 bonus（+1），
        满足 4 个策略时 bonus 更高（+2）
        """
        # 构造一只同时满足 价值+成长+质量+高息 的股票
        fundamentals = {
            "STAR": {
                "pe": 15.0,       # <20 ✅
                "pb": 2.0,        # 0<PB<3 ✅
                "roe": 20.0,      # >15 ✅ (质量)
                "dividend_yield": 4.0,  # >3 ✅ (高息) & >2 ✅ (价值)
                "revenue_growth": 30.0,  # >25 ✅ (成长)
                "profit_growth": 40.0,   # >30 ✅ (成长)
            },
        }
        result = selector.multi_strategy_selection(["STAR"], fundamentals)
        assert len(result) == 1
        _, data = result[0]
        # 4 个策略 → score = 4*2 + 1(>=3) + 1(==4) = 10
        assert data["score"] == 10
        assert set(data["strategies"]) == {"价值", "成长", "质量", "高息"}


# ===========================================================================
# test_industry_rotation_calculation — 行业轮动计算
# ===========================================================================

class TestIndustryRotationCalculation:
    """
    行业轮动计算: 按评分降序排列 + target_count 截断
    multi_strategy_selection() 即为轮动排名的核心实现。
    """

    def test_industry_rotation_sorting_by_score(self, selector):
        """
        多只股票应按评分降序排列
        """
        fundamentals = {
            "LOW":  {"pe": 12.0, "pb": 1.5, "roe": 8.0, "dividend_yield": 1.0,
                      "revenue_growth": 5.0, "profit_growth": 5.0},
            # LOW: 无策略命中 → 跳过

            "MED":  {"pe": 12.0, "pb": 1.5, "roe": 8.0, "dividend_yield": 4.0,
                      "revenue_growth": 5.0, "profit_growth": 5.0},
            # MED: 高息(4>3) → 1 策略 → score=2

            "HIGH": {"pe": 15.0, "pb": 2.0, "roe": 20.0, "dividend_yield": 4.0,
                      "revenue_growth": 30.0, "profit_growth": 40.0},
            # HIGH: 价值+成长+质量+高息 → 4 策略 → score=10
        }
        result = selector.multi_strategy_selection(
            ["LOW", "MED", "HIGH"], fundamentals
        )
        symbols = [sym for sym, _ in result]
        assert symbols == ["HIGH", "MED"]
        assert result[0][1]["score"] > result[1][1]["score"]

    def test_industry_rotation_target_count_truncation(self, selector):
        """
        target_count 限制: 选出 > target_count 只时应截断
        """
        # 构造 5 只不同评分的股票
        fundamentals = {}
        for i in range(5):
            sym = f"S{i:02d}"
            fundamentals[sym] = {
                "pe": 10.0,
                "pb": 1.0 + i * 0.3,     # 1.0, 1.3, 1.6, 1.9, 2.2
                "roe": 20.0,
                "dividend_yield": 4.0 + i,
                "revenue_growth": 30.0,
                "profit_growth": 40.0,
            }
        symbols = list(fundamentals.keys())
        result = selector.multi_strategy_selection(symbols, fundamentals, target_count=3)

        assert len(result) == 3

    def test_industry_rotation_empty_input(self, selector):
        """
        空输入: symbols=[] 或 fundamentals={} 应返回空列表
        """
        assert selector.multi_strategy_selection([], {}) == []
        assert selector.multi_strategy_selection(["X"], {}) == []

    def test_industry_rotation_trading_plan(self, selector):
        """
        选股完成后生成交易计划:
        - 不在持仓中的 → buy
        - 在持仓中但不在目标中 → sell
        - 同时在两者中 → hold
        """
        fundamentals = {
            "BUY1":  {"pe": 15.0, "pb": 2.0, "roe": 20.0, "dividend_yield": 4.0,
                       "revenue_growth": 30.0, "profit_growth": 40.0},
            "SELL1": {"pe": 15.0, "pb": 2.0, "roe": 20.0, "dividend_yield": 4.0,
                       "revenue_growth": 30.0, "profit_growth": 40.0},
        }
        selector.multi_strategy_selection(["BUY1"], fundamentals)
        # selected_stocks 现在只有 BUY1

        plan = selector.generate_trading_plan(current_holdings=["SELL1"])

        buy_syms = [s["symbol"] for s in plan["buy"]]
        assert "BUY1" in buy_syms
        assert "SELL1" in plan["sell"]
        assert plan["hold"] == []

    def test_industry_rotation_hold_overlap(self, selector):
        """
        持仓与选股结果有重叠 → 重叠部分归入 hold
        """
        fundamentals = {
            "OVERLAP": {"pe": 15.0, "pb": 2.0, "roe": 20.0, "dividend_yield": 4.0,
                         "revenue_growth": 30.0, "profit_growth": 40.0},
        }
        selector.multi_strategy_selection(["OVERLAP"], fundamentals)

        plan = selector.generate_trading_plan(current_holdings=["OVERLAP"])

        buy_syms = [s["symbol"] for s in plan["buy"]]
        assert "OVERLAP" not in buy_syms
        assert "OVERLAP" in plan["hold"]
        assert "OVERLAP" not in plan["sell"]

    def test_industry_rotation_plan_date_is_today(self, selector):
        """
        交易计划中的 date 字段应为当天日期
        """
        selector.generate_trading_plan()
        today = datetime.now().strftime("%Y-%m-%d")
        assert selector.trading_plan["date"] == today
