"""
Common test fixtures and utilities for the FHIR pipeline tests.
"""

import os
import json
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
from pyspark.sql import SparkSession

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAMPLE_PATIENT_BUNDLE_PATH = os.path.join(TEST_DATA_DIR, "sample_patient_bundle.json")
SAMPLE_PRACTITIONER_BUNDLE_PATH = os.path.join(TEST_DATA_DIR, "sample_practitioner_bundle.json")

# Create a fixture for SparkSession
@pytest.fixture(scope="session")
def spark():
    """Create a SparkSession that can be used by all tests."""
    spark = SparkSession.builder \
        .appName("fhir-pipeline-tests") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()

@pytest.fixture(scope="function")
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture(scope="session")
def mock_config_env():
    """Mock the FHIR config environment variable."""
    config_dir = os.path.join(os.path.dirname(__file__), "..", "epic-fhir-integration", "fhir_pipeline", "config")
    with patch.dict(os.environ, {"FHIR_CONFIG_DIR": config_dir}):
        yield

@pytest.fixture
def sample_patient_bundle():
    """Load sample patient bundle for testing."""
    ensure_test_data_dir()
    if not os.path.exists(SAMPLE_PATIENT_BUNDLE_PATH):
        with open(SAMPLE_PATIENT_BUNDLE_PATH, 'w') as f:
            json.dump(create_sample_patient_bundle(), f)
    
    with open(SAMPLE_PATIENT_BUNDLE_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture
def sample_practitioner_bundle():
    """Load sample practitioner bundle for testing."""
    ensure_test_data_dir()
    if not os.path.exists(SAMPLE_PRACTITIONER_BUNDLE_PATH):
        with open(SAMPLE_PRACTITIONER_BUNDLE_PATH, 'w') as f:
            json.dump(create_sample_practitioner_bundle(), f)
    
    with open(SAMPLE_PRACTITIONER_BUNDLE_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client for testing."""
    with patch('fhir_pipeline.io.fhir_client.FHIRClient') as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Mock the get_bundle method to return sample bundles
        def mock_get_bundle(resource_type, **kwargs):
            if resource_type == "Patient":
                with open(SAMPLE_PATIENT_BUNDLE_PATH, 'r') as f:
                    return json.load(f)
            elif resource_type == "Practitioner":
                with open(SAMPLE_PRACTITIONER_BUNDLE_PATH, 'r') as f:
                    return json.load(f)
            return {"resourceType": "Bundle", "entry": []}
            
        client.get_bundle.side_effect = mock_get_bundle
        yield client

def ensure_test_data_dir():
    """Ensure the test data directory exists."""
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    return TEST_DATA_DIR

def create_sample_patient_bundle():
    """Create a sample patient bundle for testing."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "identifier": [{"system": "http://example.org/fhir/mrn", "value": "12345"}],
                    "name": [{"family": "Smith", "given": ["John"]}],
                    "gender": "male",
                    "birthDate": "1970-01-01"
                }
            }
        ]
    }

def create_sample_practitioner_bundle():
    """Create a sample practitioner bundle for testing."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {
                "resource": {
                    "resourceType": "Practitioner",
                    "id": "practitioner-1",
                    "identifier": [{"system": "http://example.org/fhir/npi", "value": "1234567890"}],
                    "name": [{"family": "Johnson", "given": ["Robert"]}],
                    "telecom": [{"system": "email", "value": "robert.johnson@example.org"}]
                }
            }
        ]
    } 