import pytest
import pandas as pd
from pathlib import Path
import json
import os

from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder, CohortBuilder
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PATIENTS_PATH = FIXTURES_DIR / "sample_patients.json"
SAMPLE_OBSERVATIONS_PATH = FIXTURES_DIR / "sample_observations.json"
SAMPLE_CONDITIONS_PATH = FIXTURES_DIR / "sample_conditions.json"

@pytest.fixture
def sample_resources():
    """Load sample FHIR resources for testing."""
    
    # Create fixtures directory if it doesn't exist
    if not FIXTURES_DIR.exists():
        FIXTURES_DIR.mkdir(parents=True)
    
    # Check if sample files exist, if not create them with minimal test data
    if not SAMPLE_PATIENTS_PATH.exists():
        patients = [
            Patient.construct(
                id="patient-1",
                gender="male",
                birthDate="1970-01-01"
            ).dict(),
            Patient.construct(
                id="patient-2",
                gender="female",
                birthDate="1980-01-01"
            ).dict()
        ]
        SAMPLE_PATIENTS_PATH.write_text(json.dumps(patients))
    
    if not SAMPLE_OBSERVATIONS_PATH.exists():
        observations = [
            Observation.construct(
                id="obs-1",
                status="final",
                code={"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Blood Pressure"}]},
                subject={"reference": "Patient/patient-1"},
                valueQuantity={"value": 120, "unit": "mmHg"},
                effectiveDateTime="2023-01-01"
            ).dict(),
            Observation.construct(
                id="obs-2",
                status="final",
                code={"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Blood Pressure"}]},
                subject={"reference": "Patient/patient-2"},
                valueQuantity={"value": 110, "unit": "mmHg"},
                effectiveDateTime="2023-01-01"
            ).dict()
        ]
        SAMPLE_OBSERVATIONS_PATH.write_text(json.dumps(observations))
    
    if not SAMPLE_CONDITIONS_PATH.exists():
        conditions = [
            Condition.construct(
                id="cond-1",
                subject={"reference": "Patient/patient-1"},
                code={"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertension"}]},
                onsetDateTime="2023-01-01"
            ).dict(),
            Condition.construct(
                id="cond-2",
                subject={"reference": "Patient/patient-2"},
                code={"coding": [{"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes"}]},
                onsetDateTime="2023-01-01"
            ).dict()
        ]
        SAMPLE_CONDITIONS_PATH.write_text(json.dumps(conditions))
    
    # Load the sample data
    patients = [Patient.parse_obj(p) for p in json.loads(SAMPLE_PATIENTS_PATH.read_text())]
    observations = [Observation.parse_obj(o) for o in json.loads(SAMPLE_OBSERVATIONS_PATH.read_text())]
    conditions = [Condition.parse_obj(c) for c in json.loads(SAMPLE_CONDITIONS_PATH.read_text())]
    
    return {
        "patients": patients,
        "observations": observations,
        "conditions": conditions
    }

class TestFHIRDataScience:
    """Integration tests for the FHIR data science module."""
    
    def test_dataset_builder(self, sample_resources):
        """Test creating a dataset from FHIR resources."""
        # Initialize the dataset builder
        builder = FHIRDatasetBuilder()
        
        # Add resources to the builder
        builder.add_resources("Patient", sample_resources["patients"])
        builder.add_resources("Observation", sample_resources["observations"])
        builder.add_resources("Condition", sample_resources["conditions"])
        
        # Build a basic dataset with patient demographics
        dataset = builder.build_dataset(
            index_by="Patient",
            columns=[
                {"path": "Patient.gender", "name": "gender"},
                {"path": "Patient.birthDate", "name": "birth_date"}
            ]
        )
        
        # Verify the dataset
        assert isinstance(dataset, pd.DataFrame)
        assert len(dataset) == 2  # Two patients
        assert "gender" in dataset.columns
        assert "birth_date" in dataset.columns
        
        # Test extracting values from observations
        obs_dataset = builder.build_dataset(
            index_by="Patient",
            columns=[
                {"resource": "Observation", "path": "valueQuantity.value", "code": "8480-6", "name": "bp_value"}
            ]
        )
        
        assert "bp_value" in obs_dataset.columns
        assert not obs_dataset["bp_value"].isna().all()
    
    def test_cohort_builder(self, sample_resources):
        """Test building patient cohorts."""
        # Initialize the cohort builder
        cohort_builder = CohortBuilder(
            patients=sample_resources["patients"],
            observations=sample_resources["observations"],
            conditions=sample_resources["conditions"]
        )
        
        # Build a cohort of patients with hypertension
        hypertension_cohort = cohort_builder.with_condition(
            system="http://snomed.info/sct",
            code="38341003"  # Hypertension
        ).get_patient_ids()
        
        assert len(hypertension_cohort) == 1
        assert "patient-1" in hypertension_cohort
        
        # Build a cohort of patients with BP > 110
        high_bp_cohort = cohort_builder.with_observation(
            system="http://loinc.org",
            code="8480-6",  # Blood Pressure
            value_comparison=lambda v: v > 110
        ).get_patient_ids()
        
        assert len(high_bp_cohort) == 1
        assert "patient-1" in high_bp_cohort
        
        # Test combining cohorts
        combined_cohort = cohort_builder.with_condition(
            system="http://snomed.info/sct",
            code="38341003"  # Hypertension
        ).with_observation(
            system="http://loinc.org",
            code="8480-6",  # Blood Pressure
            value_comparison=lambda v: v > 100
        ).get_patient_ids()
        
        assert len(combined_cohort) == 1
        assert "patient-1" in combined_cohort 