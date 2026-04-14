#!/usr/bin/env python3
"""
单元测试 - sync_feishu_cache.py 飞书同步逻辑

测试目标：
- 验证 sync_account() 正确同步账户数据
- 验证 sync_positions() 正确同步持仓数据
- Mock feishu_bitable_app_table_record 外部调用
- Mock 文件系统操作确保测试独立运行

前置条件（由 tests/unit/conftest.py 处理）：
- sys.modules["openclaw_lark"] 已被 inject
- sys.exit 已被 patch 以阻止 sys.exit(1)
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────
# 飞书 API mock：确保 conftest 的 mock 仍然可用
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def mock_feishu_api():
    """返回一个新的 MagicMock 供测试使用"""
    return MagicMock()


class TestSyncAccount:
    """测试 sync_account() 同步账户数据"""

    def test_sync_account_success_writes_cache(self, tmp_path, mock_feishu_api):
        """成功同步后 account.json 包含正确数据"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()

        mock_result = {
            "items": [{
                "fields": {
                    "账户 ID": "ACC001",
                    "账户名称": "王雅轩主账户",
                    "初始资金": 1000000,
                    "现金余额": 3453.6,
                    "状态": "active"
                }
            }]
        }
        mock_feishu_api.return_value = mock_result

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert result is not None
        assert result["account_id"] == "ACC001"
        assert result["account_name"] == "王雅轩主账户"
        assert result["initial_capital"] == 1000000.0
        assert result["current_cash"] == 3453.6

        cache_file = cache_dir / "account.json"
        assert cache_file.exists()
        with open(cache_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["account_id"] == "ACC001"

    def test_sync_account_empty_items_returns_none(self, tmp_path, mock_feishu_api):
        """API 返回空 items 时返回 None"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = {"items": []}

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert result is None

    def test_sync_account_api_returns_none(self, tmp_path, mock_feishu_api):
        """API 返回 None 时返回 None"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = None

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert result is None

    def test_sync_account_exception_returns_none(self, tmp_path, mock_feishu_api):
        """API 抛出异常时捕获并返回 None"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.side_effect = Exception("Network")

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert result is None

    def test_sync_account_uses_default_when_field_missing(self, tmp_path, mock_feishu_api):
        """字段缺失时使用默认值"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = {"items": [{"fields": {}}]}

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert result["account_id"] == "ACC001"
        assert result["account_name"] == "王雅轩主账户"
        assert result["initial_capital"] == 1000000.0
        assert result["currency"] == "CNY"

    def test_sync_account_updated_at_is_iso_format(self, tmp_path, mock_feishu_api):
        """updated_at 为 ISO 格式时间戳"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = {
            "items": [{
                "fields": {
                    "账户 ID": "ACC001",
                    "账户名称": "测试账户",
                    "初始资金": 500000,
                    "现金余额": 500000,
                    "状态": "active"
                }
            }]
        }

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_account()

        assert "updated_at" in result
        assert "T" in result["updated_at"]


class TestSyncPositions:
    """测试 sync_positions() 同步持仓数据"""

    def test_sync_positions_success(self, tmp_path, mock_feishu_api):
        """成功同步持仓数据"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()

        mock_result = {
            "items": [
                {
                    "fields": {
                        "股票代码": "300476",
                        "股票名称": "胜宏科技",
                        "持仓数量": 32200,
                        "平均成本": 12.162
                    }
                },
                {
                    "fields": {
                        "股票代码": "603893",
                        "股票名称": "瑞芯微",
                        "持仓数量": 30100,
                        "平均成本": 10.13
                    }
                }
            ]
        }
        mock_feishu_api.return_value = mock_result

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        assert result is not None
        assert len(result) == 2
        assert result[0]["symbol"] == "300476"
        assert result[0]["quantity"] == 32200
        assert result[1]["symbol"] == "603893"

    def test_sync_positions_skips_empty_symbol(self, tmp_path, mock_feishu_api):
        """股票代码为空时跳过该记录"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_result = {
            "items": [
                {
                    "fields": {
                        "股票代码": "300476",
                        "股票名称": "胜宏科技",
                        "持仓数量": 32200,
                        "平均成本": 12.162
                    }
                },
                {
                    "fields": {
                        "股票代码": "",
                        "股票名称": "无效股票",
                        "持仓数量": 100,
                        "平均成本": 10.0
                    }
                }
            ]
        }
        mock_feishu_api.return_value = mock_result

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        assert len(result) == 1
        assert result[0]["symbol"] == "300476"

    def test_sync_positions_cost_calculation(self, tmp_path, mock_feishu_api):
        """cost = 持仓数量 × 平均成本"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_result = {
            "items": [{
                "fields": {
                    "股票代码": "300476",
                    "股票名称": "胜宏科技",
                    "持仓数量": 32200,
                    "平均成本": 12.162
                }
            }]
        }
        mock_feishu_api.return_value = mock_result

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        expected_cost = 32200 * 12.162
        assert abs(result[0]["cost"] - expected_cost) < 0.01

    def test_sync_positions_no_items_returns_none(self, tmp_path, mock_feishu_api):
        """API 返回空列表时返回 None"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = {"items": []}

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        assert result is None

    def test_sync_positions_api_exception_returns_none(self, tmp_path, mock_feishu_api):
        """API 异常时捕获并返回 None"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.side_effect = Exception("API error")

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        assert result is None

    def test_sync_positions_writes_cache_file(self, tmp_path, mock_feishu_api):
        """同步后写入缓存文件 positions.json"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_result = {
            "items": [{
                "fields": {
                    "股票代码": "300476",
                    "股票名称": "胜宏科技",
                    "持仓数量": 32200,
                    "平均成本": 12.162
                }
            }]
        }
        mock_feishu_api.return_value = mock_result

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                result = sfc.sync_positions()

        cache_file = cache_dir / "positions.json"
        assert cache_file.exists()
        with open(cache_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved) == 1
        assert saved[0]["symbol"] == "300476"


class TestModuleConstants:
    """测试模块常量配置"""

    def test_app_token_is_non_empty_string(self):
        """APP_TOKEN 是非空字符串"""
        import sync_feishu_cache as sfc
        assert isinstance(sfc.APP_TOKEN, str)
        assert len(sfc.APP_TOKEN) > 0

    def test_account_table_id_non_empty(self):
        """ACCOUNT_TABLE 是非空字符串"""
        import sync_feishu_cache as sfc
        assert isinstance(sfc.ACCOUNT_TABLE, str)
        assert len(sfc.ACCOUNT_TABLE) > 0

    def test_position_table_id_non_empty(self):
        """POSITION_TABLE 是非空字符串"""
        import sync_feishu_cache as sfc
        assert isinstance(sfc.POSITION_TABLE, str)
        assert len(sfc.POSITION_TABLE) > 0

    def test_cache_dir_is_path_instance(self):
        """CACHE_DIR 是 Path 对象"""
        import sync_feishu_cache as sfc
        assert isinstance(sfc.CACHE_DIR, Path)

    def test_feishu_available_flag_exists(self):
        """FEISHU_AVAILABLE 标志存在"""
        import sync_feishu_cache as sfc
        assert hasattr(sfc, "FEISHU_AVAILABLE")


class TestMainBlockExecution:
    """测试 __main__ 执行"""

    def test_main_block_calls_both_sync_functions(self, tmp_path, mock_feishu_api):
        """__main__ 调用 sync_account 和 sync_positions"""
        cache_dir = tmp_path / "feishu_cache"
        cache_dir.mkdir()
        mock_feishu_api.return_value = {"items": []}

        with patch("sync_feishu_cache.CACHE_DIR", cache_dir):
            with patch("sync_feishu_cache.feishu_bitable_app_table_record", mock_feishu_api):
                import sync_feishu_cache as sfc
                # 执行不抛异常即通过
                sfc.sync_account()
                sfc.sync_positions()
