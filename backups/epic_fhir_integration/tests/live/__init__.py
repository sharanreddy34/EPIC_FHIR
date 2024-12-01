"""
Live testing module for Epic FHIR Integration.
These tests interact with real FHIR data, either through the API or locally stored data.
"""

import pytest

# Mark all tests in this directory as 'live' tests
pytestmark = pytest.mark.live 