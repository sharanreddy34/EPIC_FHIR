import pytest
import os
import json
import logging
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime

from epic_fhir_integration.auth.jwt_auth import EpicJWTAuth
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient
from epic_fhir_integration.config.loader import load_config
from epic_fhir_integration.utils.fhirpath_extractor import FHIRPathExtractor
from epic_fhir_integration.analytics.pathling_service import PathlingService
from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder
from epic_fhir_integration.validation.validator import FHIRValidator

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def test_output_dir():
    """Create a test output directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"test_output/e2e_test_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

@pytest.fixture(scope="module")
def config():
    """Load configuration for testing."""
    config_path = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")
    return load_config(config_path)

@pytest.fixture(scope="module")
def auth(config):
    """Initialize auth manager."""
    return EpicJWTAuth(config)

@pytest.fixture(scope="module")
def client(config):
    """Initialize FHIR client."""
    return EpicFHIRClient(config)

@pytest.fixture(scope="module")
def test_patient_id():
    """Return the test patient ID."""
    return "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

def test_e2e_auth_extract_analyze(auth, client, test_patient_id, test_output_dir):
    """
    End-to-end test: Auth → Extract → Analyze
    
    This test simulates a complete workflow:
    1. Authenticate with Epic FHIR API
    2. Extract patient data
    3. Analyze data with FHIRPath
    4. Save results
    """
    # Step 1: Authenticate
    token = auth.get_access_token()
    assert token is not None
    assert "access_token" in token
    
    # Step 2: Extract patient data
    patient = client.get_patient(test_patient_id)
    assert patient is not None
    assert patient.get("resourceType") == "Patient"
    
    observations = client.get_patient_observations(test_patient_id)
    assert observations is not None
    assert len(observations) > 0
    
    # Step 3: Analyze with FHIRPath
    extractor = FHIRPathExtractor()
    
    # Extract patient demographics
    gender = extractor.extract_first(patient, "gender")
    birth_date = extractor.extract_first(patient, "birthDate")
    name = extractor.extract_first(patient, "name.where(use = 'official').given.first()")
    
    # Extract vital signs
    vital_signs = []
    for obs in observations:
        if extractor.exists(obs, "category.coding.where(code = 'vital-signs')"):
            code = extractor.extract_first(obs, "code.coding.code")
            display = extractor.extract_first(obs, "code.coding.display")
            value = extractor.extract_first(obs, "valueQuantity.value")
            unit = extractor.extract_first(obs, "valueQuantity.unit")
            date = extractor.extract_first(obs, "effectiveDateTime")
            
            if code and value:
                vital_signs.append({
                    "code": code,
                    "display": display,
                    "value": value,
                    "unit": unit,
                    "date": date
                })
    
    # Create results
    results = {
        "patient": {
            "id": test_patient_id,
            "gender": gender,
            "birthDate": birth_date,
            "name": name
        },
        "vitalSigns": vital_signs
    }
    
    # Step 4: Save results
    with open(test_output_dir / "auth_extract_analyze_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved results to {test_output_dir}/auth_extract_analyze_results.json")
    
    # Verify results
    assert results["patient"]["id"] == test_patient_id
    assert results["patient"]["gender"] is not None
    assert len(results["vitalSigns"]) > 0

def test_e2e_fhirpath_pathling(client, test_patient_id, test_output_dir):
    """
    End-to-end test: FHIRPath → Pathling pipeline
    
    This test simulates a workflow using FHIRPath to extract data and Pathling for analytics:
    1. Extract data with FHIRPath
    2. Process with Pathling
    3. Export analytics results
    """
    # Skip if not running in environment with Java
    try:
        # Simple check to see if Java is available
        import subprocess
        result = subprocess.run(["java", "-version"], capture_output=True)
        if result.returncode != 0:
            pytest.skip("Java not available, skipping Pathling test")
    except Exception:
        pytest.skip("Java check failed, skipping Pathling test")
    
    # Step 1: Extract patient data
    patient = client.get_patient(test_patient_id)
    observations = client.get_patient_observations(test_patient_id)
    conditions = client.get_patient_conditions(test_patient_id)
    
    # Use FHIRPath to extract key information
    extractor = FHIRPathExtractor()
    
    # Prepare data for Pathling
    temp_dir = tempfile.mkdtemp(prefix="pathling_e2e_")
    data_dir = Path(temp_dir)
    
    # Save patient
    with open(data_dir / "Patient.ndjson", "w") as f:
        json.dump(patient, f)
        f.write("\n")
    
    # Save observations
    with open(data_dir / "Observation.ndjson", "w") as f:
        for obs in observations:
            json.dump(obs, f)
            f.write("\n")
    
    # Save conditions
    with open(data_dir / "Condition.ndjson", "w") as f:
        for cond in conditions:
            json.dump(cond, f)
            f.write("\n")
    
    # Step 2: Initialize Pathling
    try:
        pathling = PathlingService(import_dir=str(data_dir))
        pathling.start()
        
        # Verify server is running
        assert pathling.is_running()
        
        # Step 3: Run analytics
        # Basic aggregation
        count_result = pathling.aggregate(
            resource_type="Patient",
            aggregations=["count()"]
        )
        assert count_result is not None
        assert count_result["count"] >= 1
        
        # Observation by type
        obs_result = pathling.aggregate(
            resource_type="Observation",
            aggregations=["count()"],
            group_by=["code.coding.code"]
        )
        assert obs_result is not None
        assert "count" in obs_result
        
        # Extract dataset
        dataset = pathling.extract_dataset(
            resource_type="Patient",
            columns=["id", "gender", "birthDate"]
        )
        assert dataset is not None
        assert len(dataset) >= 1
        
        # Save results
        count_result_path = test_output_dir / "pathling_patient_count.json"
        obs_result_path = test_output_dir / "pathling_obs_by_type.json"
        dataset_path = test_output_dir / "pathling_patient_dataset.csv"
        
        with open(count_result_path, "w") as f:
            json.dump(count_result, f, indent=2)
        
        with open(obs_result_path, "w") as f:
            json.dump(obs_result, f, indent=2)
        
        dataset.to_csv(dataset_path, index=False)
        
        logger.info(f"Saved Pathling results to {test_output_dir}")
    finally:
        # Clean up
        if 'pathling' in locals():
            pathling.stop()

def test_e2e_validation_dataset(client, test_patient_id, test_output_dir):
    """
    End-to-end test: Validation → Dataset creation
    
    This test simulates a workflow:
    1. Extract patient data
    2. Validate resources
    3. Create dataset from validated resources
    4. Save dataset for analysis
    """
    # Step 1: Extract patient data
    patient = client.get_patient(test_patient_id)
    observations = client.get_patient_observations(test_patient_id)
    conditions = client.get_patient_conditions(test_patient_id)
    
    # Step 2: Validate resources
    validator = FHIRValidator()
    
    # Validate patient
    patient_result = validator.validate(patient)
    assert not patient_result.has_fatal_errors()
    
    # Validate observations (up to 5)
    valid_observations = []
    for obs in observations[:5]:
        result = validator.validate(obs)
        if not result.has_fatal_errors():
            valid_observations.append(obs)
    
    # Validate conditions (up to 5)
    valid_conditions = []
    for cond in conditions[:5]:
        result = validator.validate(cond)
        if not result.has_fatal_errors():
            valid_conditions.append(cond)
    
    # Step 3: Create dataset from validated resources
    dataset_builder = FHIRDatasetBuilder()
    dataset_builder.add_patients([patient])
    dataset_builder.add_resources("Observation", valid_observations)
    dataset_builder.add_resources("Condition", valid_conditions)
    
    # Build dataset
    dataset = dataset_builder.build_dataset(
        columns=[
            "id",
            "gender",
            "birthDate",
            "Observation.count()",
            "Condition.count()"
        ]
    )
    
    assert dataset is not None
    assert len(dataset) == 1
    
    # Build observation dataset
    obs_dataset = dataset_builder.build_dataset(
        columns=[
            "id",
            "Observation.code.coding.code",
            "Observation.valueQuantity.value",
            "Observation.valueQuantity.unit",
            "Observation.effectiveDateTime"
        ],
        explode=True
    )
    
    # Step 4: Save datasets
    dataset_path = test_output_dir / "validated_patient_dataset.csv"
    obs_dataset_path = test_output_dir / "validated_observations_dataset.csv"
    
    dataset.to_csv(dataset_path, index=False)
    if len(obs_dataset) > 0:
        obs_dataset.to_csv(obs_dataset_path, index=False)
    
    # Create a validation report
    validation_report = {
        "patient": {
            "valid": not patient_result.has_fatal_errors(),
            "issues_count": len(patient_result.get_issues())
        },
        "observations": {
            "total": len(observations[:5]),
            "valid": len(valid_observations),
            "percentage_valid": len(valid_observations) / max(1, len(observations[:5])) * 100
        },
        "conditions": {
            "total": len(conditions[:5]),
            "valid": len(valid_conditions),
            "percentage_valid": len(valid_conditions) / max(1, len(conditions[:5])) * 100
        }
    }
    
    validation_path = test_output_dir / "validation_report.json"
    with open(validation_path, "w") as f:
        json.dump(validation_report, f, indent=2)
    
    logger.info(f"Saved validation dataset results to {test_output_dir}")
    
    # Assertions
    assert dataset["id"].iloc[0] == test_patient_id
    assert dataset["Observation.count()"].iloc[0] == len(valid_observations)
    assert dataset["Condition.count()"].iloc[0] == len(valid_conditions) 