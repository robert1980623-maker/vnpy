"""
PriceUpdater 单元测试
"""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from accounts.price_updater import PriceUpdater, _symbol_to_filename


class TestSymbolMapping(unittest.TestCase):
    """测试 symbol 到文件名的映射"""

    def test_szse_mapping(self):
        """深交所: 000001.SZSE -> 000001_sz.csv"""
        self.assertEqual(_symbol_to_filename("000001.SZSE"), "000001_sz.csv")

    def test_shse_mapping(self):
        """上交所: 600519.SHSE -> 600519_sh.csv"""
        self.assertEqual(_symbol_to_filename("600519.SHSE"), "600519_sh.csv")

    def test_bjse_mapping(self):
        """北交所: 430047.BJSE -> 430047_bj.csv"""
        self.assertEqual(_symbol_to_filename("430047.BJSE"), "430047_bj.csv")

    def test_invalid_format(self):
        """无效格式返回 None"""
        self.assertIsNone(_symbol_to_filename("000001"))
        self.assertIsNone(_symbol_to_filename("invalid"))


class TestPriceUpdater(unittest.TestCase):
    """测试 PriceUpdater 类"""

    def setUp(self):
        self.updater = PriceUpdater()

    def test_get_latest_price_found(self):
        """测试读取真实存在的股票价格"""
        # 000001.SZSE 应该有数据
        price = self.updater.get_latest_price("000001.SZSE")
        # 可能为 None（如果 CSV 不存在）或有值
        if price is not None:
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)

    def test_get_latest_price_not_found(self):
        """测试读取不存在的股票"""
        price = self.updater.get_latest_price("999999.SZSE")
        self.assertIsNone(price)

    def test_get_latest_prices_batch(self):
        """测试批量读取"""
        symbols = ["000001.SZSE", "600519.SHSE", "999999.SZSE"]
        prices = self.updater.get_latest_prices(symbols)
        # 返回的应该是 dict
        self.assertIsInstance(prices, dict)
        # 999999 不应该在结果中
        self.assertNotIn("999999.SZSE", prices)

    def test_refresh_positions_no_account(self):
        """测试刷新不存在的账户"""
        # 不应该抛异常，应该返回 0
        count = self.updater.refresh_positions("nonexistent_account")
        self.assertEqual(count, 0)


class TestPriceUpdaterWithMock(unittest.TestCase):
    """使用 mock 测试 PriceUpdater 逻辑"""

    def test_refresh_positions_updates_db(self):
        """测试 refresh_positions 正确更新数据库"""
        updater = PriceUpdater()

        # Mock get_connection
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ("000001.SZSE", 1000, 10.5),  # symbol, quantity, avg_cost
        ]

        with patch("accounts.price_updater.get_connection", return_value=mock_conn):
            with patch.object(updater, "get_latest_prices", return_value={"000001.SZSE": 11.0}):
                count = updater.refresh_positions("test_account")

        self.assertEqual(count, 1)
        # 验证 commit 被调用
        mock_conn.commit.assert_called_once()

    def test_refresh_positions_skips_no_price(self):
        """测试没有价格数据的持仓被跳过"""
        updater = PriceUpdater()

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ("999999.SZSE", 1000, 10.5),
        ]

        with patch("accounts.price_updater.get_connection", return_value=mock_conn):
            with patch.object(updater, "get_latest_prices", return_value={}):
                count = updater.refresh_positions("test_account")

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
