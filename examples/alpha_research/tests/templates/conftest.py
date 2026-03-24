"""Pytest configuration file for test fixtures and hooks"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = Path(tempfile.mkdtemp(prefix="alpha_research_test_"))
    yield temp_dir
    # Cleanup after all tests in session are done
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config(test_data_dir):
    """Provide a mock configuration for testing"""
    config_path = test_data_dir / "test_config.json"
    config_data = {
        "api_endpoint": "http://localhost:8000",
        "timeout": 30,
        "retries": 3
    }
    import json
    with open(config_path, 'w') as f:
        json.dump(config_data, f)
    return config_path


@pytest.fixture
def sample_market_data():
    """Provide sample market data for testing"""
    return {
        "symbol": "AAPL",
        "price": 150.00,
        "volume": 1000000,
        "timestamp": "2023-01-01T10:00:00Z"
    }


@pytest.fixture
def mock_api_client():
    """Mock API client for testing without external dependencies"""
    from unittest.mock import Mock
    mock_client = Mock()
    mock_client.get.return_value = {"status": "success", "data": {}}
    mock_client.post.return_value = {"status": "created", "id": "test_id"}
    return mock_client


def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)
