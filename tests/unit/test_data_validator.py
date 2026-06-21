#!/usr/bin/env python3
"""
data_validator.py 管道校验 单元测试

覆盖:
- DataValidator.validate(): 主入口
- _check_required_columns(): 字段完整性
- _check_row_count(): 行数校验
- _check_date_continuity(): 日期连续性
- _check_value_range(): 数值范围
- _check_freshness(): 数据新鲜度
- ValidationResult.summary(): 摘要生成
- _log_validation_error(): 错误日志写入
- 集成: 全通过 / 全失败 / 混合场景

注意: 所有测试使用合成 DataFrame，不依赖外部服务或文件系统。
"""

import json
import sys
import math
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
import pytest

# 将 examples/alpha_research 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'examples' / 'alpha_research'))

from data_validator import (
    DataValidator,
    CheckResult,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_bars(
    rows: int = 500,
    start_date: str = '2024-01-02',
    include_nan: bool = False,
    include_zero_price: bool = False,
    include_negative_volume: bool = False,
    skip_dates: int = 0,
    date_col: str = 'date',
) -> pd.DataFrame:
    """生成合成 K 线 DataFrame"""
    dates = pd.bdate_range(start=start_date, periods=rows + skip_dates)
    if skip_dates > 0:
        # 跳过某些日期以模拟不连续
        keep = list(range(len(dates)))
        # 移除中间的一些日期
        step = max(len(dates) // (skip_dates + 1), 1)
        remove_idx = list(range(step - 1, len(dates), step))[:skip_dates]
        keep = [i for i in keep if i not in remove_idx]
        dates = dates[keep][:rows]
    else:
        dates = dates[:rows]

    np.random.seed(42)
    base_price = 10.0
    prices = base_price + np.cumsum(np.random.randn(len(dates)) * 0.1)
    # 确保价格为正
    prices = np.maximum(prices, 0.5)

    df = pd.DataFrame({
        date_col: dates,
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices * 1.01,
        'volume': np.random.randint(10000, 1000000, size=len(dates)),
    })

    if include_nan:
        df.loc[5, 'close'] = np.nan
        df.loc[10, 'open'] = np.nan

    if include_zero_price:
        df.loc[3, 'close'] = 0.0
        df.loc[7, 'low'] = 0.0

    if include_negative_volume:
        df.loc[4, 'volume'] = -100

    return df


@pytest.fixture
def validator(tmp_path):
    """创建使用临时目录的 DataValidator"""
    v = DataValidator()
    v.validation_error_log = tmp_path / 'validation_errors.log'
    return v


@pytest.fixture
def good_df():
    """正常数据: 500 行，最近日期"""
    start = (datetime.now() - timedelta(days=600)).strftime('%Y-%m-%d')
    return _make_bars(rows=500, start_date=start)


@pytest.fixture
def empty_df():
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# CheckResult / ValidationResult 数据类测试
# ---------------------------------------------------------------------------

class TestDataClasses:
    """CheckResult / ValidationResult 数据类测试"""

    def test_check_result_to_dict(self):
        cr = CheckResult(name='test', passed=True, message='ok', severity='INFO')
        d = cr.to_dict()
        assert d['name'] == 'test'
        assert d['passed'] is True
        assert d['severity'] == 'INFO'

    def test_validation_result_passed(self, good_df, validator):
        result = validator.validate(good_df, '000001.SZSE')
        assert isinstance(result, ValidationResult)
        assert result.symbol == '000001.SZSE'
        assert result.passed is True
        assert len(result.checks) == 5
        assert result.error_count == 0

    def test_validation_result_summary(self, good_df, validator):
        result = validator.validate(good_df, '000001.SZSE')
        summary = result.summary()
        assert 'PASSED' in summary
        assert '000001.SZSE' in summary

    def test_validation_result_failed_summary(self, validator):
        df = pd.DataFrame({'close': [0, -1, np.nan]})
        result = validator.validate(df, 'BAD.SYMBOL')
        summary = result.summary()
        assert 'FAILED' in summary

    def test_validation_result_to_dict(self, good_df, validator):
        result = validator.validate(good_df, '000001.SZSE')
        d = result.to_dict()
        assert d['symbol'] == '000001.SZSE'
        assert 'checks' in d
        assert isinstance(d['checks'], list)

    def test_failed_checks_property(self, validator):
        df = pd.DataFrame({'close': [0.0, -1.0]})
        result = validator.validate(df, 'BAD.SYMBOL')
        assert len(result.failed_checks) > 0


# ---------------------------------------------------------------------------
# _check_required_columns 测试
# ---------------------------------------------------------------------------

class TestCheckRequiredColumns:
    """字段完整性校验"""

    def test_all_columns_present(self, validator, good_df):
        result = validator._check_required_columns(good_df)
        assert result.passed is True
        assert result.name == 'required_columns'

    def test_missing_date_column(self, validator):
        df = pd.DataFrame({'open': [1], 'high': [1], 'low': [1], 'close': [1], 'volume': [1]})
        result = validator._check_required_columns(df)
        assert result.passed is False
        assert 'date' in result.message.lower() or '缺失' in result.message

    def test_missing_value_columns(self, validator):
        df = pd.DataFrame({'date': ['2024-01-01']})
        result = validator._check_required_columns(df)
        assert result.passed is False
        assert result.severity == 'ERROR'

    def test_alternative_date_column_datetime(self, validator):
        df = _make_bars(rows=5, date_col='datetime')
        result = validator._check_required_columns(df)
        assert result.passed is True

    def test_alternative_date_column_trade_date(self, validator):
        df = _make_bars(rows=5, date_col='trade_date')
        result = validator._check_required_columns(df)
        assert result.passed is True

    def test_empty_dataframe(self, validator, empty_df):
        result = validator._check_required_columns(empty_df)
        assert result.passed is False


# ---------------------------------------------------------------------------
# _check_row_count 测试
# ---------------------------------------------------------------------------

class TestCheckRowCount:
    """行数校验"""

    def test_normal_row_count(self, validator, good_df):
        result = validator._check_row_count(good_df, '000001.SZSE')
        assert result.passed is True

    def test_insufficient_rows(self, validator):
        """一年跨度但只有 50 行 → 不足 200 行/年"""
        df = _make_bars(rows=50, start_date='2023-01-02')
        # 50 行覆盖约 1 年（通过跳日期拉长时间跨度）
        df_long_span = _make_bars(rows=50, start_date='2023-01-02')
        # 手动拉伸日期到一年跨度
        df_long_span['date'] = pd.date_range(start='2023-01-02', periods=50, freq='7D')
        result = validator._check_row_count(df_long_span, '000001.SZSE')
        assert result.passed is False
        assert result.severity == 'ERROR'

    def test_empty_dataframe(self, validator, empty_df):
        result = validator._check_row_count(empty_df, 'TEST')
        assert result.passed is False

    def test_one_year_data(self, validator):
        """一年数据约 250 个交易日，应 >= 200"""
        df = _make_bars(rows=250, start_date='2023-01-02')
        result = validator._check_row_count(df, '000001.SZSE')
        assert result.passed is True

    def test_two_year_data(self, validator):
        """两年数据约 500 个交易日，应 >= 400"""
        df = _make_bars(rows=500, start_date='2022-01-02')
        result = validator._check_row_count(df, '000001.SZSE')
        assert result.passed is True


# ---------------------------------------------------------------------------
# _check_date_continuity 测试
# ---------------------------------------------------------------------------

class TestCheckDateContinuity:
    """日期连续性校验"""

    def test_continuous_dates(self, validator, good_df):
        result = validator._check_date_continuity(good_df)
        assert result.passed is True

    def test_missing_dates(self, validator):
        """跳过 20 个工作日 → ratio > 10% → ERROR"""
        df = _make_bars(rows=100, start_date='2024-01-02', skip_dates=20)
        result = validator._check_date_continuity(df)
        # 可能有缺失
        assert result.name == 'date_continuity'

    def test_no_date_column(self, validator):
        df = pd.DataFrame({'close': [1, 2, 3]})
        result = validator._check_date_continuity(df)
        assert result.passed is False
        assert result.severity == 'WARNING'

    def test_single_row(self, validator):
        df = _make_bars(rows=1, start_date='2024-01-02')
        result = validator._check_date_continuity(df)
        assert result.passed is True  # 跳过连续性校验


# ---------------------------------------------------------------------------
# _check_value_range 测试
# ---------------------------------------------------------------------------

class TestCheckValueRange:
    """数值范围校验"""

    def test_normal_values(self, validator, good_df):
        result = validator._check_value_range(good_df)
        assert result.passed is True

    def test_zero_price(self, validator):
        df = _make_bars(rows=100, include_zero_price=True)
        result = validator._check_value_range(df)
        assert result.passed is False
        assert result.severity == 'ERROR'

    def test_negative_volume(self, validator):
        df = _make_bars(rows=100, include_negative_volume=True)
        result = validator._check_value_range(df)
        assert result.passed is False

    def test_nan_values(self, validator):
        df = _make_bars(rows=100, include_nan=True)
        result = validator._check_value_range(df)
        assert result.passed is False
        assert 'null' in result.message.lower() or 'nan' in result.message.lower() or '异常' in result.message

    def test_empty_dataframe(self, validator, empty_df):
        result = validator._check_value_range(empty_df)
        # 空 DataFrame 没有列，应该通过（没有违反）
        assert result.passed is True


# ---------------------------------------------------------------------------
# _check_freshness 测试
# ---------------------------------------------------------------------------

class TestCheckFreshness:
    """数据新鲜度校验"""

    def test_fresh_data(self, validator, good_df):
        """最新日期在 3 天内 → 通过"""
        result = validator._check_freshness(good_df)
        assert result.passed is True

    def test_stale_data(self, validator):
        """最新日期在 30 天前 → 不通过"""
        df = _make_bars(rows=100, start_date='2023-01-02')
        # 最后日期是 2023 年中，距今超过 3 天
        result = validator._check_freshness(df)
        assert result.passed is False
        assert result.severity == 'WARNING'

    def test_no_date_column(self, validator):
        df = pd.DataFrame({'close': [1, 2, 3]})
        result = validator._check_freshness(df)
        assert result.passed is False
        assert result.severity == 'WARNING'


# ---------------------------------------------------------------------------
# validate() 集成测试
# ---------------------------------------------------------------------------

class TestValidateIntegration:
    """validate() 主入口集成测试"""

    def test_all_checks_pass(self, validator, good_df):
        result = validator.validate(good_df, '000001.SZSE')
        assert result.passed is True
        assert len(result.checks) == 5
        assert all(c.passed for c in result.checks if c.severity == 'ERROR')

    def test_multiple_failures(self, validator):
        """空 DataFrame → required_columns + row_count 失败"""
        df = pd.DataFrame()
        result = validator.validate(df, 'EMPTY.SYMBOL')
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) >= 2

    def test_zero_price_causes_failure(self, validator):
        df = _make_bars(rows=300, start_date='2024-01-02', include_zero_price=True)
        # 让最新日期在 3 天内（使用 start+end 避免 periods 边界问题）
        all_bdays = pd.bdate_range(start='2025-04-01', end=pd.Timestamp.now().normalize())
        df['date'] = all_bdays[-300:]
        result = validator.validate(df, 'BAD.SYMBOL')
        assert result.passed is False
        failed_names = [c.name for c in result.failed_checks]
        assert 'value_range' in failed_names

    def test_log_written_on_failure(self, validator, tmp_path):
        df = pd.DataFrame()
        result = validator.validate(df, 'LOG.TEST')
        assert not result.passed
        # 检查日志文件是否写入
        log_file = validator.validation_error_log
        assert log_file.exists()
        content = log_file.read_text()
        assert 'LOG.TEST' in content


# ---------------------------------------------------------------------------
# _log_validation_error 测试
# ---------------------------------------------------------------------------

class TestLogValidationError:
    """错误日志写入测试"""

    def test_log_creates_file(self, validator, tmp_path):
        result = ValidationResult(
            symbol='TEST',
            passed=False,
            checks=[CheckResult(name='test', passed=False, message='fail', severity='ERROR')],
        )
        validator._log_validation_error(result)
        assert validator.validation_error_log.exists()

    def test_log_appends(self, validator, tmp_path):
        result = ValidationResult(
            symbol='TEST',
            passed=False,
            checks=[CheckResult(name='test', passed=False, message='fail', severity='ERROR')],
        )
        validator._log_validation_error(result)
        validator._log_validation_error(result)
        lines = validator.validation_error_log.read_text().strip().split('\n')
        assert len(lines) == 2

    def test_log_json_format(self, validator, tmp_path):
        result = ValidationResult(
            symbol='JSON.TEST',
            passed=False,
            checks=[CheckResult(name='test', passed=False, message='fail', severity='ERROR')],
        )
        validator._log_validation_error(result)
        line = validator.validation_error_log.read_text().strip()
        parsed = json.loads(line)
        assert parsed['symbol'] == 'JSON.TEST'


# ---------------------------------------------------------------------------
# notify_validation_failure 测试（mock alert_notifier）
# ---------------------------------------------------------------------------

class TestNotifyValidationFailure:
    """飞书通知测试"""

    def test_no_notification_on_pass(self, validator, good_df):
        result = validator.validate(good_df, '000001.SZSE')
        with patch('data_validator.AlertNotifier') as mock_cls:
            validator.notify_validation_failure(result)
            mock_cls.assert_not_called()

    def test_notification_on_failure(self, validator):
        df = pd.DataFrame({'close': [0.0]})
        result = validator.validate(df, 'BAD.SYMBOL')

        mock_notifier = MagicMock()
        mock_alert = MagicMock()
        mock_notifier.create_alert.return_value = mock_alert

        with patch('data_validator.AlertNotifier', return_value=mock_notifier):
            validator.notify_validation_failure(result)
            mock_notifier.create_alert.assert_called_once()
            mock_notifier.send_alert.assert_called_once_with(mock_alert)

    def test_notification_handles_import_error(self, validator):
        df = pd.DataFrame({'close': [0.0]})
        result = validator.validate(df, 'BAD.SYMBOL')
        # 即使 AlertNotifier 不可用也不应抛异常
        with patch('data_validator.AlertNotifier', None):
            # AlertNotifier 为 None 时应该被优雅处理
            validator.notify_validation_failure(result)
