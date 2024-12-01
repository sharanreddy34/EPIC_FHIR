"""
Pytest configuration for Epic FHIR Integration tests.
This module provides shared fixtures for all tests.
"""

import os
import pytest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    data_path = os.environ.get("EPIC_TEST_DATA_PATH", "test_data")
    return Path(data_path)

@pytest.fixture(scope="session")
def test_output_dir():
    """Return the path to the test output directory."""
    output_path = os.environ.get("TEST_OUTPUT_DIR", "test_output")
    return Path(output_path)

@pytest.fixture(scope="session")
def use_api():
    """Determine if tests should use the live API or local data."""
    return os.environ.get("RUN_LIVE_API_TESTS", "").lower() in ("true", "1", "yes") 