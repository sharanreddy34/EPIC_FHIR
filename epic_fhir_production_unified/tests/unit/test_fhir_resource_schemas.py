"""
Unit tests for the FHIR resource schemas integration module.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.resource import Resource

from epic_fhir_integration.schemas.fhir_resource_schemas import (
    get_schema_for_resource,
    get_fallback_paths,
    extract_field_from_model,
    resource_model_to_dict,
    create_model_from_dict,
)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PATIENT_PATH = FIXTURES_DIR / "sample_patient.json"
SAMPLE_OBSERVATION_PATH = FIXTURES_DIR / "sample_observation.json"

def load_fixture(file_path: Path) -> Dict[str, Any]:
    """Load a fixture file."""
    with open(file_path, "r") as f:
        return json.load(f)

class TestFhirResourceSchemas:
    """Tests for the FHIR resource schemas integration module."""
    
    def test_get_schema_for_resource(self):
        """Test getting a schema for a resource type."""
        # Get schema for a known resource type
        patient_schema = get_schema_for_resource("Patient")
        
        # Verify schema has expected properties
        assert "resourceType" in patient_schema
        assert "id" in patient_schema
        assert "name" in patient_schema
        assert "gender" in patient_schema
        
        # Test with an unknown resource type
        with pytest.raises(ValueError):
            get_schema_for_resource("UnknownResource")
    
    def test_get_fallback_paths(self):
        """Test getting fallback paths for fields."""
        # Get fallback paths for a known field
        patient_name_paths = get_fallback_paths("Patient", "name.family")
        
        # Verify paths
        assert len(patient_name_paths) > 0
        assert "name[0].family" in patient_name_paths
        
        # Test with a non-existent field
        single_path = get_fallback_paths("Patient", "non_existent_field")
        assert len(single_path) == 1
        assert single_path[0] == "non_existent_field"
    
    def test_extract_field_from_model(self):
        """Test extracting fields from a resource model."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Create a model
        patient = Patient.model_validate(patient_data)
        
        # Extract fields
        patient_id = extract_field_from_model(patient, "id")
        assert patient_id == patient_data["id"]
        
        family_name = extract_field_from_model(patient, "name.family")
        assert family_name == patient_data["name"][0]["family"]
        
        # Test with non-existent field
        non_existent = extract_field_from_model(patient, "non_existent_field")
        assert non_existent is None
    
    def test_resource_model_to_dict(self):
        """Test converting a resource model to a dictionary."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Create a model
        patient = Patient.model_validate(patient_data)
        
        # Convert to dictionary using schema
        patient_dict = resource_model_to_dict(patient)
        
        # Verify dictionary has essential fields
        assert patient_dict["resourceType"] == "Patient"
        assert patient_dict["id"] == patient_data["id"]
        
        # Test with a schema
        schema = {"resourceType": {}, "id": {}, "gender": {}}
        minimal_dict = resource_model_to_dict(patient, schema)
        assert set(minimal_dict.keys()).issubset({"resourceType", "id", "gender"})
    
    def test_create_model_from_dict(self):
        """Test creating a resource model from a dictionary."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Create model
        patient = create_model_from_dict(patient_data)
        
        # Verify model
        assert patient is not None
        assert isinstance(patient, Patient)
        assert patient.id == patient_data["id"]
        
        # Test with invalid data
        invalid_data = {"resourceType": "Patient", "gender": "invalid-gender"}
        invalid_model = create_model_from_dict(invalid_data)
        assert invalid_model is not None  # Should still create with validation warnings
        
        # Test with completely invalid data
        very_invalid_data = {"resourceType": "NonExistentType"}
        very_invalid_model = create_model_from_dict(very_invalid_data)
        assert very_invalid_model is None 