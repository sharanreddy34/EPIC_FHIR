"""
Unit tests for the Patient resource transformations using FHIR resource models.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from fhir.resources.patient import Patient

from epic_fhir_integration.transform.patient_transform import (
    calculate_age,
    extract_birth_date,
    extract_gender,
    extract_language,
    extract_patient_demographics,
    transform_patient_to_row,
    legacy_transform_patient,
)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PATIENT_PATH = FIXTURES_DIR / "sample_patient.json"

def load_fixture(file_path: Path) -> Dict[str, Any]:
    """Load a fixture file."""
    with open(file_path, "r") as f:
        return json.load(f)

class TestPatientTransform:
    """Tests for the Patient resource transformations."""
    
    def test_calculate_age(self):
        """Test calculating age from birth date."""
        # Test with a valid birth date
        # Note: This test may fail around birthdays, adjust as needed
        age = calculate_age("1990-01-01")
        assert isinstance(age, int)
        assert age > 30  # Valid as of 2024
        
        # Test with invalid birth date
        invalid_age = calculate_age("invalid-date")
        assert invalid_age is None
        
        # Test with None
        none_age = calculate_age(None)
        assert none_age is None
    
    def test_extract_birth_date(self):
        """Test extracting birth date from patient resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = Patient.model_validate(patient_data)
        
        # Extract birth date
        birth_date = extract_birth_date(patient)
        assert birth_date is not None
        assert birth_date == patient_data["birthDate"]
        
        # Test with a dateTime format (add T to the fixture data)
        if patient.birthDate:
            original_date = patient.birthDate
            patient_with_datetime = Patient.model_validate(patient_data)
            setattr(patient_with_datetime, "birthDate", original_date + "T00:00:00Z")
            datetime_birth_date = extract_birth_date(patient_with_datetime)
            assert datetime_birth_date == original_date
    
    def test_extract_gender(self):
        """Test extracting gender from patient resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = Patient.model_validate(patient_data)
        
        # Extract gender
        gender = extract_gender(patient)
        assert gender is not None
        assert gender == patient_data["gender"]
    
    def test_extract_patient_demographics(self):
        """Test extracting demographics from patient resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = Patient.model_validate(patient_data)
        
        # Extract demographics
        demographics = extract_patient_demographics(patient)
        
        # Verify demographics
        assert demographics["patient_id"] == patient_data["id"]
        assert "name" in demographics
        assert "birth_date" in demographics
        assert "gender" in demographics
        assert "address" in demographics
        assert "contact_info" in demographics
    
    def test_transform_patient_to_row(self):
        """Test transforming patient resource to row format."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = Patient.model_validate(patient_data)
        
        # Transform to row
        row = transform_patient_to_row(patient)
        
        # Verify row
        assert "patient_id" in row
        assert row["patient_id"] == patient_data["id"]
        assert "gender" in row
        assert row["gender"] == patient_data["gender"]
        
        # Check flattened name fields
        assert "name_family" in row
        assert "name_given" in row
        
        # Check data quality fields
        assert "has_birth_date" in row
        assert "has_gender" in row
        assert "has_address" in row
        assert "has_contact" in row
    
    def test_legacy_transform_patient(self):
        """Test the legacy patient transformer with both model and dictionary inputs."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Test with dictionary input
        dict_row = legacy_transform_patient(patient_data)
        assert "patient_id" in dict_row
        assert dict_row["patient_id"] == patient_data["id"]
        
        # Test with model input
        patient = Patient.model_validate(patient_data)
        model_row = legacy_transform_patient(patient)
        assert "patient_id" in model_row
        assert model_row["patient_id"] == patient_data["id"]
        
        # Verify both produce the same results
        assert dict_row["patient_id"] == model_row["patient_id"]
        assert dict_row["gender"] == model_row["gender"] 