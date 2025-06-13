import pytest
import os
import json
import logging
import tempfile
from pathlib import Path
from epic_fhir_integration.analytics.pathling_service import PathlingService
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient
from epic_fhir_integration.config.loader import load_config

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def config():
    """Load configuration for testing."""
    config_path = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")
    return load_config(config_path)

@pytest.fixture(scope="module")
def client(config):
    """Initialize FHIR client with test configuration."""
    return EpicFHIRClient(config)

@pytest.fixture(scope="module")
def test_patient_id():
    """Return the test patient ID."""
    return "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

@pytest.fixture(scope="module")
def test_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="pathling_test_")
    yield temp_dir
    # Cleanup not performed to allow inspection of test data
    logger.info(f"Test data saved in: {temp_dir}")

@pytest.fixture(scope="module")
def patient_data(client, test_patient_id, test_data_dir):
    """Fetch and save test patient data."""
    # Get patient data
    patient = client.get_patient(test_patient_id)
    observations = client.get_patient_observations(test_patient_id)
    conditions = client.get_patient_conditions(test_patient_id)
    encounters = client.get_patient_encounters(test_patient_id)
    
    # Save data for Pathling to import
    data_dir = Path(test_data_dir)
    
    with open(data_dir / "Patient.ndjson", "w") as f:
        json.dump(patient, f)
        f.write("\n")
    
    with open(data_dir / "Observation.ndjson", "w") as f:
        for obs in observations:
            json.dump(obs, f)
            f.write("\n")
    
    with open(data_dir / "Condition.ndjson", "w") as f:
        for cond in conditions:
            json.dump(cond, f)
            f.write("\n")
    
    with open(data_dir / "Encounter.ndjson", "w") as f:
        for enc in encounters:
            json.dump(enc, f)
            f.write("\n")
    
    return data_dir

@pytest.fixture(scope="module")
def pathling_service(test_data_dir):
    """Initialize and start Pathling service with test data."""
    service = PathlingService(import_dir=test_data_dir)
    service.start()
    yield service
    service.stop()

def test_pathling_server_start(pathling_service):
    """Test that Pathling server starts successfully."""
    assert pathling_service.is_running()
    assert pathling_service.get_server_url() is not None

def test_data_import(pathling_service, patient_data):
    """Test importing data into Pathling."""
    # Import was done during setup, verify resources are available
    resources = pathling_service.list_resources()
    assert "Patient" in resources
    assert "Observation" in resources
    assert "Condition" in resources
    assert "Encounter" in resources

def test_patient_count(pathling_service):
    """Test simple count aggregation."""
    result = pathling_service.aggregate(
        resource_type="Patient",
        aggregations=["count()"]
    )
    assert result is not None
    assert "count" in result
    assert result["count"] >= 1  # Should have at least our test patient

def test_observation_aggregation(pathling_service):
    """Test aggregation of observation values."""
    # Group observations by code
    result = pathling_service.aggregate(
        resource_type="Observation",
        aggregations=["count()"],
        group_by=["code.coding.code"]
    )
    assert result is not None
    assert "count" in result
    assert len(result["count"]) > 0
    assert "code.coding.code" in result
    
    # Verify we have some codes
    assert len(result["code.coding.code"]) > 0

def test_condition_filter(pathling_service):
    """Test filtering conditions by status."""
    # Get confirmed conditions
    result = pathling_service.aggregate(
        resource_type="Condition",
        aggregations=["count()"],
        filters=["verificationStatus.coding.code = 'confirmed'"]
    )
    assert result is not None
    assert "count" in result
    
    # Should have at least some conditions
    assert result["count"] >= 0

def test_dataset_extraction(pathling_service):
    """Test extracting a dataset from Pathling."""
    dataset = pathling_service.extract_dataset(
        resource_type="Patient",
        columns=["id", "gender", "birthDate"]
    )
    assert dataset is not None
    assert len(dataset) >= 1
    
    # Check columns
    assert "id" in dataset.columns
    assert "gender" in dataset.columns
    assert "birthDate" in dataset.columns

def test_measure_evaluation(pathling_service):
    """Test evaluating a clinical measure."""
    # Create a simple measure: patients with observations
    measure = {
        "population": "true",
        "numerator": "Observation.exists()"
    }
    
    result = pathling_service.evaluate_measure(measure)
    assert result is not None
    assert "population-count" in result
    assert "numerator-count" in result
    assert result["population-count"] >= 1
    assert result["numerator-count"] >= 0 