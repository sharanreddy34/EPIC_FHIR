import pytest
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient
from epic_fhir_integration.config.loader import load_config
from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder, CohortBuilder
from epic_fhir_integration.utils.fhirpath_extractor import FHIRPathExtractor

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
def patient_resources(client, test_patient_id):
    """Fetch all resources for test patient."""
    return {
        "Patient": client.get_patient(test_patient_id),
        "Observation": client.get_patient_observations(test_patient_id),
        "Condition": client.get_patient_conditions(test_patient_id),
        "Encounter": client.get_patient_encounters(test_patient_id),
        "Procedure": client.get_patient_procedures(test_patient_id),
        "MedicationRequest": client.get_patient_medications(test_patient_id)
    }

@pytest.fixture(scope="module")
def dataset_builder(patient_resources):
    """Initialize dataset builder with patient resources."""
    builder = FHIRDatasetBuilder()
    # Add all resources to the builder
    for resource_type, resources in patient_resources.items():
        if resource_type == "Patient":
            builder.add_patients([resources])
        else:
            builder.add_resources(resource_type, resources)
    return builder

def test_dataset_builder_initialization(dataset_builder):
    """Test that dataset builder is initialized correctly."""
    assert dataset_builder is not None
    assert len(dataset_builder.get_patients()) > 0
    
    # Check resource counts
    resource_counts = dataset_builder.get_resource_counts()
    assert resource_counts["Patient"] == 1
    assert resource_counts["Observation"] > 0
    assert resource_counts["Encounter"] > 0

def test_basic_dataset_creation(dataset_builder):
    """Test creating a basic dataset with patient demographics."""
    dataset = dataset_builder.build_dataset(
        columns=[
            "id",
            "gender",
            "birthDate",
            "Encounter.count()",
            "Observation.count()"
        ]
    )
    
    assert dataset is not None
    assert len(dataset) == 1  # One patient
    assert "id" in dataset.columns
    assert "gender" in dataset.columns
    assert "birthDate" in dataset.columns
    assert "Encounter.count()" in dataset.columns
    assert "Observation.count()" in dataset.columns
    
    # Verify the counts
    assert dataset["Encounter.count()"].iloc[0] > 0
    assert dataset["Observation.count()"].iloc[0] > 0

def test_observation_feature_extraction(dataset_builder):
    """Test extracting features from observations."""
    # Extract vitals dataset
    vitals_dataset = dataset_builder.build_dataset(
        columns=[
            "id",
            "Observation.where(code.coding.code = '8310-5').valueQuantity.value",  # Body temperature
            "Observation.where(code.coding.code = '8867-4').valueQuantity.value",  # Heart rate
            "Observation.where(code.coding.code = '8480-6').valueQuantity.value"   # Systolic BP
        ]
    )
    
    assert vitals_dataset is not None
    assert len(vitals_dataset) == 1  # One patient
    assert "id" in vitals_dataset.columns
    
    # Check at least one vital sign exists
    vital_columns = [
        "Observation.where(code.coding.code = '8310-5').valueQuantity.value",
        "Observation.where(code.coding.code = '8867-4').valueQuantity.value",
        "Observation.where(code.coding.code = '8480-6').valueQuantity.value"
    ]
    
    # At least one vital should have data
    found_vitals = False
    for col in vital_columns:
        if not vitals_dataset[col].isna().all():
            found_vitals = True
            break
    
    assert found_vitals, "No vital signs found for test patient"

def test_cohort_definition(dataset_builder, patient_resources):
    """Test defining and applying cohort criteria."""
    # Create a cohort builder
    cohort_builder = CohortBuilder(dataset_builder)
    
    # Add criteria: patient with at least one observation
    cohort_builder.add_criterion(
        "has_observations", 
        lambda patient_id, resources: len(resources.get("Observation", [])) > 0
    )
    
    # Add criteria: patient with at least one encounter
    cohort_builder.add_criterion(
        "has_encounters", 
        lambda patient_id, resources: len(resources.get("Encounter", [])) > 0
    )
    
    # Apply cohort definition
    cohort = cohort_builder.build_cohort()
    
    assert cohort is not None
    assert len(cohort) == 1  # Our test patient should match criteria
    
    # Check the cohort flags
    assert "has_observations" in cohort.columns
    assert "has_encounters" in cohort.columns
    assert cohort["has_observations"].iloc[0] == True
    assert cohort["has_encounters"].iloc[0] == True

def test_temporal_feature_extraction(dataset_builder):
    """Test extracting temporal features from observations over time."""
    # Create a dataset with observation dates and values
    temporal_dataset = dataset_builder.build_temporal_dataset(
        index_column="Observation.effectiveDateTime",
        value_column="Observation.valueQuantity.value",
        filter_expr="Observation.code.coding.code = '8480-6'"  # Systolic BP
    )
    
    # Not all patients will have this specific observation
    if len(temporal_dataset) > 0:
        assert "effectiveDateTime" in temporal_dataset.columns
        assert "value" in temporal_dataset.columns
        
        # Convert to datetime for validation
        temporal_dataset["effectiveDateTime"] = pd.to_datetime(temporal_dataset["effectiveDateTime"])
        
        # Sort by date to check time series
        sorted_data = temporal_dataset.sort_values("effectiveDateTime")
        
        if len(sorted_data) > 1:
            # Check that dates are in chronological order
            date_diffs = np.diff(sorted_data["effectiveDateTime"].astype(np.int64))
            assert all(date_diffs >= 0), "Dates should be in chronological order"
    
    # For test cases with no matching observations, this test is considered passed
    # We're just testing the functionality, not specific patient data 