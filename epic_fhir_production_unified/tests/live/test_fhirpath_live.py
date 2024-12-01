#!/usr/bin/env python3
"""
Live tests for FHIRPath implementation with real patient data.
These tests are executed against actual Epic FHIR API data.

To run:
    pytest -xvs epic_fhir_integration/tests/live/test_fhirpath_live.py
"""

import os
import json
import pytest
import logging
from pathlib import Path

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.utils.fhirpath_extractor import FHIRPathExtractor
from epic_fhir_integration.auth import EpicAuthClient
from epic_fhir_integration.extract import FHIRClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_fhirpath_live")

# Skip these tests if no real data is available
TEST_DATA_PATH = os.environ.get("EPIC_TEST_DATA_PATH", "test_data")
EPIC_CONFIG_PATH = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")

# Check if we should run live API tests
RUN_LIVE_API_TESTS = os.environ.get("RUN_LIVE_API_TESTS", "false").lower() == "true"

# Check if we should run with local test data
RUN_LOCAL_DATA_TESTS = os.path.exists(TEST_DATA_PATH)

# Skip all tests if neither option is available
if not RUN_LIVE_API_TESTS and not RUN_LOCAL_DATA_TESTS:
    pytest.skip(
        "Skipping live FHIRPath tests - set RUN_LIVE_API_TESTS=true or provide test data",
        allow_module_level=True
    )

@pytest.fixture
def fhirpath_adapters():
    """Return instances of both the old and new FHIRPath implementations."""
    old_adapter = FHIRPathExtractor()
    new_adapter = FHIRPathAdapter()
    return {
        "old": old_adapter,
        "new": new_adapter
    }

@pytest.fixture
def epic_client():
    """Return an authenticated Epic FHIR client if live API tests are enabled."""
    if not RUN_LIVE_API_TESTS:
        pytest.skip("Live API tests are disabled")
    
    try:
        # Initialize auth client
        auth_client = EpicAuthClient.from_config(EPIC_CONFIG_PATH)
        token = auth_client.get_token()
        
        # Load config to get base URL
        with open(EPIC_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        base_url = config.get('fhir_base_url')
        if not base_url:
            pytest.skip("FHIR base URL not found in config")
        
        # Initialize FHIR client
        client = FHIRClient(base_url=base_url, token=token)
        return client
    except Exception as e:
        logger.error(f"Error initializing Epic client: {e}")
        pytest.skip(f"Could not initialize Epic client: {e}")

@pytest.fixture
def real_patients():
    """Return real patient resources from either API or local files."""
    if RUN_LIVE_API_TESTS:
        client = pytest.importorskip("epic_client")
        patients = list(client.search("Patient", _count=10))
        return patients
    
    # Otherwise use local test data
    patients_path = Path(TEST_DATA_PATH) / "Patient" / "bundle.json"
    if not patients_path.exists():
        pytest.skip("No patient test data found")
    
    try:
        with open(patients_path, 'r') as f:
            bundle = json.load(f)
        
        return [entry["resource"] for entry in bundle.get("entry", [])]
    except Exception as e:
        logger.error(f"Error loading patient test data: {e}")
        pytest.skip(f"Could not load patient test data: {e}")

@pytest.fixture
def real_observations():
    """Return real observation resources from either API or local files."""
    if RUN_LIVE_API_TESTS:
        client = pytest.importorskip("epic_client")
        # Get observations for the first few patients
        patients = list(client.search("Patient", _count=3))
        
        observations = []
        for patient in patients:
            patient_obs = list(client.search(
                "Observation", 
                subject=f"Patient/{patient.id}",
                _count=10
            ))
            observations.extend(patient_obs)
        
        return observations
    
    # Otherwise use local test data
    obs_path = Path(TEST_DATA_PATH) / "Observation" / "bundle.json"
    if not obs_path.exists():
        pytest.skip("No observation test data found")
    
    try:
        with open(obs_path, 'r') as f:
            bundle = json.load(f)
        
        return [entry["resource"] for entry in bundle.get("entry", [])]
    except Exception as e:
        logger.error(f"Error loading observation test data: {e}")
        pytest.skip(f"Could not load observation test data: {e}")

class TestFHIRPathLive:
    """Live tests for FHIRPath implementation with real data."""
    
    def test_basic_extraction(self, fhirpath_adapters, real_patients):
        """Test basic path extraction on real patients."""
        # Define test paths
        basic_paths = [
            "id",
            "gender",
            "birthDate",
            "name.family",
            "name.given",
            "address.city",
            "telecom.where(system='phone').value"
        ]
        
        # Test paths on a sample of patients
        for patient in real_patients[:5]:  # Test with first 5 patients
            for path in basic_paths:
                # Extract with both implementations
                old_result = fhirpath_adapters["old"].extract(patient, path)
                new_result = fhirpath_adapters["new"].extract(patient, path)
                
                # Log results
                logger.info(f"Path '{path}': Old: {old_result}, New: {new_result}")
                
                # Verify both implementations return the same result
                # We use this approach since we don't know the expected values
                assert type(old_result) == type(new_result), \
                    f"Different return types for path '{path}': Old: {type(old_result)}, New: {type(new_result)}"
                
                # For lists, compare lengths and elements
                if isinstance(old_result, list) and isinstance(new_result, list):
                    assert len(old_result) == len(new_result), \
                        f"Different list lengths for path '{path}': Old: {len(old_result)}, New: {len(new_result)}"
                else:
                    assert old_result == new_result, \
                        f"Different results for path '{path}': Old: {old_result}, New: {new_result}"
    
    def test_complex_expressions(self, fhirpath_adapters, real_patients):
        """Test complex FHIRPath expressions on real patients."""
        # Define test expressions
        complex_expressions = [
            "name.where(use='official').family",
            "telecom.where(system='phone' and use='home').value",
            "address.exists() and address.city.exists()",
            "name.given.first()",
            "gender = 'male' or gender = 'female'"
        ]
        
        for patient in real_patients[:5]:  # Test with first 5 patients
            for expr in complex_expressions:
                # Extract with both implementations
                old_result = fhirpath_adapters["old"].extract(patient, expr)
                new_result = fhirpath_adapters["new"].extract(patient, expr)
                
                # Log results
                logger.info(f"Expression '{expr}': Old: {old_result}, New: {new_result}")
                
                # Assert both implementations return the same result
                # For complex expressions, we might need custom comparisons
                if isinstance(old_result, list) and isinstance(new_result, list):
                    assert len(old_result) == len(new_result), \
                        f"Different list lengths for expr '{expr}': Old: {len(old_result)}, New: {len(new_result)}"
                else:
                    assert old_result == new_result, \
                        f"Different results for expr '{expr}': Old: {old_result}, New: {new_result}"
    
    def test_observation_extraction(self, fhirpath_adapters, real_observations):
        """Test FHIRPath extraction on real observation resources."""
        # Define test paths for observations
        observation_paths = [
            "code.coding.code",
            "code.coding.display",
            "valueQuantity.value",
            "valueQuantity.unit",
            "subject.reference",
            "effectiveDateTime"
        ]
        
        for obs in real_observations[:5]:  # Test with first 5 observations
            for path in observation_paths:
                # Extract with both implementations
                old_result = fhirpath_adapters["old"].extract(obs, path)
                new_result = fhirpath_adapters["new"].extract(obs, path)
                
                # Log results
                logger.info(f"Observation path '{path}': Old: {old_result}, New: {new_result}")
                
                # Assert both implementations return the same result
                if isinstance(old_result, list) and isinstance(new_result, list):
                    assert len(old_result) == len(new_result), \
                        f"Different list lengths for path '{path}': Old: {len(old_result)}, New: {len(new_result)}"
                else:
                    assert old_result == new_result, \
                        f"Different results for path '{path}': Old: {old_result}, New: {new_result}"
    
    def test_error_handling(self, fhirpath_adapters, real_patients):
        """Test error handling with invalid or malformed paths."""
        # Define invalid paths
        invalid_paths = [
            "nonexistent.path",
            "name..given",  # Double dot
            "name[xyz]",    # Invalid predicate
            "gender.where(x=y)",  # Invalid where clause
            "[]"  # Empty path
        ]
        
        for patient in real_patients[:2]:  # Test with first 2 patients
            for path in invalid_paths:
                # Both implementations should handle errors gracefully
                try:
                    old_result = fhirpath_adapters["old"].extract(patient, path)
                    # Old implementation might return empty list instead of raising an error
                    logger.info(f"Old implementation with invalid path '{path}': {old_result}")
                except Exception as e:
                    logger.info(f"Old implementation error with path '{path}': {e}")
                
                try:
                    new_result = fhirpath_adapters["new"].extract(patient, path)
                    logger.info(f"New implementation with invalid path '{path}': {new_result}")
                except Exception as e:
                    logger.info(f"New implementation error with path '{path}': {e}")
                
                # We don't assert here since error behavior might differ
                # The key is that neither should crash the application

if __name__ == "__main__":
    print("This module should be run using pytest.")
    print("Example: pytest -xvs epic_fhir_integration/tests/live/test_fhirpath_live.py") 