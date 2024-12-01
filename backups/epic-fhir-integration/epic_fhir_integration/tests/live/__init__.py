"""
Live tests for the Epic FHIR Integration package.

These tests are designed to be run against real Epic FHIR API data.
They can be configured to use either:
1. A live Epic FHIR API endpoint
2. Previously captured test data stored locally

Environment variables:
- RUN_LIVE_API_TESTS: Set to 'true' to run tests against a live API
- EPIC_TEST_DATA_PATH: Path to directory with test data
- EPIC_CONFIG_PATH: Path to Epic auth configuration file
"""

pytestmark = pytest.mark.live 